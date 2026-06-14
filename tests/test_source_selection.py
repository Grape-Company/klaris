from uuid import uuid4

from app.modules.rag.retriever import RetrievedChunk
from app.modules.rag.source_selection import select_source_chunks


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


def test_select_source_chunks_keeps_only_strong_title_matches_when_available() -> None:
    chunks = [
        make_chunk("Ethiron", 1.0),
        make_chunk("Ethiron, The Maelstrom's Eye", 0.96),
        make_chunk("Glossary", 0.92),
        make_chunk("Iron", 0.12),
    ]

    sources = select_source_chunks(chunks)

    assert [source["page_title"] for source in sources] == [
        "Ethiron",
        "Ethiron, The Maelstrom's Eye",
    ]


def test_select_source_chunks_returns_no_sources_for_weak_matches() -> None:
    chunks = [
        make_chunk("Iron", 0.12),
        make_chunk("Glossary", 0.09),
    ]

    assert select_source_chunks(chunks) == []


def test_select_source_chunks_caps_source_count() -> None:
    chunks = [
        make_chunk("A", 0.99),
        make_chunk("B", 0.98),
        make_chunk("C", 0.97),
        make_chunk("D", 0.96),
    ]

    assert len(select_source_chunks(chunks)) == 3
