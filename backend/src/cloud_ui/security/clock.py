from __future__ import annotations

from datetime import UTC, datetime, timedelta


class Clock:
    def now(self) -> datetime:
        return datetime.now(UTC)


class ManualClock(Clock):
    def __init__(self, initial: datetime | None = None) -> None:
        self._now = initial or datetime(2026, 6, 21, 7, 0, tzinfo=UTC)

    def now(self) -> datetime:
        return self._now

    def advance(self, *, seconds: int) -> None:
        self._now += timedelta(seconds=seconds)
