from collections import defaultdict, deque
from time import monotonic


class UserRateLimiter:
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
