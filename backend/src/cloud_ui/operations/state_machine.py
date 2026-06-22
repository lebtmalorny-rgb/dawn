from __future__ import annotations

from dataclasses import dataclass

from cloud_ui.operations.models import OPERATION_STATUSES, TERMINAL_OPERATION_STATUSES


@dataclass(frozen=True)
class OperationTransitionError(Exception):
    current: str
    desired: str

    def __str__(self) -> str:
        return f"operation transition is not allowed: {self.current} -> {self.desired}"


_ALLOWED_TRANSITIONS: dict[str, frozenset[str]] = {
    "accepted": frozenset({"queued"}),
    "queued": frozenset({"dispatching"}),
    "dispatching": frozenset({"running", "unknown", "failed"}),
    "running": frozenset(
        {
            "cancel_requested",
            "succeeded",
            "partially_succeeded",
            "failed",
            "unknown",
        }
    ),
    "cancel_requested": frozenset({"cancelled", "running", "unknown"}),
    "unknown": frozenset({"running", "succeeded", "partially_succeeded", "failed", "cancelled"}),
    "succeeded": frozenset(),
    "partially_succeeded": frozenset(),
    "failed": frozenset(),
    "cancelled": frozenset(),
}


def assert_transition_allowed(current: str, desired: str) -> None:
    if current not in OPERATION_STATUSES or desired not in OPERATION_STATUSES:
        raise OperationTransitionError(current=current, desired=desired)
    if desired not in _ALLOWED_TRANSITIONS[current]:
        raise OperationTransitionError(current=current, desired=desired)


def is_terminal(status: str) -> bool:
    if status not in OPERATION_STATUSES:
        raise OperationTransitionError(current=status, desired=status)
    return status in TERMINAL_OPERATION_STATUSES
