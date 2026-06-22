from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, Request, Response
from pydantic import BaseModel
from starlette.responses import JSONResponse

from cloud_ui.security.audit import AuditEvent, AuditOutcome
from cloud_ui.security.dependencies import SecurityServices
from cloud_ui.security.identity import AuthenticationFailed, LoginRequest, Subject
from cloud_ui.security.rbac import (
    AuthorizationDenied,
    OpenStackForbidden,
    RoleBindingRequest,
    SubjectType,
)
from cloud_ui.security.sessions import (
    SessionExpired,
    SessionLimitReached,
    SessionNotFound,
    SessionRecord,
)

SESSION_COOKIE_NAME = "cloud_ui_session"
CSRF_HEADER_NAME = "x-csrf-token"


class LoginPayload(BaseModel):
    login: str
    credential: str


class SubjectPayload(BaseModel):
    subject_id: str
    display_name: str
    subject_type: str
    roles: list[str]


class LoginResponse(BaseModel):
    subject: SubjectPayload
    csrf: str
    expires_at: datetime


class CurrentSessionResponse(BaseModel):
    subject: SubjectPayload


class CapabilitiesResponse(BaseModel):
    scope: dict[str, str | None]
    capabilities: list[str]
    expires_at: datetime
    policy_revision: str


class ActiveSessionPayload(BaseModel):
    session_id: str
    subject_id: str
    display_name: str
    created_at: datetime
    last_seen_at: datetime
    idle_expires_at: datetime
    absolute_expires_at: datetime


class ActiveSessionsResponse(BaseModel):
    sessions: list[ActiveSessionPayload]


class RoleBindingPayload(BaseModel):
    subject_id: str
    subject_type: SubjectType
    role: str


class SimulatedOpenStackPayload(BaseModel):
    openstack_allowed: bool


def build_security_router(services: SecurityServices) -> APIRouter:
    router = APIRouter()

    @router.post("/session/login", response_model=LoginResponse)
    def login(
        payload: LoginPayload, request: Request, response: Response
    ) -> LoginResponse | JSONResponse:
        request_id = _request_id(request)
        try:
            result = services.identity_provider.authenticate(
                LoginRequest(login=payload.login, credential=payload.credential)
            )
        except AuthenticationFailed:
            _record_audit(
                services,
                request,
                action="session.login",
                event_type="auth",
                outcome="failure",
                target_type="session",
                target_id=None,
                subject=None,
                metadata={"reason": "authentication_failed"},
            )
            return _error(401, "authentication_failed", "Не удалось выполнить вход", request_id)

        try:
            session = services.session_manager.create_session(result.subject)
        except SessionLimitReached:
            _record_audit(
                services,
                request,
                action="session.limit_reached",
                event_type="session",
                outcome="failure",
                target_type="subject",
                target_id=result.subject.subject_id,
                subject=result.subject,
                metadata={},
            )
            return _error(409, "session_limit_reached", "Превышен лимит сессий", request_id)

        response.set_cookie(
            SESSION_COOKIE_NAME,
            session.session_id,
            httponly=True,
            secure=services.session_cookie_secure,
            samesite=services.session_cookie_samesite,
            max_age=int((session.absolute_expires_at - session.created_at).total_seconds()),
        )
        _record_audit(
            services,
            request,
            action="session.login",
            event_type="auth",
            outcome="success",
            target_type="session",
            target_id=session.session_id,
            subject=result.subject,
            session_reference=session.session_id,
            metadata={},
        )
        return LoginResponse(
            subject=_subject_payload(result.subject),
            csrf=session.csrf,
            expires_at=session.absolute_expires_at,
        )

    @router.get("/session", response_model=CurrentSessionResponse)
    def current_session(request: Request) -> CurrentSessionResponse | JSONResponse:
        session = _require_session(services, request)
        if isinstance(session, JSONResponse):
            return session
        return CurrentSessionResponse(subject=_subject_payload(session.subject))

    @router.get("/capabilities", response_model=CapabilitiesResponse)
    def capabilities(request: Request) -> CapabilitiesResponse | JSONResponse:
        session = _require_session(services, request)
        if isinstance(session, JSONResponse):
            return session
        return CapabilitiesResponse(
            scope={"type": session.subject.scope_type, "id": session.subject.scope_id},
            capabilities=sorted(session.subject.capabilities),
            expires_at=session.absolute_expires_at,
            policy_revision=services.policy_service.policy_revision,
        )

    @router.post("/session/logout", status_code=204, response_model=None)
    def logout(request: Request, response: Response) -> Response | JSONResponse:
        session = _require_session(services, request)
        if isinstance(session, JSONResponse):
            return session
        origin_error = _require_trusted_origin(services, request, session)
        if origin_error is not None:
            return origin_error
        csrf_error = _require_csrf(services, request, session)
        if csrf_error is not None:
            return csrf_error

        services.session_manager.revoke(session)
        response.delete_cookie(SESSION_COOKIE_NAME)
        _record_audit(
            services,
            request,
            action="session.logout",
            event_type="session",
            outcome="success",
            target_type="session",
            target_id=session.session_id,
            subject=session.subject,
            session_reference=session.session_id,
            metadata={},
        )
        response.status_code = 204
        return response

    @router.get("/session/active", response_model=ActiveSessionsResponse)
    def active_sessions(request: Request) -> ActiveSessionsResponse | JSONResponse:
        session = _require_session(services, request)
        if isinstance(session, JSONResponse):
            return session
        try:
            services.policy_service.require_capability(session.subject, "session.manage")
        except AuthorizationDenied as exc:
            _record_audit(
                services,
                request,
                action="authorization.denied",
                event_type="authorization",
                outcome="failure",
                target_type="session",
                target_id=None,
                subject=session.subject,
                session_reference=session.session_id,
                metadata={"code": exc.code},
            )
            return _error(403, exc.code, "Действие запрещено", _request_id(request))

        return ActiveSessionsResponse(
            sessions=[
                _active_session_payload(active_session)
                for active_session in services.session_manager.list_active_sessions()
            ]
        )

    @router.delete("/session/active/{session_id}", status_code=204, response_model=None)
    def revoke_session(
        session_id: str, request: Request, response: Response
    ) -> Response | JSONResponse:
        actor_session = _require_session(services, request)
        if isinstance(actor_session, JSONResponse):
            return actor_session
        origin_error = _require_trusted_origin(services, request, actor_session)
        if origin_error is not None:
            return origin_error
        csrf_error = _require_csrf(services, request, actor_session)
        if csrf_error is not None:
            return csrf_error

        try:
            services.policy_service.require_capability(actor_session.subject, "session.manage")
        except AuthorizationDenied as exc:
            _record_audit(
                services,
                request,
                action="authorization.denied",
                event_type="authorization",
                outcome="failure",
                target_type="session",
                target_id=session_id,
                subject=actor_session.subject,
                session_reference=actor_session.session_id,
                metadata={"code": exc.code},
            )
            return _error(403, exc.code, "Действие запрещено", _request_id(request))

        try:
            target_session = services.session_manager.revoke_session_id(session_id)
        except SessionNotFound:
            return _error(404, "session_not_found", "Сессия не найдена", _request_id(request))

        _record_audit(
            services,
            request,
            action="session.revoke",
            event_type="session",
            outcome="success",
            target_type="session",
            target_id=target_session.session_id,
            subject=actor_session.subject,
            session_reference=actor_session.session_id,
            metadata={"target_subject_id": target_session.subject.subject_id},
        )
        response.status_code = 204
        return response

    @router.post("/admin/role-bindings", response_model=None)
    def create_role_binding(
        payload: RoleBindingPayload, request: Request
    ) -> dict[str, str] | JSONResponse:
        session = _require_session(services, request)
        if isinstance(session, JSONResponse):
            return session
        origin_error = _require_trusted_origin(services, request, session)
        if origin_error is not None:
            return origin_error
        csrf_error = _require_csrf(services, request, session)
        if csrf_error is not None:
            return csrf_error

        try:
            services.policy_service.validate_role_binding(
                session.subject,
                RoleBindingRequest(
                    subject_id=payload.subject_id,
                    subject_type=payload.subject_type,
                    role=payload.role,
                ),
            )
        except AuthorizationDenied as exc:
            _record_audit(
                services,
                request,
                action="authorization.denied",
                event_type="authorization",
                outcome="failure",
                target_type="role_binding",
                target_id=payload.subject_id,
                subject=session.subject,
                session_reference=session.session_id,
                metadata={"code": exc.code},
            )
            return _error(403, exc.code, "Действие запрещено", _request_id(request))

        return {"status": "accepted"}

    @router.post("/operations/simulated-openstack-action", response_model=None)
    def simulated_openstack_action(
        payload: SimulatedOpenStackPayload, request: Request
    ) -> dict[str, str] | JSONResponse:
        session = _require_session(services, request)
        if isinstance(session, JSONResponse):
            return session
        origin_error = _require_trusted_origin(services, request, session)
        if origin_error is not None:
            return origin_error
        csrf_error = _require_csrf(services, request, session)
        if csrf_error is not None:
            return csrf_error

        try:
            services.policy_service.require_capability(
                session.subject, "workflow.execute.maintenance-host"
            )
            services.policy_service.ensure_openstack_allowed(
                openstack_allowed=payload.openstack_allowed
            )
        except AuthorizationDenied as exc:
            _record_audit(
                services,
                request,
                action="authorization.denied",
                event_type="authorization",
                outcome="failure",
                target_type="operation",
                target_id="simulated-openstack-action",
                subject=session.subject,
                session_reference=session.session_id,
                metadata={"code": exc.code},
            )
            return _error(403, exc.code, "Действие запрещено", _request_id(request))
        except OpenStackForbidden:
            _record_audit(
                services,
                request,
                action="openstack.denied",
                event_type="authorization",
                outcome="failure",
                target_type="operation",
                target_id="simulated-openstack-action",
                subject=session.subject,
                session_reference=session.session_id,
                metadata={},
            )
            return _error(
                403,
                "openstack_forbidden",
                "OpenStack отклонил операцию",
                _request_id(request),
            )

        return {"status": "accepted"}

    return router


def _subject_payload(subject: Subject) -> SubjectPayload:
    return SubjectPayload(
        subject_id=subject.subject_id,
        display_name=subject.display_name,
        subject_type=subject.subject_type,
        roles=sorted(subject.roles),
    )


def _active_session_payload(session: SessionRecord) -> ActiveSessionPayload:
    return ActiveSessionPayload(
        session_id=session.session_id,
        subject_id=session.subject.subject_id,
        display_name=session.subject.display_name,
        created_at=session.created_at,
        last_seen_at=session.last_seen_at,
        idle_expires_at=session.idle_expires_at,
        absolute_expires_at=session.absolute_expires_at,
    )


def _require_session(services: SecurityServices, request: Request) -> Any:
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


def _require_trusted_origin(
    services: SecurityServices, request: Request, session: SessionRecord
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
    services: SecurityServices, request: Request, session: Any
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
            metadata=metadata,
        )
    )


def _request_id(request: Request) -> str:
    return str(
        getattr(request.state, "request_id", None) or request.headers.get("x-request-id") or ""
    )
