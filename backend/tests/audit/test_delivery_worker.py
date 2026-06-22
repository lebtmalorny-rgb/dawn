from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
import sqlalchemy as sa
from sqlalchemy.engine import Engine

from cloud_ui.audit import schema
from cloud_ui.audit.delivery import AuditDeliveryWorker
from cloud_ui.audit.models import AuditEvent
from cloud_ui.audit.repository import AuditRepository
from cloud_ui.audit.sinks import LocalTestAuditSink


def test_delivery_worker_delivers_pending_event(
    repository: AuditRepository,
    engine: Engine,
) -> None:
    repository.record_event(_event(event_id="event-1"), queue_delivery=True)
    sink = LocalTestAuditSink()
    worker = AuditDeliveryWorker(repository=repository, sink=sink, clock=lambda: _NOW)

    result = worker.run_once()

    assert result.processed is True
    assert result.event_id == "event-1"
    assert result.status == "delivered"
    assert [envelope["event_id"] for envelope in sink.envelopes] == ["event-1"]
    events = _rows(engine, schema.audit_events)
    outbox = _rows(engine, schema.audit_outbox)[0]
    attempts = _rows(engine, schema.audit_delivery_attempts)
    assert events[0]["delivery_state"] == "delivered"
    assert outbox["state"] == "delivered"
    assert outbox["sink_message_id"] == "local-test:event-1"
    assert attempts[0]["outcome"] == "success"


def test_delivery_worker_retries_temporary_failure_and_recovers(
    repository: AuditRepository,
    engine: Engine,
) -> None:
    repository.record_event(_event(event_id="event-1"), queue_delivery=True)
    sink = LocalTestAuditSink()
    sink.fail_temporarily("siem_unavailable")
    worker = AuditDeliveryWorker(
        repository=repository,
        sink=sink,
        retry_delay_seconds=30,
        clock=lambda: _NOW,
    )

    failed = worker.run_once()
    sink.recover()
    recovered = AuditDeliveryWorker(
        repository=repository,
        sink=sink,
        retry_delay_seconds=30,
        clock=lambda: _NOW + timedelta(seconds=31),
    ).run_once()

    outbox = _rows(engine, schema.audit_outbox)[0]
    attempts = _rows(engine, schema.audit_delivery_attempts)
    assert failed.status == "retry_wait"
    assert recovered.status == "delivered"
    assert outbox["state"] == "delivered"
    assert [attempt["outcome"] for attempt in attempts] == ["temporary_failure", "success"]


def test_delivery_worker_dead_letters_temporary_failure_after_max_attempts(
    repository: AuditRepository,
    engine: Engine,
) -> None:
    repository.record_event(_event(event_id="event-1"), queue_delivery=True)
    sink = LocalTestAuditSink()
    sink.fail_temporarily("siem_unavailable")

    first = AuditDeliveryWorker(
        repository=repository,
        sink=sink,
        retry_delay_seconds=30,
        max_attempts=2,
        clock=lambda: _NOW,
    ).run_once()
    second = AuditDeliveryWorker(
        repository=repository,
        sink=sink,
        retry_delay_seconds=30,
        max_attempts=2,
        clock=lambda: _NOW + timedelta(seconds=31),
    ).run_once()

    outbox = _rows(engine, schema.audit_outbox)[0]
    attempts = _rows(engine, schema.audit_delivery_attempts)
    assert first.status == "retry_wait"
    assert second.status == "dead_letter"
    assert outbox["state"] == "dead_letter"
    assert outbox["last_error_code"] == "siem_unavailable"
    assert [attempt["outcome"] for attempt in attempts] == [
        "temporary_failure",
        "temporary_failure",
    ]


def test_delivery_worker_dead_letters_permanent_failure(
    repository: AuditRepository,
    engine: Engine,
) -> None:
    repository.record_event(_event(event_id="event-1"), queue_delivery=True)
    sink = LocalTestAuditSink()
    sink.fail_permanently("schema_rejected")
    worker = AuditDeliveryWorker(repository=repository, sink=sink, clock=lambda: _NOW)

    result = worker.run_once()

    outbox = _rows(engine, schema.audit_outbox)[0]
    attempts = _rows(engine, schema.audit_delivery_attempts)
    assert result.status == "dead_letter"
    assert outbox["state"] == "dead_letter"
    assert outbox["last_error_code"] == "schema_rejected"
    assert attempts[0]["outcome"] == "permanent_failure"


def test_delivery_worker_returns_idle_when_no_item(repository: AuditRepository) -> None:
    result = AuditDeliveryWorker(
        repository=repository,
        sink=LocalTestAuditSink(),
        clock=lambda: _NOW,
    ).run_once()

    assert result.processed is False
    assert result.status == "idle"


@sa.event.listens_for(sa.engine.Engine, "connect")
def _set_sqlite_pragma(dbapi_connection: Any, _connection_record: Any) -> None:
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


def _event(**overrides: Any) -> AuditEvent:
    values: dict[str, Any] = {
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
        "metadata": {"normal": "visible"},
    }
    values.update(overrides)
    return AuditEvent(**values)


def _rows(engine: Engine, table: sa.Table) -> list[dict[str, Any]]:
    with engine.connect() as connection:
        rows = list(connection.execute(sa.select(table)).mappings())
    return [dict(row) for row in rows]


_NOW = datetime(2026, 6, 22, 15, 0, tzinfo=UTC)


@pytest.fixture()
def engine() -> Iterator[Engine]:
    engine = sa.create_engine("sqlite+pysqlite:///:memory:", future=True)
    schema.metadata.create_all(engine)
    yield engine
    engine.dispose()


@pytest.fixture()
def repository(engine: Engine) -> AuditRepository:
    return AuditRepository(engine=engine, clock=lambda: _NOW)
