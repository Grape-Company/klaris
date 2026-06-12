from collections.abc import Mapping, Sequence

from openai.types.chat import ChatCompletionMessageParam

SYSTEM_PROMPT = """Você é um assistente especializado em Deepwoken.

Responda usando apenas as informações do CONTEXTO.
Se a resposta não estiver no CONTEXTO, diga:
"não encontrei essa informação na base atual."

Sempre cite as páginas usadas.
Não invente builds, números, talentos, requisitos ou mecânicas.
Não use conhecimento externo."""


def build_rag_prompt(
    question: str,
    context_chunks: Sequence[Mapping[str, object]],
) -> list[ChatCompletionMessageParam]:
    context_parts: list[str] = []

    for i, chunk in enumerate(context_chunks):
        header = f"[Fonte {i + 1}] Página: {chunk['page_title']}"
        heading = chunk["heading"]
        if heading:
            header += f" - Seção: {heading}"
        context_parts.append(f"{header}\n{chunk['content']}")

    context_text = "\n\n---\n\n".join(context_parts)

    messages: list[ChatCompletionMessageParam] = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": f"CONTEXTO:\n{context_text}\n\nPERGUNTA: {question}",
        },
    ]

    return messages
