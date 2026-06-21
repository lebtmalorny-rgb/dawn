from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from cloud_ui.config import Settings
from cloud_ui.security.audit import InMemoryAuditSink
from cloud_ui.security.clock import ManualClock
from cloud_ui.security.identity import IdentityProvider
from cloud_ui.security.mock_identity import build_mock_identity_provider
from cloud_ui.security.rbac import PolicyService
from cloud_ui.security.sessions import SessionManager

CookieSameSite = Literal["lax", "strict"]


@dataclass
class SecurityServices:
    identity_provider: IdentityProvider
    session_manager: SessionManager
    audit_sink: InMemoryAuditSink
    policy_service: PolicyService
    clock: ManualClock
    session_cookie_secure: bool
    session_cookie_samesite: CookieSameSite
    trusted_origins: frozenset[str]


def build_security_services(settings: Settings | None = None) -> SecurityServices:
    clock = ManualClock()
    session_cookie_samesite: CookieSameSite
    if settings is None:
        identity_provider = build_mock_identity_provider()
        session_cookie_secure = False
        session_cookie_samesite = "lax"
        trusted_origins = frozenset({"http://localhost", "http://127.0.0.1", "http://testserver"})
        session_manager = SessionManager(clock=clock)
    else:
        if settings.identity_provider != "mock" or not settings.mock_identity_enabled:
            raise ValueError("Only the P0 mock identity provider is implemented")
        identity_provider = build_mock_identity_provider()
        session_cookie_secure = settings.session_cookie_secure
        session_cookie_samesite = settings.session_cookie_samesite
        trusted_origins = frozenset(settings.trusted_origins)
        session_manager = SessionManager(
            clock=clock,
            idle_timeout_seconds=settings.session_idle_timeout_seconds,
            absolute_lifetime_seconds=settings.session_absolute_lifetime_seconds,
            simultaneous_session_limit=settings.simultaneous_session_limit,
            session_limit_policy=settings.session_limit_policy,
        )
    return SecurityServices(
        identity_provider=identity_provider,
        session_manager=session_manager,
        audit_sink=InMemoryAuditSink(),
        policy_service=PolicyService(),
        clock=clock,
        session_cookie_secure=session_cookie_secure,
        session_cookie_samesite=session_cookie_samesite,
        trusted_origins=trusted_origins,
    )
