"""Infrastructure proposal scoring utilities.

Implements a weighted `Pass-Likelihood + Land Relevance` model that scores
projects from 0 to 100 using category-level signals.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict


CATEGORY_MAXIMA: Dict[str, int] = {
    "procedural_stage": 25,
    "sponsor_strength": 10,
    "funding_clarity": 15,
    "route_specificity": 10,
    "need_case": 10,
    "row_tractability": 10,
    "local_plan_alignment": 8,
    "opposition_drag": 7,
    "land_monetization_fit": 19,
}


@dataclass(frozen=True)
class ProjectSignals:
    """Input signals for the scoring model.

    All values are integer points within their category bounds.
    Opposition drag is entered as a positive number from 0 to 7 and is
    subtracted from the final score.
    """

    procedural_stage: int
    sponsor_strength: int
    funding_clarity: int
    route_specificity: int
    need_case: int
    row_tractability: int
    local_plan_alignment: int
    opposition_drag: int
    land_monetization_fit: int

    def validate(self) -> None:
        """Validate category bounds."""

        values = {
            "procedural_stage": self.procedural_stage,
            "sponsor_strength": self.sponsor_strength,
            "funding_clarity": self.funding_clarity,
            "route_specificity": self.route_specificity,
            "need_case": self.need_case,
            "row_tractability": self.row_tractability,
            "local_plan_alignment": self.local_plan_alignment,
            "opposition_drag": self.opposition_drag,
            "land_monetization_fit": self.land_monetization_fit,
        }

        for name, value in values.items():
            max_score = CATEGORY_MAXIMA[name]
            if not isinstance(value, int):
                raise TypeError(f"{name} must be an integer, got {type(value).__name__}")
            if value < 0 or value > max_score:
                raise ValueError(f"{name} must be between 0 and {max_score}, got {value}")


def score_project(signals: ProjectSignals) -> int:
    """Compute the final project score on a 0-100 scale.

    Formula:
    A + B + C + D + E + F + G + I - H
    """

    signals.validate()

    score = (
        signals.procedural_stage
        + signals.sponsor_strength
        + signals.funding_clarity
        + signals.route_specificity
        + signals.need_case
        + signals.row_tractability
        + signals.local_plan_alignment
        + signals.land_monetization_fit
        - signals.opposition_drag
    )

    # Defensive clamp to preserve the stated 0-100 range.
    return max(0, min(100, score))


def interpret_score(score: int) -> str:
    """Return the interpretation band for a given score."""

    if score < 0 or score > 100:
        raise ValueError("score must be between 0 and 100")

    if score >= 85:
        return "very high probability / very actionable"
    if score >= 70:
        return "strong watchlist candidate"
    if score >= 55:
        return "speculative but worth targeted hunting"
    return "mostly informational, not land-first actionable"


if __name__ == "__main__":
    demo = ProjectSignals(
        procedural_stage=20,
        sponsor_strength=9,
        funding_clarity=12,
        route_specificity=10,
        need_case=10,
        row_tractability=7,
        local_plan_alignment=6,
        opposition_drag=2,
        land_monetization_fit=14,
    )
    total = score_project(demo)
    print(f"Score: {total}/100")
    print(f"Band: {interpret_score(total)}")
