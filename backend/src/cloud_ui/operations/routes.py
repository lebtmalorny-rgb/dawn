from __future__ import annotations

import hashlib
import hmac
import json
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Literal
from uuid import uuid4

from fastapi import APIRouter, Query, Request
from pydantic import BaseModel, ConfigDict, Field
from starlette.responses import JSONResponse

from cloud_ui.groups.models import GroupNotFound, ResourceGroup
from cloud_ui.groups.repository import GroupRepository
from cloud_ui.inventory.repository import InventoryRepository
from cloud_ui.operations.catalog import (
    WorkflowCatalog,
    WorkflowDefinition,
    WorkflowDefinitionNotFound,
)
from cloud_ui.operations.input_validation import InputValidationError, validate_json_input
from cloud_ui.operations.models import Operation, OperationEvent, OperationTargetCreate
from cloud_ui.operations.repository import (
    OperationIdempotencyConflict,
    OperationRepository,
)
from cloud_ui.security.audit import AuditEvent, AuditOutcome
from cloud_ui.security.dependencies import SecurityServices
from cloud_ui.security.identity import Subject
from cloud_ui.security.rbac import AuthorizationDenied
from cloud_ui.security.routes import CSRF_HEADER_NAME, SESSION_COOKIE_NAME
from cloud_ui.security.sessions import SessionExpired, SessionNotFound, SessionRecord

IDEMPOTENCY_KEY_HEADER_NAME = "idempotency-key"
DEFAULT_OPERATION_LIST_LIMIT = 50
MAX_OPERATION_LIST_LIMIT = 200
_OPERATION_ID_KEY = b"portal-operation-id"
_OPERATION_REQUEST_KEY = b"portal-operation-request"
_OPERATION_IDEMPOTENCY_KEY = b"portal-operation-idempotency-key"


@dataclass(frozen=True)
class OperationServices:
    repository: OperationRepository | None
    inventory_repository: InventoryRepository | None
    group_repository: GroupRepository | None
    catalog: WorkflowCatalog

    @property
    def available(self) -> bool:
        return self.repository is not None


class WorkflowDefinitionItem(BaseModel):
    model_config = ConfigDict(frozen=True)

    workflow_key: str
    version: str
    title: str
    description: str
    target_type: str
    required_capability: str
    risk_level: str
    approval_mode: str
    cancel_policy: str
    checksum: str
    mistral_workflow_name: None = None


class WorkflowDefinitionListResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    items: list[WorkflowDefinitionItem]
    limit: int


class OperationTargetRequest(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    target_type: Literal["host", "vm", "group"]
    cloud_id: str = Field(min_length=1, max_length=128)
    region_id: str = Field(min_length=1, max_length=128)
    resource_id: str = Field(min_length=1, max_length=128)
    expected_revision: int | None = Field(default=None, ge=1)


class OperationSubmitRequest(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    workflow_key: str = Field(min_length=1, max_length=128)
    version: str = Field(min_length=1, max_length=32)
    targets: list[OperationTargetRequest] = Field(min_length=1, max_length=200)
    input: dict[str, Any]


class OperationSubmitResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    operation_id: str
    status: str


class OperationEventResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    event_id: str
    event_type: str
    from_status: str | None
    to_status: str | None
    outcome: str
    safe_message: str
    safe_error_code: str | None
    metadata: dict[str, Any]
    created_at: datetime


class OperationDetailResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    operation_id: str
    workflow_key: str
    workflow_version: str
    status: str
    correlation_id: str
    external_execution_id: str | None
    created_at: datetime
    updated_at: datetime
    events: list[OperationEventResponse]


class CancelResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    operation_id: str
    status: str


def build_operation_router(services: OperationServices, security: SecurityServices) -> APIRouter:
    router = APIRouter()

    @router.get("/workflow-definitions", response_model=WorkflowDefinitionListResponse)
    def list_workflow_definitions(
        request: Request,
        limit: int = Query(default=DEFAULT_OPERATION_LIST_LIMIT, ge=1),
    ) -> WorkflowDefinitionListResponse | JSONResponse:
        session = _require_session(security, request)
        if isinstance(session, JSONResponse):
            return session
        denied = _require_capability(
            security,
            request,
            session,
            "operation.read",
            target_type="workflow_definition",
            target_id=None,
        )
        if denied is not None:
            return denied
        effective_limit = min(max(1, limit), MAX_OPERATION_LIST_LIMIT)
        return WorkflowDefinitionListResponse(
            items=[
                _definition_item(definition)
                for definition in services.catalog.list_definitions()[:effective_limit]
            ],
            limit=effective_limit,
        )

    @router.post("/operations", response_model=OperationSubmitResponse, status_code=202)
    def submit_operation(
        body: OperationSubmitRequest,
        request: Request,
    ) -> OperationSubmitResponse | JSONResponse:
        session = _require_session(security, request)
        if isinstance(session, JSONResponse):
            return session
        guard = _require_mutation_guard(
            security,
            request,
            session,
            capability="operation.read",
            target_type="operation",
            target_id=None,
        )
        if guard is not None:
            return guard
        repository = _require_repository(services, request)
        if isinstance(repository, JSONResponse):
            return repository
        idempotency_key = _require_idempotency_key(request)
        if isinstance(idempotency_key, JSONResponse):
            return idempotency_key
        definition = _definition_or_error(services.catalog, body, request)
        if isinstance(definition, JSONResponse):
            return definition
        denied = _require_capability(
            security,
            request,
            session,
            definition.required_capability,
            target_type="workflow_definition",
            target_id=f"{definition.workflow_key}@{definition.version}",
        )
        if denied is not None:
            return denied
        try:
            input_json = validate_json_input(definition.input_schema_json, body.input)
        except InputValidationError as exc:
            return _error(
                400,
                "invalid_workflow_input",
                f"Workflow input rejected: {exc.code}",
                _request_id(request),
            )
        targets = _operation_targets(
            services=services,
            security=security,
            session=session,
            definition=definition,
            body=body,
            request=request,
        )
        if isinstance(targets, JSONResponse):
            return targets
        request_hash = _request_hash(body=body)
        key_hash = _idempotency_key_hash(
            actor_subject_id=session.subject.subject_id,
            workflow_key=definition.workflow_key,
            workflow_version=definition.version,
            scope_type=session.subject.scope_type,
            scope_id=session.subject.scope_id,
            idempotency_key=idempotency_key,
        )
        operation_id = _operation_id(
            actor_subject_id=session.subject.subject_id,
            workflow_key=definition.workflow_key,
            workflow_version=definition.version,
            scope_type=session.subject.scope_type,
            scope_id=session.subject.scope_id,
            key_hash=key_hash,
        )
        try:
            operation = repository.accept_operation(
                operation_id=operation_id,
                workflow_key=definition.workflow_key,
                workflow_version=definition.version,
                definition_checksum=definition.checksum,
                actor_subject_id=session.subject.subject_id,
                scope_type=session.subject.scope_type,
                scope_id=session.subject.scope_id,
                idempotency_key_hash=key_hash,
                request_hash=request_hash,
                correlation_id=operation_id,
                input_json=input_json,
                targets=targets,
            )
        except OperationIdempotencyConflict:
            return _error(
                409,
                "idempotency_key_conflict",
                "Idempotency-Key уже использован для другого запроса",
                _request_id(request),
            )

        _record_audit(
            security,
            request,
            action="operation.accepted",
            event_type="operation",
            outcome="success",
            target_type="operation",
            target_id=operation.operation_id,
            subject=session.subject,
            session_reference=session.session_id,
            metadata={
                "workflow_key": definition.workflow_key,
                "workflow_version": definition.version,
                "target_count": len(targets),
                "idempotency_key_hash": key_hash,
            },
        )
        return OperationSubmitResponse(
            operation_id=operation.operation_id,
            status=operation.status,
        )

    @router.get("/operations/{operation_id}", response_model=OperationDetailResponse)
    def get_operation(
        operation_id: str,
        request: Request,
    ) -> OperationDetailResponse | JSONResponse:
        session = _require_session(security, request)
        if isinstance(session, JSONResponse):
            return session
        denied = _require_capability(
            security,
            request,
            session,
            "operation.read",
            target_type="operation",
            target_id=operation_id,
        )
        if denied is not None:
            return denied
        repository = _require_repository(services, request)
        if isinstance(repository, JSONResponse):
            return repository
        operation = repository.get_operation(operation_id)
        if operation is None:
            return _error(404, "operation_not_found", "Операция не найдена", _request_id(request))
        return _operation_detail(operation, repository.list_events(operation_id, limit=200))

    @router.post("/operations/{operation_id}/cancel", response_model=CancelResponse)
    def cancel_operation(operation_id: str, request: Request) -> CancelResponse | JSONResponse:
        session = _require_session(security, request)
        if isinstance(session, JSONResponse):
            return session
        guard = _require_mutation_guard(
            security,
            request,
            session,
            capability="operation.read",
            target_type="operation",
            target_id=operation_id,
        )
        if guard is not None:
            return guard
        return _error(
            409,
            "operation_not_cancelable",
            "Операция пока не поддерживает отмену",
            _request_id(request),
        )

    return router


def _definition_item(definition: WorkflowDefinition) -> WorkflowDefinitionItem:
    return WorkflowDefinitionItem(
        workflow_key=definition.workflow_key,
        version=definition.version,
        title=definition.title,
        description=definition.description,
        target_type=definition.target_type,
        required_capability=definition.required_capability,
        risk_level=definition.risk_level,
        approval_mode=definition.approval_mode,
        cancel_policy=definition.cancel_policy,
        checksum=definition.checksum,
    )


def _definition_or_error(
    catalog: WorkflowCatalog,
    body: OperationSubmitRequest,
    request: Request,
) -> WorkflowDefinition | JSONResponse:
    try:
        return catalog.get_definition(body.workflow_key, body.version)
    except WorkflowDefinitionNotFound:
        return _error(
            404,
            "workflow_definition_not_found",
            "Workflow definition не найден",
            _request_id(request),
        )


def _operation_targets(
    *,
    services: OperationServices,
    security: SecurityServices,
    session: SessionRecord,
    definition: WorkflowDefinition,
    body: OperationSubmitRequest,
    request: Request,
) -> list[OperationTargetCreate] | JSONResponse:
    if definition.target_type != "host":
        return _error(
            400,
            "unsupported_target_type",
            "Тип цели пока не поддерживается",
            _request_id(request),
        )
    inventory_repository = _require_inventory_repository(services, request)
    if isinstance(inventory_repository, JSONResponse):
        return inventory_repository
    operation_targets: list[OperationTargetCreate] = []
    for target in body.targets:
        if target.target_type == definition.target_type:
            target_or_error = _host_operation_target(
                inventory_repository=inventory_repository,
                target=target,
                request=request,
            )
            if isinstance(target_or_error, JSONResponse):
                return target_or_error
            operation_targets.append(target_or_error)
            continue

        if target.target_type == "group":
            expanded = _expand_group_target(
                services=services,
                security=security,
                session=session,
                inventory_repository=inventory_repository,
                target=target,
                request=request,
            )
            if isinstance(expanded, JSONResponse):
                return expanded
            operation_targets.extend(expanded)
            continue

        return _error(
            400,
            "target_type_mismatch",
            "Тип цели не соответствует workflow definition",
            _request_id(request),
        )
    return operation_targets


def _host_operation_target(
    *,
    inventory_repository: InventoryRepository,
    target: OperationTargetRequest,
    request: Request,
    source_group: ResourceGroup | None = None,
) -> OperationTargetCreate | JSONResponse:
    hypervisor = inventory_repository.get_hypervisor(
        target.cloud_id,
        target.region_id,
        target.resource_id,
    )
    if hypervisor is None:
        return _error(404, "target_not_found", "Цель операции не найдена", _request_id(request))
    snapshot: dict[str, Any] = {
        "host_name": hypervisor.host_name,
        "service_status": hypervisor.service_status,
        "service_state": hypervisor.service_state,
        "maintenance_status": hypervisor.maintenance_status,
        "observed_at": hypervisor.observed_at.isoformat(),
    }
    if source_group is not None:
        snapshot["source_group_id"] = source_group.group_id
        snapshot["source_group_revision"] = source_group.revision
    return OperationTargetCreate(
        target_type="host",
        cloud_id=target.cloud_id,
        region_id=target.region_id,
        resource_id=target.resource_id,
        snapshot=snapshot,
    )


def _expand_group_target(
    *,
    services: OperationServices,
    security: SecurityServices,
    session: SessionRecord,
    inventory_repository: InventoryRepository,
    target: OperationTargetRequest,
    request: Request,
) -> list[OperationTargetCreate] | JSONResponse:
    denied = _require_capability(
        security,
        request,
        session,
        "group.read",
        target_type="group",
        target_id=target.resource_id,
    )
    if denied is not None:
        return denied
    group_repository = _require_group_repository(services, request)
    if isinstance(group_repository, JSONResponse):
        return group_repository
    group = group_repository.get_group(target.resource_id)
    if group is None or not _can_access_group(session.subject, group):
        return _error(404, "group_not_found", "Группа не найдена", _request_id(request))
    if target.expected_revision is not None and target.expected_revision != group.revision:
        return _error(
            409,
            "stale_group_snapshot",
            "Версия группы устарела",
            _request_id(request),
        )
    if group.resource_type not in {"host", "mixed"}:
        return _error(
            400,
            "target_type_mismatch",
            "Тип группы не соответствует workflow definition",
            _request_id(request),
        )
    try:
        members = group_repository.list_members(group.group_id, limit=200)
    except GroupNotFound:
        return _error(404, "group_not_found", "Группа не найдена", _request_id(request))
    host_members = [member for member in members if member.resource_type == "host"]
    if not host_members:
        return _error(400, "empty_group_target", "Группа не содержит целей", _request_id(request))

    expanded: list[OperationTargetCreate] = []
    for member in host_members:
        expanded_target = _host_operation_target(
            inventory_repository=inventory_repository,
            target=OperationTargetRequest(
                target_type="host",
                cloud_id=member.cloud_id,
                region_id=member.region_id,
                resource_id=member.resource_id,
            ),
            request=request,
            source_group=group,
        )
        if isinstance(expanded_target, JSONResponse):
            return expanded_target
        expanded.append(expanded_target)
    return expanded


def _can_access_group(subject: Subject, group: ResourceGroup) -> bool:
    if "portal_admin" in subject.roles:
        return True
    return (
        group.owner_subject_id == subject.subject_id
        and group.scope_type == subject.scope_type
        and group.scope_id == subject.scope_id
    )


def _operation_detail(
    operation: Operation,
    events: list[OperationEvent],
) -> OperationDetailResponse:
    return OperationDetailResponse(
        operation_id=operation.operation_id,
        workflow_key=operation.workflow_key,
        workflow_version=operation.workflow_version,
        status=operation.status,
        correlation_id=operation.correlation_id,
        external_execution_id=operation.external_execution_id,
        created_at=operation.created_at,
        updated_at=operation.updated_at,
        events=[
            OperationEventResponse(
                event_id=event.event_id,
                event_type=event.event_type,
                from_status=event.from_status,
                to_status=event.to_status,
                outcome=event.outcome,
                safe_message=event.safe_message,
                safe_error_code=event.safe_error_code,
                metadata=event.metadata_json,
                created_at=event.created_at,
            )
            for event in events
        ],
    )


def _require_repository(
    services: OperationServices,
    request: Request,
) -> OperationRepository | JSONResponse:
    if services.repository is not None:
        return services.repository
    return _error(
        503,
        "operations_unavailable",
        "Operation API временно недоступен",
        _request_id(request),
    )


def _require_inventory_repository(
    services: OperationServices,
    request: Request,
) -> InventoryRepository | JSONResponse:
    if services.inventory_repository is not None:
        return services.inventory_repository
    return _error(
        503,
        "inventory_unavailable",
        "Inventory API временно недоступен",
        _request_id(request),
    )


def _require_group_repository(
    services: OperationServices,
    request: Request,
) -> GroupRepository | JSONResponse:
    if services.group_repository is not None:
        return services.group_repository
    return _error(503, "groups_unavailable", "Group API временно недоступен", _request_id(request))


def _require_mutation_guard(
    services: SecurityServices,
    request: Request,
    session: SessionRecord,
    *,
    capability: str,
    target_type: str,
    target_id: str | None,
) -> JSONResponse | None:
    origin_error = _require_trusted_origin(services, request, session)
    if origin_error is not None:
        return origin_error
    csrf_error = _require_csrf(services, request, session)
    if csrf_error is not None:
        return csrf_error
    return _require_capability(
        services,
        request,
        session,
        capability,
        target_type=target_type,
        target_id=target_id,
    )


def _require_idempotency_key(request: Request) -> str | JSONResponse:
    raw_key = request.headers.get(IDEMPOTENCY_KEY_HEADER_NAME)
    if raw_key is None or raw_key.strip() == "":
        return _error(
            400,
            "idempotency_key_required",
            "Требуется Idempotency-Key",
            _request_id(request),
        )
    return raw_key.strip()


def _require_session(services: SecurityServices, request: Request) -> SessionRecord | JSONResponse:
    request_id = _request_id(request)
    session_id = request.cookies.get(SESSION_COOKIE_NAME)
    try:
        return services.session_manager.get_session(session_id)
    except SessionExpired:
        _record_audit(
            services,
            request,
            action="session.timeout",
            event_type="session",
            outcome="failure",
            target_type="session",
            target_id=session_id,
            subject=None,
            session_reference=session_id,
            metadata={},
        )
        return _error(401, "session_expired", "Сессия истекла", request_id)
    except SessionNotFound:
        _record_audit(
            services,
            request,
            action="session.required",
            event_type="session",
            outcome="failure",
            target_type="session",
            target_id=None,
            subject=None,
            metadata={},
        )
        return _error(401, "not_authenticated", "Требуется вход", request_id)


def _require_capability(
    services: SecurityServices,
    request: Request,
    session: SessionRecord,
    capability: str,
    *,
    target_type: str,
    target_id: str | None,
) -> JSONResponse | None:
    try:
        services.policy_service.require_capability(session.subject, capability)
    except AuthorizationDenied as exc:
        _record_audit(
            services,
            request,
            action="authorization.denied",
            event_type="authorization",
            outcome="failure",
            target_type=target_type,
            target_id=target_id,
            subject=session.subject,
            session_reference=session.session_id,
            metadata={"code": exc.code, "capability": capability},
        )
        return _error(403, exc.code, "Действие запрещено", _request_id(request))
    return None


def _require_trusted_origin(
    services: SecurityServices,
    request: Request,
    session: SessionRecord,
) -> JSONResponse | None:
    origin = request.headers.get("origin")
    if origin is None or origin in services.trusted_origins:
        return None
    _record_audit(
        services,
        request,
        action="origin.denied",
        event_type="authorization",
        outcome="failure",
        target_type="session",
        target_id=session.session_id,
        subject=session.subject,
        session_reference=session.session_id,
        metadata={"reason": "untrusted_origin"},
    )
    return _error(403, "origin_forbidden", "Источник запроса запрещен", _request_id(request))


def _require_csrf(
    services: SecurityServices,
    request: Request,
    session: SessionRecord,
) -> JSONResponse | None:
    if services.session_manager.verify_csrf(session, request.headers.get(CSRF_HEADER_NAME)):
        return None
    _record_audit(
        services,
        request,
        action="csrf.denied",
        event_type="authorization",
        outcome="failure",
        target_type="session",
        target_id=session.session_id,
        subject=session.subject,
        session_reference=session.session_id,
        metadata={},
    )
    return _error(403, "csrf_failed", "CSRF проверка не пройдена", _request_id(request))


def _operation_id(
    *,
    actor_subject_id: str,
    workflow_key: str,
    workflow_version: str,
    scope_type: str,
    scope_id: str | None,
    key_hash: str,
) -> str:
    digest = _hash_payload(
        {
            "actor_subject_id": actor_subject_id,
            "workflow_key": workflow_key,
            "workflow_version": workflow_version,
            "scope_type": scope_type,
            "scope_id": scope_id,
            "key_hash": key_hash,
        },
        key=_OPERATION_ID_KEY,
    )
    return f"operation-{digest[:32]}"


def _idempotency_key_hash(
    *,
    actor_subject_id: str,
    workflow_key: str,
    workflow_version: str,
    scope_type: str,
    scope_id: str | None,
    idempotency_key: str,
) -> str:
    return _hash_payload(
        {
            "actor_subject_id": actor_subject_id,
            "workflow_key": workflow_key,
            "workflow_version": workflow_version,
            "scope_type": scope_type,
            "scope_id": scope_id,
            "idempotency_key": idempotency_key,
        },
        key=_OPERATION_IDEMPOTENCY_KEY,
    )


def _request_hash(*, body: OperationSubmitRequest) -> str:
    return _hash_payload(body.model_dump(mode="json"), key=_OPERATION_REQUEST_KEY)


def _hash_payload(payload: dict[str, Any], *, key: bytes) -> str:
    raw_payload = json.dumps(
        payload,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return hmac.new(key, raw_payload, hashlib.sha256).hexdigest()


def _error(status_code: int, code: str, message: str, request_id: str) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={"error": {"code": code, "message": message, "request_id": request_id}},
    )


def _record_audit(
    services: SecurityServices,
    request: Request,
    *,
    action: str,
    event_type: str,
    outcome: AuditOutcome,
    target_type: str,
    target_id: str | None,
    subject: Subject | None,
    metadata: dict[str, Any],
    session_reference: str | None = None,
) -> None:
    request_id = _request_id(request)
    services.audit_sink.record(
        AuditEvent(
            event_id=str(uuid4()),
            event_version="1",
            occurred_at=services.clock.now(),
            actor_type=subject.subject_type if subject is not None else "anonymous",
            actor_id=subject.subject_id if subject is not None else "anonymous",
            actor_display=subject.display_name if subject is not None else "anonymous",
            authentication_method="mock" if subject is not None else "none",
            session_reference=session_reference,
            action=action,
            event_type=event_type,
            outcome=outcome,
            target_type=target_type,
            target_id=target_id,
            request_id=request_id,
            correlation_id=request_id,
            service="cloud-ui-api",
            metadata=metadata,
        )
    )


def _request_id(request: Request) -> str:
    return str(
        getattr(request.state, "request_id", None) or request.headers.get("x-request-id") or ""
    )
