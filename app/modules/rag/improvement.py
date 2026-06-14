from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Literal

FeedbackRating = Literal["positive", "negative"]


@dataclass(frozen=True)
class FeedbackSummary:
    total_feedback: int
    positive_feedback: int
    negative_feedback: int
    correction_count: int


def summarize_feedback(feedback_rows: Sequence[Mapping[str, object]]) -> FeedbackSummary:
    positive_feedback = 0
    negative_feedback = 0
    correction_count = 0

    for row in feedback_rows:
        if row["rating"] == "positive":
            positive_feedback += 1
        elif row["rating"] == "negative":
            negative_feedback += 1

        correction = row.get("correction")
        if isinstance(correction, str) and correction.strip():
            correction_count += 1

    return FeedbackSummary(
        total_feedback=len(feedback_rows),
        positive_feedback=positive_feedback,
        negative_feedback=negative_feedback,
        correction_count=correction_count,
    )
