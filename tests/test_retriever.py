from uuid import uuid4

from app.modules.rag.retriever import RetrievedChunk, merge_ranked_chunks


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
