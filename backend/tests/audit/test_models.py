from __future__ import annotations

from datetime import UTC, datetime, timedelta, timezone

import pytest

from cloud_ui.audit.models import AuditDeliveryState, AuditEvent, AuditOutcome


def _event(**overrides: object) -> AuditEvent:
    values: dict[str, object] = {
        "event_id": "audit-event-1",
        "event_version": "1.0",
        "occurred_at": datetime(2026, 6, 22, 12, 0, 3, 123456, tzinfo=UTC),
        "actor_type": "human",
        "actor_id": "mock-user-auditor",
        "actor_display": "Security Auditor",
        "authentication_method": "mock",
        "session_reference": "session-1",
        "action": "audit.events.list",
        "event_type": "audit_access",
        "outcome": "success",
        "target_type": "audit_event",
        "target_id": "audit-event-1",
        "cloud_id": "lab-cloud",
        "region_id": "RegionOne",
        "project_id": "project-1",
        "scope_type": "project",
        "scope_id": "project-1",
        "source_ip": "192.0.2.10",
        "trusted_proxy_chain": ["198.51.100.1"],
        "request_id": "request-1",
        "correlation_id": "correlation-1",
        "operation_id": None,
        "external_execution_id": None,
        "service": "cloud-ui-api",
        "component": "audit-api",
        "safe_error_code": None,
        "delivery_state": "pending",
        "metadata": {"filter_count": 2},
    }
    values.update(overrides)
    return AuditEvent(**values)


def test_audit_event_contains_e07_mandatory_fields() -> None:
    event = _event()

    assert event.outcome == "success"
    assert event.delivery_state == "pending"
    assert event.trusted_proxy_chain == ("198.51.100.1",)
    assert event.cloud_id == "lab-cloud"
    assert event.region_id == "RegionOne"
    assert event.project_id == "project-1"
    assert event.scope_type == "project"
    assert event.scope_id == "project-1"
    assert event.component == "audit-api"


def test_audit_event_rejects_non_utc_timestamp() -> None:
    with pytest.raises(ValueError, match="must use UTC"):
        _event(occurred_at=datetime(2026, 6, 22, 15, 0, tzinfo=timezone(timedelta(hours=3))))


def test_audit_event_external_envelope_uses_second_precision() -> None:
    event = _event()

    envelope = event.to_delivery_envelope(sink_id="local-test")

    assert envelope["event_id"] == "audit-event-1"
    assert envelope["sink_id"] == "local-test"
    assert envelope["occurred_at"] == "2026-06-22T12:00:03Z"
    assert envelope["metadata"] == {"filter_count": 2}


def test_audit_outcome_and_delivery_state_literals_are_registered() -> None:
    assert set(AuditOutcome.__args__) == {"success", "failure", "unknown"}
    assert set(AuditDeliveryState.__args__) == {
        "not_queued",
        "pending",
        "claimed",
        "delivered",
        "retry_wait",
        "dead_letter",
    }
