"""API request and response models."""

from __future__ import annotations

from typing import Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field

from .domain import ProjectSignals


class SignalFields(BaseModel):
    """Shared scoring signal inputs."""

    model_config = ConfigDict(extra="forbid")

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


class ScoreRequest(SignalFields):
    """Single project scoring request."""

    project_id: Optional[str] = Field(default=None, description="External identifier for the project")
    project_name: Optional[str] = Field(default=None, description="Human-friendly project name")
    sponsor_organization: Optional[str] = None
    sector: Optional[str] = None
    region: Optional[str] = None
    notes: Optional[str] = None


class ScoreResponse(BaseModel):
    """Single project scoring response."""

    project_id: Optional[str] = None
    project_name: Optional[str] = None
    score: int
    interpretation: str
    breakdown: Dict[str, int]
    utilization: Dict[str, float]


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


class UserSummary(BaseModel):
    id: int
    organization_id: int
    email: str
    full_name: str
    role: str
    is_active: bool
    created_at: str


class OrganizationSummary(BaseModel):
    id: int
    name: str
    slug: str
    created_at: str
    member_count: int = 0
    project_count: int = 0


class RegisterRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    organization_name: str = Field(min_length=2)
    organization_slug: Optional[str] = None
    email: str
    password: str = Field(min_length=8)
    full_name: str = Field(min_length=2)


class LoginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: str
    password: str = Field(min_length=8)


class OrganizationMemberCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: str
    password: str = Field(min_length=8)
    full_name: str = Field(min_length=2)
    role: str = Field(default="analyst")


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserSummary
    organization: OrganizationSummary


class ProjectCreateRequest(ScoreRequest):
    """Request to create a persistent project."""

    project_name: str = Field(min_length=1)


class ProjectUpdateRequest(ScoreRequest):
    """Request to update a persistent project."""

    project_name: str = Field(min_length=1)


class ScoreRunRecord(BaseModel):
    """Persistent score run metadata."""

    id: int
    project_id: int
    score: int
    interpretation: str
    breakdown: Dict[str, int]
    utilization: Dict[str, float]
    triggered_by: str
    created_at: str


class ProjectSummary(BaseModel):
    """Project summary with current scoring state."""

    id: int
    organization_id: int
    owner_user_id: Optional[int] = None
    project_id: Optional[str] = None
    project_name: str
    sponsor_organization: Optional[str] = None
    sector: Optional[str] = None
    region: Optional[str] = None
    notes: Optional[str] = None
    procedural_stage: int
    sponsor_strength: int
    funding_clarity: int
    route_specificity: int
    need_case: int
    row_tractability: int
    local_plan_alignment: int
    opposition_drag: int
    land_monetization_fit: int
    latest_score: int
    latest_interpretation: str
    created_at: str
    updated_at: str


class ProjectDetail(ProjectSummary):
    """Project detail including history."""

    latest_breakdown: Dict[str, int]
    latest_utilization: Dict[str, float]
    score_history: List[ScoreRunRecord]


class PortfolioSummary(BaseModel):
    """Top-level dashboard metrics."""

    total_projects: int
    average_score: float
    high_priority_projects: int
    recent_scores: int
    top_project: Optional[ProjectSummary] = None


class CsvImportRequest(BaseModel):
    """Request body for CSV ingestion."""

    model_config = ConfigDict(extra="forbid")

    filename: str = "batch-import.csv"
    csv_content: str = Field(min_length=1)
    triggered_by: Optional[str] = None


class CsvImportResponse(BaseModel):
    """CSV ingestion result."""

    import_id: int
    filename: str
    total_projects: int
    created_projects: int
    average_score: float
    results: List[ProjectSummary]
