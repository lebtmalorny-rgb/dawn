from __future__ import annotations

import pytest

from cloud_ui.operations.mistral import (
    InMemoryMistralAdapter,
    MistralLostResponse,
    MistralUnavailable,
)


def test_in_memory_mistral_lists_executions_by_correlation() -> None:
    adapter = InMemoryMistralAdapter()

    execution = adapter.start_execution(
        workflow_name="portal.maintenance_host_precheck.v1",
        correlation_id="operation-0001",
        input_json={"dry_run": True},
    )

    assert execution.external_execution_id.startswith("mistral-execution-")
    assert execution.state == "RUNNING"
    assert adapter.list_executions_by_correlation("operation-0001") == [execution]
    assert adapter.list_executions_by_correlation("missing") == []


def test_lost_response_can_still_be_found_by_correlation() -> None:
    adapter = InMemoryMistralAdapter()
    adapter.fail_next_start_with_lost_response(create_execution=True)

    with pytest.raises(MistralLostResponse):
        adapter.start_execution(
            workflow_name="portal.maintenance_host_precheck.v1",
            correlation_id="operation-0001",
            input_json={"dry_run": True},
        )

    executions = adapter.list_executions_by_correlation("operation-0001")
    assert len(executions) == 1
    assert adapter.start_count == 1


def test_unavailable_start_does_not_create_execution() -> None:
    adapter = InMemoryMistralAdapter()
    adapter.fail_next_start_with_unavailable()

    with pytest.raises(MistralUnavailable):
        adapter.start_execution(
            workflow_name="portal.maintenance_host_precheck.v1",
            correlation_id="operation-0001",
            input_json={"dry_run": True},
        )

    assert adapter.list_executions_by_correlation("operation-0001") == []
    assert adapter.start_count == 1
