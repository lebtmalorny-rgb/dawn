from __future__ import annotations

from datetime import UTC, datetime

import sqlalchemy as sa

from cloud_ui.api import create_app
from cloud_ui.audit import schema
from cloud_ui.audit.models import AuditEvent
from cloud_ui.audit.repository import AuditRepository
from cloud_ui.audit.sink import DurableAuditSink
from cloud_ui.health import HealthReport
from cloud_ui.inventory.routes import InventoryServices


def test_durable_audit_sink_records_event_and_keeps_test_visible_copy() -> None:
    engine = sa.create_engine("sqlite+pysqlite:///:memory:", future=True)
    try:
        schema.metadata.create_all(engine)
        sink = DurableAuditSink(
            repository=AuditRepository(engine=engine, clock=lambda: _NOW),
            keep_events_for_tests=True,
        )

        sink.record(_event(metadata={"cookie": "DKB_CANARY_COOKIE", "normal": "visible"}))

        assert len(sink.events) == 1
        assert sink.events[0].metadata == {"cookie": "***", "normal": "visible"}
        with engine.connect() as connection:
            stored = connection.execute(sa.select(schema.audit_events)).mappings().one()
        assert stored["metadata_json"] == {"cookie": "***", "normal": "visible"}
    finally:
        engine.dispose()


def test_create_app_uses_durable_audit_sink_when_engine_is_available() -> None:
    engine = sa.create_engine("sqlite+pysqlite:///:memory:", future=True)
    try:
        app = create_app(
            readiness_check=lambda: HealthReport(status="ok", dependencies={}),
            inventory_services=InventoryServices(repository=None, engine=engine),
        )

        assert isinstance(app.state.security_services.audit_sink, DurableAuditSink)
    finally:
        engine.dispose()


def _event(**overrides: object) -> AuditEvent:
    values: dict[str, object] = {
        "event_id": "event-1",
        "event_version": "1.0",
        "occurred_at": _NOW,
        "actor_type": "human",
        "actor_id": "mock-user-auditor",
        "actor_display": "Security Auditor",
        "authentication_method": "mock",
        "session_reference": "session-1",
        "action": "audit.events.list",
        "event_type": "audit_access",
        "outcome": "success",
        "target_type": "audit_event",
        "target_id": "event-1",
        "request_id": "request-1",
        "correlation_id": "correlation-1",
        "service": "cloud-ui-api",
        "component": "audit-api",
        "delivery_state": "pending",
        "metadata": {"normal": "visible"},
    }
    values.update(overrides)
    return AuditEvent(**values)


_NOW = datetime(2026, 6, 22, 14, 0, tzinfo=UTC)
