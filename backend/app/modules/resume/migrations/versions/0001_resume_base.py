"""resume base tables, consents, and vector embeddings

Revision ID: 0001_resume_base
Revises: 0001_core_base
Create Date: 2026-10-17 20:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from pgvector.sqlalchemy import Vector

# revision identifiers, used by Alembic.
revision: str = '0001_resume_base'
down_revision: Union[str, None] = '0001_core_base'
branch_labels: Union[str, Sequence[str], None] = ('resume',)
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Consents Table
    op.create_table(
        'consents',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('purpose', sa.String(length=50), nullable=False),
        sa.Column('granted', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('granted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('withdrawn_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('text_version', sa.String(length=20), nullable=False, server_default='v1.0'),
        sa.UniqueConstraint('user_id', 'purpose', name='uq_user_purpose_consent'),
    )
    op.create_index('ix_consents_user_id', 'consents', ['user_id'])

    # 2. Skills Taxonomy Table
    op.create_table(
        'skills_taxonomy',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('name', sa.String(length=100), nullable=False, unique=True),
        sa.Column('category', sa.String(length=100), nullable=False),
        sa.Column('aliases', postgresql.ARRAY(sa.String()), nullable=False),
    )
    op.create_index('ix_skills_taxonomy_name', 'skills_taxonomy', ['name'])
    op.create_index('ix_skills_taxonomy_category', 'skills_taxonomy', ['category'])

    # 3. Student Profiles Table
    op.create_table(
        'student_profiles',
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), primary_key=True),
        sa.Column('raw_text', sa.Text(), nullable=True),
        sa.Column('resume_file_path', sa.String(length=500), nullable=True),
        sa.Column('parsed', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('edited', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('embedding', Vector(768), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_student_profiles_embedding ON student_profiles "
        "USING hnsw (embedding vector_cosine_ops) WITH (m = 16, ef_construction = 64)"
    )

    # 4. Student Intents Table
    op.create_table(
        'student_intents',
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), primary_key=True),
        sa.Column('raw_text', sa.Text(), nullable=False),
        sa.Column('goal_type', sa.String(length=50), nullable=True),
        sa.Column('target_roles', postgresql.ARRAY(sa.String()), nullable=False),
        sa.Column('target_domains', postgresql.ARRAY(sa.String()), nullable=False),
        sa.Column('structured', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('intent_embedding', Vector(768), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_student_intents_embedding ON student_intents "
        "USING hnsw (intent_embedding vector_cosine_ops) WITH (m = 16, ef_construction = 64)"
    )


def downgrade() -> None:
    op.drop_table('student_intents')
    op.drop_table('student_profiles')
    op.drop_table('skills_taxonomy')
    op.drop_table('consents')
