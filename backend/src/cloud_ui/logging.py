import logging
from collections.abc import Mapping
from typing import Any

from pythonjsonlogger.json import JsonFormatter

SECRET_MARKERS = (
    "password",
    "passwd",
    "secret",
    "token",
    "credential",
    "database_url",
    "rabbitmq_url",
)


def redact_mapping(values: Mapping[str, Any]) -> dict[str, Any]:
    redacted: dict[str, Any] = {}
    for key, value in values.items():
        if any(marker in key.lower() for marker in SECRET_MARKERS):
            redacted[key] = "***"
        else:
            redacted[key] = value
    return redacted


def configure_logging(level: str) -> None:
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter("%(asctime)s %(levelname)s %(name)s %(message)s"))
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level.upper())
