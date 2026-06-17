from app.modules.rag.prompt import SYSTEM_PROMPT, build_rag_prompt


def test_system_prompt_uses_klaris_persona_without_relaxing_rag_rules() -> None:
    normalized_prompt = " ".join(SYSTEM_PROMPT.split())

    assert "Klaris" in SYSTEM_PROMPT
    assert "using ONLY the information present in the supplied CONTEXT" in normalized_prompt
    assert "You have no external knowledge" in SYSTEM_PROMPT
    assert "Personality is never allowed to alter facts" in SYSTEM_PROMPT


def test_system_prompt_does_not_ask_model_to_render_sources_section() -> None:
    assert "Do not create a Sources section" in SYSTEM_PROMPT


def test_system_prompt_forces_english_responses() -> None:
    assert "Always answer in English." in SYSTEM_PROMPT
    assert "Do not switch to Portuguese" in SYSTEM_PROMPT
    assert (
        "A observação final de Klaris também deve seguir o idioma predominante"
        not in SYSTEM_PROMPT
    )


def test_system_prompt_uses_only_english_not_found_phrase() -> None:
    assert "frase de desconhecimento no idioma selecionado" not in SYSTEM_PROMPT
    assert "I could not find that information in the current archive." in SYSTEM_PROMPT
    assert "não encontrei essa informação na base atual" not in SYSTEM_PROMPT


def test_system_prompt_does_not_seed_portuguese_flavor_quote() -> None:
    assert "Poucos compreendem" not in SYSTEM_PROMPT


def test_klaris_prompt_forbids_unverified_deepwoken_facts() -> None:
    from app.modules.klaris.prompt import KLARIS_SYSTEM_PROMPT

    normalized_prompt = " ".join(KLARIS_SYSTEM_PROMPT.split())

    assert (
        "never answer Deepwoken-specific factual questions without archive evidence"
        in normalized_prompt
    )
    assert "Do not rely on your own experience" in KLARIS_SYSTEM_PROMPT
    assert "If no archive result supports the answer" in KLARIS_SYSTEM_PROMPT
    assert "Personal tone is allowed; personal factual claims are not" in KLARIS_SYSTEM_PROMPT


def test_klaris_prompt_forces_english_responses() -> None:
    from app.modules.klaris.prompt import KLARIS_SYSTEM_PROMPT

    assert "Always answer in English." in KLARIS_SYSTEM_PROMPT
    assert "Do not switch to Portuguese" in KLARIS_SYSTEM_PROMPT


def test_build_rag_prompt_keeps_context_and_question() -> None:
    messages = build_rag_prompt(
        "what is Shrine of Order?",
        [
            {
                "page_title": "Deep Shrines/Shrine of Order",
                "heading": "Effects",
                "content": "For 10, average your stats.",
            }
        ],
    )

    assert messages[0]["role"] == "system"
    assert messages[1]["role"] == "user"
    assert "Deep Shrines/Shrine of Order" in str(messages[1]["content"])
    assert "what is Shrine of Order?" in str(messages[1]["content"])
