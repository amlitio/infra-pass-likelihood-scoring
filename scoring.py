"""Backward-compatible script entry point."""

from app.cli import main
from app.domain import ProjectSignals, project_signals_from_dict
from app.service import interpret_score, score_breakdown, score_project

__all__ = [
    "ProjectSignals",
    "interpret_score",
    "main",
    "project_signals_from_dict",
    "score_breakdown",
    "score_project",
]


if __name__ == "__main__":
    main()
