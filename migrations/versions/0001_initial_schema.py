"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-01-01
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.create_table(
        "wiki_categories",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(), nullable=False, unique=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )

    op.create_table(
        "wiki_pages",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("title", sa.String(), nullable=False, unique=True),
        sa.Column("url", sa.String(), nullable=False),
        sa.Column("namespace", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("page_id", sa.Integer(), nullable=True),
        sa.Column("raw_html", sa.Text(), nullable=True),
        sa.Column("clean_text", sa.Text(), nullable=True),
        sa.Column("content_hash", sa.String(), nullable=False),
        sa.Column("last_ingested_at", sa.DateTime(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index("idx_wiki_pages_title", "wiki_pages", ["title"])

    op.create_table(
        "ingestion_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("started_at", sa.DateTime(), nullable=False),
        sa.Column("finished_at", sa.DateTime(), nullable=True),
        sa.Column("pages_found", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("pages_ingested", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("pages_failed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error_message", sa.Text(), nullable=True),
    )

    op.create_table(
        "wiki_page_categories",
        sa.Column(
            "page_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("wiki_pages.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "category_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("wiki_categories.id", ondelete="CASCADE"),
            primary_key=True,
        ),
    )

    op.execute(
        """
        CREATE TABLE wiki_chunks (
            id UUID PRIMARY KEY,
            page_id UUID NOT NULL REFERENCES wiki_pages(id) ON DELETE CASCADE,
            chunk_index INTEGER NOT NULL,
            heading TEXT,
            content TEXT NOT NULL,
            token_count INTEGER,
            embedding vector(1536),
            created_at TIMESTAMP NOT NULL,
            UNIQUE(page_id, chunk_index)
        )
        """
    )
    op.create_index("idx_wiki_chunks_page_id", "wiki_chunks", ["page_id"])
    op.execute(
        "CREATE INDEX idx_wiki_chunks_embedding ON wiki_chunks "
        "USING ivfflat (embedding vector_cosine_ops)"
    )


def downgrade() -> None:
    op.drop_index("idx_wiki_chunks_embedding", table_name="wiki_chunks")
    op.drop_index("idx_wiki_chunks_page_id", table_name="wiki_chunks")
    op.drop_table("wiki_chunks")
    op.drop_table("wiki_page_categories")
    op.drop_table("ingestion_runs")
    op.drop_index("idx_wiki_pages_title", table_name="wiki_pages")
    op.drop_table("wiki_pages")
    op.drop_table("wiki_categories")
