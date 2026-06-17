from fastapi import Header, HTTPException, status

from app.core.config import settings


async def require_admin(x_admin_api_key: str | None = Header(default=None)) -> None:
    if not settings.admin_api_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Admin API key is not configured.",
        )

    if x_admin_api_key != settings.admin_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid admin API key.",
        )


async def require_bot_or_admin(
    x_bot_api_key: str | None = Header(default=None),
    x_admin_api_key: str | None = Header(default=None),
) -> None:
    has_bot_key = bool(settings.bot_api_key)
    has_admin_key = bool(settings.admin_api_key)

    if not has_bot_key and not has_admin_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="No API keys are configured.",
        )

    if has_bot_key and x_bot_api_key == settings.bot_api_key:
        return
    if has_admin_key and x_admin_api_key == settings.admin_api_key:
        return

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid API key.",
    )
