import uuid
from datetime import UTC, datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


def _utcnow() -> datetime:
    return datetime.now(UTC)


class WikiPage(Base):
    __tablename__ = "wiki_pages"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    url: Mapped[str] = mapped_column(String, nullable=False)
    namespace: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    page_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    raw_html: Mapped[str | None] = mapped_column(Text, nullable=True)
    clean_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    content_hash: Mapped[str] = mapped_column(String, nullable=False)
    last_ingested_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=_utcnow
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=_utcnow, onupdate=_utcnow
    )

    chunks: Mapped[list["WikiChunk"]] = relationship(
        "WikiChunk", back_populates="page", cascade="all, delete-orphan"
    )
    categories: Mapped[list["WikiPageCategory"]] = relationship(
        "WikiPageCategory", back_populates="page", cascade="all, delete-orphan"
    )


class WikiCategory(Base):
    __tablename__ = "wiki_categories"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=_utcnow)

    pages: Mapped[list["WikiPageCategory"]] = relationship(
        "WikiPageCategory", back_populates="category", cascade="all, delete-orphan"
    )


class WikiPageCategory(Base):
    __tablename__ = "wiki_page_categories"

    page_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("wiki_pages.id", ondelete="CASCADE"), primary_key=True
    )
    category_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("wiki_categories.id", ondelete="CASCADE"), primary_key=True
    )

    page: Mapped["WikiPage"] = relationship("WikiPage", back_populates="categories")
    category: Mapped["WikiCategory"] = relationship("WikiCategory", back_populates="pages")


class WikiChunk(Base):
    __tablename__ = "wiki_chunks"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    page_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("wiki_pages.id", ondelete="CASCADE"), nullable=False
    )
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    heading: Mapped[str | None] = mapped_column(String, nullable=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    token_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    embedding: Mapped[list[float] | None] = mapped_column(Vector(1536), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=_utcnow)

    __table_args__ = (UniqueConstraint("page_id", "chunk_index", name="uq_page_chunk"),)

    page: Mapped["WikiPage"] = relationship("WikiPage", back_populates="chunks")


class IngestionRun(Base):
    __tablename__ = "ingestion_runs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    status: Mapped[str] = mapped_column(String, nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=_utcnow)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    pages_found: Mapped[int] = mapped_column(Integer, default=0)
    pages_ingested: Mapped[int] = mapped_column(Integer, default=0)
    pages_failed: Mapped[int] = mapped_column(Integer, default=0)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
