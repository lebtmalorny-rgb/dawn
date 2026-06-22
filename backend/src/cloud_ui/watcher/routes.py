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


class WatcherGoalPayload(BaseModel):
    model_config = ConfigDict(frozen=True)

    goal: str
    status: str


class WatcherGoalListResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    items: list[WatcherGoalPayload]


class WatcherStrategyPayload(BaseModel):
    model_config = ConfigDict(frozen=True)

    strategy: str
    allowed: bool


class WatcherStrategyListResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    items: list[WatcherStrategyPayload]


class WatcherAuditTemplatePayload(BaseModel):
    model_config = ConfigDict(frozen=True)

    template_id: str
    workflow_key: str
    dry_run_only: bool


class WatcherAuditTemplateListResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    items: list[WatcherAuditTemplatePayload]


class WatcherAuditPayload(BaseModel):
    model_config = ConfigDict(frozen=True)

    audit_id: str
    state: str


class WatcherAuditListResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    items: list[WatcherAuditPayload]


class WatcherActionPlanPayload(BaseModel):
    model_config = ConfigDict(frozen=True)

    action_plan_id: str
    state: str
    direct_apply_enabled: bool
    operation_path: str


class WatcherActionPlanListResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    items: list[WatcherActionPlanPayload]


class WatcherActionPayload(BaseModel):
    model_config = ConfigDict(frozen=True)

    action_id: str
    state: str


class WatcherActionListResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    items: list[WatcherActionPayload]


class WatcherTelemetryFreshnessPayload(BaseModel):
    model_config = ConfigDict(frozen=True)

    status: str
    age_seconds: int


class WatcherAutomaticApplyPayload(BaseModel):
    model_config = ConfigDict(frozen=True)

    enabled: bool
    reason: str


class WatcherRecommendationPayload(BaseModel):
    model_config = ConfigDict(frozen=True)

    recommendation_id: str
    action_plan_id: str
    telemetry_freshness: WatcherTelemetryFreshnessPayload
    automatic_apply: WatcherAutomaticApplyPayload
    risk_markers: list[str]


class WatcherRecommendationListResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    items: list[WatcherRecommendationPayload]


def build_watcher_router(security: SecurityServices) -> APIRouter:
    router = APIRouter()

    @router.get("/watcher/goals", response_model=WatcherGoalListResponse)
    def goals(request: Request) -> WatcherGoalListResponse | JSONResponse:
        session = _require_operation_read(security, request, target_type="watcher_goal")
        if isinstance(session, JSONResponse):
            return session
        return WatcherGoalListResponse(
            items=[WatcherGoalPayload(goal="server_consolidation", status="visible")]
        )

    @router.get("/watcher/strategies", response_model=WatcherStrategyListResponse)
    def strategies(request: Request) -> WatcherStrategyListResponse | JSONResponse:
        session = _require_operation_read(security, request, target_type="watcher_strategy")
        if isinstance(session, JSONResponse):
            return session
        return WatcherStrategyListResponse(
            items=[WatcherStrategyPayload(strategy="workload_stabilization", allowed=False)]
        )

    @router.get("/watcher/audit-templates", response_model=WatcherAuditTemplateListResponse)
    def audit_templates(request: Request) -> WatcherAuditTemplateListResponse | JSONResponse:
        session = _require_operation_read(security, request, target_type="watcher_template")
        if isinstance(session, JSONResponse):
            return session
        return WatcherAuditTemplateListResponse(
            items=[
                WatcherAuditTemplatePayload(
                    template_id="maintenance-host-precheck-template",
                    workflow_key="maintenance-host-precheck",
                    dry_run_only=True,
                )
            ]
        )

    @router.get("/watcher/audits", response_model=WatcherAuditListResponse)
    def audits(request: Request) -> WatcherAuditListResponse | JSONResponse:
        session = _require_operation_read(security, request, target_type="watcher_audit")
        if isinstance(session, JSONResponse):
            return session
        return WatcherAuditListResponse(
            items=[WatcherAuditPayload(audit_id="watcher-audit-precheck", state="SUCCEEDED")]
        )

    @router.get("/watcher/continuous-audits", response_model=WatcherAuditListResponse)
    def continuous_audits(request: Request) -> WatcherAuditListResponse | JSONResponse:
        session = _require_operation_read(
            security,
            request,
            target_type="watcher_continuous_audit",
        )
        if isinstance(session, JSONResponse):
            return session
        return WatcherAuditListResponse(
            items=[WatcherAuditPayload(audit_id="continuous-precheck", state="DISABLED")]
        )

    @router.get("/watcher/action-plans", response_model=WatcherActionPlanListResponse)
    def action_plans(request: Request) -> WatcherActionPlanListResponse | JSONResponse:
        session = _require_operation_read(security, request, target_type="watcher_action_plan")
        if isinstance(session, JSONResponse):
            return session
        return WatcherActionPlanListResponse(
            items=[
                WatcherActionPlanPayload(
                    action_plan_id="watcher-action-plan-precheck",
                    state="RECOMMENDED",
                    direct_apply_enabled=False,
                    operation_path="/api/v1/operations",
                )
            ]
        )

    @router.get("/watcher/actions", response_model=WatcherActionListResponse)
    def actions(request: Request) -> WatcherActionListResponse | JSONResponse:
        session = _require_operation_read(security, request, target_type="watcher_action")
        if isinstance(session, JSONResponse):
            return session
        return WatcherActionListResponse(
            items=[WatcherActionPayload(action_id="watcher-action-dry-run", state="PENDING")]
        )

    @router.get("/watcher/recommendations", response_model=WatcherRecommendationListResponse)
    def recommendations(request: Request) -> WatcherRecommendationListResponse | JSONResponse:
        session = _require_operation_read(security, request, target_type="watcher_recommendation")
        if isinstance(session, JSONResponse):
            return session
        return WatcherRecommendationListResponse(
            items=[
                WatcherRecommendationPayload(
                    recommendation_id="watcher-recommendation-precheck",
                    action_plan_id="watcher-action-plan-precheck",
                    telemetry_freshness=WatcherTelemetryFreshnessPayload(
                        status="partial",
                        age_seconds=300,
                    ),
                    automatic_apply=WatcherAutomaticApplyPayload(
                        enabled=False,
                        reason="disabled_by_default",
                    ),
                    risk_markers=["dry_run_only", "requires_operation_catalog"],
                )
            ]
        )

    return router


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
