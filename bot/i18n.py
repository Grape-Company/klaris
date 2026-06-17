from __future__ import annotations

STRINGS: dict[str, dict[str, str]] = {
    "pt-BR": {
        "rate_limit_user": "Limite de requisições atingido. Tente novamente em breve.",
        "rate_limit_channel": "Canal muito rápido. Aguarde um momento.",
        "rate_limit_global": "Muitas requisições no momento. Tente novamente.",
        "service_unavailable": "O arquivo está temporariamente indisponível. "
        "Tente novamente em alguns segundos.",
        "auth_error": "O bot não está autorizado a acessar o arquivo. Avise o administrador.",
        "api_rate_limit": "Muitas solicitações no servidor. Aguarde um momento.",
        "general_failure": "Ocorreu um erro inesperado. Tente novamente.",
        "invalid_response": "O arquivo retornou uma resposta inesperada.",
        "not_found": "Não encontrei essa informação na base atual.",
        "feedback_recorded": "Feedback registrado. Obrigado!",
        "feedback_missing_answer_id": "Não foi possível registrar feedback: "
        "resposta não encontrada.",
        "sources_label": "Fontes",
        "answer_id_label": "ID da Resposta",
        "help_title": "Klaris — Comandos",
        "help_description": "Eu respondo perguntas sobre Deepwoken com base "
        "no arquivo da wiki. Se eu não souber, vou admitir.",
        "help_ask": "Pergunte sobre Deepwoken",
        "help_chat": "Converse com Klaris",
        "help_help": "Mostra esta mensagem",
        "help_stats": "Mostra estatísticas do arquivo",
        "help_invite": "Convite para adicionar o bot",
        "help_feedback": "Envia feedback sobre uma resposta",
        "stats_title": "Estatísticas do Arquivo",
        "stats_total_answers": "Respostas",
        "stats_total_feedback": "Feedbacks",
        "stats_positive": "Positivos",
        "stats_negative": "Negativos",
        "stats_corrections": "Correções",
        "invite_message": "Clique aqui para me adicionar ao seu servidor!",
        "question_too_long": "A pergunta é muito longa (máximo 2000 caracteres).",
        "context_cleared": "Memória de conversa limpa.",
        "no_context": "Nenhum contexto de conversa encontrado.",
        "footer_sources": "Fontes: {count}",
    },
    "en": {
        "rate_limit_user": "Rate limit reached. Try again shortly.",
        "rate_limit_channel": "Channel is too fast. Please wait.",
        "rate_limit_global": "Too many requests globally. Try again.",
        "service_unavailable": "The archive is temporarily unavailable. "
        "Try again in a few seconds.",
        "auth_error": "The bot is not authorized to access the archive. Notify the administrator.",
        "api_rate_limit": "Too many requests to the server. Please wait.",
        "general_failure": "An unexpected error occurred. Please try again.",
        "invalid_response": "The archive returned an unexpected response.",
        "not_found": "I could not find that information in the current archive.",
        "feedback_recorded": "Feedback recorded. Thank you!",
        "feedback_missing_answer_id": "Could not record feedback: answer not found.",
        "sources_label": "Sources",
        "answer_id_label": "Answer ID",
        "help_title": "Klaris — Commands",
        "help_description": "I answer Deepwoken questions based on the wiki archive. "
        "If I don't know, I'll admit it.",
        "help_ask": "Ask about Deepwoken",
        "help_chat": "Chat with Klaris",
        "help_help": "Shows this message",
        "help_stats": "Shows archive statistics",
        "help_invite": "Invite link to add the bot",
        "help_feedback": "Submit feedback about an answer",
        "stats_title": "Archive Statistics",
        "stats_total_answers": "Answers",
        "stats_total_feedback": "Feedback",
        "stats_positive": "Positive",
        "stats_negative": "Negative",
        "stats_corrections": "Corrections",
        "invite_message": "Click here to add me to your server!",
        "question_too_long": "Question is too long (max 2000 characters).",
        "context_cleared": "Conversation context cleared.",
        "no_context": "No conversation context found.",
        "footer_sources": "Sources: {count}",
    },
}

DEFAULT_LANG: str = "pt-BR"


def gettext(language: str, key: str, **fmt: str | int | float) -> str:
    """Resolve an i18n string by language and key, optionally formatting with kwargs."""
    lang = language if language in STRINGS else DEFAULT_LANG
    template = STRINGS[lang].get(key, key)
    if fmt:
        return template.format(**fmt)
    return template
