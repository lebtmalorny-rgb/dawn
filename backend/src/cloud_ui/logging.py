import logging
from collections.abc import Mapping
from typing import Any

from pythonjsonlogger.json import JsonFormatter

from cloud_ui.audit.redaction import sanitize_metadata


def redact_mapping(values: Mapping[str, Any]) -> dict[str, Any]:
    return sanitize_metadata(values)


def configure_logging(level: str) -> None:
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter("%(asctime)s %(levelname)s %(name)s %(message)s"))
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level.upper())
