import json
import shutil
import sqlite3
import subprocess
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app
from scoring import ProjectSignals, interpret_score, project_signals_from_dict, score_breakdown, score_project


class ScoringTests(unittest.TestCase):
    def setUp(self):
        self.test_dir = Path(".test-output") / self._testMethodName
        shutil.rmtree(self.test_dir, ignore_errors=True)
        self.test_dir.mkdir(parents=True, exist_ok=True)
        settings = Settings(
            app_name="Test Platform",
            environment="test",
            version="test",
            data_dir=self.test_dir,
            database_url=f"sqlite:///{(self.test_dir / 'test.db').as_posix()}",
            allow_open_registration=True,
        )
        self.client = TestClient(create_app(settings))
        self.client.__enter__()

    def tearDown(self):
        self.client.app.state.repository.engine.dispose()
        self.client.__exit__(None, None, None)
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def register_org(self, organization_name="Atlas Infra", email="admin@example.com"):
        response = self.client.post(
            "/v1/auth/register",
            json={
                "organization_name": organization_name,
                "organization_slug": organization_name.lower().replace(" ", "-"),
                "email": email,
                "password": "supersecure",
                "full_name": "Admin User",
            },
        )
        self.assertEqual(response.status_code, 201)
        return response.json()

    def auth_headers(self, token):
        return {"Authorization": f"Bearer {token}"}

    def create_project(self, token, name="Capital Loop"):
        return self.client.post(
            "/v1/projects",
            headers=self.auth_headers(token),
            json={
                "project_name": name,
                "project_id": "P-1",
                "sponsor_organization": "Metro Works",
                "sector": "Rail",
                "region": "WA",
                "notes": "Initial review",
                "procedural_stage": 20,
                "sponsor_strength": 8,
                "funding_clarity": 10,
                "route_specificity": 8,
                "need_case": 10,
                "row_tractability": 7,
                "local_plan_alignment": 6,
                "opposition_drag": 2,
                "land_monetization_fit": 12,
            },
        )

    def test_score_formula_with_subtraction(self):
        signals = ProjectSignals(
            procedural_stage=25,
            sponsor_strength=10,
            funding_clarity=15,
            route_specificity=10,
            need_case=10,
            row_tractability=10,
            local_plan_alignment=8,
            opposition_drag=7,
            land_monetization_fit=19,
        )
        self.assertEqual(score_project(signals), 100)

    def test_breakdown_has_negative_drag(self):
        signals = ProjectSignals(1, 2, 3, 4, 5, 6, 7, 3, 9)
        breakdown = score_breakdown(signals)
        self.assertEqual(breakdown["opposition_drag"], -3)

    def test_interpret_bands(self):
        self.assertEqual(interpret_score(90), "very high probability / very actionable")
        self.assertEqual(interpret_score(80), "strong watchlist candidate")
        self.assertEqual(interpret_score(60), "speculative but worth targeted hunting")
        self.assertEqual(interpret_score(40), "mostly informational, not land-first actionable")

    def test_validation_bounds(self):
        with self.assertRaises(ValueError):
            score_project(
                ProjectSignals(
                    procedural_stage=26,
                    sponsor_strength=1,
                    funding_clarity=1,
                    route_specificity=1,
                    need_case=1,
                    row_tractability=1,
                    local_plan_alignment=1,
                    opposition_drag=1,
                    land_monetization_fit=1,
                )
            )

    def test_from_dict(self):
        payload = {
            "procedural_stage": 15,
            "sponsor_strength": 7,
            "funding_clarity": 8,
            "route_specificity": 9,
            "need_case": 9,
            "row_tractability": 5,
            "local_plan_alignment": 4,
            "opposition_drag": 2,
            "land_monetization_fit": 10,
        }
        signals = project_signals_from_dict(payload)
        self.assertIsInstance(signals, ProjectSignals)
        self.assertEqual(score_project(signals), 65)

    def test_cli_json_input(self):
        payload = {
            "procedural_stage": 20,
            "sponsor_strength": 8,
            "funding_clarity": 10,
            "route_specificity": 8,
            "need_case": 10,
            "row_tractability": 7,
            "local_plan_alignment": 6,
            "opposition_drag": 2,
            "land_monetization_fit": 12,
        }
        path = Path("cli-test-input.json")
        path.write_text(json.dumps(payload), encoding="utf-8")
        try:
            result = subprocess.run(
                ["python", "scoring.py", "--input-json", str(path)],
                text=True,
                capture_output=True,
                check=True,
            )
        finally:
            path.unlink(missing_ok=True)
        self.assertIn("Score: 79/100", result.stdout)

    def test_dashboard_served(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("Infrastructure Pass Likelihood Platform", response.text)

    def test_stateless_score_endpoint_remains_public(self):
        response = self.client.post(
            "/v1/score",
            json={
                "project_name": "North Corridor Expansion",
                "procedural_stage": 20,
                "sponsor_strength": 8,
                "funding_clarity": 10,
                "route_specificity": 8,
                "need_case": 10,
                "row_tractability": 7,
                "local_plan_alignment": 6,
                "opposition_drag": 2,
                "land_monetization_fit": 12,
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["score"], 79)

    def test_registration_login_and_profile(self):
        registered = self.register_org()
        login = self.client.post(
            "/v1/auth/login",
            json={"email": "admin@example.com", "password": "supersecure"},
        )
        self.assertEqual(login.status_code, 200)
        me = self.client.get("/v1/auth/me", headers=self.auth_headers(login.json()["access_token"]))
        self.assertEqual(me.status_code, 200)
        self.assertEqual(me.json()["email"], registered["user"]["email"])

    def test_protected_endpoints_require_auth(self):
        response = self.client.get("/v1/projects")
        self.assertEqual(response.status_code, 401)

    def test_project_creation_and_rescore_are_org_scoped(self):
        atlas = self.register_org("Atlas Infra", "atlas@example.com")
        other = self.register_org("Beacon Infra", "beacon@example.com")
        created = self.create_project(atlas["access_token"])
        self.assertEqual(created.status_code, 201)
        detail = self.client.post(
            f"/v1/projects/{created.json()['id']}/rescore",
            headers=self.auth_headers(atlas["access_token"]),
        )
        self.assertEqual(len(detail.json()["score_history"]), 2)
        hidden = self.client.get(
            f"/v1/projects/{created.json()['id']}",
            headers=self.auth_headers(other["access_token"]),
        )
        self.assertEqual(hidden.status_code, 404)

    def test_admin_can_add_member(self):
        registered = self.register_org()
        response = self.client.post(
            "/v1/organizations/me/users",
            headers=self.auth_headers(registered["access_token"]),
            json={
                "email": "analyst@example.com",
                "password": "teamsecure",
                "full_name": "Analyst User",
                "role": "analyst",
            },
        )
        self.assertEqual(response.status_code, 201)
        members = self.client.get(
            "/v1/organizations/me/users",
            headers=self.auth_headers(registered["access_token"]),
        )
        self.assertEqual(len(members.json()), 2)

    def test_csv_import_and_portfolio_summary(self):
        registered = self.register_org()
        response = self.client.post(
            "/v1/imports/csv",
            headers=self.auth_headers(registered["access_token"]),
            json={
                "filename": "import.csv",
                "csv_content": (
                    "project_id,project_name,sponsor_organization,sector,region,notes,"
                    "procedural_stage,sponsor_strength,funding_clarity,route_specificity,"
                    "need_case,row_tractability,local_plan_alignment,opposition_drag,"
                    "land_monetization_fit\n"
                    "P-401,North Reach,GridCo,Transmission,CA,Fast track,18,8,11,8,9,6,5,2,13\n"
                    "P-402,Delta Pump,Civic Water,Water,NV,Expansion,14,7,9,7,8,6,6,1,11\n"
                ),
            },
        )
        self.assertEqual(response.status_code, 201)
        portfolio = self.client.get(
            "/v1/portfolio",
            headers=self.auth_headers(registered["access_token"]),
        )
        self.assertEqual(portfolio.json()["total_projects"], 2)

    def test_health_reports_database_backend(self):
        response = self.client.get("/health/ready")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["database_backend"], "sqlite")

    def test_legacy_sqlite_db_is_backed_up_and_reset(self):
        self.client.app.state.repository.engine.dispose()
        self.client.__exit__(None, None, None)
        legacy_db = self.test_dir / "test.db"
        legacy_db.unlink(missing_ok=True)
        with sqlite3.connect(legacy_db) as connection:
            connection.executescript(
                """
                CREATE TABLE projects (
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
                """
            )
        settings = Settings(
            app_name="Test Platform",
            environment="test",
            version="test",
            data_dir=self.test_dir,
            database_url=f"sqlite:///{legacy_db.as_posix()}",
            allow_open_registration=True,
        )
        self.client = TestClient(create_app(settings))
        self.client.__enter__()
        response = self.client.post(
            "/v1/auth/register",
            json={
                "organization_name": "Reset Org",
                "organization_slug": "reset-org",
                "email": "reset@example.com",
                "password": "supersecure",
                "full_name": "Reset Admin",
            },
        )
        self.assertEqual(response.status_code, 201)
        backups = list(self.test_dir.glob("test.legacy-*.db"))
        self.assertTrue(backups)


if __name__ == "__main__":
    unittest.main()
