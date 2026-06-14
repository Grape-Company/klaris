"""add rag answer feedback

Revision ID: 0003
Revises: 0002
Create Date: 2026-06-14
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "rag_answer_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("answer", sa.Text(), nullable=False),
        sa.Column("top_k", sa.Integer(), nullable=False),
        sa.Column("prompt_version", sa.String(), nullable=False),
        sa.Column("model", sa.String(), nullable=False),
        sa.Column("source_chunk_ids", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("retrieval_scores", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "rag_answer_feedback",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("answer_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("rating", sa.String(), nullable=False),
        sa.Column("correction", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint(
            "rating IN ('positive', 'negative')",
            name="ck_rag_answer_feedback_rating",
        ),
        sa.ForeignKeyConstraint(["answer_id"], ["rag_answer_logs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idx_rag_answer_feedback_answer_id",
        "rag_answer_feedback",
        ["answer_id"],
    )
    op.create_index(
        "idx_rag_answer_feedback_rating",
        "rag_answer_feedback",
        ["rating"],
    )


def downgrade() -> None:
    op.drop_index("idx_rag_answer_feedback_rating", table_name="rag_answer_feedback")
    op.drop_index("idx_rag_answer_feedback_answer_id", table_name="rag_answer_feedback")
    op.drop_table("rag_answer_feedback")
    op.drop_table("rag_answer_logs")
