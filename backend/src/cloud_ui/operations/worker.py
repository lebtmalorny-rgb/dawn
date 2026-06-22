from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime

from cloud_ui.operations.catalog import WorkflowCatalog
from cloud_ui.operations.mistral import (
    MistralAdapter,
    MistralExecution,
    MistralLostResponse,
    MistralUnavailable,
)
from cloud_ui.operations.models import Operation
from cloud_ui.operations.repository import OperationRepository


@dataclass(frozen=True)
class OperationWorkerResult:
    processed: bool
    operation_id: str | None
    status: str | None


class OperationWorker:
    def __init__(
        self,
        *,
        repository: OperationRepository,
        catalog: WorkflowCatalog,
        mistral: MistralAdapter,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._repository = repository
        self._catalog = catalog
        self._mistral = mistral
        self._clock = clock or (lambda: datetime.now(UTC))

    def run_once(self) -> OperationWorkerResult:
        outbox_item = self._repository.claim_next_outbox_item(now=self._clock())
        if outbox_item is None:
            return OperationWorkerResult(processed=False, operation_id=None, status=None)

        operation = self._repository.get_operation(outbox_item.operation_id)
        if operation is None:
            self._repository.mark_outbox_dispatched(outbox_item.outbox_id)
            return OperationWorkerResult(
                processed=True,
                operation_id=outbox_item.operation_id,
                status="missing",
            )

        operation = self._prepare_dispatch(operation)
        definition = self._catalog.get_definition(
            operation.workflow_key,
            operation.workflow_version,
        )
        existing_execution = self._first_execution(operation.correlation_id)
        if existing_execution is not None:
            running = self._attach_and_mark_running(
                operation=operation,
                execution=existing_execution,
                attempt_outcome="lookup_existing",
                outbox_id=outbox_item.outbox_id,
            )
            return OperationWorkerResult(
                processed=True,
                operation_id=running.operation_id,
                status=running.status,
            )

        try:
            execution = self._mistral.start_execution(
                workflow_name=definition.mistral_workflow_name,
                correlation_id=operation.correlation_id,
                input_json=operation.input_json,
            )
        except MistralLostResponse:
            self._repository.record_attempt(
                operation_id=operation.operation_id,
                adapter_action="start_execution",
                outcome="start_lost_response",
                safe_error_code="mistral_lost_response",
            )
            execution_after_loss = self._first_execution(operation.correlation_id)
            if execution_after_loss is not None:
                running = self._attach_and_mark_running(
                    operation=operation,
                    execution=execution_after_loss,
                    attempt_outcome="lookup_existing",
                    outbox_id=outbox_item.outbox_id,
                )
                return OperationWorkerResult(
                    processed=True,
                    operation_id=running.operation_id,
                    status=running.status,
                )
            unknown = self._mark_unknown(
                operation=operation,
                outbox_id=outbox_item.outbox_id,
                safe_error_code="mistral_lost_response",
            )
            return OperationWorkerResult(
                processed=True,
                operation_id=unknown.operation_id,
                status=unknown.status,
            )
        except MistralUnavailable:
            self._repository.record_attempt(
                operation_id=operation.operation_id,
                adapter_action="start_execution",
                outcome="start_unavailable",
                safe_error_code="mistral_unavailable",
            )
            unknown = self._mark_unknown(
                operation=operation,
                outbox_id=outbox_item.outbox_id,
                safe_error_code="mistral_unavailable",
            )
            return OperationWorkerResult(
                processed=True,
                operation_id=unknown.operation_id,
                status=unknown.status,
            )

        self._repository.record_attempt(
            operation_id=operation.operation_id,
            adapter_action="start_execution",
            outcome="start_success",
            external_execution_id=execution.external_execution_id,
        )
        running = self._attach_and_mark_running(
            operation=operation,
            execution=execution,
            attempt_outcome=None,
            outbox_id=outbox_item.outbox_id,
        )
        return OperationWorkerResult(
            processed=True,
            operation_id=running.operation_id,
            status=running.status,
        )

    def _prepare_dispatch(self, operation: Operation) -> Operation:
        current = operation
        if current.status == "accepted":
            current = self._repository.transition_operation(
                operation_id=current.operation_id,
                desired_status="queued",
                event_type="operation.queued",
                safe_message="Operation queued for dispatch",
                metadata={},
            )
        if current.status == "queued":
            current = self._repository.transition_operation(
                operation_id=current.operation_id,
                desired_status="dispatching",
                event_type="operation.dispatching",
                safe_message="Operation dispatch started",
                metadata={},
            )
        return current

    def _first_execution(self, correlation_id: str) -> MistralExecution | None:
        executions = self._mistral.list_executions_by_correlation(correlation_id)
        if not executions:
            return None
        return executions[0]

    def _attach_and_mark_running(
        self,
        *,
        operation: Operation,
        execution: MistralExecution,
        attempt_outcome: str | None,
        outbox_id: str,
    ) -> Operation:
        if attempt_outcome is not None:
            self._repository.record_attempt(
                operation_id=operation.operation_id,
                adapter_action="lookup_execution",
                outcome=attempt_outcome,
                external_execution_id=execution.external_execution_id,
            )
        attached = self._repository.attach_external_execution(
            operation_id=operation.operation_id,
            external_execution_id=execution.external_execution_id,
        )
        if attached.status != "running":
            attached = self._repository.transition_operation(
                operation_id=operation.operation_id,
                desired_status="running",
                event_type="operation.running",
                safe_message="External execution is running",
                metadata={"external_execution_id": execution.external_execution_id},
            )
        self._repository.mark_outbox_dispatched(outbox_id)
        return attached

    def _mark_unknown(
        self,
        *,
        operation: Operation,
        outbox_id: str,
        safe_error_code: str,
    ) -> Operation:
        unknown = self._repository.transition_operation(
            operation_id=operation.operation_id,
            desired_status="unknown",
            event_type="operation.unknown",
            safe_message="External execution state requires reconciliation",
            safe_error_code=safe_error_code,
            metadata={},
            outcome="unknown",
        )
        self._repository.mark_outbox_dispatched(outbox_id)
        return unknown
