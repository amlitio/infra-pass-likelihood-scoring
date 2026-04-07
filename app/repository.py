"""SQLite-backed persistence for projects and score history."""

from __future__ import annotations

import csv
import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from io import StringIO
from typing import Iterator

from .config import Settings
from .schemas import (
    CsvImportRequest,
    CsvImportResponse,
    ProjectCreateRequest,
    ProjectDetail,
    ProjectSummary,
    ProjectUpdateRequest,
    ScoreRequest,
    ScoreRunRecord,
)
from .service import build_score_response


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class ProjectRepository:
    """Persistence gateway for Phase 1 product workflows."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self.database_path = settings.database_path

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        self.settings.data_dir.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        try:
            yield connection
            connection.commit()
        finally:
            connection.close()

    def init_db(self) -> None:
        with self.connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS projects (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project_id TEXT,
                    project_name TEXT NOT NULL,
                    sponsor_organization TEXT,
                    sector TEXT,
                    region TEXT,
                    notes TEXT,
                    procedural_stage INTEGER NOT NULL,
                    sponsor_strength INTEGER NOT NULL,
                    funding_clarity INTEGER NOT NULL,
                    route_specificity INTEGER NOT NULL,
                    need_case INTEGER NOT NULL,
                    row_tractability INTEGER NOT NULL,
                    local_plan_alignment INTEGER NOT NULL,
                    opposition_drag INTEGER NOT NULL,
                    land_monetization_fit INTEGER NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS score_runs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project_pk INTEGER NOT NULL,
                    score INTEGER NOT NULL,
                    interpretation TEXT NOT NULL,
                    breakdown_json TEXT NOT NULL,
                    utilization_json TEXT NOT NULL,
                    triggered_by TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (project_pk) REFERENCES projects(id)
                );

                CREATE TABLE IF NOT EXISTS imports (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    filename TEXT NOT NULL,
                    total_projects INTEGER NOT NULL,
                    created_projects INTEGER NOT NULL,
                    average_score REAL NOT NULL,
                    created_at TEXT NOT NULL
                );
                """
            )

    def _row_to_project_summary(self, row: sqlite3.Row, latest_run: sqlite3.Row) -> ProjectSummary:
        return ProjectSummary(
            id=row["id"],
            project_id=row["project_id"],
            project_name=row["project_name"],
            sponsor_organization=row["sponsor_organization"],
            sector=row["sector"],
            region=row["region"],
            notes=row["notes"],
            procedural_stage=row["procedural_stage"],
            sponsor_strength=row["sponsor_strength"],
            funding_clarity=row["funding_clarity"],
            route_specificity=row["route_specificity"],
            need_case=row["need_case"],
            row_tractability=row["row_tractability"],
            local_plan_alignment=row["local_plan_alignment"],
            opposition_drag=row["opposition_drag"],
            land_monetization_fit=row["land_monetization_fit"],
            latest_score=latest_run["score"],
            latest_interpretation=latest_run["interpretation"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    def _get_latest_run_row(self, conn: sqlite3.Connection, project_pk: int) -> sqlite3.Row:
        latest = conn.execute(
            """
            SELECT *
            FROM score_runs
            WHERE project_pk = ?
            ORDER BY id DESC
            LIMIT 1
            """,
            (project_pk,),
        ).fetchone()
        if latest is None:
            raise LookupError(f"missing score history for project {project_pk}")
        return latest

    def _score_and_insert_run(
        self,
        conn: sqlite3.Connection,
        project_pk: int,
        payload: ScoreRequest,
        triggered_by: str,
    ) -> None:
        score = build_score_response(payload)
        conn.execute(
            """
            INSERT INTO score_runs (
                project_pk, score, interpretation, breakdown_json,
                utilization_json, triggered_by, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                project_pk,
                score.score,
                score.interpretation,
                json.dumps(score.breakdown),
                json.dumps(score.utilization),
                triggered_by,
                utc_now(),
            ),
        )

    def create_project(self, payload: ProjectCreateRequest, triggered_by: str = "manual-create") -> ProjectDetail:
        now = utc_now()
        with self.connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO projects (
                    project_id, project_name, sponsor_organization, sector, region, notes,
                    procedural_stage, sponsor_strength, funding_clarity, route_specificity,
                    need_case, row_tractability, local_plan_alignment, opposition_drag,
                    land_monetization_fit, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    payload.project_id,
                    payload.project_name,
                    payload.sponsor_organization,
                    payload.sector,
                    payload.region,
                    payload.notes,
                    payload.procedural_stage,
                    payload.sponsor_strength,
                    payload.funding_clarity,
                    payload.route_specificity,
                    payload.need_case,
                    payload.row_tractability,
                    payload.local_plan_alignment,
                    payload.opposition_drag,
                    payload.land_monetization_fit,
                    now,
                    now,
                ),
            )
            project_pk = int(cursor.lastrowid)
            self._score_and_insert_run(conn, project_pk, payload, triggered_by)
        return self.get_project(project_pk)

    def update_project(self, project_pk: int, payload: ProjectUpdateRequest, triggered_by: str = "manual-update") -> ProjectDetail:
        now = utc_now()
        with self.connect() as conn:
            existing = conn.execute("SELECT id FROM projects WHERE id = ?", (project_pk,)).fetchone()
            if existing is None:
                raise LookupError(f"project {project_pk} not found")
            conn.execute(
                """
                UPDATE projects
                SET project_id = ?, project_name = ?, sponsor_organization = ?, sector = ?, region = ?, notes = ?,
                    procedural_stage = ?, sponsor_strength = ?, funding_clarity = ?, route_specificity = ?,
                    need_case = ?, row_tractability = ?, local_plan_alignment = ?, opposition_drag = ?,
                    land_monetization_fit = ?, updated_at = ?
                WHERE id = ?
                """,
                (
                    payload.project_id,
                    payload.project_name,
                    payload.sponsor_organization,
                    payload.sector,
                    payload.region,
                    payload.notes,
                    payload.procedural_stage,
                    payload.sponsor_strength,
                    payload.funding_clarity,
                    payload.route_specificity,
                    payload.need_case,
                    payload.row_tractability,
                    payload.local_plan_alignment,
                    payload.opposition_drag,
                    payload.land_monetization_fit,
                    now,
                    project_pk,
                ),
            )
            self._score_and_insert_run(conn, project_pk, payload, triggered_by)
        return self.get_project(project_pk)

    def rescore_project(self, project_pk: int, triggered_by: str = "manual-rescore") -> ProjectDetail:
        project = self.get_project(project_pk)
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
        with self.connect() as conn:
            self._score_and_insert_run(conn, project_pk, payload, triggered_by)
        return self.get_project(project_pk)

    def list_projects(self) -> list[ProjectSummary]:
        with self.connect() as conn:
            rows = conn.execute("SELECT * FROM projects ORDER BY updated_at DESC, id DESC").fetchall()
            projects: list[ProjectSummary] = []
            for row in rows:
                latest = self._get_latest_run_row(conn, int(row["id"]))
                projects.append(self._row_to_project_summary(row, latest))
            return projects

    def get_project(self, project_pk: int) -> ProjectDetail:
        with self.connect() as conn:
            row = conn.execute("SELECT * FROM projects WHERE id = ?", (project_pk,)).fetchone()
            if row is None:
                raise LookupError(f"project {project_pk} not found")
            latest = self._get_latest_run_row(conn, project_pk)
            history_rows = conn.execute(
                """
                SELECT * FROM score_runs
                WHERE project_pk = ?
                ORDER BY id DESC
                """,
                (project_pk,),
            ).fetchall()
            history = [
                ScoreRunRecord(
                    id=history_row["id"],
                    project_pk=history_row["project_pk"],
                    score=history_row["score"],
                    interpretation=history_row["interpretation"],
                    breakdown=json.loads(history_row["breakdown_json"]),
                    utilization=json.loads(history_row["utilization_json"]),
                    triggered_by=history_row["triggered_by"],
                    created_at=history_row["created_at"],
                )
                for history_row in history_rows
            ]
            summary = self._row_to_project_summary(row, latest)
            return ProjectDetail(
                **summary.model_dump(),
                latest_breakdown=json.loads(latest["breakdown_json"]),
                latest_utilization=json.loads(latest["utilization_json"]),
                score_history=history,
            )

    def get_portfolio_summary(self) -> dict[str, object]:
        projects = self.list_projects()
        if not projects:
            return {
                "total_projects": 0,
                "average_score": 0.0,
                "high_priority_projects": 0,
                "recent_scores": 0,
                "top_project": None,
            }
        scores = [project.latest_score for project in projects]
        top_project = max(projects, key=lambda item: item.latest_score)
        return {
            "total_projects": len(projects),
            "average_score": round(sum(scores) / len(scores), 2),
            "high_priority_projects": sum(1 for score in scores if score >= 70),
            "recent_scores": min(len(projects), 5),
            "top_project": top_project,
        }

    def import_csv(self, payload: CsvImportRequest) -> CsvImportResponse:
        reader = csv.DictReader(StringIO(payload.csv_content))
        rows = list(reader)
        if not rows:
            raise ValueError("CSV import did not include any data rows")

        projects: list[ProjectSummary] = []
        for row in rows:
            project = self.create_project(
                ProjectCreateRequest(
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
                triggered_by=payload.triggered_by or self.settings.default_batch_actor,
            )
            projects.append(
                ProjectSummary(
                    **project.model_dump(
                        exclude={"latest_breakdown", "latest_utilization", "score_history"}
                    )
                )
            )

        average_score = round(sum(project.latest_score for project in projects) / len(projects), 2)
        with self.connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO imports (filename, total_projects, created_projects, average_score, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (payload.filename, len(rows), len(projects), average_score, utc_now()),
            )
            import_id = int(cursor.lastrowid)
        return CsvImportResponse(
            import_id=import_id,
            filename=payload.filename,
            total_projects=len(rows),
            created_projects=len(projects),
            average_score=average_score,
            results=projects,
        )
