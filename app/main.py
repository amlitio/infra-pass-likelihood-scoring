"""FastAPI application entry point."""

from __future__ import annotations

from fastapi import FastAPI

from .config import Settings
from .schemas import BatchScoreRequest, BatchScoreResponse, ScoreRequest, ScoreResponse


settings = Settings.from_env()
app = FastAPI(
    title=settings.app_name,
    version=settings.version,
    docs_url="/docs",
    redoc_url="/redoc",
)


@app.get("/health/live")
def liveness() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/health/ready")
def readiness() -> dict[str, str]:
    return {
        "status": "ready",
        "environment": settings.environment,
        "version": settings.version,
    }


@app.get("/v1/metadata")
def metadata() -> dict[str, object]:
    return {
        "application": settings.app_name,
        "environment": settings.environment,
        "version": settings.version,
        "capabilities": ["single-score", "batch-score", "health-checks"],
    }


@app.post("/v1/score", response_model=ScoreResponse)
def score_endpoint(payload: ScoreRequest) -> ScoreResponse:
    return ScoreResponse.from_request(payload)


@app.post("/v1/score/batch", response_model=BatchScoreResponse)
def batch_score_endpoint(payload: BatchScoreRequest) -> BatchScoreResponse:
    results = [ScoreResponse.from_request(project) for project in payload.projects]
    scores = [result.score for result in results]
    return BatchScoreResponse(
        total_projects=len(results),
        average_score=round(sum(scores) / len(scores), 2),
        highest_score=max(scores),
        lowest_score=min(scores),
        results=results,
    )
