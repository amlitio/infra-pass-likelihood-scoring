"""Database models."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def utc_now() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class Base(DeclarativeBase):
    pass


class Organization(Base):
    __tablename__ = "organizations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(120), nullable=False, unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    users: Mapped[list["User"]] = relationship(back_populates="organization", cascade="all, delete-orphan")
    projects: Mapped[list["Project"]] = relationship(back_populates="organization", cascade="all, delete-orphan")


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    organization_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(40), nullable=False, default="analyst")
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    organization: Mapped["Organization"] = relationship(back_populates="users")
    sessions: Mapped[list["SessionToken"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    projects: Mapped[list["Project"]] = relationship(back_populates="owner")


class SessionToken(Base):
    __tablename__ = "sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    token_hash: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    user_agent: Mapped[str | None] = mapped_column(String(255), nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(64), nullable=True)

    user: Mapped["User"] = relationship(back_populates="sessions")


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    organization_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"), nullable=False)
    owner_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    project_id: Mapped[str | None] = mapped_column(String(120), nullable=True)
    project_name: Mapped[str] = mapped_column(String(255), nullable=False)
    sponsor_organization: Mapped[str | None] = mapped_column(String(255), nullable=True)
    sector: Mapped[str | None] = mapped_column(String(120), nullable=True)
    region: Mapped[str | None] = mapped_column(String(120), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    procedural_stage: Mapped[int] = mapped_column(Integer, nullable=False)
    sponsor_strength: Mapped[int] = mapped_column(Integer, nullable=False)
    funding_clarity: Mapped[int] = mapped_column(Integer, nullable=False)
    route_specificity: Mapped[int] = mapped_column(Integer, nullable=False)
    need_case: Mapped[int] = mapped_column(Integer, nullable=False)
    row_tractability: Mapped[int] = mapped_column(Integer, nullable=False)
    local_plan_alignment: Mapped[int] = mapped_column(Integer, nullable=False)
    opposition_drag: Mapped[int] = mapped_column(Integer, nullable=False)
    land_monetization_fit: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    organization: Mapped["Organization"] = relationship(back_populates="projects")
    owner: Mapped["User | None"] = relationship(back_populates="projects")
    score_runs: Mapped[list["ScoreRun"]] = relationship(back_populates="project", cascade="all, delete-orphan")


class ScoreRun(Base):
    __tablename__ = "score_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), nullable=False)
    score: Mapped[int] = mapped_column(Integer, nullable=False)
    interpretation: Mapped[str] = mapped_column(String(255), nullable=False)
    breakdown: Mapped[dict] = mapped_column(JSON, nullable=False)
    utilization: Mapped[dict] = mapped_column(JSON, nullable=False)
    triggered_by: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    project: Mapped["Project"] = relationship(back_populates="score_runs")


class ImportJob(Base):
    __tablename__ = "imports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    organization_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"), nullable=False)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    total_projects: Mapped[int] = mapped_column(Integer, nullable=False)
    created_projects: Mapped[int] = mapped_column(Integer, nullable=False)
    average_score: Mapped[float] = mapped_column(nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
