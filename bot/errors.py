from __future__ import annotations

import httpx
import structlog

logger = structlog.get_logger()


class BotError(Exception):
    """Base exception for bot errors."""


class ApiConnectionError(BotError):
    """Connection/timeout errors."""


class ApiAuthError(BotError):
    """401/403 errors."""


class ApiRateLimitError(BotError):
    """429 errors."""


class ApiServerError(BotError):
    """5xx errors."""


class ApiUnexpectedError(BotError):
    """Unexpected response format."""


async def handle_api_error(
    exc: Exception,
    status_code: int | None = None,
    endpoint: str | None = None,
    duration_ms: float | None = None,
) -> str:
    """Maps any exception to a user-facing i18n key. Logs structured context."""
    logger.error(
        "api_error",
        error_type=type(exc).__name__,
        error_message=str(exc),
        status_code=status_code,
        endpoint=endpoint,
        duration_ms=duration_ms,
    )

    if isinstance(exc, httpx.HTTPStatusError):
        actual = exc.response.status_code
        if actual == 429:
            return "api_rate_limit"
        if actual in (401, 403):
            return "auth_error"
        if actual >= 500:
            return "service_unavailable"
        if actual == 404:
            return "not_found"
        return "general_failure"

    if isinstance(exc, (httpx.ConnectError, httpx.TimeoutException)):
        return "service_unavailable"

    if isinstance(exc, ValueError):
        return "invalid_response"

    return "general_failure"


def map_status_to_error(status_code: int, language: str) -> str:
    """Maps HTTP status code to an i18n key. Language reserved for locale-specific mapping."""
    _ = language
    if status_code == 429:
        return "api_rate_limit"
    if status_code in (401, 403):
        return "auth_error"
    if status_code >= 500:
        return "service_unavailable"
    if status_code == 404:
        return "not_found"
    return "general_failure"
