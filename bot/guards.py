from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass
from time import monotonic

import structlog

logger = structlog.get_logger()


@dataclass
class GuardResult:
    allowed: bool = True
    reason: str = ""
    i18n_key: str = ""

    def is_allowed(self) -> bool:
        return self.allowed


class WindowRateLimiter:
    def __init__(self, limit: int, window_seconds: int) -> None:
        self.limit = limit
        self.window_seconds = window_seconds
        self._events: dict[str, deque[float]] = defaultdict(deque)

    def allow(self, key: str, now: float | None = None) -> bool:
        current = monotonic() if now is None else now
        events = self._events[key]

        while events and current - events[0] >= self.window_seconds:
            events.popleft()

        if len(events) >= self.limit:
            return False

        events.append(current)
        return True

    def remaining(self, key: str, now: float | None = None) -> int:
        current = monotonic() if now is None else now
        events = self._events[key]

        while events and current - events[0] >= self.window_seconds:
            events.popleft()

        return max(0, self.limit - len(events))


class BotGuard:
    def __init__(
        self,
        user_limiter: WindowRateLimiter,
        channel_limiter: WindowRateLimiter,
        global_limiter: WindowRateLimiter,
        blacklisted_users: set[str],
        blacklisted_guilds: set[str],
    ) -> None:
        self._user_limiter = user_limiter
        self._channel_limiter = channel_limiter
        self._global_limiter = global_limiter
        self._blacklisted_users = blacklisted_users
        self._blacklisted_guilds = blacklisted_guilds

    def check_interaction(self, interaction: object) -> GuardResult:
        user_id = str(interaction.user.id)  # type: ignore[union-attr]
        channel_id = str(interaction.channel_id)  # type: ignore[union-attr]
        guild_id = str(interaction.guild_id) if interaction.guild_id else None  # type: ignore[union-attr]

        if user_id in self._blacklisted_users:
            return GuardResult(
                allowed=False,
                reason="user_blacklisted",
                i18n_key="user_blocked",
            )

        if guild_id and guild_id in self._blacklisted_guilds:
            return GuardResult(
                allowed=False,
                reason="guild_blacklisted",
                i18n_key="guild_blocked",
            )

        if not self._global_limiter.allow("global"):
            return GuardResult(
                allowed=False,
                reason="global_rate_limit",
                i18n_key="rate_limit_global",
            )

        channel_key = f"channel:{channel_id}"
        if not self._channel_limiter.allow(channel_key):
            return GuardResult(
                allowed=False,
                reason="channel_rate_limit",
                i18n_key="rate_limit_channel",
            )

        user_key = f"user:{user_id}"
        if not self._user_limiter.allow(user_key):
            return GuardResult(
                allowed=False,
                reason="user_rate_limit",
                i18n_key="rate_limit_user",
            )

        return GuardResult(allowed=True)
