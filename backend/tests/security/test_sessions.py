from __future__ import annotations

from datetime import timedelta

from cloud_ui.security.dependencies import build_security_services
from cloud_ui.security.identity import LoginRequest


def test_session_manager_defaults_to_900_second_idle_timeout() -> None:
    security = build_security_services()
    subject = security.identity_provider.authenticate(
        LoginRequest(login="viewer", credential="viewer-code")
    ).subject

    session = security.session_manager.create_session(subject)

    assert session.idle_expires_at == session.created_at + timedelta(seconds=900)
