import unittest

from scoring import ProjectSignals, interpret_score, score_project


class ScoringTests(unittest.TestCase):
    def test_score_formula(self):
        signals = ProjectSignals(
            procedural_stage=25,
            sponsor_strength=10,
            funding_clarity=15,
            route_specificity=10,
            need_case=10,
            row_tractability=10,
            local_plan_alignment=8,
            opposition_drag=0,
            land_monetization_fit=12,
        )
        self.assertEqual(score_project(signals), 100)

    def test_interpret_bands(self):
        self.assertEqual(interpret_score(90), "very high probability / very actionable")
        self.assertEqual(interpret_score(80), "strong watchlist candidate")
        self.assertEqual(interpret_score(60), "speculative but worth targeted hunting")
        self.assertEqual(
            interpret_score(40),
            "mostly informational, not land-first actionable",
        )

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


if __name__ == "__main__":
    unittest.main()
