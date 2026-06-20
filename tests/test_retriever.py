from uuid import uuid4

from app.modules.rag.query import analyze_query
from app.modules.rag.retriever import (
    RetrievedChunk,
    expanded_search_queries,
    keyword_patterns,
    merge_ranked_chunks,
)


def make_chunk(title: str, score: float) -> RetrievedChunk:
    return {
        "id": uuid4(),
        "chunk_index": 0,
        "heading": None,
        "content": f"Page: {title}",
        "token_count": 10,
        "page_title": title,
        "page_url": f"https://example.test/wiki/{title}",
        "score": score,
    }


def test_merge_ranked_chunks_prioritizes_keyword_matches() -> None:
    keyword_chunk = make_chunk("Deep Shrines/Shrine of Order", 1.0)
    vector_chunk = make_chunk("Valikor (Vow of Iron)", 0.11)

    results = merge_ranked_chunks([keyword_chunk], [vector_chunk], top_k=2)

    assert [chunk["page_title"] for chunk in results] == [
        "Deep Shrines/Shrine of Order",
        "Valikor (Vow of Iron)",
    ]


def test_merge_ranked_chunks_deduplicates_keyword_and_vector_results() -> None:
    chunk_id = uuid4()
    keyword_chunk = make_chunk("Shrine of Order", 1.0)
    keyword_chunk["id"] = chunk_id
    vector_chunk = make_chunk("Shrine of Order", 0.8)
    vector_chunk["id"] = chunk_id

    results = merge_ranked_chunks([keyword_chunk], [vector_chunk], top_k=8)

    assert len(results) == 1
    assert results[0]["score"] == 1.0


def test_merge_ranked_chunks_keeps_stronger_vector_match_over_weak_keyword_match() -> None:
    weak_keyword = make_chunk("Chainwarden", 0.89)
    strong_vector = make_chunk("Chainwarden", 0.96)

    results = merge_ranked_chunks([weak_keyword], [strong_vector], top_k=1)

    assert results == [strong_vector]


def test_keyword_patterns_extracts_subject_from_natural_question() -> None:
    assert keyword_patterns(analyze_query("what is Shrine of Order?")) == [
        "%what is Shrine of Order%",
        "%Shrine of Order%",
    ]


def test_keyword_patterns_extracts_subject_from_who_question() -> None:
    assert keyword_patterns(analyze_query("who is Ethiron?")) == [
        "%who is Ethiron%",
        "%Ethiron%",
    ]


def test_keyword_patterns_strips_articles_without_manual_typo_patch() -> None:
    assert keyword_patterns(analyze_query("what is the megalodount?")) == [
        "%what is the megalodount%",
        "%megalodount%",
    ]


def test_keyword_patterns_include_subject_and_oath_qualifier() -> None:
    assert keyword_patterns(analyze_query("Chainwarden oath")) == [
        "%Chainwarden oath%",
        "%Chainwarden%",
        "%Chainwarden%oath%",
        "%oath%Chainwarden%",
    ]


def test_expanded_search_queries_preserve_qualified_entity_queries() -> None:
    assert expanded_search_queries("Chainwarden oath") == [
        "Chainwarden oath",
        "Chainwarden Oath",
        "Chainwarden",
    ]
