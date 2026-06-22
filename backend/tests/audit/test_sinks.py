from __future__ import annotations

import pytest

from cloud_ui.audit.sinks import (
    FluentdHttpAuditSink,
    LocalTestAuditSink,
    PermanentSinkError,
    TemporarySinkError,
)


def test_local_test_sink_acknowledges_and_stores_envelope() -> None:
    sink = LocalTestAuditSink()
    envelope = {"event_id": "event-1", "metadata": {"normal": "visible"}}

    ack = sink.send(envelope)

    assert ack.message_id == "local-test:event-1"
    assert sink.envelopes == [envelope]


def test_local_test_sink_can_model_temporary_and_permanent_failures() -> None:
    sink = LocalTestAuditSink()
    sink.fail_temporarily("siem_unavailable")

    with pytest.raises(TemporarySinkError) as temporary:
        sink.send({"event_id": "event-1"})

    sink.recover()
    sink.fail_permanently("schema_rejected")

    with pytest.raises(PermanentSinkError) as permanent:
        sink.send({"event_id": "event-1"})

    assert temporary.value.safe_error_code == "siem_unavailable"
    assert permanent.value.safe_error_code == "schema_rejected"


def test_fluentd_http_sink_builds_redacted_json_payload_without_network() -> None:
    payload = FluentdHttpAuditSink.build_payload(
        {
            "event_id": "event-1",
            "occurred_at": "2026-06-22T12:00:03Z",
            "metadata": {"token": "***"},
        },
        tag="cloud_ui.audit",
    )

    assert payload == {
        "tag": "cloud_ui.audit",
        "time": "2026-06-22T12:00:03Z",
        "record": {
            "event_id": "event-1",
            "occurred_at": "2026-06-22T12:00:03Z",
            "metadata": {"token": "***"},
        },
    }
    assert "DKB_CANARY" not in repr(payload)
