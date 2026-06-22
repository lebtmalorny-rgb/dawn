from __future__ import annotations

from typing import Any


def build_audit_event_json_schema() -> dict[str, Any]:
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": "Cloud UI Audit Event",
        "type": "object",
        "required": [
            "event_id",
            "event_version",
            "occurred_at",
            "actor",
            "action",
            "event_type",
            "outcome",
            "target",
            "request_id",
            "correlation_id",
            "service",
            "metadata",
        ],
        "additionalProperties": True,
    }
