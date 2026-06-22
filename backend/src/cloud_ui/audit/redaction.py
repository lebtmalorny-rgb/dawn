from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

REDACTED = "***"

SECRET_KEY_MARKERS = (
    "password",
    "passwd",
    "secret",
    "token",
    "credential",
    "authorization",
    "cookie",
    "private_key",
    "database_url",
    "rabbitmq_url",
)
RAW_BODY_KEYS = {"body", "request_body", "response_body", "raw_body"}
SECRET_VALUE_MARKERS = (
    "DKB_CANARY",
    "BEGIN PRIVATE KEY",
    "Bearer ",
)


def sanitize_metadata(metadata: Mapping[str, Any]) -> dict[str, Any]:
    sanitized = _sanitize_mapping(metadata)
    if isinstance(sanitized, dict):
        return sanitized
    return {}


def _sanitize_mapping(values: Mapping[str, Any]) -> dict[str, Any] | str:
    if values and all(_is_secret_key(key) or _is_raw_body_key(key) for key in values):
        return REDACTED
    redacted: dict[str, Any] = {}
    for key, value in values.items():
        if _is_secret_key(key) or _is_raw_body_key(key):
            redacted[key] = REDACTED
        else:
            redacted[key] = _sanitize_value(value)
    return redacted


def _sanitize_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        return _sanitize_mapping(value)
    if isinstance(value, str):
        return REDACTED if _is_secret_value(value) else value
    if isinstance(value, Sequence) and not isinstance(value, str | bytes | bytearray):
        return [_sanitize_value(item) for item in value]
    return value


def _is_secret_key(key: str) -> bool:
    normalized = key.lower()
    return any(marker in normalized for marker in SECRET_KEY_MARKERS)


def _is_raw_body_key(key: str) -> bool:
    return key.lower() in RAW_BODY_KEYS


def _is_secret_value(value: str) -> bool:
    return any(marker in value for marker in SECRET_VALUE_MARKERS)
