from __future__ import annotations

from cloud_ui.audit.redaction import REDACTED, sanitize_metadata


def test_sanitize_metadata_removes_secret_canaries_recursively() -> None:
    metadata = {
        "normal": "visible",
        "password": "DKB_CANARY_PASSWORD",
        "nested": {
            "auth_token": "DKB_CANARY_TOKEN",
            "items": [
                {"cookie": "DKB_CANARY_COOKIE"},
                "Bearer DKB_CANARY_AUTH",
                "-----BEGIN PRIVATE KEY-----DKB_CANARY_KEY",
            ],
        },
        "workflow": {
            "summary": "safe",
            "workflow_secret": "DKB_CANARY_WORKFLOW_SECRET",
        },
        "database_url": "mysql://user:DKB_CANARY_DB@db/cloud_ui",
        "rabbitmq_url": "amqp://user:DKB_CANARY_RABBIT@rabbitmq/%2Fcloud-ui",
    }

    sanitized = sanitize_metadata(metadata)

    assert sanitized["normal"] == "visible"
    assert sanitized["password"] == REDACTED
    assert sanitized["nested"]["auth_token"] == REDACTED
    assert sanitized["nested"]["items"] == [REDACTED, REDACTED, REDACTED]
    assert sanitized["workflow"] == {"summary": "safe", "workflow_secret": REDACTED}
    assert sanitized["database_url"] == REDACTED
    assert sanitized["rabbitmq_url"] == REDACTED
    assert "DKB_CANARY" not in repr(sanitized)


def test_sanitize_metadata_drops_raw_body_by_default() -> None:
    sanitized = sanitize_metadata(
        {
            "request_body": {"reason": "contains business data"},
            "response_body": {"status": "debug"},
            "body": "raw payload",
            "safe_error_code": "invalid_input",
        }
    )

    assert sanitized["request_body"] == REDACTED
    assert sanitized["response_body"] == REDACTED
    assert sanitized["body"] == REDACTED
    assert sanitized["safe_error_code"] == "invalid_input"
