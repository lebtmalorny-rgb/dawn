from __future__ import annotations

import hashlib
import hmac
import json
from dataclasses import dataclass
from typing import Any, Literal, cast
from uuid import uuid4

from fastapi import APIRouter, Query, Request
from pydantic import BaseModel, ConfigDict
from sqlalchemy.engine import Engine
from starlette.responses import JSONResponse

from cloud_ui.config import DEV_INVENTORY_CURSOR_SIGNING_KEY, Settings
from cloud_ui.db import create_db_engine
from cloud_ui.groups.models import ResourceGroup
from cloud_ui.groups.repository import GroupRepository
from cloud_ui.groups.routes import GroupServices
from cloud_ui.inventory.cursor import CursorCodec, CursorTampered
from cloud_ui.inventory.models import (
    HypervisorFilters,
    HypervisorItem,
    InstanceFilters,
    InstanceItem,
    InventoryFreshness,
    InventorySort,
    InventoryWarning,
)
from cloud_ui.inventory.repository import InventoryRepository
from cloud_ui.security.audit import AuditEvent, AuditOutcome
from cloud_ui.security.dependencies import SecurityServices
from cloud_ui.security.identity import Subject
from cloud_ui.security.rbac import AuthorizationDenied
from cloud_ui.security.routes import CSRF_HEADER_NAME, SESSION_COOKIE_NAME
from cloud_ui.security.sessions import SessionExpired, SessionNotFound, SessionRecord

DEFAULT_CLOUD_ID = "synthetic"
DEFAULT_REGION_ID = "RegionOne"
DEFAULT_LIST_LIMIT = 50
MAX_LIST_LIMIT = 200
DEFAULT_INSTANCE_SORT = "name.asc"
DEFAULT_HYPERVISOR_SORT = "host_name.asc"
IDEMPOTENCY_KEY_HEADER_NAME = "idempotency-key"

INSTANCE_FILTER_PARAMS = frozenset(
    {
        "q",
        "project_id",
        "status",
        "host_name",
        "hypervisor_id",
        "availability_zone",
        "group_id",
    }
)
HYPERVISOR_FILTER_PARAMS = frozenset(
    {
        "q",
        "service_status",
        "service_state",
        "host_name",
        "availability_zone",
        "maintenance_status",
        "group_id",
    }
)
COMMON_LIST_PARAMS = frozenset({"cloud_id", "region_id", "limit", "cursor", "sort"})
INSTANCE_SORT_FIELDS = frozenset(
    {
        "instance_id",
        "name",
        "project_id",
        "status",
        "host_name",
        "availability_zone",
        "source_updated_at",
        "observed_at",
    }
)
HYPERVISOR_SORT_FIELDS = frozenset(
    {
        "hypervisor_id",
        "host_name",
        "service_status",
        "service_state",
        "availability_zone",
        "observed_at",
    }
)

SortDirection = Literal["asc", "desc"]


@dataclass(frozen=True)
class InventoryServices:
    repository: InventoryRepository | None
    engine: Engine | None = None
    default_limit: int = DEFAULT_LIST_LIMIT
    max_limit: int = MAX_LIST_LIMIT
    operation_signing_key: str = DEV_INVENTORY_CURSOR_SIGNING_KEY

    @property
    def available(self) -> bool:
        return self.repository is not None


class InstanceListResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    items: list[InstanceItem]
    next_cursor: str | None
    limit: int
    sort: str
    partial: bool
    warnings: list[InventoryWarning]
    freshness: InventoryFreshness | None


class HypervisorListResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    items: list[HypervisorItem]
    next_cursor: str | None
    limit: int
    sort: str
    partial: bool
    warnings: list[InventoryWarning]
    freshness: InventoryFreshness | None


class InstanceRefreshTarget(BaseModel):
    model_config = ConfigDict(frozen=True)

    cloud_id: str
    region_id: str
    instance_id: str


class InstanceRefreshResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    status: Literal["accepted"]
    operation_id: str
    target: InstanceRefreshTarget


class InventoryModuleDescriptor(BaseModel):
    model_config = ConfigDict(frozen=True)

    key: str
    title: str
    path: str | None
    enabled: bool
    required_capability: str | None
    status: Literal["enabled", "disabled"]
    reason: str | None


class InventoryModulesResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    modules: list[InventoryModuleDescriptor]


def build_inventory_services(settings: Settings) -> InventoryServices:
    engine = create_db_engine(str(settings.database_url))
    repository = InventoryRepository(
        engine=engine,
        cursor_codec=CursorCodec(signing_key=settings.inventory_cursor_signing_key),
        default_limit=settings.inventory_default_limit,
        max_limit=settings.inventory_max_limit,
        stale_after_seconds=settings.inventory_stale_after_seconds,
    )
    return InventoryServices(
        repository=repository,
        engine=engine,
        default_limit=settings.inventory_default_limit,
        max_limit=settings.inventory_max_limit,
        operation_signing_key=settings.inventory_cursor_signing_key,
    )


def unavailable_inventory_services() -> InventoryServices:
    return InventoryServices(repository=None)


def build_inventory_router(services: InventoryServices, security: SecurityServices) -> APIRouter:
    return build_inventory_router_with_groups(services, security, None)


def build_inventory_router_with_groups(
    services: InventoryServices,
    security: SecurityServices,
    groups: GroupServices | None,
) -> APIRouter:
    router = APIRouter()

    @router.get("/instances", response_model=InstanceListResponse)
    def list_instances(
        request: Request,
        cloud_id: str = DEFAULT_CLOUD_ID,
        region_id: str = DEFAULT_REGION_ID,
        limit: int = Query(default=DEFAULT_LIST_LIMIT, ge=1),
        cursor: str | None = Query(default=None),
        sort: str = DEFAULT_INSTANCE_SORT,
        q: str | None = Query(default=None),
        project_id: str | None = Query(default=None),
        status: str | None = Query(default=None),
        host_name: str | None = Query(default=None),
        hypervisor_id: str | None = Query(default=None),
        availability_zone: str | None = Query(default=None),
        group_id: str | None = Query(default=None),
    ) -> InstanceListResponse | JSONResponse:
        session = _require_session(security, request)
        if isinstance(session, JSONResponse):
            return session
        denied = _require_capability(
            security,
            request,
            session,
            "instance.read",
            target_type="instances",
            target_id=None,
        )
        if denied is not None:
            return denied
        repository = _require_repository(services, request)
        if isinstance(repository, JSONResponse):
            return repository
        group_error = _require_group_filter_access(
            groups=groups,
            security=security,
            request=request,
            session=session,
            group_id=group_id,
            expected_resource_type="vm",
        )
        if group_error is not None:
            return group_error

        query_error = _reject_unsupported_query(
            request,
            allowed=COMMON_LIST_PARAMS | INSTANCE_FILTER_PARAMS,
        )
        if query_error is not None:
            return query_error
        effective_limit = _effective_limit(_query_limit(limit, request), services)
        parsed_sort = _parse_sort(sort, allowed_fields=INSTANCE_SORT_FIELDS, request=request)
        if isinstance(parsed_sort, JSONResponse):
            return parsed_sort

        try:
            page = repository.list_instances(
                filters=InstanceFilters(
                    cloud_id=cloud_id,
                    region_id=region_id,
                    q=q,
                    project_id=project_id,
                    status=status,
                    host_name=host_name,
                    hypervisor_id=hypervisor_id,
                    availability_zone=availability_zone,
                    group_id=group_id,
                ),
                sort=parsed_sort,
                limit=effective_limit,
                cursor=cursor,
            )
        except CursorTampered:
            return _error(400, "cursor_tampered", "Некорректный cursor", _request_id(request))
        except Exception:
            return _inventory_unavailable(request)

        return InstanceListResponse(
            items=page.items,
            next_cursor=page.next_cursor,
            limit=effective_limit,
            sort=_sort_key(parsed_sort),
            partial=page.partial,
            warnings=page.warnings,
            freshness=page.freshness,
        )

    @router.get(
        "/instances/{cloud_id}/{region_id}/{instance_id}",
        response_model=InstanceItem,
    )
    def instance_detail(
        cloud_id: str,
        region_id: str,
        instance_id: str,
        request: Request,
    ) -> InstanceItem | JSONResponse:
        session = _require_session(security, request)
        if isinstance(session, JSONResponse):
            return session
        denied = _require_capability(
            security,
            request,
            session,
            "instance.read",
            target_type="instance",
            target_id=_instance_target_id(cloud_id, region_id, instance_id),
        )
        if denied is not None:
            return denied
        repository = _require_repository(services, request)
        if isinstance(repository, JSONResponse):
            return repository

        try:
            item = repository.get_instance(cloud_id, region_id, instance_id)
        except Exception:
            return _inventory_unavailable(request)
        if item is None:
            return _error(404, "instance_not_found", "Инстанс не найден", _request_id(request))
        return item

    @router.post(
        "/instances/{cloud_id}/{region_id}/{instance_id}/refresh",
        response_model=InstanceRefreshResponse,
    )
    def refresh_instance(
        cloud_id: str,
        region_id: str,
        instance_id: str,
        request: Request,
    ) -> InstanceRefreshResponse | JSONResponse:
        session = _require_session(security, request)
        if isinstance(session, JSONResponse):
            return session
        origin_error = _require_trusted_origin(security, request, session)
        if origin_error is not None:
            return origin_error
        csrf_error = _require_csrf(security, request, session)
        if csrf_error is not None:
            return csrf_error
        denied = _require_capability(
            security,
            request,
            session,
            "instance.refresh",
            target_type="instance",
            target_id=_instance_target_id(cloud_id, region_id, instance_id),
        )
        if denied is not None:
            return denied
        idempotency_key = _require_idempotency_key(request)
        if isinstance(idempotency_key, JSONResponse):
            return idempotency_key
        unavailable = _require_inventory_available(services, request)
        if unavailable is not None:
            return unavailable

        target_id = _instance_target_id(cloud_id, region_id, instance_id)
        operation_id = _refresh_operation_id(
            cloud_id=cloud_id,
            region_id=region_id,
            instance_id=instance_id,
            idempotency_key=idempotency_key,
            actor_subject_id=session.subject.subject_id,
            operation_signing_key=services.operation_signing_key,
        )
        _record_audit(
            security,
            request,
            action="instance.refresh.requested",
            event_type="inventory",
            outcome="success",
            target_type="instance",
            target_id=target_id,
            subject=session.subject,
            session_reference=session.session_id,
            metadata={"operation_id": operation_id},
        )
        return InstanceRefreshResponse(
            status="accepted",
            operation_id=operation_id,
            target=InstanceRefreshTarget(
                cloud_id=cloud_id,
                region_id=region_id,
                instance_id=instance_id,
            ),
        )

    @router.get("/hypervisors", response_model=HypervisorListResponse)
    def list_hypervisors(
        request: Request,
        cloud_id: str = DEFAULT_CLOUD_ID,
        region_id: str = DEFAULT_REGION_ID,
        limit: int = Query(default=DEFAULT_LIST_LIMIT, ge=1),
        cursor: str | None = Query(default=None),
        sort: str = DEFAULT_HYPERVISOR_SORT,
        q: str | None = Query(default=None),
        service_status: str | None = Query(default=None),
        service_state: str | None = Query(default=None),
        host_name: str | None = Query(default=None),
        availability_zone: str | None = Query(default=None),
        maintenance_status: str | None = Query(default=None),
        group_id: str | None = Query(default=None),
    ) -> HypervisorListResponse | JSONResponse:
        session = _require_session(security, request)
        if isinstance(session, JSONResponse):
            return session
        denied = _require_capability(
            security,
            request,
            session,
            "hypervisor.read",
            target_type="hypervisors",
            target_id=None,
        )
        if denied is not None:
            return denied
        repository = _require_repository(services, request)
        if isinstance(repository, JSONResponse):
            return repository
        group_error = _require_group_filter_access(
            groups=groups,
            security=security,
            request=request,
            session=session,
            group_id=group_id,
            expected_resource_type="host",
        )
        if group_error is not None:
            return group_error

        query_error = _reject_unsupported_query(
            request,
            allowed=COMMON_LIST_PARAMS | HYPERVISOR_FILTER_PARAMS,
        )
        if query_error is not None:
            return query_error
        effective_limit = _effective_limit(_query_limit(limit, request), services)
        parsed_sort = _parse_sort(sort, allowed_fields=HYPERVISOR_SORT_FIELDS, request=request)
        if isinstance(parsed_sort, JSONResponse):
            return parsed_sort

        try:
            page = repository.list_hypervisors(
                filters=HypervisorFilters(
                    cloud_id=cloud_id,
                    region_id=region_id,
                    q=q,
                    service_status=service_status,
                    service_state=service_state,
                    host_name=host_name,
                    availability_zone=availability_zone,
                    maintenance_status=maintenance_status,
                    group_id=group_id,
                ),
                sort=parsed_sort,
                limit=effective_limit,
                cursor=cursor,
            )
        except CursorTampered:
            return _error(400, "cursor_tampered", "Некорректный cursor", _request_id(request))
        except Exception:
            return _inventory_unavailable(request)

        return HypervisorListResponse(
            items=page.items,
            next_cursor=page.next_cursor,
            limit=effective_limit,
            sort=_sort_key(parsed_sort),
            partial=page.partial,
            warnings=page.warnings,
            freshness=page.freshness,
        )

    @router.get(
        "/hypervisors/{cloud_id}/{region_id}/{hypervisor_id}",
        response_model=HypervisorItem,
    )
    def hypervisor_detail(
        cloud_id: str,
        region_id: str,
        hypervisor_id: str,
        request: Request,
    ) -> HypervisorItem | JSONResponse:
        session = _require_session(security, request)
        if isinstance(session, JSONResponse):
            return session
        denied = _require_capability(
            security,
            request,
            session,
            "hypervisor.read",
            target_type="hypervisor",
            target_id=_hypervisor_target_id(cloud_id, region_id, hypervisor_id),
        )
        if denied is not None:
            return denied
        repository = _require_repository(services, request)
        if isinstance(repository, JSONResponse):
            return repository

        try:
            item = repository.get_hypervisor(cloud_id, region_id, hypervisor_id)
        except Exception:
            return _inventory_unavailable(request)
        if item is None:
            return _error(
                404,
                "hypervisor_not_found",
                "Гипервизор не найден",
                _request_id(request),
            )
        return item

    @router.get("/inventory/modules", response_model=InventoryModulesResponse)
    def inventory_modules(request: Request) -> InventoryModulesResponse | JSONResponse:
        session = _require_session(security, request)
        if isinstance(session, JSONResponse):
            return session
        unavailable = _require_inventory_available(services, request)
        if unavailable is not None:
            return unavailable
        return InventoryModulesResponse(modules=_module_descriptors(session.subject))

    return router


def _require_repository(
    services: InventoryServices, request: Request
) -> InventoryRepository | JSONResponse:
    if services.repository is not None:
        return services.repository
    return _inventory_unavailable(request)


def _require_inventory_available(
    services: InventoryServices, request: Request
) -> JSONResponse | None:
    if services.available:
        return None
    return _inventory_unavailable(request)


def _require_group_filter_access(
    *,
    groups: GroupServices | None,
    security: SecurityServices,
    request: Request,
    session: SessionRecord,
    group_id: str | None,
    expected_resource_type: str,
) -> JSONResponse | None:
    if group_id is None:
        return None
    repository = _require_group_repository(groups, request)
    if isinstance(repository, JSONResponse):
        return repository
    group = repository.get_group(group_id)
    if group is None:
        return _error(404, "group_not_found", "Группа не найдена", _request_id(request))
    if not _can_access_group(session.subject, group):
        _record_audit(
            security,
            request,
            action="authorization.denied",
            event_type="authorization",
            outcome="failure",
            target_type="group",
            target_id=group_id,
            subject=session.subject,
            session_reference=session.session_id,
            metadata={"reason": "group_access_denied"},
        )
        return _error(404, "group_not_found", "Группа не найдена", _request_id(request))
    if not _group_can_filter_resource_type(group, expected_resource_type):
        return _error(
            400,
            "group_resource_type_mismatch",
            "Тип группы не соответствует inventory filter",
            _request_id(request),
        )
    return None


def _require_group_repository(
    groups: GroupServices | None,
    request: Request,
) -> GroupRepository | JSONResponse:
    if groups is not None and groups.repository is not None:
        return groups.repository
    return _error(503, "groups_unavailable", "Group API временно недоступен", _request_id(request))


def _can_access_group(subject: Subject, group: ResourceGroup) -> bool:
    if "portal_admin" in subject.roles:
        return True
    return (
        group.owner_subject_id == subject.subject_id
        and group.scope_type == subject.scope_type
        and group.scope_id == subject.scope_id
    )


def _group_can_filter_resource_type(group: ResourceGroup, expected_resource_type: str) -> bool:
    return group.resource_type == expected_resource_type or group.resource_type == "mixed"


def _inventory_unavailable(request: Request) -> JSONResponse:
    return _error(
        503,
        "inventory_unavailable",
        "Inventory API временно недоступен",
        _request_id(request),
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


def _reject_unsupported_query(request: Request, *, allowed: frozenset[str]) -> JSONResponse | None:
    unsupported = sorted(set(request.query_params.keys()) - allowed)
    if not unsupported:
        return None
    return _error(
        400,
        "unsupported_filter",
        "Неподдерживаемый параметр фильтра",
        _request_id(request),
    )


def _effective_limit(raw_limit: int | None, services: InventoryServices) -> int:
    requested_limit = services.default_limit if raw_limit is None else raw_limit
    return max(1, min(requested_limit, services.max_limit))


def _query_limit(parsed_limit: int, request: Request) -> int | None:
    if "limit" in request.query_params:
        return parsed_limit
    return None


def _parse_sort(
    raw_sort: str,
    *,
    allowed_fields: frozenset[str],
    request: Request,
) -> InventorySort | JSONResponse:
    parts = raw_sort.rsplit(".", 1)
    if len(parts) != 2:
        return _error(400, "unsupported_sort", "Неподдерживаемая сортировка", _request_id(request))
    field, direction = parts
    if field not in allowed_fields or direction not in {"asc", "desc"}:
        return _error(400, "unsupported_sort", "Неподдерживаемая сортировка", _request_id(request))
    return InventorySort(field=field, direction=cast(SortDirection, direction))


def _sort_key(sort: InventorySort) -> str:
    return f"{sort.field}.{sort.direction}"


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
    services: SecurityServices, request: Request, session: SessionRecord
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


def _module_descriptors(subject: Subject) -> list[InventoryModuleDescriptor]:
    descriptors = [
        _capability_module(
            key="instances",
            title="Инстансы",
            path="/api/v1/instances",
            required_capability="instance.read",
            subject=subject,
        ),
        _capability_module(
            key="hypervisors",
            title="Гипервизоры",
            path="/api/v1/hypervisors",
            required_capability="hypervisor.read",
            subject=subject,
        ),
    ]
    descriptors.extend(
        [
            _disabled_module("compute_services", "Сервисы Nova Compute"),
            _disabled_module("network_agents", "Агенты Neutron"),
            _disabled_module("volume_services", "Сервисы Cinder"),
            _disabled_module("image_tasks", "Задачи Glance"),
            _disabled_module("topology", "Топология"),
            _disabled_module("capacity", "Емкость"),
        ]
    )
    return descriptors


def _capability_module(
    *,
    key: str,
    title: str,
    path: str,
    required_capability: str,
    subject: Subject,
) -> InventoryModuleDescriptor:
    enabled = required_capability in subject.capabilities
    return InventoryModuleDescriptor(
        key=key,
        title=title,
        path=path if enabled else None,
        enabled=enabled,
        required_capability=required_capability,
        status="enabled" if enabled else "disabled",
        reason=None if enabled else "missing_capability",
    )


def _disabled_module(key: str, title: str) -> InventoryModuleDescriptor:
    contracts = {
        "compute_services": ("compute_service.read", "/api/v1/compute-services"),
        "network_agents": ("network_agent.read", "/api/v1/network-agents"),
        "volume_services": ("volume_service.read", "/api/v1/volume-services"),
        "image_tasks": ("image_task.read", "/api/v1/image-tasks"),
        "topology": ("topology.read", "/api/v1/topology"),
        "capacity": ("capacity.read", "/api/v1/capacity"),
    }
    required_capability, path = contracts[key]
    return InventoryModuleDescriptor(
        key=key,
        title=title,
        path=path,
        enabled=False,
        required_capability=required_capability,
        status="disabled",
        reason="module_not_implemented",
    )


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


def _instance_target_id(cloud_id: str, region_id: str, instance_id: str) -> str:
    return f"{cloud_id}/{region_id}/{instance_id}"


def _hypervisor_target_id(cloud_id: str, region_id: str, hypervisor_id: str) -> str:
    return f"{cloud_id}/{region_id}/{hypervisor_id}"


def _refresh_operation_id(
    *,
    cloud_id: str,
    region_id: str,
    instance_id: str,
    idempotency_key: str,
    actor_subject_id: str,
    operation_signing_key: str,
) -> str:
    payload = json.dumps(
        {
            "actor_subject_id": actor_subject_id,
            "cloud_id": cloud_id,
            "idempotency_key": idempotency_key,
            "instance_id": instance_id,
            "region_id": region_id,
        },
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    digest = hmac.new(
        operation_signing_key.encode("utf-8"),
        payload,
        hashlib.sha256,
    ).hexdigest()
    return f"inventory-refresh-{digest[:32]}"
