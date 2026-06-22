from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
import sqlalchemy as sa
from sqlalchemy.engine import Engine

from cloud_ui.audit import schema
from cloud_ui.audit.models import AuditEvent
from cloud_ui.audit.repository import AuditReplayConflict, AuditRepository


@pytest.fixture()
def engine() -> Iterator[Engine]:
    engine = sa.create_engine("sqlite+pysqlite:///:memory:", future=True)
    schema.metadata.create_all(engine)
    yield engine
    engine.dispose()


@pytest.fixture()
def repository(engine: Engine) -> AuditRepository:
    return AuditRepository(engine=engine, clock=lambda: _NOW)


def test_record_event_persists_sanitized_event_and_outbox(
    repository: AuditRepository,
    engine: Engine,
) -> None:
    stored = repository.record_event(
        _event(metadata={"normal": "visible", "token": "DKB_CANARY_TOKEN"}),
        queue_delivery=True,
    )

    events = _rows(engine, schema.audit_events)
    outbox = _rows(engine, schema.audit_outbox)

    assert stored.event_id == "event-1"
    assert stored.metadata == {"normal": "visible", "token": "***"}
    assert events[0]["metadata_json"] == {"normal": "visible", "token": "***"}
    assert events[0]["delivery_state"] == "pending"
    assert events[0]["event_hash"]
    assert outbox[0]["event_id"] == "event-1"
    assert outbox[0]["state"] == "pending"
    assert outbox[0]["attempt_count"] == 0
    assert outbox[0]["envelope_json"]["metadata"] == {"normal": "visible", "token": "***"}
    assert "DKB_CANARY" not in repr(events)
    assert "DKB_CANARY" not in repr(outbox)


def test_record_event_replays_same_hash_without_duplicate_rows(
    repository: AuditRepository,
    engine: Engine,
) -> None:
    first = repository.record_event(_event(), queue_delivery=True)
    second = repository.record_event(_event(), queue_delivery=True)

    assert second == first
    assert len(_rows(engine, schema.audit_events)) == 1
    assert len(_rows(engine, schema.audit_outbox)) == 1


def test_record_event_rejects_same_event_id_with_different_payload(
    repository: AuditRepository,
) -> None:
    repository.record_event(_event(metadata={"normal": "first"}), queue_delivery=True)

    with pytest.raises(AuditReplayConflict) as exc_info:
        repository.record_event(_event(metadata={"normal": "second"}), queue_delivery=True)

    assert exc_info.value.event_id == "event-1"


def test_claim_next_outbox_item_uses_stable_order(repository: AuditRepository) -> None:
    repository.record_event(_event(event_id="event-1"), queue_delivery=True)
    repository.record_event(_event(event_id="event-2"), queue_delivery=True)

    first = repository.claim_next_outbox_item(now=_NOW + timedelta(seconds=1))
    second = repository.claim_next_outbox_item(now=_NOW + timedelta(seconds=1))

    assert first is not None
    assert first.event_id == "event-1"
    assert first.state == "claimed"
    assert first.attempt_count == 1
    assert second is not None
    assert second.event_id == "event-2"


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
        "delivery_state": "pending",
        "metadata": {"normal": "visible"},
    }
    values.update(overrides)
    return AuditEvent(**values)


def _rows(engine: Engine, table: sa.Table) -> list[dict[str, Any]]:
    with engine.connect() as connection:
        rows = list(connection.execute(sa.select(table)).mappings())
    return [_normalize_row(dict(row)) for row in rows]


def _normalize_row(row: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value.replace(tzinfo=UTC)
        if isinstance(value, datetime) and value.tzinfo is None
        else value
        for key, value in row.items()
    }


_NOW = datetime(2026, 6, 22, 14, 0, tzinfo=UTC)
