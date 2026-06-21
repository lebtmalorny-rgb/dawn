from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
import sqlalchemy as sa
from sqlalchemy.engine import Engine

from cloud_ui.inventory import schema
from cloud_ui.inventory.cursor import CursorCodec
from cloud_ui.inventory.models import HypervisorFilters, InstanceFilters, InventorySort
from cloud_ui.inventory.reconciliation import InventoryReconciler
from cloud_ui.inventory.repository import InventoryRepository
from cloud_ui.inventory.synthetic import SyntheticInventorySource


class StepClock:
    def __init__(self) -> None:
        self._current = datetime(2026, 6, 21, 10, 0, tzinfo=UTC)

    def __call__(self) -> datetime:
        timestamp = self._current
        self._current = self._current + timedelta(seconds=1)
        return timestamp


class FailingOnSecondInstanceChunkSource(SyntheticInventorySource):
    def iter_instances(self, chunk_size: int) -> Iterator[list[dict[str, Any]]]:
        for index, chunk in enumerate(super().iter_instances(chunk_size), start=1):
            if index == 2:
                raise RuntimeError("upstream failure contained secret-token-value")
            yield chunk


class FailingOnSecondHypervisorChunkSource(SyntheticInventorySource):
    def iter_hypervisors(self, chunk_size: int) -> Iterator[list[dict[str, Any]]]:
        for index, chunk in enumerate(super().iter_hypervisors(chunk_size), start=1):
            if index == 2:
                raise RuntimeError("hypervisor source failed")
            yield chunk


class FinalizationFailureReconciler(InventoryReconciler):
    def _complete_successful_full_sync(self, **_kwargs: Any) -> None:
        raise RuntimeError("finalization failed")


def test_synthetic_full_sync_populates_instances_and_hypervisors() -> None:
    engine = _create_engine()
    try:
        repository = _repository(engine)
        reconciler = InventoryReconciler(
            repository=repository,
            source=SyntheticInventorySource(instance_count=12, hypervisor_count=3),
            clock=StepClock(),
            chunk_size=5,
        )

        result = reconciler.run_full_sync(
            request_id="request-full-sync",
            correlation_id="correlation-full-sync",
        )

        assert result.status == "success"
        assert result.instance_count == 12
        assert result.hypervisor_count == 3

        instances = repository.list_instances(
            filters=InstanceFilters(cloud_id="synthetic", region_id="RegionOne"),
            sort=InventorySort(field="instance_id", direction="asc"),
            limit=50,
            cursor=None,
        )
        hypervisors = repository.list_hypervisors(
            filters=HypervisorFilters(cloud_id="synthetic", region_id="RegionOne"),
            sort=InventorySort(field="hypervisor_id", direction="asc"),
            limit=50,
            cursor=None,
        )

        assert [item.instance_id for item in instances.items] == [
            f"inst-{index:08d}" for index in range(1, 13)
        ]
        assert [item.hypervisor_id for item in hypervisors.items] == [
            "hyp-0001",
            "hyp-0002",
            "hyp-0003",
        ]
        assert _sync_run_statuses(engine) == {
            "hypervisors": ["success"],
            "instances": ["success"],
        }
    finally:
        engine.dispose()


def test_full_sync_is_idempotent_for_same_seed() -> None:
    engine = _create_engine()
    try:
        repository = _repository(engine)
        first = InventoryReconciler(
            repository=repository,
            source=SyntheticInventorySource(instance_count=12, hypervisor_count=3, seed="same"),
            clock=StepClock(),
            chunk_size=5,
        ).run_full_sync(request_id="request-1", correlation_id="correlation-1")
        second = InventoryReconciler(
            repository=repository,
            source=SyntheticInventorySource(instance_count=12, hypervisor_count=3, seed="same"),
            clock=StepClock(),
            chunk_size=5,
        ).run_full_sync(request_id="request-2", correlation_id="correlation-2")

        assert first.generation == 1
        assert second.generation == 2
        assert _active_count(engine, schema.instances) == 12
        assert _active_count(engine, schema.hypervisors) == 3
        assert _max_generation(engine, schema.instances) == 2
        assert _max_generation(engine, schema.hypervisors) == 2
    finally:
        engine.dispose()


def test_partial_failure_records_failure_and_keeps_old_rows() -> None:
    engine = _create_engine()
    try:
        repository = _repository(engine)
        InventoryReconciler(
            repository=repository,
            source=SyntheticInventorySource(instance_count=12, hypervisor_count=3),
            clock=StepClock(),
            chunk_size=5,
        ).run_full_sync(request_id="request-success", correlation_id="correlation-success")

        result = InventoryReconciler(
            repository=repository,
            source=FailingOnSecondInstanceChunkSource(instance_count=12, hypervisor_count=3),
            clock=StepClock(),
            chunk_size=5,
        ).run_full_sync(request_id="request-partial", correlation_id="correlation-partial")

        assert result.status == "partial"
        assert _active_count(engine, schema.instances) == 12
        assert _deleted_ids(engine, schema.instances, "instance_id") == []
        assert _sync_run_statuses(engine)["instances"][-1] == "partial"

        failure = _latest_failure(engine)
        assert failure["error_code"] == "inventory_source_chunk_failed"
        assert failure["safe_message"] == "Inventory source chunk failed during full sync."
        assert "secret-token-value" not in failure["safe_message"]
    finally:
        engine.dispose()


def test_partial_hypervisor_failure_does_not_tombstone_missing_instance_rows() -> None:
    engine = _create_engine()
    try:
        repository = _repository(engine)
        clock = StepClock()
        InventoryReconciler(
            repository=repository,
            source=SyntheticInventorySource(instance_count=12, hypervisor_count=3),
            clock=clock,
            chunk_size=5,
        ).run_full_sync(request_id="request-success", correlation_id="correlation-success")

        result = InventoryReconciler(
            repository=repository,
            source=FailingOnSecondHypervisorChunkSource(instance_count=10, hypervisor_count=3),
            clock=clock,
            chunk_size=2,
        ).run_full_sync(request_id="request-partial", correlation_id="correlation-partial")

        assert result.status == "partial"
        assert _active_count(engine, schema.instances) == 12
        assert _deleted_ids(engine, schema.instances, "instance_id") == []
        assert _sync_run_statuses(engine)["hypervisors"][-1] == "partial"
        assert _run_status(engine, generation=2, resource_type="instances") != "success"

        page = repository.list_instances(
            filters=InstanceFilters(cloud_id="synthetic", region_id="RegionOne"),
            sort=InventorySort(field="instance_id", direction="asc"),
            limit=50,
            cursor=None,
        )

        assert page.partial is True
        assert [warning.code for warning in page.warnings] == ["inventory_source_chunk_failed"]
    finally:
        engine.dispose()


def test_finalization_failure_marks_region_partial_and_reraises() -> None:
    engine = _create_engine()
    try:
        repository = _repository(engine)
        reconciler = FinalizationFailureReconciler(
            repository=repository,
            source=SyntheticInventorySource(instance_count=12, hypervisor_count=3),
            clock=StepClock(),
            chunk_size=5,
        )

        with pytest.raises(RuntimeError, match="finalization failed"):
            reconciler.run_full_sync(
                request_id="request-finalization-failure",
                correlation_id="correlation-finalization-failure",
            )

        assert _region_status(engine) == "partial"
        assert _run_status(engine, generation=1, resource_type="instances") != "success"
        assert _run_status(engine, generation=1, resource_type="hypervisors") != "success"
    finally:
        engine.dispose()


def test_successful_full_sync_tombstones_missing_old_rows() -> None:
    engine = _create_engine()
    try:
        repository = _repository(engine)
        InventoryReconciler(
            repository=repository,
            source=SyntheticInventorySource(instance_count=12, hypervisor_count=3),
            clock=StepClock(),
            chunk_size=5,
        ).run_full_sync(request_id="request-1", correlation_id="correlation-1")

        result = InventoryReconciler(
            repository=repository,
            source=SyntheticInventorySource(instance_count=10, hypervisor_count=3),
            clock=StepClock(),
            chunk_size=5,
        ).run_full_sync(request_id="request-2", correlation_id="correlation-2")

        assert result.status == "success"
        assert result.generation == 2
        assert _active_count(engine, schema.instances) == 10
        assert _deleted_ids(engine, schema.instances, "instance_id") == [
            "inst-00000011",
            "inst-00000012",
        ]
        assert _active_count(engine, schema.hypervisors) == 3
    finally:
        engine.dispose()


def _create_engine() -> Engine:
    engine = sa.create_engine("sqlite+pysqlite:///:memory:", future=True)
    schema.metadata.create_all(engine)
    return engine


def _repository(engine: Engine) -> InventoryRepository:
    return InventoryRepository(
        engine=engine,
        cursor_codec=CursorCodec(signing_key="dev-inventory-cursor-key"),
        default_limit=50,
        max_limit=200,
        stale_after_seconds=900,
    )


def _sync_run_statuses(engine: Engine) -> dict[str, list[str]]:
    statement = (
        sa.select(
            schema.inventory_sync_runs.c.resource_type,
            schema.inventory_sync_runs.c.status,
        )
        .order_by(
            schema.inventory_sync_runs.c.generation,
            schema.inventory_sync_runs.c.resource_type,
        )
    )
    statuses: dict[str, list[str]] = {}
    with engine.connect() as connection:
        for row in connection.execute(statement).mappings():
            statuses.setdefault(str(row["resource_type"]), []).append(str(row["status"]))
    return statuses


def _run_status(engine: Engine, *, generation: int, resource_type: str) -> str:
    statement = sa.select(schema.inventory_sync_runs.c.status).where(
        schema.inventory_sync_runs.c.cloud_id == "synthetic",
        schema.inventory_sync_runs.c.region_id == "RegionOne",
        schema.inventory_sync_runs.c.generation == generation,
        schema.inventory_sync_runs.c.resource_type == resource_type,
    )
    with engine.connect() as connection:
        return str(connection.execute(statement).scalar_one())


def _region_status(engine: Engine) -> str:
    statement = sa.select(schema.regions.c.sync_status).where(
        schema.regions.c.cloud_id == "synthetic",
        schema.regions.c.region_id == "RegionOne",
    )
    with engine.connect() as connection:
        return str(connection.execute(statement).scalar_one())


def _active_count(engine: Engine, table: sa.Table) -> int:
    statement = sa.select(sa.func.count()).select_from(table).where(table.c.deleted_at.is_(None))
    with engine.connect() as connection:
        return int(connection.execute(statement).scalar_one())


def _max_generation(engine: Engine, table: sa.Table) -> int:
    statement = sa.select(sa.func.max(table.c.sync_generation)).select_from(table)
    with engine.connect() as connection:
        return int(connection.execute(statement).scalar_one())


def _deleted_ids(engine: Engine, table: sa.Table, id_column: str) -> list[str]:
    statement = (
        sa.select(table.c[id_column])
        .where(table.c.deleted_at.is_not(None))
        .order_by(table.c[id_column])
    )
    with engine.connect() as connection:
        return [str(row[id_column]) for row in connection.execute(statement).mappings()]


def _latest_failure(engine: Engine) -> dict[str, Any]:
    statement = (
        sa.select(schema.inventory_sync_failures)
        .order_by(schema.inventory_sync_failures.c.occurred_at.desc())
        .limit(1)
    )
    with engine.connect() as connection:
        row = connection.execute(statement).mappings().one()
    return dict(row)
