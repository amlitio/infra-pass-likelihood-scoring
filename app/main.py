"""FastAPI application entry point."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .config import Settings
from .repository import ProjectRepository
from .schemas import (
    BatchScoreRequest,
    BatchScoreResponse,
    CsvImportRequest,
    CsvImportResponse,
    PortfolioSummary,
    ProjectCreateRequest,
    ProjectDetail,
    ProjectSummary,
    ProjectUpdateRequest,
    ScoreRequest,
    ScoreResponse,
)
from .service import build_score_response
from .ui import STATIC_DIR


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings.from_env()
    repository = ProjectRepository(settings)

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        repository.init_db()
        yield

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
            "database_path": str(settings.database_path),
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
                "dashboard-ui",
            ],
        }

    @app.get("/v1/portfolio", response_model=PortfolioSummary)
    def portfolio_summary() -> PortfolioSummary:
        return PortfolioSummary(**repository.get_portfolio_summary())

    @app.get("/v1/projects", response_model=list[ProjectSummary])
    def list_projects() -> list[ProjectSummary]:
        return repository.list_projects()

    @app.get("/v1/projects/{project_pk}", response_model=ProjectDetail)
    def get_project(project_pk: int) -> ProjectDetail:
        try:
            return repository.get_project(project_pk)
        except LookupError as error:
            raise HTTPException(status_code=404, detail=str(error)) from error

    @app.post("/v1/projects", response_model=ProjectDetail, status_code=201)
    def create_project(payload: ProjectCreateRequest) -> ProjectDetail:
        return repository.create_project(payload)

    @app.put("/v1/projects/{project_pk}", response_model=ProjectDetail)
    def update_project(project_pk: int, payload: ProjectUpdateRequest) -> ProjectDetail:
        try:
            return repository.update_project(project_pk, payload)
        except LookupError as error:
            raise HTTPException(status_code=404, detail=str(error)) from error

    @app.post("/v1/projects/{project_pk}/rescore", response_model=ProjectDetail)
    def rescore_project(project_pk: int) -> ProjectDetail:
        try:
            return repository.rescore_project(project_pk)
        except LookupError as error:
            raise HTTPException(status_code=404, detail=str(error)) from error

    @app.post("/v1/imports/csv", response_model=CsvImportResponse, status_code=201)
    def import_csv(payload: CsvImportRequest) -> CsvImportResponse:
        try:
            return repository.import_csv(payload)
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
