from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Protocol

from cloud_ui.audit.models import AuditEvent, AuditOutcome
from cloud_ui.audit.redaction import sanitize_metadata

__all__ = [
    "AuditEvent",
    "AuditOutcome",
    "AuditSink",
    "InMemoryAuditSink",
    "sanitize_audit_metadata",
]


class AuditSink(Protocol):
    def record(self, event: AuditEvent) -> None:
        """Persist an already sanitized audit event."""


class InMemoryAuditSink(AuditSink):
    def __init__(self) -> None:
        self.events: list[AuditEvent] = []

    def record(self, event: AuditEvent) -> None:
        self.events.append(event.model_copy(update={"metadata": sanitize_metadata(event.metadata)}))


def sanitize_audit_metadata(metadata: Mapping[str, Any]) -> dict[str, Any]:
    return sanitize_metadata(metadata)
