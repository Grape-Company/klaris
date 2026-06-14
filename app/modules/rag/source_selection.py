from app.modules.rag.retriever import RetrievedChunk

TITLE_MATCH_SOURCE_SCORE = 0.95
CONTENT_MATCH_SOURCE_SCORE = 0.9
MAX_SOURCES = 3


def select_source_chunks(chunks: list[RetrievedChunk]) -> list[RetrievedChunk]:
    strong_title_matches = [
        chunk for chunk in chunks if chunk["score"] >= TITLE_MATCH_SOURCE_SCORE
    ]
    if strong_title_matches:
        return _unique_page_chunks(strong_title_matches, MAX_SOURCES)

    content_matches = [
        chunk for chunk in chunks if chunk["score"] >= CONTENT_MATCH_SOURCE_SCORE
    ]
    return _unique_page_chunks(content_matches, MAX_SOURCES)


def _unique_page_chunks(
    chunks: list[RetrievedChunk],
    max_sources: int,
) -> list[RetrievedChunk]:
    selected: list[RetrievedChunk] = []
    seen: set[tuple[str, str]] = set()

    for chunk in chunks:
        key = (chunk["page_title"], chunk["page_url"])
        if key in seen:
            continue
        selected.append(chunk)
        seen.add(key)
        if len(selected) >= max_sources:
            break

    return selected
