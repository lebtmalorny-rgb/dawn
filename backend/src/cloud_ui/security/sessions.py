from __future__ import annotations

import hmac
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Literal

from cloud_ui.security.clock import Clock
from cloud_ui.security.identity import Subject

SessionLimitPolicy = Literal["deny", "disconnect_oldest"]


class SessionNotFound(Exception):
    """Raised when a session cookie is absent or unknown."""


class SessionExpired(Exception):
    """Raised when a session exists but is no longer active."""


class SessionLimitReached(Exception):
    """Raised when the configured simultaneous-session policy denies login."""


@dataclass
class SessionRecord:
    session_id: str
    subject: Subject
    created_at: datetime
    last_seen_at: datetime
    idle_expires_at: datetime
    absolute_expires_at: datetime
    csrf: str
    revoked_at: datetime | None = None


class SessionManager:
    def __init__(
        self,
        *,
        clock: Clock,
        idle_timeout_seconds: int = 900,
        absolute_lifetime_seconds: int = 28_800,
        simultaneous_session_limit: int = 1,
        session_limit_policy: SessionLimitPolicy = "deny",
    ) -> None:
        self._clock = clock
        self._idle_timeout = timedelta(seconds=idle_timeout_seconds)
        self._absolute_lifetime = timedelta(seconds=absolute_lifetime_seconds)
        self._limit = simultaneous_session_limit
        self._limit_policy = session_limit_policy
        self._sessions: dict[str, SessionRecord] = {}

    def create_session(self, subject: Subject) -> SessionRecord:
        self._enforce_session_limit(subject)
        now = self._clock.now()
        session = SessionRecord(
            session_id=secrets.token_urlsafe(32),
            subject=subject,
            created_at=now,
            last_seen_at=now,
            idle_expires_at=now + self._idle_timeout,
            absolute_expires_at=now + self._absolute_lifetime,
            csrf=secrets.token_urlsafe(32),
        )
        self._sessions[session.session_id] = session
        return session

    def get_session(self, session_id: str | None) -> SessionRecord:
        if not session_id:
            raise SessionNotFound()
        session = self._sessions.get(session_id)
        if session is None or session.revoked_at is not None:
            raise SessionNotFound()

        now = self._clock.now()
        if session.idle_expires_at <= now or session.absolute_expires_at <= now:
            session.revoked_at = now
            raise SessionExpired()

        session.last_seen_at = now
        session.idle_expires_at = now + self._idle_timeout
        return session

    def revoke(self, session: SessionRecord) -> None:
        session.revoked_at = self._clock.now()

    def revoke_session_id(self, session_id: str) -> SessionRecord:
        session = self._sessions.get(session_id)
        if session is None or session.revoked_at is not None:
            raise SessionNotFound()
        session.revoked_at = self._clock.now()
        return session

    def list_active_sessions(self) -> list[SessionRecord]:
        now = self._clock.now()
        return sorted(
            [
                session
                for session in self._sessions.values()
                if session.revoked_at is None
                and session.idle_expires_at > now
                and session.absolute_expires_at > now
            ],
            key=lambda session: session.created_at,
        )

    def verify_csrf(self, session: SessionRecord, value: str | None) -> bool:
        return value is not None and hmac.compare_digest(session.csrf, value)

    def _enforce_session_limit(self, subject: Subject) -> None:
        active_sessions = [
            session
            for session in self._sessions.values()
            if session.subject.subject_id == subject.subject_id
            and session.revoked_at is None
            and session.idle_expires_at > self._clock.now()
            and session.absolute_expires_at > self._clock.now()
        ]
        if len(active_sessions) < self._limit:
            return
        if self._limit_policy == "disconnect_oldest":
            oldest = min(active_sessions, key=lambda session: session.created_at)
            oldest.revoked_at = self._clock.now()
            return
        raise SessionLimitReached()
