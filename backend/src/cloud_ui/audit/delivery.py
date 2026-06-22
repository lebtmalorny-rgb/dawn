from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from cloud_ui.audit.repository import AuditRepository
from cloud_ui.audit.sinks import AuditSinkAdapter, PermanentSinkError, TemporarySinkError


@dataclass(frozen=True)
class AuditDeliveryResult:
    processed: bool
    status: str
    event_id: str | None = None


class AuditDeliveryWorker:
    def __init__(
        self,
        *,
        repository: AuditRepository,
        sink: AuditSinkAdapter,
        retry_delay_seconds: int = 30,
        max_attempts: int = 3,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._repository = repository
        self._sink = sink
        self._retry_delay = timedelta(seconds=retry_delay_seconds)
        self._max_attempts = max_attempts
        self._clock = clock or (lambda: datetime.now(UTC))

    def _now(self) -> datetime:
        now = self._clock()
        if now.tzinfo is None:
            return now.replace(tzinfo=UTC)
        return now.astimezone(UTC)

    def run_once(self) -> AuditDeliveryResult:
        now = self._now()
        item = self._repository.claim_next_outbox_item(now=now)
        if item is None:
            return AuditDeliveryResult(processed=False, status="idle")

        try:
            ack = self._sink.send(item.envelope)
        except TemporarySinkError as exc:
            self._repository.record_delivery_attempt(
                outbox_id=item.outbox_id,
                event_id=item.event_id,
                sink_id=item.sink_id,
                outcome="temporary_failure",
                safe_error_code=exc.safe_error_code,
                created_at=now,
                attempt_count=item.attempt_count,
            )
            if item.attempt_count >= self._max_attempts:
                self._repository.mark_outbox_dead_letter(
                    item.outbox_id,
                    safe_error_code=exc.safe_error_code,
                    now=now,
                )
                return AuditDeliveryResult(
                    processed=True,
                    status="dead_letter",
                    event_id=item.event_id,
                )
            self._repository.schedule_outbox_retry(
                item.outbox_id,
                safe_error_code=exc.safe_error_code,
                retry_at=now + self._retry_delay,
                now=now,
            )
            return AuditDeliveryResult(
                processed=True,
                status="retry_wait",
                event_id=item.event_id,
            )
        except PermanentSinkError as exc:
            self._repository.record_delivery_attempt(
                outbox_id=item.outbox_id,
                event_id=item.event_id,
                sink_id=item.sink_id,
                outcome="permanent_failure",
                safe_error_code=exc.safe_error_code,
                created_at=now,
                attempt_count=item.attempt_count,
            )
            self._repository.mark_outbox_dead_letter(
                item.outbox_id,
                safe_error_code=exc.safe_error_code,
                now=now,
            )
            return AuditDeliveryResult(
                processed=True,
                status="dead_letter",
                event_id=item.event_id,
            )

        self._repository.record_delivery_attempt(
            outbox_id=item.outbox_id,
            event_id=item.event_id,
            sink_id=item.sink_id,
            outcome="success",
            ack_id=ack.message_id,
            created_at=now,
            attempt_count=item.attempt_count,
        )
        self._repository.mark_outbox_delivered(
            item.outbox_id,
            sink_message_id=ack.message_id,
            now=now,
        )
        return AuditDeliveryResult(processed=True, status="delivered", event_id=item.event_id)

    def run_heartbeat(self) -> AuditDeliveryResult:
        now = self._now()
        queue_depth, oldest_age = self._repository.audit_queue_status(now=now)
        envelope = {
            "event_id": "audit-heartbeat",
            "occurred_at": now.replace(microsecond=0).isoformat().replace("+00:00", "Z"),
            "queue_depth": queue_depth,
            "oldest_pending_age_seconds": oldest_age,
        }
        try:
            self._sink.heartbeat(envelope)
        except (TemporarySinkError, PermanentSinkError):
            self._repository.upsert_heartbeat(
                sink_id=self._sink.sink_id,
                state="failed",
                at=now,
                queue_depth=queue_depth,
                oldest_pending_age_seconds=oldest_age,
            )
            return AuditDeliveryResult(processed=True, status="heartbeat_failed")

        self._repository.upsert_heartbeat(
            sink_id=self._sink.sink_id,
            state="ok",
            at=now,
            queue_depth=queue_depth,
            oldest_pending_age_seconds=oldest_age,
        )
        return AuditDeliveryResult(processed=True, status="heartbeat_ok")
