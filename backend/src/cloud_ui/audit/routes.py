from dataclasses import dataclass, field
from datetime import datetime
from typing import Annotated, Any
from uuid import uuid4

from fastapi import APIRouter, Query, Request
from pydantic import BaseModel, ConfigDict, Field, model_validator
from starlette.responses import JSONResponse

from cloud_ui.audit.models import AuditEvent, AuditOutcome
from cloud_ui.audit.repository import (
    AuditEventFilters,
    AuditListCursor,
    AuditRepository,
)
from cloud_ui.config import DEV_AUDIT_CURSOR_SIGNING_KEY
from cloud_ui.inventory.cursor import CursorCodec, CursorTampered
from cloud_ui.security.dependencies import SecurityServices
from cloud_ui.security.identity import Subject
from cloud_ui.security.rbac import AuthorizationDenied
from cloud_ui.security.routes import CSRF_HEADER_NAME, SESSION_COOKIE_NAME
from cloud_ui.security.sessions import SessionExpired, SessionNotFound, SessionRecord

DEFAULT_AUDIT_LIST_LIMIT = 50
MAX_AUDIT_LIST_LIMIT = 200
AUDIT_SORT = "occurred_at.desc,event_id.desc"


@dataclass(frozen=True)
class AuditServices:
    repository: AuditRepository | None
    cursor_codec: CursorCodec = field(
        default_factory=lambda: CursorCodec(signing_key=DEV_AUDIT_CURSOR_SIGNING_KEY)
    )
    default_limit: int = DEFAULT_AUDIT_LIST_LIMIT
    max_limit: int = MAX_AUDIT_LIST_LIMIT

    @property
    def available(self) -> bool:
        return self.repository is not None


class AuditActorResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    type: str
    id: str
    display: str
    authentication_method: str
    session_reference: str | None


class AuditTargetResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    type: str
    id: str | None


class AuditScopeResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    cloud_id: str | None
    region_id: str | None
    project_id: str | None
    scope_type: str | None
    scope_id: str | None


class AuditSourceResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    ip: str | None
    trusted_proxy_chain: list[str]


class AuditEventResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    event_id: str
    event_version: str
    occurred_at: datetime
    actor: AuditActorResponse
    action: str
    event_type: str
    outcome: str
    target: AuditTargetResponse
    scope: AuditScopeResponse
    source: AuditSourceResponse
    request_id: str
    correlation_id: str
    operation_id: str | None
    external_execution_id: str | None
    service: str
    component: str | None
    safe_error_code: str | None
    delivery_state: str
    metadata: dict[str, Any]


class AuditEventListResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    items: list[AuditEventResponse]
    next_cursor: str | None
    limit: int
    sort: str


class AuditExportRequest(BaseModel):
    model_config = ConfigDict(frozen=True, populate_by_name=True, extra="forbid")

    from_: datetime
    to: datetime
    limit: int = Field(default=1_000, ge=1, le=10_000)

    @model_validator(mode="before")
    @classmethod
    def accept_json_from_key(cls, value: Any) -> Any:
        if isinstance(value, dict) and "from" in value and "from_" not in value:
            normalized = dict(value)
            normalized["from_"] = normalized.pop("from")
            return normalized
        return value


class AuditExportResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    export_request_id: str
    status: str


def build_audit_router(services: AuditServices, security: SecurityServices) -> APIRouter:
    router = APIRouter()

    @router.get("/audit/events", response_model=AuditEventListResponse)
    def list_audit_events(
        request: Request,
        limit: int | None = Query(default=None, ge=1),
        cursor: str | None = Query(default=None),
        from_: Annotated[datetime | None, Query(alias="from")] = None,
        to: datetime | None = None,
        action: str | None = Query(default=None),
        outcome: str | None = Query(default=None),
        actor_id: str | None = Query(default=None),
        target_type: str | None = Query(default=None),
        target_id: str | None = Query(default=None),
        request_id: str | None = Query(default=None),
        correlation_id: str | None = Query(default=None),
        operation_id: str | None = Query(default=None),
        delivery_state: str | None = Query(default=None),
        safe_error_code: str | None = Query(default=None),
    ) -> AuditEventListResponse | JSONResponse:
        session = _require_session(security, request)
        if isinstance(session, JSONResponse):
            return session
        denied = _require_capability(
            security,
            request,
            session,
            "audit.read",
            target_type="audit_event",
            target_id=None,
        )
        if denied is not None:
            return denied
        repository = _require_repository(services, request)
        if isinstance(repository, JSONResponse):
            return repository
        filters = AuditEventFilters(
            occurred_from=from_,
            occurred_to=to,
            action=action,
            outcome=outcome,
            actor_id=actor_id,
            target_type=target_type,
            target_id=target_id,
            request_id=request_id,
            correlation_id=correlation_id,
            operation_id=operation_id,
            delivery_state=delivery_state,
            safe_error_code=safe_error_code,
        )
        filter_payload = _filter_payload(filters)
        audit_cursor = _decode_audit_cursor(
            services.cursor_codec,
            cursor,
            request,
            filter_payload=filter_payload,
        )
        if isinstance(audit_cursor, JSONResponse):
            return audit_cursor
        effective_limit = min(max(1, limit or services.default_limit), services.max_limit)
        page = repository.list_events(
            filters=filters,
            limit=effective_limit,
            cursor=audit_cursor,
        )
        _record_audit(
            security,
            request,
            action="audit.events.list",
            event_type="audit_access",
            outcome="success",
            target_type="audit_event",
            target_id=None,
            subject=session.subject,
            session_reference=session.session_id,
            metadata={"filter_count": len(filter_payload), "limit": effective_limit},
        )
        return AuditEventListResponse(
            items=[_audit_event_response(event) for event in page.items],
            next_cursor=_encode_audit_cursor(
                services.cursor_codec,
                page.next_cursor,
                filter_payload=filter_payload,
            ),
            limit=effective_limit,
            sort=AUDIT_SORT,
        )

    @router.get("/audit/events/{event_id}", response_model=AuditEventResponse)
    def get_audit_event(event_id: str, request: Request) -> AuditEventResponse | JSONResponse:
        session = _require_session(security, request)
        if isinstance(session, JSONResponse):
            return session
        denied = _require_capability(
            security,
            request,
            session,
            "audit.read",
            target_type="audit_event",
            target_id=event_id,
        )
        if denied is not None:
            return denied
        repository = _require_repository(services, request)
        if isinstance(repository, JSONResponse):
            return repository
        event = repository.get_event(event_id)
        if event is None:
            return _error(
                404,
                "audit_event_not_found",
                "Событие аудита не найдено",
                _request_id(request),
            )
        _record_audit(
            security,
            request,
            action="audit.event.detail",
            event_type="audit_access",
            outcome="success",
            target_type="audit_event",
            target_id=event.event_id,
            subject=session.subject,
            session_reference=session.session_id,
            metadata={},
        )
        return _audit_event_response(event)

    @router.post("/audit/export", response_model=AuditExportResponse, status_code=202)
    def request_audit_export(
        body: AuditExportRequest,
        request: Request,
    ) -> AuditExportResponse | JSONResponse:
        session = _require_session(security, request)
        if isinstance(session, JSONResponse):
            return session
        guard = _require_mutation_guard(
            security,
            request,
            session,
            capability="audit.export",
            target_type="audit_export",
            target_id=None,
        )
        if guard is not None:
            return guard
        repository = _require_repository(services, request)
        if isinstance(repository, JSONResponse):
            return repository
        export_request_id = f"audit-export-{uuid4().hex}"
        _record_audit(
            security,
            request,
            action="audit.export.requested",
            event_type="audit_access",
            outcome="success",
            target_type="audit_export",
            target_id=export_request_id,
            subject=session.subject,
            session_reference=session.session_id,
            metadata={
                "from": body.from_.isoformat(),
                "to": body.to.isoformat(),
                "limit": body.limit,
            },
        )
        return AuditExportResponse(export_request_id=export_request_id, status="accepted")

    return router


def _audit_event_response(event: AuditEvent) -> AuditEventResponse:
    return AuditEventResponse(
        event_id=event.event_id,
        event_version=event.event_version,
        occurred_at=event.occurred_at,
        actor=AuditActorResponse(
            type=event.actor_type,
            id=event.actor_id,
            display=event.actor_display,
            authentication_method=event.authentication_method,
            session_reference=event.session_reference,
        ),
        action=event.action,
        event_type=event.event_type,
        outcome=event.outcome,
        target=AuditTargetResponse(type=event.target_type, id=event.target_id),
        scope=AuditScopeResponse(
            cloud_id=event.cloud_id,
            region_id=event.region_id,
            project_id=event.project_id,
            scope_type=event.scope_type,
            scope_id=event.scope_id,
        ),
        source=AuditSourceResponse(
            ip=event.source_ip,
            trusted_proxy_chain=list(event.trusted_proxy_chain),
        ),
        request_id=event.request_id,
        correlation_id=event.correlation_id,
        operation_id=event.operation_id,
        external_execution_id=event.external_execution_id,
        service=event.service,
        component=event.component,
        safe_error_code=event.safe_error_code,
        delivery_state=event.delivery_state,
        metadata=event.metadata,
    )


def _decode_audit_cursor(
    codec: CursorCodec,
    cursor: str | None,
    request: Request,
    *,
    filter_payload: dict[str, Any],
) -> AuditListCursor | None | JSONResponse:
    if cursor is None:
        return None
    try:
        payload = codec.decode(cursor)
    except CursorTampered:
        return _cursor_tampered(request)

    if payload.get("sort") != AUDIT_SORT or payload.get("filters") != filter_payload:
        return _cursor_tampered(request)
    occurred_at = payload.get("occurred_at")
    event_id = payload.get("event_id")
    if not isinstance(occurred_at, str) or not isinstance(event_id, str):
        return _cursor_tampered(request)
    try:
        parsed_occurred_at = datetime.fromisoformat(occurred_at)
    except ValueError:
        return _cursor_tampered(request)
    return AuditListCursor(occurred_at=parsed_occurred_at, event_id=event_id)


def _encode_audit_cursor(
    codec: CursorCodec,
    cursor: AuditListCursor | None,
    *,
    filter_payload: dict[str, Any],
) -> str | None:
    if cursor is None:
        return None
    return codec.encode(
        {
            "sort": AUDIT_SORT,
            "occurred_at": cursor.occurred_at.isoformat(),
            "event_id": cursor.event_id,
            "filters": filter_payload,
        }
    )


def _filter_payload(filters: AuditEventFilters) -> dict[str, Any]:
    payload: dict[str, Any] = {}
    if filters.occurred_from is not None:
        payload["from"] = filters.occurred_from.isoformat()
    if filters.occurred_to is not None:
        payload["to"] = filters.occurred_to.isoformat()
    for field_name in (
        "action",
        "outcome",
        "actor_id",
        "target_type",
        "target_id",
        "request_id",
        "correlation_id",
        "operation_id",
        "delivery_state",
        "safe_error_code",
    ):
        value = getattr(filters, field_name)
        if value is not None:
            payload[field_name] = value
    return payload


def _cursor_tampered(request: Request) -> JSONResponse:
    return _error(400, "cursor_tampered", "Некорректный cursor", _request_id(request))


def _require_repository(
    services: AuditServices,
    request: Request,
) -> AuditRepository | JSONResponse:
    if services.repository is not None:
        return services.repository
    return _error(503, "audit_unavailable", "Audit API временно недоступен", _request_id(request))


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
            component="audit-api",
            metadata=metadata,
        )
    )


def _request_id(request: Request) -> str:
    return str(
        getattr(request.state, "request_id", None) or request.headers.get("x-request-id") or ""
    )
