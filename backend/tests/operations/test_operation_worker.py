from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, datetime

import pytest
import sqlalchemy as sa
from sqlalchemy.engine import Engine

from cloud_ui.operations import schema
from cloud_ui.operations.catalog import build_builtin_workflow_catalog
from cloud_ui.operations.mistral import InMemoryMistralAdapter
from cloud_ui.operations.models import OperationTargetCreate
from cloud_ui.operations.repository import OperationRepository
from cloud_ui.operations.worker import OperationWorker


def test_worker_uses_existing_execution_lookup_before_start(
    repository: OperationRepository,
) -> None:
    adapter = InMemoryMistralAdapter()
    adapter.create_execution(
        workflow_name="portal.maintenance_host_precheck.v1",
        correlation_id="operation-0001",
        input_json={"dry_run": True},
    )
    _accept(repository, operation_id="operation-0001")
    worker = _worker(repository, adapter)

    result = worker.run_once()

    operation = repository.get_operation("operation-0001")
    assert result.processed is True
    assert result.operation_id == "operation-0001"
    assert result.status == "running"
    assert operation is not None
    assert operation.external_execution_id is not None
    assert adapter.start_count == 0
    assert _attempt_outcomes(repository.engine) == ["lookup_existing"]


def test_worker_handles_lost_response_without_duplicate_execution(
    repository: OperationRepository,
) -> None:
    adapter = InMemoryMistralAdapter()
    adapter.fail_next_start_with_lost_response(create_execution=True)
    _accept(repository, operation_id="operation-0001")
    worker = _worker(repository, adapter)

    first = worker.run_once()
    second = worker.run_once()

    operation = repository.get_operation("operation-0001")
    assert first.processed is True
    assert first.status == "running"
    assert second.processed is False
    assert operation is not None
    assert operation.status == "running"
    assert len(adapter.list_executions_by_correlation("operation-0001")) == 1
    assert adapter.start_count == 1
    assert _attempt_outcomes(repository.engine) == ["start_lost_response", "lookup_existing"]


def test_worker_marks_mistral_unavailable_as_unknown(repository: OperationRepository) -> None:
    adapter = InMemoryMistralAdapter()
    adapter.fail_next_start_with_unavailable()
    _accept(repository, operation_id="operation-0001")
    worker = _worker(repository, adapter)

    result = worker.run_once()

    operation = repository.get_operation("operation-0001")
    assert result.processed is True
    assert result.status == "unknown"
    assert operation is not None
    assert operation.status == "unknown"
    assert operation.external_execution_id is None
    assert adapter.start_count == 1
    assert _attempt_outcomes(repository.engine) == ["start_unavailable"]


def test_worker_returns_noop_when_outbox_is_empty(repository: OperationRepository) -> None:
    result = _worker(repository, InMemoryMistralAdapter()).run_once()

    assert result.processed is False
    assert result.operation_id is None
    assert result.status is None


def _worker(repository: OperationRepository, adapter: InMemoryMistralAdapter) -> OperationWorker:
    return OperationWorker(
        repository=repository,
        catalog=build_builtin_workflow_catalog(environment="local"),
        mistral=adapter,
        clock=lambda: _NOW,
    )


def _accept(repository: OperationRepository, *, operation_id: str) -> None:
    repository.accept_operation(
        operation_id=operation_id,
        workflow_key="maintenance-host-precheck",
        workflow_version="1.0.0",
        definition_checksum="checksum-1",
        actor_subject_id="mock-user-admin",
        scope_type="system",
        scope_id=None,
        idempotency_key_hash=f"key-{operation_id}",
        request_hash=f"request-{operation_id}",
        correlation_id=operation_id,
        input_json={"reason": "maintenance dry run", "dry_run": True},
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


def _attempt_outcomes(engine: Engine) -> list[str]:
    with engine.connect() as connection:
        rows = list(
            connection.execute(
                sa.select(schema.operation_attempts.c.outcome).order_by(
                    schema.operation_attempts.c.created_at.asc(),
                    schema.operation_attempts.c.attempt_id.asc(),
                )
            )
        )
    return [str(row[0]) for row in rows]


@pytest.fixture()
def repository() -> Iterator[OperationRepository]:
    engine = sa.create_engine("sqlite+pysqlite:///:memory:", future=True)
    schema.metadata.create_all(engine)
    yield OperationRepository(engine=engine, clock=lambda: _NOW)
    engine.dispose()


_NOW = datetime(2026, 6, 22, 10, 0, tzinfo=UTC)
