from collections.abc import Mapping, Sequence

from bot.i18n import DEFAULT_LANG, gettext

DISCORD_MESSAGE_LIMIT = 2000
TRUNCATION_SUFFIX = "\n\n[truncated]"


def format_klaris_response(
    payload: Mapping[str, object],
    language: str = DEFAULT_LANG,
) -> str:
    response = str(
        payload.get("response") or payload.get("answer") or "I could not find that information."
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
            parts.append(f"{gettext(language, 'sources_label')}:\n" + "\n".join(source_lines))

    message = "\n\n".join(part for part in parts if part)
    return _truncate_message(message)


def _truncate_message(message: str) -> str:
    if len(message) <= DISCORD_MESSAGE_LIMIT:
        return message
    max_body = DISCORD_MESSAGE_LIMIT - len(TRUNCATION_SUFFIX)
    if max_body <= 0:
        return TRUNCATION_SUFFIX[:DISCORD_MESSAGE_LIMIT]
    return message[:max_body].rstrip() + TRUNCATION_SUFFIX
