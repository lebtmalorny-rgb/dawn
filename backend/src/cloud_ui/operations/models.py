from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict

OperationStatus = Literal[
    "accepted",
    "queued",
    "dispatching",
    "running",
    "cancel_requested",
    "succeeded",
    "partially_succeeded",
    "failed",
    "cancelled",
    "unknown",
]

OPERATION_STATUSES: frozenset[str] = frozenset(
    {
        "accepted",
        "queued",
        "dispatching",
        "running",
        "cancel_requested",
        "succeeded",
        "partially_succeeded",
        "failed",
        "cancelled",
        "unknown",
    }
)

TERMINAL_OPERATION_STATUSES: frozenset[str] = frozenset(
    {"succeeded", "partially_succeeded", "failed", "cancelled"}
)


class OperationTargetCreate(BaseModel):
    model_config = ConfigDict(frozen=True)

    target_type: str
    cloud_id: str
    region_id: str
    resource_id: str
    snapshot: dict[str, Any]


class Operation(BaseModel):
    model_config = ConfigDict(frozen=True)

    operation_id: str
    workflow_key: str
    workflow_version: str
    definition_checksum: str
    actor_subject_id: str
    scope_type: str
    scope_id: str | None
    status: str
    request_hash: str
    idempotency_key_hash: str
    target_snapshot_json: list[dict[str, Any]]
    input_json: dict[str, Any]
    correlation_id: str
    external_execution_id: str | None
    created_at: datetime
    updated_at: datetime
    accepted_at: datetime
    started_at: datetime | None
    completed_at: datetime | None


class OperationEvent(BaseModel):
    model_config = ConfigDict(frozen=True)

    event_id: str
    operation_id: str
    event_type: str
    from_status: str | None
    to_status: str | None
    outcome: str
    safe_message: str
    safe_error_code: str | None
    metadata_json: dict[str, Any]
    created_at: datetime


class OperationOutboxItem(BaseModel):
    model_config = ConfigDict(frozen=True)

    outbox_id: str
    operation_id: str
    event_type: str
    state: str
    attempt_count: int
    not_before_at: datetime
    created_at: datetime
    updated_at: datetime
