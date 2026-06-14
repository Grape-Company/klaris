from app.modules.rag.prompt import SYSTEM_PROMPT, build_rag_prompt


def test_system_prompt_uses_klaris_persona_without_relaxing_rag_rules() -> None:
    normalized_prompt = " ".join(SYSTEM_PROMPT.split())

    assert "Klaris" in SYSTEM_PROMPT
    assert "EXCLUSIVAMENTE as informações presentes no CONTEXTO" in normalized_prompt
    assert "NÃO possui conhecimento externo" in SYSTEM_PROMPT
    assert "A personalidade nunca tem permissão para alterar fatos" in SYSTEM_PROMPT


def test_system_prompt_does_not_ask_model_to_render_sources_section() -> None:
    assert "Não crie uma seção de Fontes" in SYSTEM_PROMPT


def test_system_prompt_answers_in_same_language_as_user() -> None:
    assert "English is the primary language" in SYSTEM_PROMPT
    assert "If the user's language is ambiguous, answer in English" in SYSTEM_PROMPT
    assert (
        "A observação final de Klaris também deve seguir o idioma predominante"
        not in SYSTEM_PROMPT
    )


def test_system_prompt_does_not_force_portuguese_not_found_phrase() -> None:
    assert "frase de desconhecimento no idioma selecionado" in SYSTEM_PROMPT
    assert "I could not find that information in the current archive." in SYSTEM_PROMPT


def test_system_prompt_does_not_seed_portuguese_flavor_quote() -> None:
    assert "Poucos compreendem" not in SYSTEM_PROMPT


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
