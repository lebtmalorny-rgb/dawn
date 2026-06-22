from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

AuditOutcome = Literal["success", "failure", "unknown"]
AuditDeliveryState = Literal[
    "not_queued",
    "pending",
    "claimed",
    "delivered",
    "retry_wait",
    "dead_letter",
]


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
    metadata: dict[str, Any] = Field(default_factory=dict)
    cloud_id: str | None = None
    region_id: str | None = None
    project_id: str | None = None
    scope_type: str | None = None
    scope_id: str | None = None
    source_ip: str | None = None
    trusted_proxy_chain: tuple[str, ...] = ()
    operation_id: str | None = None
    external_execution_id: str | None = None
    component: str | None = None
    safe_error_code: str | None = None
    delivery_state: AuditDeliveryState = "not_queued"

    @field_validator("occurred_at")
    @classmethod
    def require_utc_timestamp(cls, value: datetime) -> datetime:
        offset = value.utcoffset()
        if value.tzinfo is None or offset is None:
            raise ValueError("Audit event timestamp must be timezone-aware")
        if offset.total_seconds() != 0:
            raise ValueError("Audit event timestamp must use UTC")
        return value

    def to_delivery_envelope(self, *, sink_id: str) -> dict[str, Any]:
        occurred_at = self.occurred_at.replace(microsecond=0)
        return {
            "event_id": self.event_id,
            "event_version": self.event_version,
            "sink_id": sink_id,
            "occurred_at": occurred_at.isoformat().replace("+00:00", "Z"),
            "actor": {
                "type": self.actor_type,
                "id": self.actor_id,
                "display": self.actor_display,
                "authentication_method": self.authentication_method,
                "session_reference": self.session_reference,
            },
            "action": self.action,
            "event_type": self.event_type,
            "outcome": self.outcome,
            "target": {"type": self.target_type, "id": self.target_id},
            "scope": {
                "cloud_id": self.cloud_id,
                "region_id": self.region_id,
                "project_id": self.project_id,
                "scope_type": self.scope_type,
                "scope_id": self.scope_id,
            },
            "source": {
                "ip": self.source_ip,
                "trusted_proxy_chain": list(self.trusted_proxy_chain),
            },
            "request_id": self.request_id,
            "correlation_id": self.correlation_id,
            "operation_id": self.operation_id,
            "external_execution_id": self.external_execution_id,
            "service": self.service,
            "component": self.component,
            "safe_error_code": self.safe_error_code,
            "delivery_state": self.delivery_state,
            "metadata": self.metadata,
        }
