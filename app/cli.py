"""CLI entry point for the scoring platform."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .domain import CATEGORY_MAXIMA, project_signals_from_dict
from .service import interpret_score, score_breakdown, score_project


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


def _signals_from_args(args: argparse.Namespace):
    if args.input_json:
        payload = json.loads(args.input_json.read_text())
        return project_signals_from_dict(payload)

    if args.demo:
        return project_signals_from_dict(
            {
                "procedural_stage": 20,
                "sponsor_strength": 9,
                "funding_clarity": 12,
                "route_specificity": 10,
                "need_case": 10,
                "row_tractability": 7,
                "local_plan_alignment": 6,
                "opposition_drag": 2,
                "land_monetization_fit": 14,
            }
        )

    values = {field: getattr(args, field) for field in CATEGORY_MAXIMA}
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
