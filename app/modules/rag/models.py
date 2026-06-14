import uuid
from datetime import UTC, datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


def _utcnow() -> datetime:
    return datetime.now(UTC)


class RAGAnswerLog(Base):
    __tablename__ = "rag_answer_logs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    question: Mapped[str] = mapped_column(Text, nullable=False)
    answer: Mapped[str] = mapped_column(Text, nullable=False)
    top_k: Mapped[int] = mapped_column(Integer, nullable=False)
    prompt_version: Mapped[str] = mapped_column(String, nullable=False)
    model: Mapped[str] = mapped_column(String, nullable=False)
    source_chunk_ids: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    retrieval_scores: Mapped[list[dict[str, object]]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=_utcnow)

    feedback: Mapped[list["RAGAnswerFeedback"]] = relationship(
        "RAGAnswerFeedback",
        back_populates="answer",
        cascade="all, delete-orphan",
    )


class RAGAnswerFeedback(Base):
    __tablename__ = "rag_answer_feedback"
    __table_args__ = (
        CheckConstraint(
            "rating IN ('positive', 'negative')",
            name="ck_rag_answer_feedback_rating",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    answer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("rag_answer_logs.id", ondelete="CASCADE"),
        nullable=False,
    )
    rating: Mapped[str] = mapped_column(String, nullable=False)
    correction: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=_utcnow)

    answer: Mapped[RAGAnswerLog] = relationship("RAGAnswerLog", back_populates="feedback")
