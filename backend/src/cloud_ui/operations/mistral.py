from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from pydantic import BaseModel, ConfigDict


class MistralExecution(BaseModel):
    model_config = ConfigDict(frozen=True)

    external_execution_id: str
    workflow_name: str
    correlation_id: str
    input_json: dict[str, Any]
    state: str


class MistralAdapter(Protocol):
    def start_execution(
        self,
        *,
        workflow_name: str,
        correlation_id: str,
        input_json: dict[str, Any],
    ) -> MistralExecution:
        """Start an execution or raise a typed adapter error."""

    def list_executions_by_correlation(self, correlation_id: str) -> list[MistralExecution]:
        """Return known executions carrying the portal correlation ID."""

    def get_execution(self, external_execution_id: str) -> MistralExecution:
        """Return a single execution by external ID."""

    def cancel_execution(self, external_execution_id: str) -> MistralExecution:
        """Request cancellation when Mistral state allows it."""


class MistralAdapterError(Exception):
    code = "mistral_adapter_error"

    def __init__(self, message: str | None = None) -> None:
        super().__init__(message or self.code)


class MistralLostResponse(MistralAdapterError):
    code = "mistral_lost_response"


class MistralUnavailable(MistralAdapterError):
    code = "mistral_unavailable"


class MistralNotFound(MistralAdapterError):
    code = "mistral_not_found"


@dataclass
class _StartFailure:
    mode: str
    create_execution: bool


class InMemoryMistralAdapter:
    def __init__(self) -> None:
        self._executions: list[MistralExecution] = []
        self._next_start_failure: _StartFailure | None = None
        self.start_count = 0

    def fail_next_start_with_lost_response(self, *, create_execution: bool) -> None:
        self._next_start_failure = _StartFailure(
            mode="lost_response",
            create_execution=create_execution,
        )

    def fail_next_start_with_unavailable(self) -> None:
        self._next_start_failure = _StartFailure(mode="unavailable", create_execution=False)

    def create_execution(
        self,
        *,
        workflow_name: str,
        correlation_id: str,
        input_json: dict[str, Any],
    ) -> MistralExecution:
        execution = MistralExecution(
            external_execution_id=f"mistral-execution-{len(self._executions) + 1:06d}",
            workflow_name=workflow_name,
            correlation_id=correlation_id,
            input_json=input_json,
            state="RUNNING",
        )
        self._executions.append(execution)
        return execution

    def start_execution(
        self,
        *,
        workflow_name: str,
        correlation_id: str,
        input_json: dict[str, Any],
    ) -> MistralExecution:
        self.start_count += 1
        failure = self._next_start_failure
        self._next_start_failure = None
        if failure is not None and failure.mode == "unavailable":
            raise MistralUnavailable()
        if failure is not None and failure.mode == "lost_response":
            if failure.create_execution:
                self.create_execution(
                    workflow_name=workflow_name,
                    correlation_id=correlation_id,
                    input_json=input_json,
                )
            raise MistralLostResponse()
        return self.create_execution(
            workflow_name=workflow_name,
            correlation_id=correlation_id,
            input_json=input_json,
        )

    def list_executions_by_correlation(self, correlation_id: str) -> list[MistralExecution]:
        return [
            execution
            for execution in self._executions
            if execution.correlation_id == correlation_id
        ]

    def get_execution(self, external_execution_id: str) -> MistralExecution:
        for execution in self._executions:
            if execution.external_execution_id == external_execution_id:
                return execution
        raise MistralNotFound()

    def cancel_execution(self, external_execution_id: str) -> MistralExecution:
        execution = self.get_execution(external_execution_id)
        cancelled = execution.model_copy(update={"state": "CANCELLED"})
        self._executions = [
            cancelled
            if item.external_execution_id == external_execution_id
            else item
            for item in self._executions
        ]
        return cancelled
