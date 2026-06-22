from __future__ import annotations

from collections.abc import Callable, Sequence
from datetime import UTC, datetime
from typing import Any

import sqlalchemy as sa
from sqlalchemy.engine import Connection, Engine, RowMapping

from cloud_ui.operations import schema
from cloud_ui.operations.models import (
    Operation,
    OperationEvent,
    OperationOutboxItem,
    OperationTargetCreate,
)
from cloud_ui.operations.state_machine import assert_transition_allowed, is_terminal


class OperationRepositoryError(Exception):
    code = "operation_repository_error"

    def __init__(self, message: str | None = None) -> None:
        super().__init__(message or self.code)


class OperationNotFound(OperationRepositoryError):
    code = "operation_not_found"


class OperationIdempotencyConflict(OperationRepositoryError):
    code = "operation_idempotency_conflict"

    def __init__(self, *, existing_operation_id: str) -> None:
        self.existing_operation_id = existing_operation_id
        super().__init__(self.code)


class OutboxItemNotFound(OperationRepositoryError):
    code = "operation_outbox_not_found"


class OperationRepository:
    def __init__(
        self,
        *,
        engine: Engine,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._engine = engine
        self._clock = clock or (lambda: datetime.now(UTC))

    @property
    def engine(self) -> Engine:
        return self._engine

    def _now(self) -> datetime:
        return _as_utc(self._clock())

    def accept_operation(
        self,
        *,
        operation_id: str,
        workflow_key: str,
        workflow_version: str,
        definition_checksum: str,
        actor_subject_id: str,
        scope_type: str,
        scope_id: str | None,
        idempotency_key_hash: str,
        request_hash: str,
        correlation_id: str,
        input_json: dict[str, Any],
        targets: Sequence[OperationTargetCreate],
    ) -> Operation:
        now = self._now()
        scope_hash = _scope_hash(scope_type=scope_type, scope_id=scope_id)
        target_snapshot = [target.model_dump() for target in targets]
        operation_row = {
            "operation_id": operation_id,
            "workflow_key": workflow_key,
            "workflow_version": workflow_version,
            "definition_checksum": definition_checksum,
            "actor_subject_id": actor_subject_id,
            "scope_type": scope_type,
            "scope_id": scope_id,
            "status": "accepted",
            "request_hash": request_hash,
            "idempotency_key_hash": idempotency_key_hash,
            "target_snapshot_json": target_snapshot,
            "input_json": input_json,
            "correlation_id": correlation_id,
            "external_execution_id": None,
            "created_at": now,
            "updated_at": now,
            "accepted_at": now,
            "started_at": None,
            "completed_at": None,
        }
        with self._engine.begin() as connection:
            existing = _idempotency_row(
                connection=connection,
                actor_subject_id=actor_subject_id,
                workflow_key=workflow_key,
                workflow_version=workflow_version,
                scope_hash=scope_hash,
                key_hash=idempotency_key_hash,
            )
            if existing is not None:
                if str(existing["request_hash"]) != request_hash:
                    raise OperationIdempotencyConflict(
                        existing_operation_id=str(existing["operation_id"])
                    )
                return _operation_by_id(connection, str(existing["operation_id"]))

            connection.execute(schema.operations.insert().values(operation_row))
            for target in targets:
                connection.execute(
                    schema.operation_targets.insert().values(
                        operation_id=operation_id,
                        target_type=target.target_type,
                        cloud_id=target.cloud_id,
                        region_id=target.region_id,
                        resource_id=target.resource_id,
                        snapshot_json=target.snapshot,
                        status="accepted",
                        created_at=now,
                        updated_at=now,
                    )
                )
            _append_event(
                connection=connection,
                operation_id=operation_id,
                event_type="operation.accepted",
                from_status=None,
                to_status="accepted",
                outcome="success",
                safe_message="Operation accepted",
                safe_error_code=None,
                metadata={},
                created_at=now,
            )
            connection.execute(
                schema.operation_outbox.insert().values(
                    outbox_id=_outbox_id(operation_id),
                    operation_id=operation_id,
                    event_type="operation.dispatch",
                    state="pending",
                    attempt_count=0,
                    not_before_at=now,
                    created_at=now,
                    updated_at=now,
                )
            )
            connection.execute(
                schema.operation_idempotency_keys.insert().values(
                    actor_subject_id=actor_subject_id,
                    workflow_key=workflow_key,
                    workflow_version=workflow_version,
                    scope_hash=scope_hash,
                    key_hash=idempotency_key_hash,
                    request_hash=request_hash,
                    operation_id=operation_id,
                    created_at=now,
                )
            )
        return _operation_from_mapping(operation_row)

    def get_operation(self, operation_id: str) -> Operation | None:
        statement = sa.select(schema.operations).where(
            schema.operations.c.operation_id == operation_id
        )
        with self._engine.connect() as connection:
            row = connection.execute(statement).mappings().one_or_none()
        if row is None:
            return None
        return _operation_from_mapping(row)

    def list_events(self, operation_id: str, *, limit: int) -> list[OperationEvent]:
        statement = (
            sa.select(schema.operation_events)
            .where(schema.operation_events.c.operation_id == operation_id)
            .order_by(
                schema.operation_events.c.created_at.asc(),
                schema.operation_events.c.event_id.asc(),
            )
            .limit(max(1, limit))
        )
        with self._engine.connect() as connection:
            rows = list(connection.execute(statement).mappings())
        return [_event_from_mapping(row) for row in rows]

    def transition_operation(
        self,
        *,
        operation_id: str,
        desired_status: str,
        event_type: str,
        safe_message: str,
        metadata: dict[str, Any],
        safe_error_code: str | None = None,
        outcome: str = "success",
    ) -> Operation:
        now = self._now()
        with self._engine.begin() as connection:
            current = _operation_row(connection, operation_id)
            if current is None:
                raise OperationNotFound(f"operation not found: {operation_id}")
            current_status = str(current["status"])
            assert_transition_allowed(current_status, desired_status)
            values: dict[str, Any] = {"status": desired_status, "updated_at": now}
            if desired_status == "running" and current["started_at"] is None:
                values["started_at"] = now
            if is_terminal(desired_status):
                values["completed_at"] = now
            connection.execute(
                schema.operations.update()
                .where(schema.operations.c.operation_id == operation_id)
                .values(**values)
            )
            _append_event(
                connection=connection,
                operation_id=operation_id,
                event_type=event_type,
                from_status=current_status,
                to_status=desired_status,
                outcome=outcome,
                safe_message=safe_message,
                safe_error_code=safe_error_code,
                metadata=metadata,
                created_at=now,
            )
            return _operation_by_id(connection, operation_id)

    def claim_next_outbox_item(self, *, now: datetime | None = None) -> OperationOutboxItem | None:
        claim_time = _as_utc(now or self._now())
        with self._engine.begin() as connection:
            row = (
                connection.execute(
                    sa.select(schema.operation_outbox)
                    .where(
                        schema.operation_outbox.c.state == "pending",
                        schema.operation_outbox.c.not_before_at <= claim_time,
                    )
                    .order_by(
                        schema.operation_outbox.c.created_at.asc(),
                        schema.operation_outbox.c.outbox_id.asc(),
                    )
                    .limit(1)
                )
                .mappings()
                .one_or_none()
            )
            if row is None:
                return None
            attempt_count = int(row["attempt_count"]) + 1
            connection.execute(
                schema.operation_outbox.update()
                .where(schema.operation_outbox.c.outbox_id == row["outbox_id"])
                .values(state="claimed", attempt_count=attempt_count, updated_at=claim_time)
            )
            claimed = _outbox_row(connection, str(row["outbox_id"]))
            if claimed is None:
                raise OutboxItemNotFound(str(row["outbox_id"]))
            return _outbox_from_mapping(claimed)

    def mark_outbox_dispatched(self, outbox_id: str) -> OperationOutboxItem:
        now = self._now()
        with self._engine.begin() as connection:
            connection.execute(
                schema.operation_outbox.update()
                .where(schema.operation_outbox.c.outbox_id == outbox_id)
                .values(state="dispatched", updated_at=now)
            )
            row = _outbox_row(connection, outbox_id)
            if row is None:
                raise OutboxItemNotFound(outbox_id)
            return _outbox_from_mapping(row)


def _operation_by_id(connection: Connection, operation_id: str) -> Operation:
    row = _operation_row(connection, operation_id)
    if row is None:
        raise OperationNotFound(f"operation not found: {operation_id}")
    return _operation_from_mapping(row)


def _operation_row(connection: Connection, operation_id: str) -> RowMapping | None:
    return (
        connection.execute(
            sa.select(schema.operations).where(schema.operations.c.operation_id == operation_id)
        )
        .mappings()
        .one_or_none()
    )


def _idempotency_row(
    *,
    connection: Connection,
    actor_subject_id: str,
    workflow_key: str,
    workflow_version: str,
    scope_hash: str,
    key_hash: str,
) -> RowMapping | None:
    return (
        connection.execute(
            sa.select(schema.operation_idempotency_keys).where(
                schema.operation_idempotency_keys.c.actor_subject_id == actor_subject_id,
                schema.operation_idempotency_keys.c.workflow_key == workflow_key,
                schema.operation_idempotency_keys.c.workflow_version == workflow_version,
                schema.operation_idempotency_keys.c.scope_hash == scope_hash,
                schema.operation_idempotency_keys.c.key_hash == key_hash,
            )
        )
        .mappings()
        .one_or_none()
    )


def _outbox_row(connection: Connection, outbox_id: str) -> RowMapping | None:
    return (
        connection.execute(
            sa.select(schema.operation_outbox).where(
                schema.operation_outbox.c.outbox_id == outbox_id
            )
        )
        .mappings()
        .one_or_none()
    )


def _append_event(
    *,
    connection: Connection,
    operation_id: str,
    event_type: str,
    from_status: str | None,
    to_status: str | None,
    outcome: str,
    safe_message: str,
    safe_error_code: str | None,
    metadata: dict[str, Any],
    created_at: datetime,
) -> None:
    connection.execute(
        schema.operation_events.insert().values(
            event_id=_next_event_id(connection, operation_id),
            operation_id=operation_id,
            event_type=event_type,
            from_status=from_status,
            to_status=to_status,
            outcome=outcome,
            safe_message=safe_message,
            safe_error_code=safe_error_code,
            metadata_json=metadata,
            created_at=created_at,
        )
    )


def _next_event_id(connection: Connection, operation_id: str) -> str:
    existing_count = int(
        connection.execute(
            sa.select(sa.func.count())
            .select_from(schema.operation_events)
            .where(schema.operation_events.c.operation_id == operation_id)
        ).scalar_one()
    )
    return f"{operation_id}-event-{existing_count + 1:06d}"


def _outbox_id(operation_id: str) -> str:
    return f"{operation_id}-outbox-dispatch"


def _scope_hash(*, scope_type: str, scope_id: str | None) -> str:
    return f"{scope_type}:{scope_id or ''}"


def _operation_from_mapping(row: RowMapping | dict[str, Any]) -> Operation:
    return Operation(
        operation_id=str(row["operation_id"]),
        workflow_key=str(row["workflow_key"]),
        workflow_version=str(row["workflow_version"]),
        definition_checksum=str(row["definition_checksum"]),
        actor_subject_id=str(row["actor_subject_id"]),
        scope_type=str(row["scope_type"]),
        scope_id=_optional_string(row["scope_id"]),
        status=str(row["status"]),
        request_hash=str(row["request_hash"]),
        idempotency_key_hash=str(row["idempotency_key_hash"]),
        target_snapshot_json=_list_of_dicts(row["target_snapshot_json"]),
        input_json=_dict_json(row["input_json"]),
        correlation_id=str(row["correlation_id"]),
        external_execution_id=_optional_string(row["external_execution_id"]),
        created_at=_as_utc(row["created_at"]),
        updated_at=_as_utc(row["updated_at"]),
        accepted_at=_as_utc(row["accepted_at"]),
        started_at=_optional_datetime(row["started_at"]),
        completed_at=_optional_datetime(row["completed_at"]),
    )


def _event_from_mapping(row: RowMapping) -> OperationEvent:
    return OperationEvent(
        event_id=str(row["event_id"]),
        operation_id=str(row["operation_id"]),
        event_type=str(row["event_type"]),
        from_status=_optional_string(row["from_status"]),
        to_status=_optional_string(row["to_status"]),
        outcome=str(row["outcome"]),
        safe_message=str(row["safe_message"]),
        safe_error_code=_optional_string(row["safe_error_code"]),
        metadata_json=_dict_json(row["metadata_json"]),
        created_at=_as_utc(row["created_at"]),
    )


def _outbox_from_mapping(row: RowMapping) -> OperationOutboxItem:
    return OperationOutboxItem(
        outbox_id=str(row["outbox_id"]),
        operation_id=str(row["operation_id"]),
        event_type=str(row["event_type"]),
        state=str(row["state"]),
        attempt_count=int(row["attempt_count"]),
        not_before_at=_as_utc(row["not_before_at"]),
        created_at=_as_utc(row["created_at"]),
        updated_at=_as_utc(row["updated_at"]),
    )


def _optional_string(value: Any) -> str | None:
    if value is None:
        return None
    return str(value)


def _dict_json(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise TypeError("expected JSON object")
    return value


def _list_of_dicts(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        raise TypeError("expected JSON array")
    return [_dict_json(item) for item in value]


def _optional_datetime(value: Any) -> datetime | None:
    if value is None:
        return None
    return _as_utc(value)


def _as_utc(value: Any) -> datetime:
    if not isinstance(value, datetime):
        raise TypeError("expected datetime")
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)
