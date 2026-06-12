import re
from dataclasses import dataclass

import tiktoken


@dataclass
class Chunk:
    page_title: str
    heading: str | None
    content: str
    chunk_index: int
    token_count: int


CHUNK_TARGET_TOKENS = 700
CHUNK_MAX_TOKENS = 900
CHUNK_OVERLAP_TOKENS = 100

_tokenizer = tiktoken.get_encoding("cl100k_base")


def _count_tokens(text: str) -> int:
    return len(_tokenizer.encode(text))


def _split_by_headings(text: str) -> list[tuple[str | None, str]]:
    sections: list[tuple[str | None, str]] = []
    current_heading: str | None = None
    current_lines: list[str] = []

    for line in text.split("\n"):
        heading_match = re.match(r"^(#{1,3})\s+(.+)$", line.strip())
        if heading_match:
            if current_lines:
                sections.append((current_heading, "\n".join(current_lines).strip()))
                current_lines = []
            current_heading = heading_match.group(2).strip()
        else:
            current_lines.append(line)

    if current_lines:
        sections.append((current_heading, "\n".join(current_lines).strip()))

    return sections


def chunk_page(page_title: str, clean_text: str) -> list[Chunk]:
    sections = _split_by_headings(clean_text)

    chunks: list[Chunk] = []
    chunk_index = 0

    for heading, content in sections:
        if not content:
            continue

        content_tokens = _count_tokens(content)

        if content_tokens <= CHUNK_MAX_TOKENS:
            chunks.append(_make_chunk(page_title, heading, content, chunk_index))
            chunk_index += 1
            continue

        paragraphs = _split_paragraphs(content)
        buffer: list[str] = []
        buffer_tokens = 0

        for para in paragraphs:
            para_tokens = _count_tokens(para)

            if para_tokens > CHUNK_MAX_TOKENS:
                if buffer:
                    chunk_content = "\n\n".join(buffer)
                    chunks.append(_make_chunk(page_title, heading, chunk_content, chunk_index))
                    chunk_index += 1
                    buffer = []
                    buffer_tokens = 0
                sub_chunks = _split_large_paragraph(page_title, heading, para, chunk_index)
                chunks.extend(sub_chunks)
                chunk_index += len(sub_chunks)
                continue

            if buffer_tokens + para_tokens > CHUNK_MAX_TOKENS and buffer:
                chunk_content = "\n\n".join(buffer)
                chunks.append(_make_chunk(page_title, heading, chunk_content, chunk_index))
                chunk_index += 1
                overlap = _compute_overlap(buffer, CHUNK_OVERLAP_TOKENS)
                buffer = overlap
                buffer_tokens = _count_tokens("\n\n".join(overlap))

            buffer.append(para)
            buffer_tokens += para_tokens

        if buffer:
            chunk_content = "\n\n".join(buffer)
            chunks.append(_make_chunk(page_title, heading, chunk_content, chunk_index))
            chunk_index += 1

    return chunks


def _make_chunk(page_title: str, heading: str | None, content: str, index: int) -> Chunk:
    parts = [f"Page: {page_title}"]
    if heading:
        parts.append(f"Section: {heading}")
    parts.append("")
    parts.append(content)

    full_content = "\n".join(parts)
    return Chunk(
        page_title=page_title,
        heading=heading,
        content=full_content,
        chunk_index=index,
        token_count=_count_tokens(full_content),
    )


def _split_paragraphs(text: str) -> list[str]:
    paragraphs = re.split(r"\n\s*\n", text)
    return [p.strip() for p in paragraphs if p.strip()]


def _compute_overlap(buffer: list[str], overlap_tokens: int) -> list[str]:
    overlap: list[str] = []
    tokens = 0
    for para in reversed(buffer):
        para_tokens = _count_tokens(para)
        if tokens + para_tokens > overlap_tokens:
            break
        overlap.insert(0, para)
        tokens += para_tokens
    return overlap


def _split_large_paragraph(
    page_title: str, heading: str | None, paragraph: str, start_index: int
) -> list[Chunk]:
    sentences = re.split(r"(?<=[.!?])\s+", paragraph)
    chunks: list[Chunk] = []
    buffer: list[str] = []
    buffer_tokens = 0
    index = start_index

    for sentence in sentences:
        sentence_tokens = _count_tokens(sentence)

        if sentence_tokens > CHUNK_MAX_TOKENS:
            if buffer:
                chunk_content = " ".join(buffer)
                chunks.append(_make_chunk(page_title, heading, chunk_content, index))
                index += 1
                buffer = []
                buffer_tokens = 0
            words = sentence.split()
            word_buffer: list[str] = []
            word_tokens = 0
            for word in words:
                word_tokens_word = _count_tokens(word + " ")
                if word_tokens + word_tokens_word > CHUNK_MAX_TOKENS and word_buffer:
                    chunk_content = " ".join(word_buffer)
                    chunks.append(_make_chunk(page_title, heading, chunk_content, index))
                    index += 1
                    word_buffer = [word]
                    word_tokens = word_tokens_word
                else:
                    word_buffer.append(word)
                    word_tokens += word_tokens_word
            if word_buffer:
                chunk_content = " ".join(word_buffer)
                chunks.append(_make_chunk(page_title, heading, chunk_content, index))
                index += 1
            continue

        if buffer_tokens + sentence_tokens > CHUNK_MAX_TOKENS and buffer:
            chunk_content = " ".join(buffer)
            chunks.append(_make_chunk(page_title, heading, chunk_content, index))
            index += 1
            overlap = _compute_overlap(buffer, CHUNK_OVERLAP_TOKENS // 2)
            buffer = overlap
            buffer_tokens = _count_tokens(" ".join(overlap))
            buffer.append(sentence)
            buffer_tokens += sentence_tokens
        else:
            buffer.append(sentence)
            buffer_tokens += sentence_tokens

    if buffer:
        chunk_content = " ".join(buffer)
        chunks.append(_make_chunk(page_title, heading, chunk_content, index))

    return chunks
