from __future__ import annotations

from typing import Any
from uuid import uuid4

from fastapi import APIRouter, Request
from pydantic import BaseModel, ConfigDict
from starlette.responses import JSONResponse

from cloud_ui.security.audit import AuditEvent, AuditOutcome
from cloud_ui.security.dependencies import SecurityServices
from cloud_ui.security.identity import Subject
from cloud_ui.security.rbac import AuthorizationDenied
from cloud_ui.security.routes import SESSION_COOKIE_NAME
from cloud_ui.security.sessions import SessionExpired, SessionNotFound, SessionRecord


class MasakariApprovalGatePayload(BaseModel):
    model_config = ConfigDict(frozen=True)

    required: bool
    status: str


class MasakariConsulMatrixPayload(BaseModel):
    model_config = ConfigDict(frozen=True)

    enabled: bool
    status: str
    coverage: list[str]


class MasakariProcessMonitorPayload(BaseModel):
    model_config = ConfigDict(frozen=True)

    status: str
    reason: str


class MasakariSegmentPayload(BaseModel):
    model_config = ConfigDict(frozen=True)

    segment_id: str
    name: str
    recovery_method: str
    approval_gate: MasakariApprovalGatePayload
    consul_matrix: MasakariConsulMatrixPayload
    processmonitor: MasakariProcessMonitorPayload


class MasakariSegmentListResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    items: list[MasakariSegmentPayload]


class MasakariSegmentHostPayload(BaseModel):
    model_config = ConfigDict(frozen=True)

    host: str
    control_attributes: str
    reserved: bool
    on_maintenance: bool
    recovery_method: str


class MasakariSegmentHostListResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    items: list[MasakariSegmentHostPayload]


class MasakariConflictStatePayload(BaseModel):
    model_config = ConfigDict(frozen=True)

    nova_masakari_conflict: bool
    safe_message: str


class MasakariNotificationPayload(BaseModel):
    model_config = ConfigDict(frozen=True)

    notification_id: str
    segment_id: str
    host: str
    type: str
    status: str
    direct_recovery_enabled: bool
    conflict_state: MasakariConflictStatePayload


class MasakariNotificationListResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    items: list[MasakariNotificationPayload]


class MasakariTimelineEventPayload(BaseModel):
    model_config = ConfigDict(frozen=True)

    event_id: str
    event_type: str
    source: str
    safe_message: str


class MasakariTimelineResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    items: list[MasakariTimelineEventPayload]


def build_masakari_router(security: SecurityServices) -> APIRouter:
    router = APIRouter()

    @router.get("/masakari/segments", response_model=MasakariSegmentListResponse)
    def segments(request: Request) -> MasakariSegmentListResponse | JSONResponse:
        session = _require_operation_read(security, request, target_type="masakari_segment")
        if isinstance(session, JSONResponse):
            return session
        return MasakariSegmentListResponse(items=[_segment_payload()])

    @router.get("/masakari/segments/{segment_id}", response_model=MasakariSegmentPayload)
    def segment_detail(segment_id: str, request: Request) -> MasakariSegmentPayload | JSONResponse:
        session = _require_operation_read(security, request, target_type="masakari_segment")
        if isinstance(session, JSONResponse):
            return session
        if segment_id != "segment-precheck":
            return _error(404, "segment_not_found", "Сегмент не найден", _request_id(request))
        return _segment_payload()

    @router.get(
        "/masakari/segments/{segment_id}/hosts",
        response_model=MasakariSegmentHostListResponse,
    )
    def segment_hosts(
        segment_id: str,
        request: Request,
    ) -> MasakariSegmentHostListResponse | JSONResponse:
        session = _require_operation_read(security, request, target_type="masakari_segment_host")
        if isinstance(session, JSONResponse):
            return session
        if segment_id != "segment-precheck":
            return _error(404, "segment_not_found", "Сегмент не найден", _request_id(request))
        return MasakariSegmentHostListResponse(
            items=[
                MasakariSegmentHostPayload(
                    host="compute-a",
                    control_attributes="COMPUTE_HOST",
                    reserved=False,
                    on_maintenance=False,
                    recovery_method="auto",
                )
            ]
        )

    @router.get("/masakari/notifications", response_model=MasakariNotificationListResponse)
    def notifications(request: Request) -> MasakariNotificationListResponse | JSONResponse:
        session = _require_operation_read(security, request, target_type="masakari_notification")
        if isinstance(session, JSONResponse):
            return session
        return MasakariNotificationListResponse(items=[_notification_payload()])

    @router.get(
        "/masakari/notifications/{notification_id}",
        response_model=MasakariNotificationPayload,
    )
    def notification_detail(
        notification_id: str,
        request: Request,
    ) -> MasakariNotificationPayload | JSONResponse:
        session = _require_operation_read(security, request, target_type="masakari_notification")
        if isinstance(session, JSONResponse):
            return session
        if notification_id != "notification-precheck":
            return _error(
                404,
                "notification_not_found",
                "Уведомление не найдено",
                _request_id(request),
            )
        return _notification_payload()

    @router.get("/masakari/recovery-timeline", response_model=MasakariTimelineResponse)
    def recovery_timeline(request: Request) -> MasakariTimelineResponse | JSONResponse:
        session = _require_operation_read(security, request, target_type="masakari_timeline")
        if isinstance(session, JSONResponse):
            return session
        return MasakariTimelineResponse(
            items=[
                MasakariTimelineEventPayload(
                    event_id="timeline-precheck",
                    event_type="diagnostic",
                    source="portal-p0-mock",
                    safe_message="Recovery execution is disabled until operation approval.",
                )
            ]
        )

    return router


def _segment_payload() -> MasakariSegmentPayload:
    return MasakariSegmentPayload(
        segment_id="segment-precheck",
        name="precheck-segment",
        recovery_method="auto",
        approval_gate=MasakariApprovalGatePayload(required=True, status="not_requested"),
        consul_matrix=MasakariConsulMatrixPayload(
            enabled=True,
            status="partial",
            coverage=["hostmonitor"],
        ),
        processmonitor=MasakariProcessMonitorPayload(
            status="unsupported",
            reason="kolla_container_context_requires_lab_evidence",
        ),
    )


def _notification_payload() -> MasakariNotificationPayload:
    return MasakariNotificationPayload(
        notification_id="notification-precheck",
        segment_id="segment-precheck",
        host="compute-a",
        type="COMPUTE_HOST",
        status="diagnostic",
        direct_recovery_enabled=False,
        conflict_state=MasakariConflictStatePayload(
            nova_masakari_conflict=True,
            safe_message="Nova service state and Masakari notification need approval review.",
        ),
    )


def _require_operation_read(
    services: SecurityServices,
    request: Request,
    *,
    target_type: str,
) -> SessionRecord | JSONResponse:
    session = _require_session(services, request)
    if isinstance(session, JSONResponse):
        return session
    try:
        services.policy_service.require_capability(session.subject, "operation.read")
    except AuthorizationDenied as exc:
        _record_audit(
            services,
            request,
            action="authorization.denied",
            event_type="authorization",
            outcome="failure",
            target_type=target_type,
            target_id=None,
            subject=session.subject,
            session_reference=session.session_id,
            metadata={"code": exc.code, "capability": "operation.read"},
        )
        return _error(403, exc.code, "Действие запрещено", _request_id(request))
    return session


def _require_session(services: SecurityServices, request: Request) -> SessionRecord | JSONResponse:
    request_id = _request_id(request)
    session_id = request.cookies.get(SESSION_COOKIE_NAME)
    try:
        return services.session_manager.get_session(session_id)
    except SessionExpired:
        return _error(401, "session_expired", "Сессия истекла", request_id)
    except SessionNotFound:
        return _error(401, "not_authenticated", "Требуется вход", request_id)


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
