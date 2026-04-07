"""Core domain models for proposal scoring."""

from __future__ import annotations

from dataclasses import asdict, dataclass
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
    """Input signals for the scoring model."""

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
        values = asdict(self)
        for name, value in values.items():
            max_score = CATEGORY_MAXIMA[name]
            if not isinstance(value, int):
                raise TypeError(f"{name} must be an integer, got {type(value).__name__}")
            if value < 0 or value > max_score:
                raise ValueError(f"{name} must be between 0 and {max_score}, got {value}")


def project_signals_from_dict(raw: Dict[str, int]) -> ProjectSignals:
    """Build ProjectSignals from dictionary input."""

    return ProjectSignals(
        procedural_stage=raw["procedural_stage"],
        sponsor_strength=raw["sponsor_strength"],
        funding_clarity=raw["funding_clarity"],
        route_specificity=raw["route_specificity"],
        need_case=raw["need_case"],
        row_tractability=raw["row_tractability"],
        local_plan_alignment=raw["local_plan_alignment"],
        opposition_drag=raw["opposition_drag"],
        land_monetization_fit=raw["land_monetization_fit"],
    )
