"""Persistence layer with SQLite and PostgreSQL support."""

from __future__ import annotations

import csv
import shutil
import sqlite3
from contextlib import contextmanager
from datetime import UTC, datetime
from io import StringIO
from pathlib import Path
from typing import Iterator

from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session, sessionmaker

from .auth import generate_access_token, hash_access_token, hash_password, token_expiry, utc_now, verify_password
from .config import Settings
from .models import AccessToken, Base, ImportJob, Organization, Project, ScoreRun, User
from .schemas import (
    AuthResponse,
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
    ScoreRequest,
    ScoreRunRecord,
    UserSummary,
)
from .service import build_score_response


def _slugify(name: str) -> str:
    candidate = "".join(ch.lower() if ch.isalnum() else "-" for ch in name).strip("-")
    while "--" in candidate:
        candidate = candidate.replace("--", "-")
    return candidate or "organization"


class ProjectRepository:
    """Persistence gateway for product workflows."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self._build_engine()

    def _build_engine(self) -> None:
        connect_args = {"check_same_thread": False} if self.settings.database_backend == "sqlite" else {}
        if self.settings.database_backend == "sqlite":
            self.settings.data_dir.mkdir(parents=True, exist_ok=True)
        self.engine = create_engine(self.settings.database_url, future=True, connect_args=connect_args)
        self.session_factory = sessionmaker(bind=self.engine, expire_on_commit=False, future=True)

    def _sqlite_db_path(self) -> Path:
        return Path(self.settings.database_url.removeprefix("sqlite:///"))

    def _is_legacy_sqlite_schema(self) -> bool:
        if self.settings.database_backend != "sqlite":
            return False
        db_path = self._sqlite_db_path()
        if not db_path.exists():
            return False
        with sqlite3.connect(db_path) as connection:
            tables = {
                row[0]
                for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                ).fetchall()
            }
            if "projects" not in tables:
                return False
            project_columns = {
                row[1] for row in connection.execute("PRAGMA table_info(projects)").fetchall()
            }
            if "organization_id" not in project_columns:
                return True
            if "score_runs" in tables:
                score_run_columns = {
                    row[1] for row in connection.execute("PRAGMA table_info(score_runs)").fetchall()
                }
                if "project_id" not in score_run_columns or "breakdown" not in score_run_columns:
                    return True
        return False

    def _reset_legacy_sqlite_db(self) -> None:
        db_path = self._sqlite_db_path()
        if not db_path.exists():
            return
        timestamp = datetime.now(UTC).strftime("%Y%m%d%H%M%S")
        backup_path = db_path.with_name(f"{db_path.stem}.legacy-{timestamp}{db_path.suffix}")
        self.engine.dispose()
        shutil.copy2(db_path, backup_path)
        db_path.unlink()
        self._build_engine()

    @contextmanager
    def session(self) -> Iterator[Session]:
        session = self.session_factory()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def init_db(self) -> None:
        if self._is_legacy_sqlite_schema():
            self._reset_legacy_sqlite_db()
        Base.metadata.create_all(self.engine)

    def _user_summary(self, user: User) -> UserSummary:
        return UserSummary(
            id=user.id,
            organization_id=user.organization_id,
            email=user.email,
            full_name=user.full_name,
            role=user.role,
            is_active=user.is_active,
            created_at=user.created_at.isoformat(),
        )

    def _organization_summary(self, session: Session, organization: Organization) -> OrganizationSummary:
        member_count = session.scalar(select(func.count()).select_from(User).where(User.organization_id == organization.id)) or 0
        project_count = session.scalar(select(func.count()).select_from(Project).where(Project.organization_id == organization.id)) or 0
        return OrganizationSummary(
            id=organization.id,
            name=organization.name,
            slug=organization.slug,
            created_at=organization.created_at.isoformat(),
            member_count=int(member_count),
            project_count=int(project_count),
        )

    def _latest_score_run(self, project: Project) -> ScoreRun:
        if not project.score_runs:
            raise LookupError(f"missing score history for project {project.id}")
        return max(project.score_runs, key=lambda run: run.id)

    def _project_summary(self, project: Project) -> ProjectSummary:
        latest = self._latest_score_run(project)
        return ProjectSummary(
            id=project.id,
            organization_id=project.organization_id,
            owner_user_id=project.owner_user_id,
            project_id=project.project_id,
            project_name=project.project_name,
            sponsor_organization=project.sponsor_organization,
            sector=project.sector,
            region=project.region,
            notes=project.notes,
            procedural_stage=project.procedural_stage,
            sponsor_strength=project.sponsor_strength,
            funding_clarity=project.funding_clarity,
            route_specificity=project.route_specificity,
            need_case=project.need_case,
            row_tractability=project.row_tractability,
            local_plan_alignment=project.local_plan_alignment,
            opposition_drag=project.opposition_drag,
            land_monetization_fit=project.land_monetization_fit,
            latest_score=latest.score,
            latest_interpretation=latest.interpretation,
            created_at=project.created_at.isoformat(),
            updated_at=project.updated_at.isoformat(),
        )

    def _project_detail(self, project: Project) -> ProjectDetail:
        latest = self._latest_score_run(project)
        history = [
            ScoreRunRecord(
                id=run.id,
                project_id=run.project_id,
                score=run.score,
                interpretation=run.interpretation,
                breakdown=run.breakdown,
                utilization=run.utilization,
                triggered_by=run.triggered_by,
                created_at=run.created_at.isoformat(),
            )
            for run in sorted(project.score_runs, key=lambda item: item.id, reverse=True)
        ]
        summary = self._project_summary(project)
        return ProjectDetail(
            **summary.model_dump(),
            latest_breakdown=latest.breakdown,
            latest_utilization=latest.utilization,
            score_history=history,
        )

    def _create_score_run(self, project: Project, payload: ScoreRequest, triggered_by: str) -> ScoreRun:
        score = build_score_response(payload)
        return ScoreRun(
            project=project,
            score=score.score,
            interpretation=score.interpretation,
            breakdown=score.breakdown,
            utilization=score.utilization,
            triggered_by=triggered_by,
            created_at=utc_now(),
        )

    def register(self, payload: RegisterRequest) -> AuthResponse:
        with self.session() as session:
            if session.scalar(select(User).where(User.email == payload.email)) is not None:
                raise ValueError("email is already registered")
            slug = payload.organization_slug or _slugify(payload.organization_name)
            if session.scalar(select(Organization).where(Organization.slug == slug)) is not None:
                raise ValueError("organization slug is already in use")
            organization = Organization(name=payload.organization_name, slug=slug)
            user = User(
                organization=organization,
                email=payload.email,
                full_name=payload.full_name,
                role="admin",
                password_hash=hash_password(payload.password),
                is_active=True,
            )
            session.add_all([organization, user])
            session.flush()
            token_value = generate_access_token()
            token = AccessToken(
                user=user,
                token_hash=hash_access_token(token_value),
                expires_at=token_expiry(self.settings.auth_token_ttl_hours),
            )
            session.add(token)
            session.flush()
            return AuthResponse(
                access_token=token_value,
                user=self._user_summary(user),
                organization=self._organization_summary(session, organization),
            )

    def login(self, payload: LoginRequest) -> AuthResponse:
        with self.session() as session:
            user = session.scalar(select(User).where(User.email == payload.email))
            if user is None or not verify_password(payload.password, user.password_hash):
                raise LookupError("invalid credentials")
            if not user.is_active:
                raise PermissionError("user is inactive")
            token_value = generate_access_token()
            session.add(
                AccessToken(
                    user=user,
                    token_hash=hash_access_token(token_value),
                    expires_at=token_expiry(self.settings.auth_token_ttl_hours),
                )
            )
            session.flush()
            return AuthResponse(
                access_token=token_value,
                user=self._user_summary(user),
                organization=self._organization_summary(session, user.organization),
            )

    def authenticate_token(self, token: str) -> User:
        with self.session() as session:
            token_row = session.scalar(
                select(AccessToken).where(AccessToken.token_hash == hash_access_token(token))
            )
            if token_row is None or token_row.expires_at <= utc_now():
                raise LookupError("invalid or expired token")
            user = token_row.user
            if not user.is_active:
                raise PermissionError("user is inactive")
            session.expunge(user)
            return user

    def get_user(self, user_id: int) -> UserSummary:
        with self.session() as session:
            user = session.get(User, user_id)
            if user is None:
                raise LookupError("user not found")
            return self._user_summary(user)

    def get_organization(self, organization_id: int) -> OrganizationSummary:
        with self.session() as session:
            organization = session.get(Organization, organization_id)
            if organization is None:
                raise LookupError("organization not found")
            return self._organization_summary(session, organization)

    def create_member(self, organization_id: int, payload: OrganizationMemberCreateRequest) -> UserSummary:
        with self.session() as session:
            if session.scalar(select(User).where(User.email == payload.email)) is not None:
                raise ValueError("email is already registered")
            organization = session.get(Organization, organization_id)
            if organization is None:
                raise LookupError("organization not found")
            user = User(
                organization=organization,
                email=payload.email,
                full_name=payload.full_name,
                role=payload.role,
                password_hash=hash_password(payload.password),
                is_active=True,
            )
            session.add(user)
            session.flush()
            return self._user_summary(user)

    def list_members(self, organization_id: int) -> list[UserSummary]:
        with self.session() as session:
            users = session.scalars(
                select(User).where(User.organization_id == organization_id).order_by(User.created_at.asc())
            ).all()
            return [self._user_summary(user) for user in users]

    def create_project(self, organization_id: int, owner_user_id: int, payload: ProjectCreateRequest, triggered_by: str) -> ProjectDetail:
        with self.session() as session:
            project = Project(
                organization_id=organization_id,
                owner_user_id=owner_user_id,
                project_id=payload.project_id,
                project_name=payload.project_name,
                sponsor_organization=payload.sponsor_organization,
                sector=payload.sector,
                region=payload.region,
                notes=payload.notes,
                procedural_stage=payload.procedural_stage,
                sponsor_strength=payload.sponsor_strength,
                funding_clarity=payload.funding_clarity,
                route_specificity=payload.route_specificity,
                need_case=payload.need_case,
                row_tractability=payload.row_tractability,
                local_plan_alignment=payload.local_plan_alignment,
                opposition_drag=payload.opposition_drag,
                land_monetization_fit=payload.land_monetization_fit,
                created_at=utc_now(),
                updated_at=utc_now(),
            )
            session.add(project)
            session.flush()
            session.add(self._create_score_run(project, payload, triggered_by))
            session.flush()
            session.refresh(project)
            return self._project_detail(project)

    def update_project(self, organization_id: int, project_id: int, payload: ProjectUpdateRequest, triggered_by: str) -> ProjectDetail:
        with self.session() as session:
            project = session.get(Project, project_id)
            if project is None or project.organization_id != organization_id:
                raise LookupError(f"project {project_id} not found")
            for field in [
                "project_id",
                "project_name",
                "sponsor_organization",
                "sector",
                "region",
                "notes",
                "procedural_stage",
                "sponsor_strength",
                "funding_clarity",
                "route_specificity",
                "need_case",
                "row_tractability",
                "local_plan_alignment",
                "opposition_drag",
                "land_monetization_fit",
            ]:
                setattr(project, field, getattr(payload, field))
            project.updated_at = utc_now()
            session.add(self._create_score_run(project, payload, triggered_by))
            session.flush()
            session.refresh(project)
            return self._project_detail(project)

    def rescore_project(self, organization_id: int, project_id: int, triggered_by: str) -> ProjectDetail:
        with self.session() as session:
            project = session.get(Project, project_id)
            if project is None or project.organization_id != organization_id:
                raise LookupError(f"project {project_id} not found")
            payload = ProjectCreateRequest(
                project_id=project.project_id,
                project_name=project.project_name,
                sponsor_organization=project.sponsor_organization,
                sector=project.sector,
                region=project.region,
                notes=project.notes,
                procedural_stage=project.procedural_stage,
                sponsor_strength=project.sponsor_strength,
                funding_clarity=project.funding_clarity,
                route_specificity=project.route_specificity,
                need_case=project.need_case,
                row_tractability=project.row_tractability,
                local_plan_alignment=project.local_plan_alignment,
                opposition_drag=project.opposition_drag,
                land_monetization_fit=project.land_monetization_fit,
            )
            project.updated_at = utc_now()
            session.add(self._create_score_run(project, payload, triggered_by))
            session.flush()
            session.refresh(project)
            return self._project_detail(project)

    def list_projects(self, organization_id: int) -> list[ProjectSummary]:
        with self.session() as session:
            projects = session.scalars(
                select(Project).where(Project.organization_id == organization_id).order_by(Project.updated_at.desc(), Project.id.desc())
            ).all()
            return [self._project_summary(project) for project in projects]

    def get_project(self, organization_id: int, project_id: int) -> ProjectDetail:
        with self.session() as session:
            project = session.get(Project, project_id)
            if project is None or project.organization_id != organization_id:
                raise LookupError(f"project {project_id} not found")
            return self._project_detail(project)

    def get_portfolio_summary(self, organization_id: int) -> PortfolioSummary:
        projects = self.list_projects(organization_id)
        if not projects:
            return PortfolioSummary(total_projects=0, average_score=0.0, high_priority_projects=0, recent_scores=0, top_project=None)
        scores = [project.latest_score for project in projects]
        return PortfolioSummary(
            total_projects=len(projects),
            average_score=round(sum(scores) / len(scores), 2),
            high_priority_projects=sum(1 for score in scores if score >= 70),
            recent_scores=min(len(projects), 5),
            top_project=max(projects, key=lambda item: item.latest_score),
        )

    def import_csv(self, organization_id: int, owner_user_id: int, payload: CsvImportRequest, triggered_by: str) -> CsvImportResponse:
        reader = csv.DictReader(StringIO(payload.csv_content))
        rows = list(reader)
        if not rows:
            raise ValueError("CSV import did not include any data rows")
        results: list[ProjectSummary] = []
        for row in rows:
            project = self.create_project(
                organization_id=organization_id,
                owner_user_id=owner_user_id,
                payload=ProjectCreateRequest(
                    project_id=row.get("project_id") or None,
                    project_name=row["project_name"],
                    sponsor_organization=row.get("sponsor_organization") or None,
                    sector=row.get("sector") or None,
                    region=row.get("region") or None,
                    notes=row.get("notes") or None,
                    procedural_stage=int(row["procedural_stage"]),
                    sponsor_strength=int(row["sponsor_strength"]),
                    funding_clarity=int(row["funding_clarity"]),
                    route_specificity=int(row["route_specificity"]),
                    need_case=int(row["need_case"]),
                    row_tractability=int(row["row_tractability"]),
                    local_plan_alignment=int(row["local_plan_alignment"]),
                    opposition_drag=int(row["opposition_drag"]),
                    land_monetization_fit=int(row["land_monetization_fit"]),
                ),
                triggered_by=triggered_by,
            )
            results.append(ProjectSummary(**project.model_dump(exclude={"latest_breakdown", "latest_utilization", "score_history"})))
        average_score = round(sum(project.latest_score for project in results) / len(results), 2)
        with self.session() as session:
            job = ImportJob(
                organization_id=organization_id,
                filename=payload.filename,
                total_projects=len(rows),
                created_projects=len(results),
                average_score=average_score,
                created_at=utc_now(),
            )
            session.add(job)
            session.flush()
            return CsvImportResponse(
                import_id=job.id,
                filename=payload.filename,
                total_projects=len(rows),
                created_projects=len(results),
                average_score=average_score,
                results=results,
            )
