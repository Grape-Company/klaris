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
    "how do i get ",
)
LEADING_SUBJECT_WORDS = {"a", "an", "the", "o", "os", "as", "um", "uma"}
TRAILING_SUBJECT_WORDS = {
    "requirement",
    "requirements",
    "req",
    "reqs",
    "location",
    "locations",
    "obtainment",
    "progression",
}
INVALID_SUBJECT_WORDS = {
    "como",
    "conseguir",
    "consigo",
    "pegar",
    "obter",
    "what",
    "how",
    "where",
    "who",
}
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
DEEPWOKEN_FACT_MARKERS = {
    "attunement",
    "attunements",
    "boss",
    "build",
    "deepwoken",
    "faction",
    "galebreathe",
    "item",
    "mantra",
    "oath",
    "oaths",
    "talent",
    "thundercall",
    "weapon",
}
PORTUGUESE_SUBJECT_PATTERNS = (
    re.compile(r"\bcomo\s+(?:consigo|conseguir|pegar|obter)\s+(?:a\s+|o\s+)?Oath\s+(.+)", re.I),
    re.compile(r"\bo\s+que\s+faz\s+(.+)", re.I),
    re.compile(r"\bonde\s+(?:fica|encontro|achar)\s+(.+)", re.I),
    re.compile(r"\bquem\s+(?:é|e)\s+(.+)", re.I),
    re.compile(r"\bo\s+que\s+(?:é|e)\s+(.+)", re.I),
)
TERM_SUBJECT_PATTERNS = (
    re.compile(r"\bOath\s+([A-Za-z][A-Za-z' -]{1,60})", re.I),
    re.compile(r"\b([A-Za-z][A-Za-z' -]{1,60})\s+Oath\b", re.I),
)


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

    for pattern in PORTUGUESE_SUBJECT_PATTERNS:
        match = pattern.search(normalized)
        if match:
            subject = normalize_subject(match.group(1))
            if subject.casefold().startswith("oath "):
                subject = normalize_subject(subject[5:])
            if subject:
                subjects.append(subject)

    for pattern in TERM_SUBJECT_PATTERNS:
        match = pattern.search(normalized)
        if match:
            subject = normalize_subject(match.group(1))
            subject_words = {word.casefold() for word in subject.split()}
            if subject and not subject_words.intersection(INVALID_SUBJECT_WORDS):
                subjects.append(subject)

    return list(dict.fromkeys(subjects))


def normalize_subject(subject: str) -> str:
    words = subject.strip(" ?.!,").split()
    while words and words[0].casefold() in LEADING_SUBJECT_WORDS:
        words.pop(0)
    while words and words[-1].casefold() in TRAILING_SUBJECT_WORDS:
        words.pop()
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

    if any(marker in compact for marker in PORTUGUESE_MARKERS):
        return "pt"
    return "en"


def not_found_answer(question: str) -> str:
    if preferred_language(question) == "pt":
        return PT_NOT_FOUND_ANSWER
    return EN_NOT_FOUND_ANSWER


def answer_indicates_not_found(answer: str) -> bool:
    lowered = answer.lower()
    return PT_NOT_FOUND_ANSWER in lowered or EN_NOT_FOUND_ANSWER.lower() in lowered


def needs_knowledge_search(message: str) -> bool:
    if small_talk_answer(message):
        return False

    intent = analyze_query(message)
    compact = intent.clean_query.casefold()
    if intent.subjects:
        return True

    if any(marker in compact for marker in DEEPWOKEN_FACT_MARKERS):
        return True

    question_markers = (
        "what ",
        "who ",
        "where ",
        "how ",
        "qual ",
        "quais ",
        "quem ",
        "onde ",
        "como ",
        "o que ",
    )
    return compact.endswith("?") and compact.startswith(question_markers)
