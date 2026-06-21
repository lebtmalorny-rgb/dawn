from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable, Mapping, Sequence
from datetime import UTC, datetime, timedelta
from typing import Any

import sqlalchemy as sa
from sqlalchemy.engine import Engine, RowMapping

from cloud_ui.inventory import schema
from cloud_ui.inventory.cursor import CursorCodec, CursorTampered
from cloud_ui.inventory.models import (
    HypervisorFilters,
    HypervisorItem,
    InstanceFilters,
    InstanceItem,
    InventoryFreshness,
    InventoryPage,
    InventorySort,
    InventoryWarning,
)

_WARNING_LIMIT = 5


class InventoryRepository:
    def __init__(
        self,
        *,
        engine: Engine,
        cursor_codec: CursorCodec,
        default_limit: int,
        max_limit: int,
        stale_after_seconds: int,
    ) -> None:
        self._engine = engine
        self._cursor_codec = cursor_codec
        self._default_limit = default_limit
        self._max_limit = max_limit
        self._stale_after_seconds = stale_after_seconds

    @property
    def engine(self) -> Engine:
        return self._engine

    def list_instances(
        self,
        *,
        filters: InstanceFilters,
        sort: InventorySort,
        limit: int | None,
        cursor: str | None,
    ) -> InventoryPage[InstanceItem]:
        page_limit = self._clamp_limit(limit)
        sort_column = _instance_sort_column(sort.field)
        id_column = schema.instances.c.instance_id
        filters_hash = _filters_hash(filters)
        last = self._decode_cursor(
            cursor=cursor,
            resource="instances",
            filters_hash=filters_hash,
            sort=sort,
        )
        conditions = _instance_conditions(filters)
        if last is not None:
            conditions.append(_keyset_condition(sort, sort_column, id_column, last))

        order_by = _order_by(sort, sort_column, id_column, "instance_id")
        statement = (
            sa.select(schema.instances)
            .where(*conditions)
            .order_by(*order_by)
            .limit(page_limit + 1)
        )

        with self._engine.connect() as connection:
            rows = list(connection.execute(statement).mappings())
            page_rows = rows[:page_limit]
            items = [_instance_item_from_row(row) for row in page_rows]
            next_cursor = self._next_cursor(
                resource="instances",
                filters_hash=filters_hash,
                sort=sort,
                id_field="instance_id",
                rows=page_rows,
                has_more=len(rows) > page_limit,
            )
            warnings = self._warnings(connection, filters.cloud_id, filters.region_id)
            freshness = self._freshness(
                connection,
                schema.instances,
                filters.cloud_id,
                filters.region_id,
            )

        return InventoryPage[InstanceItem](
            items=items,
            next_cursor=next_cursor,
            partial=bool(warnings),
            warnings=warnings,
            freshness=freshness,
        )

    def get_instance(
        self,
        cloud_id: str,
        region_id: str,
        instance_id: str,
    ) -> InstanceItem | None:
        statement = sa.select(schema.instances).where(
            schema.instances.c.cloud_id == cloud_id,
            schema.instances.c.region_id == region_id,
            schema.instances.c.instance_id == instance_id,
            schema.instances.c.deleted_at.is_(None),
        )
        with self._engine.connect() as connection:
            row = connection.execute(statement).mappings().one_or_none()
        if row is None:
            return None
        return _instance_item_from_row(row)

    def list_hypervisors(
        self,
        *,
        filters: HypervisorFilters,
        sort: InventorySort,
        limit: int | None,
        cursor: str | None,
    ) -> InventoryPage[HypervisorItem]:
        page_limit = self._clamp_limit(limit)
        sort_column = _hypervisor_sort_column(sort.field)
        id_column = schema.hypervisors.c.hypervisor_id
        filters_hash = _filters_hash(filters)
        last = self._decode_cursor(
            cursor=cursor,
            resource="hypervisors",
            filters_hash=filters_hash,
            sort=sort,
        )
        conditions = _hypervisor_conditions(filters)
        if last is not None:
            conditions.append(_keyset_condition(sort, sort_column, id_column, last))

        order_by = _order_by(sort, sort_column, id_column, "hypervisor_id")
        statement = (
            sa.select(schema.hypervisors)
            .where(*conditions)
            .order_by(*order_by)
            .limit(page_limit + 1)
        )

        with self._engine.connect() as connection:
            rows = list(connection.execute(statement).mappings())
            page_rows = rows[:page_limit]
            items = [_hypervisor_item_from_row(row) for row in page_rows]
            next_cursor = self._next_cursor(
                resource="hypervisors",
                filters_hash=filters_hash,
                sort=sort,
                id_field="hypervisor_id",
                rows=page_rows,
                has_more=len(rows) > page_limit,
            )
            warnings = self._warnings(
                connection,
                filters.cloud_id,
                filters.region_id,
            )
            freshness = self._freshness(
                connection,
                schema.hypervisors,
                filters.cloud_id,
                filters.region_id,
            )

        return InventoryPage[HypervisorItem](
            items=items,
            next_cursor=next_cursor,
            partial=bool(warnings),
            warnings=warnings,
            freshness=freshness,
        )

    def get_hypervisor(
        self,
        cloud_id: str,
        region_id: str,
        hypervisor_id: str,
    ) -> HypervisorItem | None:
        statement = sa.select(schema.hypervisors).where(
            schema.hypervisors.c.cloud_id == cloud_id,
            schema.hypervisors.c.region_id == region_id,
            schema.hypervisors.c.hypervisor_id == hypervisor_id,
            schema.hypervisors.c.deleted_at.is_(None),
        )
        with self._engine.connect() as connection:
            row = connection.execute(statement).mappings().one_or_none()
        if row is None:
            return None
        return _hypervisor_item_from_row(row)

    def replace_instance_rows(self, rows: Sequence[Mapping[str, Any]]) -> None:
        self._replace_rows(
            schema.instances,
            rows,
            key_columns=("cloud_id", "region_id", "instance_id"),
        )

    def replace_hypervisor_rows(self, rows: Sequence[Mapping[str, Any]]) -> None:
        self._replace_rows(
            schema.hypervisors,
            rows,
            key_columns=("cloud_id", "region_id", "hypervisor_id"),
        )

    def _clamp_limit(self, limit: int | None) -> int:
        requested_limit = self._default_limit if limit is None else limit
        return max(1, min(requested_limit, self._max_limit))

    def _decode_cursor(
        self,
        *,
        cursor: str | None,
        resource: str,
        filters_hash: str,
        sort: InventorySort,
    ) -> dict[str, Any] | None:
        if cursor is None:
            return None
        payload = self._cursor_codec.decode(cursor)
        if (
            payload.get("resource") != resource
            or payload.get("filters_hash") != filters_hash
            or payload.get("sort") != _sort_key(sort)
        ):
            raise CursorTampered()
        last = payload.get("last")
        if not isinstance(last, dict):
            raise CursorTampered()
        if not isinstance(last.get("id"), str):
            raise CursorTampered()
        if sort.field not in last:
            raise CursorTampered()
        return last

    def _next_cursor(
        self,
        *,
        resource: str,
        filters_hash: str,
        sort: InventorySort,
        id_field: str,
        rows: Sequence[RowMapping],
        has_more: bool,
    ) -> str | None:
        if not has_more or not rows:
            return None
        last_row = rows[-1]
        return self._cursor_codec.encode(
            {
                "resource": resource,
                "filters_hash": filters_hash,
                "sort": _sort_key(sort),
                "last": {
                    sort.field: _json_scalar(last_row[sort.field]),
                    "id": last_row[id_field],
                },
            }
        )

    def _warnings(
        self,
        connection: sa.Connection,
        cloud_id: str,
        region_id: str,
    ) -> list[InventoryWarning]:
        statement = (
            sa.select(schema.inventory_sync_failures)
            .join(
                schema.regions,
                sa.and_(
                    schema.regions.c.cloud_id == schema.inventory_sync_failures.c.cloud_id,
                    schema.regions.c.region_id == schema.inventory_sync_failures.c.region_id,
                ),
            )
            .where(
                schema.inventory_sync_failures.c.cloud_id == cloud_id,
                schema.inventory_sync_failures.c.region_id == region_id,
                sa.or_(
                    schema.regions.c.last_successful_sync_at.is_(None),
                    schema.inventory_sync_failures.c.occurred_at
                    > schema.regions.c.last_successful_sync_at,
                ),
            )
            .order_by(
                schema.inventory_sync_failures.c.occurred_at.desc(),
                schema.inventory_sync_failures.c.failure_id.desc(),
            )
            .limit(_WARNING_LIMIT)
        )
        rows = list(connection.execute(statement).mappings())
        if rows:
            return [
                InventoryWarning(
                    code=str(row["error_code"]),
                    title="Inventory synchronization partially failed",
                    detail=str(row["safe_message"]),
                    source=str(row["source"]),
                )
                for row in rows
            ]

        region = (
            connection.execute(
                sa.select(
                    schema.regions.c.sync_status,
                    schema.regions.c.last_attempted_sync_at,
                    schema.regions.c.last_successful_sync_at,
                ).where(
                    schema.regions.c.cloud_id == cloud_id,
                    schema.regions.c.region_id == region_id,
                )
            )
            .mappings()
            .one_or_none()
        )
        if region is None or region["sync_status"] != "partial":
            return []
        last_attempted_sync_at = _as_utc(region["last_attempted_sync_at"])
        last_successful_sync_at = _as_utc(region["last_successful_sync_at"])
        if last_attempted_sync_at is None or (
            last_successful_sync_at is not None
            and last_attempted_sync_at <= last_successful_sync_at
        ):
            return []

        return [
            InventoryWarning(
                code="inventory_sync_partial",
                title="Inventory synchronization partially failed",
                detail="Inventory synchronization did not complete for this region.",
                source="inventory",
            )
        ]

    def _freshness(
        self,
        connection: sa.Connection,
        table: sa.Table,
        cloud_id: str,
        region_id: str,
    ) -> InventoryFreshness:
        observed_at = _as_utc(
            connection.execute(
                sa.select(sa.func.max(table.c.observed_at)).where(
                    table.c.cloud_id == cloud_id,
                    table.c.region_id == region_id,
                    table.c.deleted_at.is_(None),
                )
            ).scalar_one_or_none()
        )
        last_successful_sync_at = _as_utc(
            connection.execute(
                sa.select(schema.regions.c.last_successful_sync_at).where(
                    schema.regions.c.cloud_id == cloud_id,
                    schema.regions.c.region_id == region_id,
                )
            ).scalar_one_or_none()
        )
        recency_marker = _newest_datetime(observed_at, last_successful_sync_at)
        is_stale = recency_marker is None or datetime.now(UTC) - recency_marker > timedelta(
            seconds=self._stale_after_seconds
        )
        return InventoryFreshness(
            observed_at=observed_at,
            last_successful_sync_at=last_successful_sync_at,
            stale_after_seconds=self._stale_after_seconds,
            is_stale=is_stale,
        )

    def _replace_rows(
        self,
        table: sa.Table,
        rows: Sequence[Mapping[str, Any]],
        *,
        key_columns: tuple[str, ...],
    ) -> None:
        row_values = [dict(row) for row in rows]
        if not row_values:
            return

        with self._engine.begin() as connection:
            for row in row_values:
                conditions = [table.c[column] == row[column] for column in key_columns]
                connection.execute(table.delete().where(*conditions))
            connection.execute(table.insert(), row_values)


def _filters_hash(filters: InstanceFilters | HypervisorFilters) -> str:
    payload = filters.model_dump(exclude_none=True, mode="json")
    raw_payload = json.dumps(payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
    return hashlib.sha256(raw_payload.encode("utf-8")).hexdigest()


def _sort_key(sort: InventorySort) -> str:
    return f"{sort.field}.{sort.direction}"


def _instance_conditions(filters: InstanceFilters) -> list[sa.ColumnElement[bool]]:
    conditions = [
        schema.instances.c.cloud_id == filters.cloud_id,
        schema.instances.c.region_id == filters.region_id,
        schema.instances.c.deleted_at.is_(None),
    ]
    optional_filters = {
        "project_id": filters.project_id,
        "status": filters.status,
        "host_name": filters.host_name,
        "hypervisor_id": filters.hypervisor_id,
        "availability_zone": filters.availability_zone,
    }
    for column_name, value in optional_filters.items():
        if value is not None:
            conditions.append(schema.instances.c[column_name] == value)
    query = _normalized_query(filters.q)
    if query is not None:
        conditions.append(
            _search_condition(
                (
                    schema.instances.c.instance_id,
                    schema.instances.c.name,
                    schema.instances.c.project_id,
                    schema.instances.c.status,
                    schema.instances.c.host_name,
                    schema.instances.c.availability_zone,
                ),
                query,
            )
        )
    return conditions


def _hypervisor_conditions(filters: HypervisorFilters) -> list[sa.ColumnElement[bool]]:
    conditions = [
        schema.hypervisors.c.cloud_id == filters.cloud_id,
        schema.hypervisors.c.region_id == filters.region_id,
        schema.hypervisors.c.deleted_at.is_(None),
    ]
    optional_filters = {
        "service_status": filters.service_status,
        "service_state": filters.service_state,
        "host_name": filters.host_name,
        "availability_zone": filters.availability_zone,
        "maintenance_status": filters.maintenance_status,
    }
    for column_name, value in optional_filters.items():
        if value is not None:
            conditions.append(schema.hypervisors.c[column_name] == value)
    query = _normalized_query(filters.q)
    if query is not None:
        conditions.append(
            _search_condition(
                (
                    schema.hypervisors.c.hypervisor_id,
                    schema.hypervisors.c.host_name,
                    schema.hypervisors.c.service_status,
                    schema.hypervisors.c.service_state,
                    schema.hypervisors.c.availability_zone,
                ),
                query,
            )
        )
    return conditions


def _normalized_query(value: str | None) -> str | None:
    if value is None:
        return None
    query = value.strip().lower()
    return query or None


def _search_condition(
    columns: Iterable[sa.Column[Any]],
    query: str,
) -> sa.ColumnElement[bool]:
    pattern = _contains_pattern(query)
    return sa.or_(
        *(
            sa.func.lower(sa.func.coalesce(column, "")).like(pattern, escape="\\")
            for column in columns
        )
    )


def _contains_pattern(query: str) -> str:
    escaped = (
        query.replace("\\", "\\\\")
        .replace("%", "\\%")
        .replace("_", "\\_")
    )
    return f"%{escaped}%"


def _instance_sort_column(field: str) -> sa.Column[Any]:
    allowed = {
        "instance_id": schema.instances.c.instance_id,
        "name": schema.instances.c.name,
        "project_id": schema.instances.c.project_id,
        "status": schema.instances.c.status,
        "host_name": schema.instances.c.host_name,
        "availability_zone": schema.instances.c.availability_zone,
        "source_updated_at": schema.instances.c.source_updated_at,
        "observed_at": schema.instances.c.observed_at,
    }
    return _allowed_sort_column(field, allowed)


def _hypervisor_sort_column(field: str) -> sa.Column[Any]:
    allowed = {
        "hypervisor_id": schema.hypervisors.c.hypervisor_id,
        "host_name": schema.hypervisors.c.host_name,
        "service_status": schema.hypervisors.c.service_status,
        "service_state": schema.hypervisors.c.service_state,
        "availability_zone": schema.hypervisors.c.availability_zone,
        "observed_at": schema.hypervisors.c.observed_at,
    }
    return _allowed_sort_column(field, allowed)


def _allowed_sort_column(field: str, allowed: Mapping[str, sa.Column[Any]]) -> sa.Column[Any]:
    try:
        return allowed[field]
    except KeyError as exc:
        raise ValueError(f"unsupported inventory sort field: {field}") from exc


def _order_by(
    sort: InventorySort,
    sort_column: sa.Column[Any],
    id_column: sa.Column[Any],
    id_field: str,
) -> list[sa.ColumnElement[Any]]:
    direction = sort_column.asc if sort.direction == "asc" else sort_column.desc
    if sort.field == id_field:
        return [direction()]
    id_direction = id_column.asc if sort.direction == "asc" else id_column.desc
    if not _uses_null_bucket(sort_column):
        return [direction(), id_direction()]
    return [_null_bucket_column(sort, sort_column).asc(), direction(), id_direction()]


def _keyset_condition(
    sort: InventorySort,
    sort_column: sa.Column[Any],
    id_column: sa.Column[Any],
    last: Mapping[str, Any],
) -> sa.ColumnElement[bool]:
    last_sort_value = _keyset_sort_value(sort_column, last[sort.field])
    last_id = last["id"]
    if sort.field == id_column.name:
        if sort.direction == "asc":
            return sort_column > last_sort_value
        return sort_column < last_sort_value

    if not _uses_null_bucket(sort_column):
        if last_sort_value is None:
            raise CursorTampered()
        if sort.direction == "asc":
            return sa.or_(
                sort_column > last_sort_value,
                sa.and_(sort_column == last_sort_value, id_column > last_id),
            )
        return sa.or_(
            sort_column < last_sort_value,
            sa.and_(sort_column == last_sort_value, id_column < last_id),
        )

    last_null_bucket = _null_bucket_value(sort.direction, last_sort_value)
    null_bucket_column = _null_bucket_column(sort, sort_column)
    if last_sort_value is None:
        same_bucket_condition = (
            id_column > last_id if sort.direction == "asc" else id_column < last_id
        )
    elif sort.direction == "asc":
        same_bucket_condition = sa.or_(
            sort_column > last_sort_value,
            sa.and_(sort_column == last_sort_value, id_column > last_id),
        )
    else:
        same_bucket_condition = sa.or_(
            sort_column < last_sort_value,
            sa.and_(sort_column == last_sort_value, id_column < last_id),
        )

    return sa.or_(
        null_bucket_column > last_null_bucket,
        sa.and_(null_bucket_column == last_null_bucket, same_bucket_condition),
    )


def _instance_item_from_row(row: RowMapping) -> InstanceItem:
    return InstanceItem(
        cloud_id=str(row["cloud_id"]),
        region_id=str(row["region_id"]),
        instance_id=str(row["instance_id"]),
        name=str(row["name"]),
        project_id=str(row["project_id"]),
        user_id=str(row["user_id"]),
        status=str(row["status"]),
        power_state=str(row["power_state"]),
        task_state=_optional_string(row["task_state"]),
        vm_state=str(row["vm_state"]),
        host_name=_optional_string(row["host_name"]),
        hypervisor_id=_optional_string(row["hypervisor_id"]),
        availability_zone=_optional_string(row["availability_zone"]),
        flavor_id=_optional_string(row["flavor_id"]),
        vcpus=int(row["vcpus"]),
        ram_mb=int(row["ram_mb"]),
        disk_gb=int(row["disk_gb"]),
        image_id=_optional_string(row["image_id"]),
        boot_volume_id=_optional_string(row["boot_volume_id"]),
        addresses=_dict_json(row["addresses_json"]),
        source_created_at=_as_utc(row["source_created_at"]),
        source_updated_at=_as_utc(row["source_updated_at"]),
        observed_at=_required_datetime(row["observed_at"]),
        sync_generation=int(row["sync_generation"]),
        sync_status=str(row["sync_status"]),
    )


def _hypervisor_item_from_row(row: RowMapping) -> HypervisorItem:
    return HypervisorItem(
        cloud_id=str(row["cloud_id"]),
        region_id=str(row["region_id"]),
        hypervisor_id=str(row["hypervisor_id"]),
        host_name=str(row["host_name"]),
        service_id=_optional_string(row["service_id"]),
        service_status=str(row["service_status"]),
        service_state=str(row["service_state"]),
        hypervisor_type=_optional_string(row["hypervisor_type"]),
        hypervisor_version=_optional_string(row["hypervisor_version"]),
        availability_zone=_optional_string(row["availability_zone"]),
        aggregates=_string_list_json(row["aggregates_json"]),
        vcpus_total=int(row["vcpus_total"]),
        vcpus_used=int(row["vcpus_used"]),
        ram_mb_total=int(row["ram_mb_total"]),
        ram_mb_used=int(row["ram_mb_used"]),
        disk_gb_total=int(row["disk_gb_total"]),
        disk_gb_used=int(row["disk_gb_used"]),
        running_vms=int(row["running_vms"]),
        disabled_reason=_optional_string(row["disabled_reason"]),
        maintenance_status=_optional_string(row["maintenance_status"]),
        observed_at=_required_datetime(row["observed_at"]),
        sync_generation=int(row["sync_generation"]),
        sync_status=str(row["sync_status"]),
    )


def _optional_string(value: object) -> str | None:
    if value is None:
        return None
    return str(value)


def _dict_json(value: object) -> dict[str, Any]:
    if isinstance(value, dict):
        return dict(value)
    return {}


def _string_list_json(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value]


def _required_datetime(value: object) -> datetime:
    timestamp = _as_utc(value)
    if timestamp is None:
        raise ValueError("required inventory timestamp is missing")
    return timestamp


def _as_utc(value: object) -> datetime | None:
    if value is None:
        return None
    if not isinstance(value, datetime):
        raise TypeError(f"expected datetime value, got {type(value).__name__}")
    offset = value.utcoffset()
    if value.tzinfo is None or offset is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _newest_datetime(*values: datetime | None) -> datetime | None:
    timestamps = [value for value in values if value is not None]
    if not timestamps:
        return None
    return max(timestamps)


def _json_scalar(value: object) -> str | int | float | bool | None:
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, str | int | float | bool) or value is None:
        return value
    return str(value)


def _keyset_sort_value(sort_column: sa.Column[Any], value: object) -> object:
    if isinstance(sort_column.type, sa.DateTime) and isinstance(value, str):
        try:
            return datetime.fromisoformat(value)
        except ValueError as exc:
            raise CursorTampered() from exc
    return value


def _null_bucket_column(
    sort: InventorySort,
    sort_column: sa.Column[Any],
) -> sa.ColumnElement[int]:
    if sort.direction == "asc":
        return sa.case((sort_column.is_(None), 0), else_=1)
    return sa.case((sort_column.is_(None), 1), else_=0)


def _uses_null_bucket(sort_column: sa.Column[Any]) -> bool:
    return bool(sort_column.nullable)


def _null_bucket_value(direction: str, value: object) -> int:
    if direction == "asc":
        return 0 if value is None else 1
    return 1 if value is None else 0
