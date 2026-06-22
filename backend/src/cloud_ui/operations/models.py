from __future__ import annotations

from typing import Literal

OperationStatus = Literal[
    "accepted",
    "queued",
    "dispatching",
    "running",
    "cancel_requested",
    "succeeded",
    "partially_succeeded",
    "failed",
    "cancelled",
    "unknown",
]

OPERATION_STATUSES: frozenset[str] = frozenset(
    {
        "accepted",
        "queued",
        "dispatching",
        "running",
        "cancel_requested",
        "succeeded",
        "partially_succeeded",
        "failed",
        "cancelled",
        "unknown",
    }
)

TERMINAL_OPERATION_STATUSES: frozenset[str] = frozenset(
    {"succeeded", "partially_succeeded", "failed", "cancelled"}
)
