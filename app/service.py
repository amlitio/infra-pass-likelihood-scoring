"""Scoring services."""

from __future__ import annotations

from dataclasses import asdict
from typing import Dict

from .domain import CATEGORY_MAXIMA, ProjectSignals
from .schemas import ScoreRequest, ScoreResponse


def score_breakdown(signals: ProjectSignals) -> Dict[str, int]:
    """Return each additive component and the signed opposition contribution."""

    signals.validate()
    parts = asdict(signals)
    parts["opposition_drag"] = -parts["opposition_drag"]
    return parts


def score_project(signals: ProjectSignals) -> int:
    """Compute final project score on the documented 0..100 scale."""

    total = sum(score_breakdown(signals).values())
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


def category_utilization(signals: ProjectSignals) -> Dict[str, float]:
    """Return normalized category utilization as percentages of category maxima."""

    signals.validate()
    values = asdict(signals)
    return {
        name: round((value / CATEGORY_MAXIMA[name]) * 100, 2)
        for name, value in values.items()
    }


def build_score_response(request: ScoreRequest) -> ScoreResponse:
    """Score a request and return a normalized response object."""

    signals = request.to_signals()
    total = score_project(signals)
    return ScoreResponse(
        project_id=request.project_id,
        project_name=request.project_name,
        score=total,
        interpretation=interpret_score(total),
        breakdown=score_breakdown(signals),
        utilization=category_utilization(signals),
    )
