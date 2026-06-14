from uuid import uuid4

from app.modules.rag.answer_policy import disambiguation_answer, is_disambiguation_chunk
from app.modules.rag.retriever import RetrievedChunk


def make_chunk(title: str, content: str, score: float = 1.0) -> RetrievedChunk:
    return {
        "id": uuid4(),
        "chunk_index": 0,
        "heading": None,
        "content": content,
        "token_count": 10,
        "page_title": title,
        "page_url": f"https://example.test/wiki/{title}",
        "score": score,
    }


def test_is_disambiguation_chunk_detects_wiki_disambiguation_copy() -> None:
    chunk = make_chunk(
        "Megalodaunt",
        "This might have not been the page you were looking for, view the disambiguation.",
    )

    assert is_disambiguation_chunk(chunk)


def test_disambiguation_answer_explains_base_article_is_missing() -> None:
    primary = make_chunk(
        "Megalodaunt",
        "Page: Megalodaunt\n\nThis might have not been the page you were looking for.",
        0.35,
    )
    alpha = make_chunk("Alpha Megalodaunt", "Page: Alpha Megalodaunt", 0.3)
    crimson = make_chunk("Crimson Megalodaunt", "Page: Crimson Megalodaunt", 0.26)

    response = disambiguation_answer("what is the megalodount?", [primary, alpha, crimson])

    assert response is not None
    assert "disambiguation page" in response.answer
    assert "Alpha Megalodaunt" in response.answer
    assert "Crimson Megalodaunt" in response.answer
    assert [source["page_title"] for source in response.source_chunks] == ["Megalodaunt"]


def test_disambiguation_answer_ignores_normal_chunks() -> None:
    chunk = make_chunk("Ethiron", "Ethiron is a Drowned God.")

    assert disambiguation_answer("who is Ethiron?", [chunk]) is None
