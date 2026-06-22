from __future__ import annotations

import pytest

from cloud_ui.operations.state_machine import (
    OperationTransitionError,
    assert_transition_allowed,
    is_terminal,
)


@pytest.mark.parametrize(
    ("current", "desired"),
    [
        ("accepted", "queued"),
        ("queued", "dispatching"),
        ("dispatching", "running"),
        ("dispatching", "unknown"),
        ("running", "succeeded"),
        ("running", "partially_succeeded"),
        ("running", "failed"),
        ("running", "unknown"),
        ("running", "cancel_requested"),
        ("cancel_requested", "cancelled"),
        ("cancel_requested", "running"),
        ("unknown", "running"),
        ("unknown", "succeeded"),
        ("unknown", "partially_succeeded"),
        ("unknown", "failed"),
        ("unknown", "cancelled"),
    ],
)
def test_operation_state_machine_allows_documented_transitions(
    current: str,
    desired: str,
) -> None:
    assert_transition_allowed(current, desired)


@pytest.mark.parametrize(
    ("current", "desired"),
    [
        ("accepted", "running"),
        ("queued", "succeeded"),
        ("dispatching", "cancelled"),
        ("running", "queued"),
        ("cancel_requested", "succeeded"),
        ("succeeded", "running"),
        ("partially_succeeded", "failed"),
        ("failed", "unknown"),
        ("cancelled", "running"),
    ],
)
def test_operation_state_machine_rejects_unsafe_transitions(
    current: str,
    desired: str,
) -> None:
    with pytest.raises(OperationTransitionError) as exc_info:
        assert_transition_allowed(current, desired)

    assert exc_info.value.current == current
    assert exc_info.value.desired == desired


@pytest.mark.parametrize(
    ("status", "expected"),
    [
        ("accepted", False),
        ("queued", False),
        ("dispatching", False),
        ("running", False),
        ("cancel_requested", False),
        ("unknown", False),
        ("succeeded", True),
        ("partially_succeeded", True),
        ("failed", True),
        ("cancelled", True),
    ],
)
def test_is_terminal_matches_operation_contract(status: str, expected: bool) -> None:
    assert is_terminal(status) is expected


def test_unknown_status_is_rejected() -> None:
    with pytest.raises(OperationTransitionError) as exc_info:
        assert_transition_allowed("running", "waiting")

    assert exc_info.value.current == "running"
    assert exc_info.value.desired == "waiting"
