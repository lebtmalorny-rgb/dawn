from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, datetime
from typing import Any

import pytest
import sqlalchemy as sa
from sqlalchemy.engine import Engine

from cloud_ui.audit import schema
from cloud_ui.audit.delivery import AuditDeliveryWorker
from cloud_ui.audit.repository import AuditRepository
from cloud_ui.audit.sinks import LocalTestAuditSink


def test_delivery_worker_records_successful_heartbeat(
    repository: AuditRepository,
    engine: Engine,
) -> None:
    sink = LocalTestAuditSink()
    worker = AuditDeliveryWorker(repository=repository, sink=sink, clock=lambda: _NOW)

    result = worker.run_heartbeat()

    heartbeats = _rows(engine, schema.audit_heartbeats)
    assert result.status == "heartbeat_ok"
    assert heartbeats == [
        {
            "sink_id": "local-test",
            "state": "ok",
            "last_success_at": _NOW,
            "last_failure_at": None,
            "queue_depth": 0,
            "oldest_pending_age_seconds": None,
            "updated_at": _NOW,
        }
    ]


def test_delivery_worker_records_failed_heartbeat(
    repository: AuditRepository,
    engine: Engine,
) -> None:
    sink = LocalTestAuditSink()
    sink.fail_temporarily("siem_unavailable")
    worker = AuditDeliveryWorker(repository=repository, sink=sink, clock=lambda: _NOW)

    result = worker.run_heartbeat()

    heartbeats = _rows(engine, schema.audit_heartbeats)
    assert result.status == "heartbeat_failed"
    assert heartbeats[0]["state"] == "failed"
    assert heartbeats[0]["last_failure_at"] == _NOW


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
