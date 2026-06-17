from dataclasses import dataclass

from app.modules.rag.query import analyze_query
from app.modules.rag.retriever import RetrievedChunk

DISAMBIGUATION_MARKERS = (
    "disambiguation",
    "this might have not been the page you were looking for",
)
MAX_ALTERNATIVES = 3
MIN_ALTERNATIVE_SCORE = 0.2


@dataclass(frozen=True)
class DirectAnswer:
    answer: str
    source_chunks: list[RetrievedChunk]


def disambiguation_answer(question: str, chunks: list[RetrievedChunk]) -> DirectAnswer | None:
    if not chunks:
        return None

    primary = chunks[0]
    if not is_disambiguation_chunk(primary):
        return None

    intent = analyze_query(question)
    subject = intent.subjects[0] if intent.subjects else primary["page_title"]
    alternatives = nearby_alternatives(primary, chunks)

    if intent.language == "pt":
        answer = (
            f"Encontrei uma página de desambiguação para {subject}, mas não um artigo "
            "detalhado da entidade base na base atual."
        )
        if alternatives:
            answer += "\n\nPáginas próximas encontradas:\n" + "\n".join(
                f"- {chunk['page_title']}" for chunk in alternatives
            )
        answer += (
            "\n\nA base não tem detalhes suficientes para definir a entidade base com precisão."
        )
    else:
        answer = (
            f"I found a disambiguation page for {subject}, but not a detailed base "
            "article for the base entity in the current archive."
        )
        if alternatives:
            answer += "\n\nNearby pages found:\n" + "\n".join(
                f"- {chunk['page_title']}" for chunk in alternatives
            )
        answer += (
            "\n\nThe archive does not contain enough detail to define the base entity precisely."
        )

    return DirectAnswer(answer=answer, source_chunks=[primary])


def is_disambiguation_chunk(chunk: RetrievedChunk) -> bool:
    content = chunk["content"].casefold()
    return any(marker in content for marker in DISAMBIGUATION_MARKERS)


def nearby_alternatives(
    primary: RetrievedChunk,
    chunks: list[RetrievedChunk],
) -> list[RetrievedChunk]:
    alternatives: list[RetrievedChunk] = []
    seen: set[str] = {primary["page_title"]}

    for chunk in chunks[1:]:
        if chunk["score"] < MIN_ALTERNATIVE_SCORE:
            continue
        if chunk["page_title"] in seen:
            continue
        alternatives.append(chunk)
        seen.add(chunk["page_title"])
        if len(alternatives) >= MAX_ALTERNATIVES:
            break

    return alternatives
