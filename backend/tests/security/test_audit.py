from __future__ import annotations

from datetime import UTC, datetime, timedelta, timezone

import pytest

from cloud_ui.security.audit import AuditEvent, InMemoryAuditSink


def test_audit_event_redacts_canary_metadata_before_storage() -> None:
    sink = InMemoryAuditSink()
    event = AuditEvent(
        event_id="event-1",
        event_version="1",
        occurred_at=datetime(2026, 6, 21, 7, 0, tzinfo=UTC),
        actor_type="human",
        actor_id="mock-user-operator",
        actor_display="Оператор облака",
        authentication_method="mock",
        session_reference="session-1",
        action="session.login",
        event_type="auth",
        outcome="success",
        target_type="session",
        target_id="session-1",
        request_id="request-1",
        correlation_id="request-1",
        service="cloud-ui-api",
        metadata={
            "auth_" + "token": "canary-value",
            "normal": "visible",
        },
    )

    sink.record(event)

    stored = sink.events[0]
    assert stored.metadata["auth_" + "token"] == "***"
    assert stored.metadata["normal"] == "visible"


def test_audit_event_requires_utc_timestamp() -> None:
    event = AuditEvent(
        event_id="event-1",
        event_version="1",
        occurred_at=datetime(2026, 6, 21, 7, 0, tzinfo=UTC),
        actor_type="system",
        actor_id="anonymous",
        actor_display="anonymous",
        authentication_method="none",
        session_reference=None,
        action="session.login",
        event_type="auth",
        outcome="failure",
        target_type="session",
        target_id=None,
        request_id="request-1",
        correlation_id="request-1",
        service="cloud-ui-api",
        metadata={},
    )

    assert event.occurred_at.tzinfo is UTC


def test_audit_event_rejects_non_utc_timestamp() -> None:
    with pytest.raises(ValueError, match="must use UTC"):
        AuditEvent(
            event_id="event-1",
            event_version="1",
            occurred_at=datetime(2026, 6, 21, 10, 0, tzinfo=timezone(timedelta(hours=3))),
            actor_type="system",
            actor_id="anonymous",
            actor_display="anonymous",
            authentication_method="none",
            session_reference=None,
            action="session.login",
            event_type="auth",
            outcome="failure",
            target_type="session",
            target_id=None,
            request_id="request-1",
            correlation_id="request-1",
            service="cloud-ui-api",
            metadata={},
        )
