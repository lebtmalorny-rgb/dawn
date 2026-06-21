from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from typing import Any, Literal, Protocol

from pydantic import BaseModel, ConfigDict, field_validator

from cloud_ui.logging import redact_mapping

AuditOutcome = Literal["success", "failure", "unknown"]


class AuditEvent(BaseModel):
    model_config = ConfigDict(frozen=True)

    event_id: str
    event_version: str
    occurred_at: datetime
    actor_type: str
    actor_id: str
    actor_display: str
    authentication_method: str
    session_reference: str | None
    action: str
    event_type: str
    outcome: AuditOutcome
    target_type: str
    target_id: str | None
    request_id: str
    correlation_id: str
    service: str
    metadata: dict[str, Any]

    @field_validator("occurred_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        offset = value.utcoffset()
        if value.tzinfo is None or offset is None:
            raise ValueError("Audit event timestamp must be timezone-aware")
        if offset.total_seconds() != 0:
            raise ValueError("Audit event timestamp must use UTC")
        return value


class AuditSink(Protocol):
    def record(self, event: AuditEvent) -> None:
        """Persist an already sanitized audit event."""


class InMemoryAuditSink(AuditSink):
    def __init__(self) -> None:
        self.events: list[AuditEvent] = []

    def record(self, event: AuditEvent) -> None:
        self.events.append(event.model_copy(update={"metadata": sanitize_metadata(event.metadata)}))


def sanitize_metadata(metadata: Mapping[str, Any]) -> dict[str, Any]:
    return redact_mapping(metadata)
