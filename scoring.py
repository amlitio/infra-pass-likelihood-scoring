"""Infrastructure proposal scoring utilities and CLI.

Implements the weighted Pass-Likelihood + Land Relevance model:
A + B + C + D + E + F + G + I - H
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path
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

    All values are integer points within category bounds.
    `opposition_drag` is entered as 0..7 and subtracted.
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
        values = asdict(self)
        for name, value in values.items():
            max_score = CATEGORY_MAXIMA[name]
            if not isinstance(value, int):
                raise TypeError(f"{name} must be an integer, got {type(value).__name__}")
            if value < 0 or value > max_score:
                raise ValueError(f"{name} must be between 0 and {max_score}, got {value}")


def score_breakdown(signals: ProjectSignals) -> Dict[str, int]:
    """Return each additive component and the signed opposition contribution."""

    signals.validate()
    parts = asdict(signals)
    parts["opposition_drag"] = -parts["opposition_drag"]
    return parts


def score_project(signals: ProjectSignals) -> int:
    """Compute final project score on the documented 0..100 scale."""

    parts = score_breakdown(signals)
    total = sum(parts.values())
    return max(0, min(100, total))


def interpret_score(score: int) -> str:
    """Return interpretation band for a score."""

    if score < 0 or score > 100:
        raise ValueError("score must be between 0 and 100")

    if score >= 85:
        return "very high probability / very actionable"
    if score >= 70:
        return "strong watchlist candidate"
    if score >= 55:
        return "speculative but worth targeted hunting"
    return "mostly informational, not land-first actionable"


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


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Score infrastructure proposals (0-100).")
    parser.add_argument("--input-json", type=Path, help="Path to JSON object with scoring fields.")
    parser.add_argument("--demo", action="store_true", help="Run with built-in demo values.")

    for field, max_value in CATEGORY_MAXIMA.items():
        parser.add_argument(
            f"--{field.replace('_', '-')}",
            type=int,
            help=f"{field} (0-{max_value})",
        )

    return parser


def _signals_from_args(args: argparse.Namespace) -> ProjectSignals:
    if args.input_json:
        payload = json.loads(args.input_json.read_text())
        return project_signals_from_dict(payload)

    if args.demo:
        return ProjectSignals(
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

    values = {
        field: getattr(args, field)
        for field in CATEGORY_MAXIMA
    }
    missing = [name for name, value in values.items() if value is None]
    if missing:
        missing_flags = ", ".join(f"--{name.replace('_', '-')}" for name in missing)
        raise ValueError(
            "Missing required arguments. Provide --demo, --input-json, "
            f"or all scoring flags. Missing: {missing_flags}"
        )

    return project_signals_from_dict(values)


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    try:
        signals = _signals_from_args(args)
        breakdown = score_breakdown(signals)
        total = score_project(signals)
    except (TypeError, ValueError, KeyError, json.JSONDecodeError) as error:
        parser.error(str(error))

    print("Breakdown:")
    for name, value in breakdown.items():
        print(f"  {name}: {value}")
    print(f"Score: {total}/100")
    print(f"Band: {interpret_score(total)}")


if __name__ == "__main__":
    main()
