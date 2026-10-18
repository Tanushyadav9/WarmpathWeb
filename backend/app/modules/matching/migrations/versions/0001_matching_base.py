"""matching base tables and vector indices

Revision ID: 0001_matching_base
Revises: 
Create Date: 2026-10-17 20:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

try:
    from pgvector.sqlalchemy import Vector
except ImportError:
    from sqlalchemy.types import UserDefinedType

    class Vector(UserDefinedType):
        def __init__(self, dim: int = 768):
            self.dim = dim

        def get_col_spec(self, **kw) -> str:
            return f"vector({self.dim})"


revision: str = "0001_matching_base"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = ("matching",)
depends_on: Union[str, Sequence[str], None] = ("0001_core_base",)


def upgrade() -> None:
    # 1. Giver profiles table
    op.create_table(
        "giver_profiles",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("offers", postgresql.JSONB(as_json=True), nullable=False),
        sa.Column("topics", postgresql.ARRAY(sa.String()), nullable=False),
        sa.Column("skills", postgresql.JSONB(as_json=True), nullable=False),
        sa.Column("domains", postgresql.ARRAY(sa.String()), nullable=False),
        sa.Column("company", sa.String(length=255), nullable=True),
        sa.Column("role_title", sa.String(length=255), nullable=True),
        sa.Column("bio", sa.Text(), nullable=True),
        sa.Column("languages", postgresql.ARRAY(sa.String()), nullable=False),
        sa.Column("embedding", Vector(768), nullable=True),
        sa.Column("response_stats", postgresql.JSONB(as_json=True), nullable=False),
        sa.Column("weekly_capacity", sa.Integer(), nullable=False, server_default="3"),
        sa.Column("institution_id", sa.Integer(), nullable=True),
        sa.Column("department", sa.String(length=100), nullable=True),
        sa.Column("batch", sa.Integer(), nullable=True),
        sa.Column("societies", postgresql.ARRAY(sa.String()), nullable=False),
        sa.Column("daily_impressions_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("daily_impressions_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("user_id"),
    )

    # 2. HNSW cosine vector index on giver_profiles embedding
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_giver_profiles_embedding "
        "ON giver_profiles USING hnsw (embedding vector_cosine_ops) "
        "WITH (m = 16, ef_construction = 64);"
    )

    # 3. High-throughput B-tree indexes for filtered candidate retrieval
    op.create_index("ix_giver_profiles_institution_id", "giver_profiles", ["institution_id"])
    op.create_index("ix_giver_profiles_capacity", "giver_profiles", ["weekly_capacity"])
    op.create_index("ix_giver_profiles_impressions", "giver_profiles", ["daily_impressions_count"])
    op.create_index("ix_giver_profiles_inst_cap", "giver_profiles", ["institution_id", "weekly_capacity"])

    # 3. Student match local projection table
    op.create_table(
        "student_match_profiles",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("institution_id", sa.Integer(), nullable=True),
        sa.Column("department", sa.String(length=100), nullable=True),
        sa.Column("batch", sa.Integer(), nullable=True),
        sa.Column("societies", postgresql.ARRAY(sa.String()), nullable=False),
        sa.Column("skills", postgresql.JSONB(as_json=True), nullable=False),
        sa.Column("domains", postgresql.ARRAY(sa.String()), nullable=False),
        sa.Column("profile_embedding", Vector(768), nullable=True),
        sa.Column("intent_goal", sa.Text(), nullable=True),
        sa.Column("intent_roles", postgresql.ARRAY(sa.String()), nullable=False),
        sa.Column("intent_domains", postgresql.ARRAY(sa.String()), nullable=False),
        sa.Column("intent_help_type", sa.String(length=100), nullable=True),
        sa.Column("intent_embedding", Vector(768), nullable=True),
        sa.Column("profile_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("user_id"),
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_giver_profiles_embedding;")
    op.drop_table("student_match_profiles")
    op.drop_table("giver_profiles")
