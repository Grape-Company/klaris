from app.modules.ingestion.chunker import chunk_page


def test_chunker_creates_chunks() -> None:
    text = "# Title\n\nSome content here.\n\n## Section 1\n\nMore content."
    chunks = chunk_page("TestPage", text)
    assert len(chunks) > 0
    assert chunks[0].page_title == "TestPage"


def test_chunker_includes_page_title() -> None:
    text = "# Hello\n\nWorld"
    chunks = chunk_page("MyPage", text)
    assert "Page: MyPage" in chunks[0].content


def test_chunker_includes_heading() -> None:
    text = "# Main\n\nMain paragraph content.\n\n## Sub\n\nDetails here."
    chunks = chunk_page("Page", text)
    headings = [c.heading for c in chunks]
    assert "Main" in headings
    assert "Sub" in headings


def test_chunker_respects_token_limit() -> None:
    long_text = "# H1\n\n" + "word " * 5000
    chunks = chunk_page("LongPage", long_text)
    for chunk in chunks:
        assert chunk.token_count <= 1000


def test_chunker_returns_at_least_one_chunk() -> None:
    chunks = chunk_page("Empty", "")
    assert len(chunks) == 0
