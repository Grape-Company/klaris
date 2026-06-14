import re
from dataclasses import dataclass
from typing import Literal

Language = Literal["en", "pt"]

EN_NOT_FOUND_ANSWER = "I could not find that information in the current archive."
PT_NOT_FOUND_ANSWER = "não encontrei essa informação na base atual."

QUESTION_PREFIXES = (
    "what is ",
    "what are ",
    "who is ",
    "who are ",
    "where is ",
    "where are ",
    "how to get ",
)
LEADING_SUBJECT_WORDS = {"a", "an", "the", "o", "os", "as", "um", "uma"}
SMALL_TALK_GREETINGS = {
    "oi",
    "olá",
    "ola",
    "opa",
    "eai",
    "e aí",
    "hello",
    "hi",
    "hey",
    "bom dia",
    "boa tarde",
    "boa noite",
}
ENGLISH_SMALL_TALK_GREETINGS = {"hello", "hi", "hey"}
BOT_NAME_WORDS = {"klaris", "llfiend"}
PORTUGUESE_MARKERS = {
    "quem",
    "qual",
    "quais",
    "onde",
    "como",
    "porque",
    "por que",
    "o que",
    "não",
    "voce",
    "você",
    "sobre",
}


@dataclass(frozen=True)
class QueryIntent:
    raw_query: str
    clean_query: str
    language: Language
    subjects: list[str]


def analyze_query(query: str) -> QueryIntent:
    clean_query = clean_text(query)
    return QueryIntent(
        raw_query=query,
        clean_query=clean_query,
        language=preferred_language(clean_query),
        subjects=extract_subjects(clean_query),
    )


def clean_text(value: str) -> str:
    return " ".join(value.split()).strip(" ?.!").strip()


def extract_subjects(query: str) -> list[str]:
    normalized = clean_text(query)
    lowered = normalized.casefold()
    subjects: list[str] = []

    for prefix in QUESTION_PREFIXES:
        if lowered.startswith(prefix):
            subject = normalize_subject(normalized[len(prefix) :])
            if subject:
                subjects.append(subject)

    return list(dict.fromkeys(subjects))


def normalize_subject(subject: str) -> str:
    words = subject.strip(" ?.!,").split()
    while words and words[0].casefold() in LEADING_SUBJECT_WORDS:
        words.pop(0)
    return " ".join(words).strip(" ?.!,")


def small_talk_answer(question: str) -> str | None:
    normalized = re.sub(r"[^a-zA-ZÀ-ÿ\s]", " ", question.lower())
    words = [word for word in normalized.split() if word not in BOT_NAME_WORDS]
    normalized = " ".join(words)

    if normalized not in SMALL_TALK_GREETINGS:
        return None

    if normalized in ENGLISH_SMALL_TALK_GREETINGS:
        return (
            "Klaris stirs among old pages. Ask me about Deepwoken, and I will answer "
            "only with what the archive reveals."
        )

    return (
        "Klaris desperta entre páginas antigas. Faça sua pergunta sobre Deepwoken, "
        "e eu responderei apenas com o que a base revelar."
    )


def preferred_language(question: str) -> Language:
    normalized = re.sub(r"[^a-zA-ZÀ-ÿ\s]", " ", question.lower())
    compact = " ".join(normalized.split())
    words = set(compact.split())

    if any(marker in compact for marker in PORTUGUESE_MARKERS):
        return "pt"
    if words & PORTUGUESE_MARKERS:
        return "pt"
    return "en"


def not_found_answer(question: str) -> str:
    if preferred_language(question) == "pt":
        return PT_NOT_FOUND_ANSWER
    return EN_NOT_FOUND_ANSWER


def answer_indicates_not_found(answer: str) -> bool:
    lowered = answer.lower()
    return (
        PT_NOT_FOUND_ANSWER in lowered
        or EN_NOT_FOUND_ANSWER.lower() in lowered
    )
