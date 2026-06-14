from collections.abc import Mapping, Sequence

DISCORD_MESSAGE_LIMIT = 2000
TRUNCATION_SUFFIX = "\n\n[truncated]"


def format_klaris_response(payload: Mapping[str, object]) -> str:
    response = str(
        payload.get("response")
        or payload.get("answer")
        or "I could not find that information."
    )
    sources = payload.get("sources")

    parts = [response.strip()]
    if isinstance(sources, Sequence) and not isinstance(sources, str) and sources:
        source_lines = []
        for source in sources[:5]:
            if not isinstance(source, Mapping):
                continue
            title = source.get("title")
            url = source.get("url")
            if title and url:
                source_lines.append(f"- {title}: {url}")
        if source_lines:
            parts.append(f"{_source_heading(response)}:\n" + "\n".join(source_lines))

    message = "\n\n".join(part for part in parts if part)
    return _truncate_message(message)


def _source_heading(text: str) -> str:
    portuguese_markers = {
        " o ",
        " a ",
        " os ",
        " as ",
        " de ",
        " da ",
        " do ",
        " dos ",
        " das ",
        " que ",
        " não ",
        " uma ",
        " seu ",
        " sua ",
    }
    normalized = f" {text.lower()} "
    if any(marker in normalized for marker in portuguese_markers):
        return "Fontes"
    return "Sources"


def _truncate_message(message: str) -> str:
    if len(message) <= DISCORD_MESSAGE_LIMIT:
        return message
    max_body = DISCORD_MESSAGE_LIMIT - len(TRUNCATION_SUFFIX)
    if max_body <= 0:
        return TRUNCATION_SUFFIX[:DISCORD_MESSAGE_LIMIT]
    return message[:max_body].rstrip() + TRUNCATION_SUFFIX
