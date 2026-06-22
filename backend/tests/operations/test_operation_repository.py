from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
import sqlalchemy as sa
from sqlalchemy.engine import Engine

from cloud_ui.operations import schema
from cloud_ui.operations.models import OperationTargetCreate
from cloud_ui.operations.repository import (
    OperationIdempotencyConflict,
    OperationRepository,
)
from cloud_ui.operations.state_machine import OperationTransitionError


@pytest.fixture()
def engine() -> Iterator[Engine]:
    engine = sa.create_engine("sqlite+pysqlite:///:memory:", future=True)
    schema.metadata.create_all(engine)
    yield engine
    engine.dispose()


@pytest.fixture()
def repository(engine: Engine) -> OperationRepository:
    return OperationRepository(engine=engine, clock=lambda: _NOW)


def test_accept_operation_persists_operation_targets_event_outbox_and_idempotency(
    repository: OperationRepository,
    engine: Engine,
) -> None:
    operation = repository.accept_operation(
        operation_id="operation-0001",
        workflow_key="maintenance-host-precheck",
        workflow_version="1.0.0",
        definition_checksum="checksum-1",
        actor_subject_id="mock-user-admin",
        scope_type="system",
        scope_id=None,
        idempotency_key_hash="key-hash-1",
        request_hash="request-hash-1",
        correlation_id="corr-operation-0001",
        input_json={"reason": "maintenance dry run"},
        targets=[
            OperationTargetCreate(
                target_type="host",
                cloud_id="synthetic",
                region_id="RegionOne",
                resource_id="hypervisor-0001",
                snapshot={"host_name": "compute-a", "service_state": "up"},
            )
        ],
    )

    assert operation.operation_id == "operation-0001"
    assert operation.status == "accepted"
    assert operation.external_execution_id is None
    assert operation.created_at == _NOW
    assert repository.get_operation("operation-0001") == operation

    events = repository.list_events("operation-0001", limit=10)
    targets = _rows(engine, schema.operation_targets)
    outbox = _rows(engine, schema.operation_outbox)
    idempotency = _rows(engine, schema.operation_idempotency_keys)

    assert [(event.event_type, event.to_status) for event in events] == [
        ("operation.accepted", "accepted")
    ]
    assert targets == [
        {
            "operation_id": "operation-0001",
            "target_type": "host",
            "cloud_id": "synthetic",
            "region_id": "RegionOne",
            "resource_id": "hypervisor-0001",
            "snapshot_json": {"host_name": "compute-a", "service_state": "up"},
            "status": "accepted",
            "created_at": _NOW,
            "updated_at": _NOW,
        }
    ]
    assert [row["operation_id"] for row in outbox] == ["operation-0001"]
    assert outbox[0]["state"] == "pending"
    assert idempotency == [
        {
            "actor_subject_id": "mock-user-admin",
            "workflow_key": "maintenance-host-precheck",
            "workflow_version": "1.0.0",
            "scope_hash": "system:",
            "key_hash": "key-hash-1",
            "request_hash": "request-hash-1",
            "operation_id": "operation-0001",
            "created_at": _NOW,
        }
    ]


def test_accept_operation_replays_same_idempotency_key_and_request(
    repository: OperationRepository,
    engine: Engine,
) -> None:
    first = _accept(repository, operation_id="operation-0001")
    second = _accept(repository, operation_id="operation-0002")

    assert second == first
    assert [row["operation_id"] for row in _rows(engine, schema.operations)] == [
        "operation-0001"
    ]
    assert [row["operation_id"] for row in _rows(engine, schema.operation_outbox)] == [
        "operation-0001"
    ]


def test_accept_operation_rejects_same_idempotency_key_with_different_request(
    repository: OperationRepository,
    engine: Engine,
) -> None:
    _accept(repository, operation_id="operation-0001", request_hash="request-hash-1")

    with pytest.raises(OperationIdempotencyConflict) as exc_info:
        _accept(repository, operation_id="operation-0002", request_hash="request-hash-2")

    assert exc_info.value.existing_operation_id == "operation-0001"
    assert [row["operation_id"] for row in _rows(engine, schema.operations)] == [
        "operation-0001"
    ]


def test_idempotency_key_is_bound_to_workflow_version(
    repository: OperationRepository,
    engine: Engine,
) -> None:
    first = _accept(
        repository,
        operation_id="operation-0001",
        workflow_version="1.0.0",
        request_hash="request-hash-v1",
    )
    second = _accept(
        repository,
        operation_id="operation-0002",
        workflow_version="1.0.1",
        request_hash="request-hash-v2",
    )

    assert first.operation_id == "operation-0001"
    assert second.operation_id == "operation-0002"
    assert [row["operation_id"] for row in _rows(engine, schema.operations)] == [
        "operation-0001",
        "operation-0002",
    ]


def test_transition_operation_enforces_state_machine_and_appends_timeline(
    repository: OperationRepository,
) -> None:
    _accept(repository, operation_id="operation-0001")

    queued = repository.transition_operation(
        operation_id="operation-0001",
        desired_status="queued",
        event_type="operation.queued",
        safe_message="Operation queued for dispatch",
        metadata={"outbox_id": "outbox-0001"},
    )
    with pytest.raises(OperationTransitionError):
        repository.transition_operation(
            operation_id="operation-0001",
            desired_status="succeeded",
            event_type="operation.completed",
            safe_message="Unsafe shortcut",
            metadata={},
        )

    assert queued.status == "queued"
    assert [
        (event.event_type, event.from_status, event.to_status)
        for event in repository.list_events("operation-0001", limit=10)
    ] == [
        ("operation.accepted", None, "accepted"),
        ("operation.queued", "accepted", "queued"),
    ]


def test_outbox_claim_and_mark_dispatched_are_stable(repository: OperationRepository) -> None:
    _accept(repository, operation_id="operation-0001")
    _accept(
        repository,
        operation_id="operation-0002",
        idempotency_key_hash="key-hash-2",
        request_hash="request-hash-2",
    )

    first = repository.claim_next_outbox_item(now=_NOW + timedelta(seconds=1))
    second = repository.claim_next_outbox_item(now=_NOW + timedelta(seconds=1))

    assert first is not None
    assert first.operation_id == "operation-0001"
    assert first.state == "claimed"
    assert first.attempt_count == 1
    assert second is not None
    assert second.operation_id == "operation-0002"

    dispatched = repository.mark_outbox_dispatched(first.outbox_id)

    assert dispatched.state == "dispatched"
    assert repository.claim_next_outbox_item(now=_NOW + timedelta(seconds=1)) is None


def _accept(
    repository: OperationRepository,
    *,
    operation_id: str,
    workflow_version: str = "1.0.0",
    idempotency_key_hash: str = "key-hash-1",
    request_hash: str = "request-hash-1",
) -> Any:
    return repository.accept_operation(
        operation_id=operation_id,
        workflow_key="maintenance-host-precheck",
        workflow_version=workflow_version,
        definition_checksum=f"checksum-{workflow_version}",
        actor_subject_id="mock-user-admin",
        scope_type="system",
        scope_id=None,
        idempotency_key_hash=idempotency_key_hash,
        request_hash=request_hash,
        correlation_id=f"corr-{operation_id}",
        input_json={"reason": "maintenance dry run"},
        targets=[
            OperationTargetCreate(
                target_type="host",
                cloud_id="synthetic",
                region_id="RegionOne",
                resource_id="hypervisor-0001",
                snapshot={"host_name": "compute-a"},
            )
        ],
    )


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


_NOW = datetime(2026, 6, 22, 10, 0, tzinfo=UTC)
