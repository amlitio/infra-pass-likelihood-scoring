"""initial schema"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "20260407_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    existing_tables = set(inspector.get_table_names())
    if {"organizations", "users", "sessions", "projects", "score_runs", "imports"}.issubset(existing_tables):
        return

    op.create_table(
        "organizations",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("slug", sa.String(length=120), nullable=False, unique=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("organization_id", sa.Integer(), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False, unique=True),
        sa.Column("full_name", sa.String(length=255), nullable=False),
        sa.Column("role", sa.String(length=40), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "sessions",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("token_hash", sa.String(length=128), nullable=False, unique=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("user_agent", sa.String(length=255), nullable=True),
        sa.Column("ip_address", sa.String(length=64), nullable=True),
    )
    op.create_table(
        "projects",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("organization_id", sa.Integer(), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("owner_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("project_id", sa.String(length=120), nullable=True),
        sa.Column("project_name", sa.String(length=255), nullable=False),
        sa.Column("sponsor_organization", sa.String(length=255), nullable=True),
        sa.Column("sector", sa.String(length=120), nullable=True),
        sa.Column("region", sa.String(length=120), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("procedural_stage", sa.Integer(), nullable=False),
        sa.Column("sponsor_strength", sa.Integer(), nullable=False),
        sa.Column("funding_clarity", sa.Integer(), nullable=False),
        sa.Column("route_specificity", sa.Integer(), nullable=False),
        sa.Column("need_case", sa.Integer(), nullable=False),
        sa.Column("row_tractability", sa.Integer(), nullable=False),
        sa.Column("local_plan_alignment", sa.Integer(), nullable=False),
        sa.Column("opposition_drag", sa.Integer(), nullable=False),
        sa.Column("land_monetization_fit", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "score_runs",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("project_id", sa.Integer(), sa.ForeignKey("projects.id"), nullable=False),
        sa.Column("score", sa.Integer(), nullable=False),
        sa.Column("interpretation", sa.String(length=255), nullable=False),
        sa.Column("breakdown", sa.JSON(), nullable=False),
        sa.Column("utilization", sa.JSON(), nullable=False),
        sa.Column("triggered_by", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "imports",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("organization_id", sa.Integer(), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column("total_projects", sa.Integer(), nullable=False),
        sa.Column("created_projects", sa.Integer(), nullable=False),
        sa.Column("average_score", sa.Float(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("imports")
    op.drop_table("score_runs")
    op.drop_table("projects")
    op.drop_table("sessions")
    op.drop_table("users")
    op.drop_table("organizations")
