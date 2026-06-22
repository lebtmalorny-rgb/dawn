from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol


@dataclass(frozen=True)
class SinkAck:
    message_id: str


class SinkError(Exception):
    def __init__(self, safe_error_code: str) -> None:
        self.safe_error_code = safe_error_code
        super().__init__(safe_error_code)


class TemporarySinkError(SinkError):
    pass


class PermanentSinkError(SinkError):
    pass


class AuditSinkAdapter(Protocol):
    sink_id: str

    def send(self, envelope: dict[str, Any]) -> SinkAck:
        """Send one sanitized audit event envelope."""

    def heartbeat(self, envelope: dict[str, Any]) -> SinkAck:
        """Send one sanitized heartbeat envelope."""


class LocalTestAuditSink(AuditSinkAdapter):
    sink_id = "local-test"

    def __init__(self) -> None:
        self.envelopes: list[dict[str, Any]] = []
        self.heartbeats: list[dict[str, Any]] = []
        self._temporary_error: str | None = None
        self._permanent_error: str | None = None

    def send(self, envelope: dict[str, Any]) -> SinkAck:
        self._raise_if_configured()
        self.envelopes.append(envelope)
        return SinkAck(message_id=f"{self.sink_id}:{envelope.get('event_id', 'unknown')}")

    def heartbeat(self, envelope: dict[str, Any]) -> SinkAck:
        self._raise_if_configured()
        self.heartbeats.append(envelope)
        return SinkAck(message_id=f"{self.sink_id}:heartbeat")

    def fail_temporarily(self, safe_error_code: str) -> None:
        self._temporary_error = safe_error_code
        self._permanent_error = None

    def fail_permanently(self, safe_error_code: str) -> None:
        self._permanent_error = safe_error_code
        self._temporary_error = None

    def recover(self) -> None:
        self._temporary_error = None
        self._permanent_error = None

    def _raise_if_configured(self) -> None:
        if self._temporary_error is not None:
            raise TemporarySinkError(self._temporary_error)
        if self._permanent_error is not None:
            raise PermanentSinkError(self._permanent_error)


class FluentdHttpAuditSink:
    sink_id = "fluentd-http"

    @staticmethod
    def build_payload(envelope: dict[str, Any], *, tag: str) -> dict[str, Any]:
        return {
            "tag": tag,
            "time": envelope.get("occurred_at"),
            "record": envelope,
        }
