from __future__ import annotations

from cloud_ui.audit.models import AuditEvent
from cloud_ui.audit.repository import AuditRepository
from cloud_ui.security.audit import AuditSink


class DurableAuditSink(AuditSink):
    def __init__(
        self,
        *,
        repository: AuditRepository,
        keep_events_for_tests: bool = False,
    ) -> None:
        self._repository = repository
        self._keep_events_for_tests = keep_events_for_tests
        self.events: list[AuditEvent] = []

    def record(self, event: AuditEvent) -> None:
        stored = self._repository.record_event(event, queue_delivery=True)
        if self._keep_events_for_tests:
            self.events.append(stored)

