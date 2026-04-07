import json
import subprocess
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app
from scoring import ProjectSignals, interpret_score, project_signals_from_dict, score_breakdown, score_project


class ScoringTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

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

    def test_health_endpoints(self):
        live = self.client.get("/health/live")
        ready = self.client.get("/health/ready")
        self.assertEqual(live.status_code, 200)
        self.assertEqual(live.json()["status"], "ok")
        self.assertEqual(ready.status_code, 200)
        self.assertEqual(ready.json()["status"], "ready")

    def test_single_score_endpoint(self):
        response = self.client.post(
            "/v1/score",
            json={
                "project_id": "P-100",
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
        body = response.json()
        self.assertEqual(body["score"], 79)
        self.assertEqual(body["project_id"], "P-100")
        self.assertIn("utilization", body)

    def test_batch_score_endpoint(self):
        response = self.client.post(
            "/v1/score/batch",
            json={
                "projects": [
                    {
                        "project_id": "P-1",
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
                    {
                        "project_id": "P-2",
                        "procedural_stage": 15,
                        "sponsor_strength": 7,
                        "funding_clarity": 8,
                        "route_specificity": 9,
                        "need_case": 9,
                        "row_tractability": 5,
                        "local_plan_alignment": 4,
                        "opposition_drag": 2,
                        "land_monetization_fit": 10,
                    },
                ]
            },
        )
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["total_projects"], 2)
        self.assertEqual(body["highest_score"], 79)
        self.assertEqual(body["lowest_score"], 65)
        self.assertEqual(body["average_score"], 72.0)


if __name__ == "__main__":
    unittest.main()
