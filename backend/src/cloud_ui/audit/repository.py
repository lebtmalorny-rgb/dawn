from __future__ import annotations

import hashlib
import json
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

import sqlalchemy as sa
from sqlalchemy.engine import Connection, Engine, RowMapping

from cloud_ui.audit import schema
from cloud_ui.audit.models import AuditEvent
from cloud_ui.audit.redaction import sanitize_metadata

DEFAULT_SINK_ID = "local-test"


class AuditRepositoryError(Exception):
    code = "audit_repository_error"


class AuditReplayConflict(AuditRepositoryError):
    code = "audit_replay_conflict"

    def __init__(self, *, event_id: str) -> None:
        self.event_id = event_id
        super().__init__(self.code)


@dataclass(frozen=True)
class AuditOutboxItem:
    outbox_id: str
    event_id: str
    sink_id: str
    state: str
    attempt_count: int
    envelope: dict[str, Any]
    event_hash: str
    not_before_at: datetime


class AuditRepository:
    def __init__(
        self,
        *,
        engine: Engine,
        clock: Callable[[], datetime] | None = None,
        sink_id: str = DEFAULT_SINK_ID,
    ) -> None:
        self._engine = engine
        self._clock = clock or (lambda: datetime.now(UTC))
        self._sink_id = sink_id

    @property
    def engine(self) -> Engine:
        return self._engine

    def _now(self) -> datetime:
        return _as_utc(self._clock())

    def record_event(self, event: AuditEvent, *, queue_delivery: bool = True) -> AuditEvent:
        now = self._now()
        sanitized = event.model_copy(
            update={
                "metadata": sanitize_metadata(event.metadata),
                "delivery_state": "pending" if queue_delivery else "not_queued",
            }
        )
        envelope = sanitized.to_delivery_envelope(sink_id=self._sink_id)
        event_hash = _hash_envelope(envelope)
        with self._engine.begin() as connection:
            existing = _event_row(connection, sanitized.event_id)
            if existing is not None:
                if str(existing["event_hash"]) != event_hash:
                    raise AuditReplayConflict(event_id=sanitized.event_id)
                return _event_from_mapping(existing)

            connection.execute(
                schema.audit_events.insert().values(
                    _event_row_values(sanitized, event_hash=event_hash, created_at=now)
                )
            )
            if queue_delivery:
                connection.execute(
                    schema.audit_outbox.insert().values(
                        outbox_id=_outbox_id(sanitized.event_id, self._sink_id),
                        event_id=sanitized.event_id,
                        sink_id=self._sink_id,
                        state="pending",
                        attempt_count=0,
                        not_before_at=now,
                        envelope_json=envelope,
                        event_hash=event_hash,
                        last_error_code=None,
                        last_error_at=None,
                        delivered_at=None,
                        sink_message_id=None,
                        created_at=now,
                        updated_at=now,
                    )
                )
        return sanitized

    def claim_next_outbox_item(self, *, now: datetime | None = None) -> AuditOutboxItem | None:
        claim_time = _as_utc(now or self._now())
        with self._engine.begin() as connection:
            row = (
                connection.execute(
                    sa.select(schema.audit_outbox)
                    .where(
                        schema.audit_outbox.c.state.in_(["pending", "retry_wait"]),
                        schema.audit_outbox.c.not_before_at <= claim_time,
                    )
                    .order_by(
                        schema.audit_outbox.c.not_before_at.asc(),
                        schema.audit_outbox.c.outbox_id.asc(),
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
                schema.audit_outbox.update()
                .where(schema.audit_outbox.c.outbox_id == row["outbox_id"])
                .values(state="claimed", attempt_count=attempt_count, updated_at=claim_time)
            )
            claimed = _outbox_row(connection, str(row["outbox_id"]))
        if claimed is None:
            return None
        return _outbox_from_mapping(claimed)


def _event_row_values(
    event: AuditEvent,
    *,
    event_hash: str,
    created_at: datetime,
) -> dict[str, Any]:
    return {
        "event_id": event.event_id,
        "event_version": event.event_version,
        "occurred_at": event.occurred_at,
        "actor_type": event.actor_type,
        "actor_id": event.actor_id,
        "actor_display": event.actor_display,
        "authentication_method": event.authentication_method,
        "session_reference": event.session_reference,
        "action": event.action,
        "event_type": event.event_type,
        "outcome": event.outcome,
        "target_type": event.target_type,
        "target_id": event.target_id,
        "cloud_id": event.cloud_id,
        "region_id": event.region_id,
        "project_id": event.project_id,
        "scope_type": event.scope_type,
        "scope_id": event.scope_id,
        "source_ip": event.source_ip,
        "trusted_proxy_chain_json": list(event.trusted_proxy_chain),
        "request_id": event.request_id,
        "correlation_id": event.correlation_id,
        "operation_id": event.operation_id,
        "external_execution_id": event.external_execution_id,
        "service": event.service,
        "component": event.component,
        "safe_error_code": event.safe_error_code,
        "delivery_state": event.delivery_state,
        "event_hash": event_hash,
        "metadata_json": event.metadata,
        "created_at": created_at,
    }


def _event_from_mapping(row: RowMapping) -> AuditEvent:
    return AuditEvent(
        event_id=str(row["event_id"]),
        event_version=str(row["event_version"]),
        occurred_at=_as_utc(row["occurred_at"]),
        actor_type=str(row["actor_type"]),
        actor_id=str(row["actor_id"]),
        actor_display=str(row["actor_display"]),
        authentication_method=str(row["authentication_method"]),
        session_reference=_optional_str(row["session_reference"]),
        action=str(row["action"]),
        event_type=str(row["event_type"]),
        outcome=row["outcome"],
        target_type=str(row["target_type"]),
        target_id=_optional_str(row["target_id"]),
        cloud_id=_optional_str(row["cloud_id"]),
        region_id=_optional_str(row["region_id"]),
        project_id=_optional_str(row["project_id"]),
        scope_type=_optional_str(row["scope_type"]),
        scope_id=_optional_str(row["scope_id"]),
        source_ip=_optional_str(row["source_ip"]),
        trusted_proxy_chain=tuple(row["trusted_proxy_chain_json"] or []),
        request_id=str(row["request_id"]),
        correlation_id=str(row["correlation_id"]),
        operation_id=_optional_str(row["operation_id"]),
        external_execution_id=_optional_str(row["external_execution_id"]),
        service=str(row["service"]),
        component=_optional_str(row["component"]),
        safe_error_code=_optional_str(row["safe_error_code"]),
        delivery_state=row["delivery_state"] or "not_queued",
        metadata=dict(row["metadata_json"]),
    )


def _event_row(connection: Connection, event_id: str) -> RowMapping | None:
    return (
        connection.execute(
            sa.select(schema.audit_events).where(schema.audit_events.c.event_id == event_id)
        )
        .mappings()
        .one_or_none()
    )


def _outbox_row(connection: Connection, outbox_id: str) -> RowMapping | None:
    return (
        connection.execute(
            sa.select(schema.audit_outbox).where(schema.audit_outbox.c.outbox_id == outbox_id)
        )
        .mappings()
        .one_or_none()
    )


def _outbox_from_mapping(row: RowMapping) -> AuditOutboxItem:
    return AuditOutboxItem(
        outbox_id=str(row["outbox_id"]),
        event_id=str(row["event_id"]),
        sink_id=str(row["sink_id"]),
        state=str(row["state"]),
        attempt_count=int(row["attempt_count"]),
        envelope=dict(row["envelope_json"]),
        event_hash=str(row["event_hash"]),
        not_before_at=_as_utc(row["not_before_at"]),
    )


def _outbox_id(event_id: str, sink_id: str) -> str:
    return f"{event_id}:{sink_id}"


def _hash_envelope(envelope: dict[str, Any]) -> str:
    payload = json.dumps(envelope, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _as_utc(value: Any) -> datetime:
    if not isinstance(value, datetime):
        raise TypeError("expected datetime")
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _optional_str(value: Any) -> str | None:
    return None if value is None else str(value)

