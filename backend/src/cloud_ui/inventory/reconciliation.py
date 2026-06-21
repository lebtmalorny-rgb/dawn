from __future__ import annotations

import hashlib
import json
from collections.abc import Callable, Iterator, Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Literal, Protocol

import sqlalchemy as sa
from sqlalchemy.engine import Connection

from cloud_ui.inventory import schema
from cloud_ui.inventory.repository import InventoryRepository

SyncStatus = Literal["success", "partial"]


class InventorySource(Protocol):
    @property
    def cloud_id(self) -> str: ...

    @property
    def region_id(self) -> str: ...

    @property
    def source_name(self) -> str: ...

    def iter_instances(self, chunk_size: int) -> Iterator[Sequence[Mapping[str, Any]]]: ...

    def iter_hypervisors(self, chunk_size: int) -> Iterator[Sequence[Mapping[str, Any]]]: ...


@dataclass(frozen=True)
class SyncRunResult:
    status: SyncStatus
    instance_count: int
    hypervisor_count: int
    generation: int
    instance_run_id: str | None
    hypervisor_run_id: str | None


@dataclass(frozen=True)
class _ResourceSyncResult:
    status: SyncStatus
    count: int
    run_id: str


class InventoryReconciler:
    def __init__(
        self,
        *,
        repository: InventoryRepository,
        source: InventorySource,
        clock: Callable[[], datetime],
        chunk_size: int = 500,
    ) -> None:
        if chunk_size < 1:
            raise ValueError("chunk_size must be positive")
        self._engine = repository.engine
        self._source = source
        self._clock = clock
        self._chunk_size = chunk_size

    def run_full_sync(self, *, request_id: str, correlation_id: str) -> SyncRunResult:
        generation = self._next_generation()
        self._ensure_cloud_region(self._now())

        instances = self._sync_resource(
            resource_type="instances",
            table=schema.instances,
            key_columns=("cloud_id", "region_id", "instance_id"),
            id_column="instance_id",
            iterator_factory=self._source.iter_instances,
            generation=generation,
            request_id=request_id,
            correlation_id=correlation_id,
        )
        if instances.status == "partial":
            self._mark_region_partial(self._now())
            return SyncRunResult(
                status="partial",
                instance_count=instances.count,
                hypervisor_count=0,
                generation=generation,
                instance_run_id=instances.run_id,
                hypervisor_run_id=None,
            )

        hypervisors = self._sync_resource(
            resource_type="hypervisors",
            table=schema.hypervisors,
            key_columns=("cloud_id", "region_id", "hypervisor_id"),
            id_column="hypervisor_id",
            iterator_factory=self._source.iter_hypervisors,
            generation=generation,
            request_id=request_id,
            correlation_id=correlation_id,
        )
        if hypervisors.status == "partial":
            self._mark_region_partial(self._now())
            return SyncRunResult(
                status="partial",
                instance_count=instances.count,
                hypervisor_count=hypervisors.count,
                generation=generation,
                instance_run_id=instances.run_id,
                hypervisor_run_id=hypervisors.run_id,
            )

        completed_at = self._now()
        self._complete_successful_full_sync(
            instances=instances,
            hypervisors=hypervisors,
            generation=generation,
            completed_at=completed_at,
        )
        return SyncRunResult(
            status="success",
            instance_count=instances.count,
            hypervisor_count=hypervisors.count,
            generation=generation,
            instance_run_id=instances.run_id,
            hypervisor_run_id=hypervisors.run_id,
        )

    def _sync_resource(
        self,
        *,
        resource_type: str,
        table: sa.Table,
        key_columns: tuple[str, ...],
        id_column: str,
        iterator_factory: Callable[[int], Iterator[Sequence[Mapping[str, Any]]]],
        generation: int,
        request_id: str,
        correlation_id: str,
    ) -> _ResourceSyncResult:
        run_id = _run_id(self._source.source_name, resource_type, generation)
        with self._engine.begin() as connection:
            self._insert_run(
                connection=connection,
                run_id=run_id,
                resource_type=resource_type,
                generation=generation,
                request_id=request_id,
                correlation_id=correlation_id,
                started_at=self._now(),
            )

        count = 0
        cursor_value: str | None = None
        try:
            for chunk in iterator_factory(self._chunk_size):
                if not chunk:
                    continue
                rows = [
                    _projection_row(row, generation=generation, observed_at=self._now())
                    for row in chunk
                ]
                next_count = count + len(rows)
                next_cursor_value = str(rows[-1][id_column])
                with self._engine.begin() as connection:
                    _replace_rows(connection, table, rows, key_columns=key_columns)
                    self._upsert_cursor(
                        connection=connection,
                        run_id=run_id,
                        resource_type=resource_type,
                        cursor_value=next_cursor_value,
                        generation=generation,
                    )
                    self._update_run_counts(
                        connection=connection,
                        run_id=run_id,
                        status="running",
                        completed_at=None,
                        items_seen=next_count,
                        items_upserted=next_count,
                        items_deleted=0,
                        error_count=0,
                    )
                count = next_count
                cursor_value = next_cursor_value
        except Exception:
            completed_at = self._now()
            with self._engine.begin() as connection:
                self._insert_failure(
                    connection=connection,
                    run_id=run_id,
                    resource_type=resource_type,
                    chunk_cursor=cursor_value,
                    occurred_at=completed_at,
                )
                self._update_run_counts(
                    connection=connection,
                    run_id=run_id,
                    status="partial",
                    completed_at=completed_at,
                    items_seen=count,
                    items_upserted=count,
                    items_deleted=0,
                    error_count=1,
                )
            return _ResourceSyncResult(status="partial", count=count, run_id=run_id)

        completed_at = self._now()
        with self._engine.begin() as connection:
            self._update_run_counts(
                connection=connection,
                run_id=run_id,
                status="success",
                completed_at=completed_at,
                items_seen=count,
                items_upserted=count,
                items_deleted=0,
                error_count=0,
            )
        return _ResourceSyncResult(status="success", count=count, run_id=run_id)

    def _next_generation(self) -> int:
        statement = sa.select(sa.func.max(schema.inventory_sync_runs.c.generation)).where(
            schema.inventory_sync_runs.c.cloud_id == self._source.cloud_id,
            schema.inventory_sync_runs.c.region_id == self._source.region_id,
        )
        with self._engine.connect() as connection:
            current = connection.execute(statement).scalar_one()
        return int(current or 0) + 1

    def _ensure_cloud_region(self, now: datetime) -> None:
        with self._engine.begin() as connection:
            cloud_update = (
                schema.clouds.update()
                .where(schema.clouds.c.cloud_id == self._source.cloud_id)
                .values(
                    display_name=self._source.cloud_id,
                    enabled=True,
                    updated_at=now,
                )
            )
            cloud_result = connection.execute(cloud_update)
            if (cloud_result.rowcount or 0) == 0:
                connection.execute(
                    schema.clouds.insert(),
                    {
                        "cloud_id": self._source.cloud_id,
                        "display_name": self._source.cloud_id,
                        "enabled": True,
                        "created_at": now,
                        "updated_at": now,
                        "last_sync_at": None,
                    },
                )

            region_update = (
                schema.regions.update()
                .where(
                    schema.regions.c.cloud_id == self._source.cloud_id,
                    schema.regions.c.region_id == self._source.region_id,
                )
                .values(
                    display_name=self._source.region_id,
                    enabled=True,
                    last_attempted_sync_at=now,
                    sync_status="running",
                )
            )
            region_result = connection.execute(region_update)
            if (region_result.rowcount or 0) == 0:
                connection.execute(
                    schema.regions.insert(),
                    {
                        "cloud_id": self._source.cloud_id,
                        "region_id": self._source.region_id,
                        "display_name": self._source.region_id,
                        "enabled": True,
                        "last_successful_sync_at": None,
                        "last_attempted_sync_at": now,
                        "sync_status": "running",
                    },
                )

    def _insert_run(
        self,
        *,
        connection: Connection,
        run_id: str,
        resource_type: str,
        generation: int,
        request_id: str,
        correlation_id: str,
        started_at: datetime,
    ) -> None:
        connection.execute(
            schema.inventory_sync_runs.insert(),
            {
                "run_id": run_id,
                "cloud_id": self._source.cloud_id,
                "region_id": self._source.region_id,
                "resource_type": resource_type,
                "sync_mode": "full",
                "generation": generation,
                "status": "running",
                "started_at": started_at,
                "completed_at": None,
                "request_id": request_id,
                "correlation_id": correlation_id,
                "items_seen": 0,
                "items_upserted": 0,
                "items_deleted": 0,
                "error_count": 0,
            },
        )

    def _upsert_cursor(
        self,
        *,
        connection: Connection,
        run_id: str,
        resource_type: str,
        cursor_value: str,
        generation: int,
    ) -> None:
        cursor_id = _cursor_id(self._source.cloud_id, self._source.region_id, resource_type)
        values = {
            "run_id": run_id,
            "cloud_id": self._source.cloud_id,
            "region_id": self._source.region_id,
            "resource_type": resource_type,
            "cursor_value": cursor_value,
            "generation": generation,
            "retry_count": 0,
            "updated_at": self._now(),
        }
        result = connection.execute(
            schema.inventory_sync_cursors.update()
            .where(schema.inventory_sync_cursors.c.cursor_id == cursor_id)
            .values(**values)
        )
        if (result.rowcount or 0) == 0:
            connection.execute(
                schema.inventory_sync_cursors.insert(),
                {"cursor_id": cursor_id, **values},
            )

    def _update_run_counts(
        self,
        *,
        connection: Connection,
        run_id: str,
        status: str,
        completed_at: datetime | None,
        items_seen: int,
        items_upserted: int,
        items_deleted: int,
        error_count: int,
    ) -> None:
        connection.execute(
            schema.inventory_sync_runs.update()
            .where(schema.inventory_sync_runs.c.run_id == run_id)
            .values(
                status=status,
                completed_at=completed_at,
                items_seen=items_seen,
                items_upserted=items_upserted,
                items_deleted=items_deleted,
                error_count=error_count,
            )
        )

    def _insert_failure(
        self,
        *,
        connection: Connection,
        run_id: str,
        resource_type: str,
        chunk_cursor: str | None,
        occurred_at: datetime,
    ) -> None:
        connection.execute(
            schema.inventory_sync_failures.insert(),
            {
                "failure_id": f"{run_id}-failure-0001",
                "run_id": run_id,
                "cloud_id": self._source.cloud_id,
                "region_id": self._source.region_id,
                "resource_type": resource_type,
                "source": self._source.source_name,
                "chunk_cursor": chunk_cursor,
                "error_code": "inventory_source_chunk_failed",
                "safe_message": "Inventory source chunk failed during full sync.",
                "occurred_at": occurred_at,
            },
        )

    def _complete_successful_full_sync(
        self,
        *,
        instances: _ResourceSyncResult,
        hypervisors: _ResourceSyncResult,
        generation: int,
        completed_at: datetime,
    ) -> None:
        with self._engine.begin() as connection:
            instance_deleted = _tombstone_missing(
                connection,
                schema.instances,
                cloud_id=self._source.cloud_id,
                region_id=self._source.region_id,
                generation=generation,
                deleted_at=completed_at,
            )
            hypervisor_deleted = _tombstone_missing(
                connection,
                schema.hypervisors,
                cloud_id=self._source.cloud_id,
                region_id=self._source.region_id,
                generation=generation,
                deleted_at=completed_at,
            )
            self._update_run_counts(
                connection=connection,
                run_id=instances.run_id,
                status="success",
                completed_at=completed_at,
                items_seen=instances.count,
                items_upserted=instances.count,
                items_deleted=instance_deleted,
                error_count=0,
            )
            self._update_run_counts(
                connection=connection,
                run_id=hypervisors.run_id,
                status="success",
                completed_at=completed_at,
                items_seen=hypervisors.count,
                items_upserted=hypervisors.count,
                items_deleted=hypervisor_deleted,
                error_count=0,
            )
            connection.execute(
                schema.regions.update()
                .where(
                    schema.regions.c.cloud_id == self._source.cloud_id,
                    schema.regions.c.region_id == self._source.region_id,
                )
                .values(
                    last_successful_sync_at=completed_at,
                    last_attempted_sync_at=completed_at,
                    sync_status="ok",
                )
            )
            connection.execute(
                schema.clouds.update()
                .where(schema.clouds.c.cloud_id == self._source.cloud_id)
                .values(last_sync_at=completed_at, updated_at=completed_at)
            )

    def _mark_region_partial(self, attempted_at: datetime) -> None:
        with self._engine.begin() as connection:
            connection.execute(
                schema.regions.update()
                .where(
                    schema.regions.c.cloud_id == self._source.cloud_id,
                    schema.regions.c.region_id == self._source.region_id,
                )
                .values(last_attempted_sync_at=attempted_at, sync_status="partial")
            )
            connection.execute(
                schema.clouds.update()
                .where(schema.clouds.c.cloud_id == self._source.cloud_id)
                .values(updated_at=attempted_at)
            )

    def _now(self) -> datetime:
        return _as_utc(self._clock())


def _projection_row(
    row: Mapping[str, Any],
    *,
    generation: int,
    observed_at: datetime,
) -> dict[str, Any]:
    projected = dict(row)
    projected["observed_at"] = observed_at
    projected["sync_generation"] = generation
    projected["sync_status"] = "ok"
    projected["deleted_at"] = None
    projected["change_hash"] = _change_hash(projected)
    return projected


def _replace_rows(
    connection: Connection,
    table: sa.Table,
    rows: Sequence[Mapping[str, Any]],
    *,
    key_columns: tuple[str, ...],
) -> None:
    for row in rows:
        conditions = [table.c[column] == row[column] for column in key_columns]
        connection.execute(table.delete().where(*conditions))
    connection.execute(table.insert(), [dict(row) for row in rows])


def _tombstone_missing(
    connection: Connection,
    table: sa.Table,
    *,
    cloud_id: str,
    region_id: str,
    generation: int,
    deleted_at: datetime,
) -> int:
    result = connection.execute(
        table.update()
        .where(
            table.c.cloud_id == cloud_id,
            table.c.region_id == region_id,
            table.c.sync_generation < generation,
            table.c.deleted_at.is_(None),
        )
        .values(deleted_at=deleted_at, sync_status="deleted")
    )
    return int(result.rowcount or 0)


def _run_id(source_name: str, resource_type: str, generation: int) -> str:
    return f"{source_name}-{resource_type}-full-{generation:08d}"


def _cursor_id(cloud_id: str, region_id: str, resource_type: str) -> str:
    return f"{cloud_id}:{region_id}:{resource_type}:full"


def _change_hash(row: Mapping[str, Any]) -> str:
    ignored_fields = {"change_hash", "deleted_at", "observed_at", "sync_generation"}
    payload = {
        key: value
        for key, value in row.items()
        if key not in ignored_fields and value is not None
    }
    serialized = json.dumps(
        payload,
        default=_json_default,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )
    return hashlib.sha256(serialized.encode()).hexdigest()


def _json_default(value: object) -> str:
    if isinstance(value, datetime):
        return _as_utc(value).isoformat()
    raise TypeError(f"Object of type {type(value).__name__} is not JSON serializable")


def _as_utc(value: datetime) -> datetime:
    offset = value.utcoffset()
    if value.tzinfo is None or offset is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)
