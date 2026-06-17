from app.modules.rag.query import (
    analyze_query,
    answer_indicates_not_found,
    needs_knowledge_search,
    not_found_answer,
    preferred_language,
    small_talk_answer,
)


def test_small_talk_answer_handles_greetings_without_sources() -> None:
    answer = small_talk_answer("oi")

    assert answer is not None
    assert "Klaris" in answer
    assert "Ask me" in answer
    assert "Faça sua pergunta" not in answer


def test_small_talk_answer_handles_english_greeting_with_bot_name() -> None:
    answer = small_talk_answer("hello, klaris")

    assert answer is not None
    assert "Ask me" in answer
    assert "Faça sua pergunta" not in answer


def test_small_talk_answer_ignores_real_questions() -> None:
    assert small_talk_answer("what is Shrine of Order?") is None


def test_answer_indicates_not_found_matches_supported_phrases() -> None:
    assert answer_indicates_not_found("I could not find that information in the current archive.")


def test_answer_indicates_not_found_ignores_real_answer() -> None:
    assert not answer_indicates_not_found("Shrine of Order averages your stats.")


def test_preferred_language_defaults_to_english_for_english_or_ambiguous_text() -> None:
    assert preferred_language("who is Ethiron?") == "en"
    assert preferred_language("Ethiron") == "en"


def test_preferred_language_detects_portuguese() -> None:
    assert preferred_language("quem é Ethiron?") == "pt"


def test_not_found_answer_is_always_english() -> None:
    assert not_found_answer("who is Ethiron?") == (
        "I could not find that information in the current archive."
    )
    assert not_found_answer("quem é Ethiron?") == (
        "I could not find that information in the current archive."
    )


def test_analyze_query_extracts_clean_subject_without_leading_article() -> None:
    intent = analyze_query("what is the megalodount?")

    assert intent.clean_query == "what is the megalodount"
    assert intent.subjects == ["megalodount"]


def test_analyze_query_extracts_oath_subject_from_portuguese_question() -> None:
    intent = analyze_query("como conseguir a Oath Blightsurger?")

    assert intent.subjects == ["Blightsurger"]


def test_analyze_query_extracts_subject_from_oath_requirements_query() -> None:
    intent = analyze_query("Blightsurger Oath requirements")

    assert intent.subjects == ["Blightsurger"]


def test_needs_knowledge_search_routes_deepwoken_factual_questions() -> None:
    assert needs_knowledge_search("como conseguir a Oath Blightsurger?")
    assert not needs_knowledge_search("oi Klaris")
