"""API request and response models."""

from __future__ import annotations

from typing import Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field

from .domain import ProjectSignals
from .service import category_utilization, interpret_score, score_breakdown, score_project


class ScoreRequest(BaseModel):
    """Single project scoring request."""

    model_config = ConfigDict(extra="forbid")

    project_id: Optional[str] = Field(default=None, description="External identifier for the project")
    project_name: Optional[str] = Field(default=None, description="Human-friendly project name")
    procedural_stage: int = Field(ge=0, le=25)
    sponsor_strength: int = Field(ge=0, le=10)
    funding_clarity: int = Field(ge=0, le=15)
    route_specificity: int = Field(ge=0, le=10)
    need_case: int = Field(ge=0, le=10)
    row_tractability: int = Field(ge=0, le=10)
    local_plan_alignment: int = Field(ge=0, le=8)
    opposition_drag: int = Field(ge=0, le=7)
    land_monetization_fit: int = Field(ge=0, le=19)

    def to_signals(self) -> ProjectSignals:
        return ProjectSignals(
            procedural_stage=self.procedural_stage,
            sponsor_strength=self.sponsor_strength,
            funding_clarity=self.funding_clarity,
            route_specificity=self.route_specificity,
            need_case=self.need_case,
            row_tractability=self.row_tractability,
            local_plan_alignment=self.local_plan_alignment,
            opposition_drag=self.opposition_drag,
            land_monetization_fit=self.land_monetization_fit,
        )


class ScoreResponse(BaseModel):
    """Single project scoring response."""

    project_id: Optional[str] = None
    project_name: Optional[str] = None
    score: int
    interpretation: str
    breakdown: Dict[str, int]
    utilization: Dict[str, float]

    @classmethod
    def from_request(cls, request: ScoreRequest) -> "ScoreResponse":
        signals = request.to_signals()
        total = score_project(signals)
        return cls(
            project_id=request.project_id,
            project_name=request.project_name,
            score=total,
            interpretation=interpret_score(total),
            breakdown=score_breakdown(signals),
            utilization=category_utilization(signals),
        )


class BatchScoreRequest(BaseModel):
    """Bulk scoring request."""

    model_config = ConfigDict(extra="forbid")

    projects: List[ScoreRequest] = Field(min_length=1, max_length=500)


class BatchScoreResponse(BaseModel):
    """Bulk scoring response with summary stats."""

    total_projects: int
    average_score: float
    highest_score: int
    lowest_score: int
    results: List[ScoreResponse]
