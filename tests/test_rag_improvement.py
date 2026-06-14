from typing import Any
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.modules.rag.improvement import summarize_feedback
from app.modules.rag.schemas import RAGFeedbackRequest


def test_feedback_request_accepts_controlled_rating_and_correction() -> None:
    answer_id = uuid4()

    request = RAGFeedbackRequest(
        answer_id=answer_id,
        rating="negative",
        correction="The retrieved source does not support that requirement.",
    )

    assert request.answer_id == answer_id
    assert request.rating == "negative"
    assert request.correction is not None


def test_feedback_request_rejects_unknown_rating() -> None:
    invalid_rating: Any = "maybe"

    with pytest.raises(ValidationError):
        RAGFeedbackRequest(answer_id=uuid4(), rating=invalid_rating)


def test_summarize_feedback_counts_ratings_and_corrections() -> None:
    summary = summarize_feedback(
        [
            {"rating": "positive", "correction": None},
            {"rating": "negative", "correction": "Missing source."},
            {"rating": "negative", "correction": ""},
        ]
    )

    assert summary.total_feedback == 3
    assert summary.positive_feedback == 1
    assert summary.negative_feedback == 2
    assert summary.correction_count == 1
