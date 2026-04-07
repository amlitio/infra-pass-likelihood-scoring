"""FastAPI application entry point."""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import Depends, FastAPI, Header, HTTPException, Request, Response, status
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .config import Settings
from .models import User
from .repository import ProjectRepository
from .schemas import (
    AuthResponse,
    BatchScoreRequest,
    BatchScoreResponse,
    CsvImportRequest,
    CsvImportResponse,
    LoginRequest,
    OrganizationMemberCreateRequest,
    OrganizationSummary,
    PortfolioSummary,
    ProjectCreateRequest,
    ProjectDetail,
    ProjectSummary,
    ProjectUpdateRequest,
    RegisterRequest,
    RevokeSessionRequest,
    ScoreRequest,
    ScoreResponse,
    SessionSummary,
    UserSummary,
)
from .service import build_score_response
from .ui import STATIC_DIR


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings.from_env()
    repository = ProjectRepository(settings)

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        repository.init_db()
        try:
            yield
        finally:
            repository.engine.dispose()

    app = FastAPI(
        title=settings.app_name,
        version=settings.version,
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )
    app.state.settings = settings
    app.state.repository = repository
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

    def get_repository() -> ProjectRepository:
        return app.state.repository

    def set_session_cookie(response: Response, token: str) -> None:
        response.set_cookie(
            key=settings.session_cookie_name,
            value=token,
            httponly=True,
            secure=settings.session_cookie_secure,
            samesite="lax",
            max_age=settings.auth_token_ttl_hours * 3600,
            path="/",
        )

    def clear_session_cookie(response: Response) -> None:
        response.delete_cookie(key=settings.session_cookie_name, path="/")

    def resolve_token(request: Request, authorization: str | None) -> str:
        if authorization and authorization.lower().startswith("bearer "):
            return authorization.split(" ", 1)[1].strip()
        cookie_token = request.cookies.get(settings.session_cookie_name)
        if cookie_token:
            return cookie_token
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="missing session")

    def get_current_user(
        request: Request,
        authorization: Annotated[str | None, Header()] = None,
        repo: ProjectRepository = Depends(get_repository),
    ) -> User:
        token = resolve_token(request, authorization)
        try:
            return repo.authenticate_token(token)
        except (LookupError, PermissionError) as error:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(error)) from error

    def get_current_token(request: Request, authorization: Annotated[str | None, Header()] = None) -> str:
        return resolve_token(request, authorization)

    def require_admin(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role != "admin":
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="admin role required")
        return current_user

    @app.get("/", include_in_schema=False)
    def index() -> FileResponse:
        return FileResponse(STATIC_DIR / "index.html")

    @app.get("/health/live")
    def liveness() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/health/ready")
    def readiness() -> dict[str, str]:
        return {
            "status": "ready",
            "environment": settings.environment,
            "version": settings.version,
            "database_backend": settings.database_backend,
        }

    @app.get("/v1/metadata")
    def metadata() -> dict[str, object]:
        return {
            "application": settings.app_name,
            "environment": settings.environment,
            "version": settings.version,
            "capabilities": [
                "single-score",
                "batch-score",
                "project-registry",
                "score-history",
                "csv-import",
                "organization-auth",
                "managed-sessions",
                "postgresql-ready",
                "dashboard-ui",
            ],
        }

    @app.post("/v1/auth/register", response_model=AuthResponse, status_code=201)
    def register(
        payload: RegisterRequest,
        request: Request,
        response: Response,
        repo: ProjectRepository = Depends(get_repository),
    ) -> AuthResponse:
        if not settings.allow_open_registration:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="open registration is disabled")
        try:
            auth_response = repo.register(
                payload,
                user_agent=request.headers.get("user-agent"),
                ip_address=request.client.host if request.client else None,
            )
            set_session_cookie(response, auth_response.access_token)
            return auth_response
        except ValueError as error:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error

    @app.post("/v1/auth/login", response_model=AuthResponse)
    def login(
        payload: LoginRequest,
        request: Request,
        response: Response,
        repo: ProjectRepository = Depends(get_repository),
    ) -> AuthResponse:
        try:
            auth_response = repo.login(
                payload,
                user_agent=request.headers.get("user-agent"),
                ip_address=request.client.host if request.client else None,
            )
            set_session_cookie(response, auth_response.access_token)
            return auth_response
        except LookupError as error:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(error)) from error
        except PermissionError as error:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(error)) from error

    @app.post("/v1/auth/logout", status_code=204)
    def logout(
        token: str = Depends(get_current_token),
        repo: ProjectRepository = Depends(get_repository),
    ) -> Response:
        repo.revoke_token(token)
        response = Response(status_code=204)
        clear_session_cookie(response)
        return response

    @app.get("/v1/auth/me", response_model=UserSummary)
    def auth_me(
        current_user: User = Depends(get_current_user),
        repo: ProjectRepository = Depends(get_repository),
    ) -> UserSummary:
        return repo.get_user(current_user.id)

    @app.get("/v1/auth/sessions", response_model=list[SessionSummary])
    def auth_sessions(
        current_user: User = Depends(get_current_user),
        token: str = Depends(get_current_token),
        repo: ProjectRepository = Depends(get_repository),
    ) -> list[SessionSummary]:
        return repo.list_sessions(current_user.id, token)

    @app.post("/v1/auth/sessions/revoke", status_code=204)
    def revoke_session(
        payload: RevokeSessionRequest,
        current_user: User = Depends(get_current_user),
        repo: ProjectRepository = Depends(get_repository),
    ) -> Response:
        try:
            repo.revoke_session(current_user.id, payload)
            return Response(status_code=204)
        except LookupError as error:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error

    @app.get("/v1/organizations/me", response_model=OrganizationSummary)
    def organization_me(
        current_user: User = Depends(get_current_user),
        repo: ProjectRepository = Depends(get_repository),
    ) -> OrganizationSummary:
        return repo.get_organization(current_user.organization_id)

    @app.get("/v1/organizations/me/users", response_model=list[UserSummary])
    def list_members(
        current_user: User = Depends(get_current_user),
        repo: ProjectRepository = Depends(get_repository),
    ) -> list[UserSummary]:
        return repo.list_members(current_user.organization_id)

    @app.post("/v1/organizations/me/users", response_model=UserSummary, status_code=201)
    def create_member(
        payload: OrganizationMemberCreateRequest,
        current_user: User = Depends(require_admin),
        repo: ProjectRepository = Depends(get_repository),
    ) -> UserSummary:
        try:
            return repo.create_member(current_user.organization_id, payload)
        except ValueError as error:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error

    @app.get("/v1/portfolio", response_model=PortfolioSummary)
    def portfolio_summary(
        current_user: User = Depends(get_current_user),
        repo: ProjectRepository = Depends(get_repository),
    ) -> PortfolioSummary:
        return repo.get_portfolio_summary(current_user.organization_id)

    @app.get("/v1/projects", response_model=list[ProjectSummary])
    def list_projects(
        current_user: User = Depends(get_current_user),
        repo: ProjectRepository = Depends(get_repository),
    ) -> list[ProjectSummary]:
        return repo.list_projects(current_user.organization_id)

    @app.get("/v1/projects/{project_pk}", response_model=ProjectDetail)
    def get_project(
        project_pk: int,
        current_user: User = Depends(get_current_user),
        repo: ProjectRepository = Depends(get_repository),
    ) -> ProjectDetail:
        try:
            return repo.get_project(current_user.organization_id, project_pk)
        except LookupError as error:
            raise HTTPException(status_code=404, detail=str(error)) from error

    @app.post("/v1/projects", response_model=ProjectDetail, status_code=201)
    def create_project(
        payload: ProjectCreateRequest,
        current_user: User = Depends(get_current_user),
        repo: ProjectRepository = Depends(get_repository),
    ) -> ProjectDetail:
        return repo.create_project(current_user.organization_id, current_user.id, payload, current_user.email)

    @app.put("/v1/projects/{project_pk}", response_model=ProjectDetail)
    def update_project(
        project_pk: int,
        payload: ProjectUpdateRequest,
        current_user: User = Depends(get_current_user),
        repo: ProjectRepository = Depends(get_repository),
    ) -> ProjectDetail:
        try:
            return repo.update_project(current_user.organization_id, project_pk, payload, current_user.email)
        except LookupError as error:
            raise HTTPException(status_code=404, detail=str(error)) from error

    @app.post("/v1/projects/{project_pk}/rescore", response_model=ProjectDetail)
    def rescore_project(
        project_pk: int,
        current_user: User = Depends(get_current_user),
        repo: ProjectRepository = Depends(get_repository),
    ) -> ProjectDetail:
        try:
            return repo.rescore_project(current_user.organization_id, project_pk, current_user.email)
        except LookupError as error:
            raise HTTPException(status_code=404, detail=str(error)) from error

    @app.post("/v1/imports/csv", response_model=CsvImportResponse, status_code=201)
    def import_csv(
        payload: CsvImportRequest,
        current_user: User = Depends(get_current_user),
        repo: ProjectRepository = Depends(get_repository),
    ) -> CsvImportResponse:
        try:
            return repo.import_csv(
                current_user.organization_id,
                current_user.id,
                payload,
                payload.triggered_by or current_user.email or settings.default_batch_actor,
            )
        except (KeyError, ValueError) as error:
            raise HTTPException(status_code=400, detail=str(error)) from error

    @app.post("/v1/score", response_model=ScoreResponse)
    def score_endpoint(payload: ScoreRequest) -> ScoreResponse:
        return build_score_response(payload)

    @app.post("/v1/score/batch", response_model=BatchScoreResponse)
    def batch_score_endpoint(payload: BatchScoreRequest) -> BatchScoreResponse:
        results = [build_score_response(project) for project in payload.projects]
        scores = [result.score for result in results]
        return BatchScoreResponse(
            total_projects=len(results),
            average_score=round(sum(scores) / len(scores), 2),
            highest_score=max(scores),
            lowest_score=min(scores),
            results=results,
        )

    return app


app = create_app()
