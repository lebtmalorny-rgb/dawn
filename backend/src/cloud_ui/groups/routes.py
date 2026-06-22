from __future__ import annotations

import hashlib
import hmac
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Literal
from uuid import uuid4

import sqlalchemy as sa
from fastapi import APIRouter, Query, Request
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.engine import RowMapping
from sqlalchemy.exc import IntegrityError
from starlette.responses import JSONResponse

from cloud_ui.groups import schema as group_schema
from cloud_ui.groups.models import (
    GroupMember,
    GroupNotFound,
    GroupRevisionConflict,
    ResourceGroup,
)
from cloud_ui.groups.repository import GroupRepository
from cloud_ui.groups.rules import GroupRuleCompiler, GroupRuleError
from cloud_ui.inventory import schema as inventory_schema
from cloud_ui.inventory.models import HypervisorItem, InstanceItem
from cloud_ui.inventory.repository import InventoryRepository
from cloud_ui.security.audit import AuditEvent, AuditOutcome
from cloud_ui.security.dependencies import SecurityServices
from cloud_ui.security.identity import Subject
from cloud_ui.security.rbac import AuthorizationDenied
from cloud_ui.security.routes import CSRF_HEADER_NAME, SESSION_COOKIE_NAME
from cloud_ui.security.sessions import SessionExpired, SessionNotFound, SessionRecord

DEFAULT_GROUP_LIST_LIMIT = 50
MAX_GROUP_LIST_LIMIT = 200
DEFAULT_PREVIEW_LIMIT = 50
MAX_PREVIEW_LIMIT = 50
IDEMPOTENCY_KEY_HEADER_NAME = "idempotency-key"


@dataclass(frozen=True)
class GroupServices:
    repository: GroupRepository | None
    inventory_repository: InventoryRepository | None

    @property
    def available(self) -> bool:
        return self.repository is not None


class ScopeResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    type: str
    id: str | None


class GroupCreateRequest(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str = Field(min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=1024)
    resource_type: Literal["vm", "host", "mixed"]
    membership_mode: Literal["explicit", "dynamic", "imported"] = "explicit"
    scope_id: str | None = None


class GroupUpdateRequest(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    revision: int = Field(ge=1)
    name: str = Field(min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=1024)


class GroupMemberRequest(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    resource_type: Literal["vm", "host"]
    cloud_id: str = Field(min_length=1, max_length=128)
    region_id: str = Field(min_length=1, max_length=128)
    resource_id: str = Field(min_length=1, max_length=128)


class GroupRuleValidationRequest(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    resource_type: Literal["vm", "host"]
    rule: dict[str, Any]


class GroupPreviewRequest(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    rule: dict[str, Any]
    cloud_id: str = "synthetic"
    region_id: str = "RegionOne"
    limit: int = Field(default=DEFAULT_PREVIEW_LIMIT, ge=1)


class GroupResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    group_id: str
    name: str
    description: str | None
    resource_type: str
    scope: ScopeResponse
    membership_mode: str
    rule_version: int
    rule_body_json: dict[str, Any] | None
    owner_subject_id: str
    revision: int
    created_at: datetime
    updated_at: datetime


class GroupListResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    items: list[GroupResponse]
    limit: int


class GroupMemberItem(BaseModel):
    model_config = ConfigDict(frozen=True)

    group_id: str
    resource_type: str
    cloud_id: str
    region_id: str
    resource_id: str
    source: str
    added_by: str
    added_at: datetime
    expires_at: datetime | None


class GroupMemberResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    member: GroupMemberItem
    operation_id: str


class GroupMembersResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    items: list[GroupMemberItem]
    limit: int


class GroupDeleteResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    status: Literal["deleted"]


class GroupPreviewResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    items: list[InstanceItem | HypervisorItem]
    count_estimate: int
    limit: int
    explain: list[str]
    warnings: list[str]


class RuleValidationResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    valid: Literal[True]
    explain: list[str]


def build_group_router(services: GroupServices, security: SecurityServices) -> APIRouter:
    router = APIRouter()

    @router.get("/groups", response_model=GroupListResponse)
    def list_groups(
        request: Request,
        limit: int = Query(default=DEFAULT_GROUP_LIST_LIMIT, ge=1),
    ) -> GroupListResponse | JSONResponse:
        session = _require_session(security, request)
        if isinstance(session, JSONResponse):
            return session
        denied = _require_capability(
            security,
            request,
            session,
            "group.read",
            target_type="group",
            target_id=None,
        )
        if denied is not None:
            return denied
        repository = _require_repository(services, request)
        if isinstance(repository, JSONResponse):
            return repository

        effective_limit = _effective_limit(limit, MAX_GROUP_LIST_LIMIT)
        groups = repository.list_groups(
            actor_id=session.subject.subject_id,
            scope_type=_list_scope_type(session.subject),
            scope_id=_list_scope_id(session.subject),
            include_admin=_is_portal_admin(session.subject),
            limit=effective_limit,
        )
        return GroupListResponse(
            items=[_group_response(group) for group in groups],
            limit=effective_limit,
        )

    @router.post("/groups", response_model=GroupResponse, status_code=201)
    def create_group(
        body: GroupCreateRequest,
        request: Request,
    ) -> GroupResponse | JSONResponse:
        session = _require_session(security, request)
        if isinstance(session, JSONResponse):
            return session
        guard = _require_mutation_guard(
            security,
            request,
            session,
            capability="group.manage",
            target_type="group",
            target_id=None,
        )
        if guard is not None:
            return guard
        repository = _require_repository(services, request)
        if isinstance(repository, JSONResponse):
            return repository

        scope_id = _group_scope_id_for_create(
            security=security,
            request=request,
            session=session,
            body=body,
        )
        if isinstance(scope_id, JSONResponse):
            return scope_id
        if body.resource_type in {"host", "mixed"} and not _is_portal_admin(session.subject):
            return _authorization_denied(
                security,
                request,
                session,
                target_type="group",
                target_id=None,
                metadata={"reason": "host_group_requires_admin"},
            )
        if body.resource_type == "mixed" and body.membership_mode == "dynamic":
            return _error(
                400,
                "unsupported_group_mode",
                "Для mixed group dynamic preview пока не определен",
                _request_id(request),
            )

        try:
            group = repository.create_group(
                actor_id=session.subject.subject_id,
                scope_type="project",
                scope_id=scope_id,
                name=body.name,
                description=body.description,
                resource_type=body.resource_type,
                membership_mode=body.membership_mode,
            )
        except ValueError:
            return _error(400, "invalid_scope", "Некорректная область группы", _request_id(request))
        _record_audit(
            security,
            request,
            action="group.create",
            event_type="group",
            outcome="success",
            target_type="group",
            target_id=group.group_id,
            subject=session.subject,
            session_reference=session.session_id,
            metadata={"revision": group.revision, "resource_type": group.resource_type},
        )
        return _group_response(group)

    @router.get("/groups/{group_id}", response_model=GroupResponse)
    def get_group(group_id: str, request: Request) -> GroupResponse | JSONResponse:
        loaded = _load_accessible_group(
            services=services,
            security=security,
            request=request,
            capability="group.read",
            group_id=group_id,
        )
        if isinstance(loaded, JSONResponse):
            return loaded
        group, _session = loaded
        return _group_response(group)

    @router.patch("/groups/{group_id}", response_model=GroupResponse)
    def update_group(
        group_id: str,
        body: GroupUpdateRequest,
        request: Request,
    ) -> GroupResponse | JSONResponse:
        loaded = _load_accessible_group(
            services=services,
            security=security,
            request=request,
            capability="group.manage",
            group_id=group_id,
            mutation=True,
        )
        if isinstance(loaded, JSONResponse):
            return loaded
        _group, session = loaded
        repository = _require_repository(services, request)
        if isinstance(repository, JSONResponse):
            return repository

        try:
            updated = repository.update_group(
                group_id=group_id,
                actor_id=session.subject.subject_id,
                expected_revision=body.revision,
                name=body.name,
                description=body.description,
            )
        except GroupRevisionConflict:
            return _error(
                409,
                "group_revision_conflict",
                "Версия группы устарела",
                _request_id(request),
            )
        except GroupNotFound:
            return _group_not_found(request)

        _record_audit(
            security,
            request,
            action="group.update",
            event_type="group",
            outcome="success",
            target_type="group",
            target_id=updated.group_id,
            subject=session.subject,
            session_reference=session.session_id,
            metadata={"revision": updated.revision},
        )
        return _group_response(updated)

    @router.delete("/groups/{group_id}", response_model=GroupDeleteResponse)
    def delete_group(group_id: str, request: Request) -> GroupDeleteResponse | JSONResponse:
        loaded = _load_accessible_group(
            services=services,
            security=security,
            request=request,
            capability="group.manage",
            group_id=group_id,
            mutation=True,
        )
        if isinstance(loaded, JSONResponse):
            return loaded
        _group, session = loaded
        repository = _require_repository(services, request)
        if isinstance(repository, JSONResponse):
            return repository
        try:
            repository.delete_group(group_id=group_id, actor_id=session.subject.subject_id)
        except GroupNotFound:
            return _group_not_found(request)
        _record_audit(
            security,
            request,
            action="group.delete",
            event_type="group",
            outcome="success",
            target_type="group",
            target_id=group_id,
            subject=session.subject,
            session_reference=session.session_id,
            metadata={},
        )
        return GroupDeleteResponse(status="deleted")

    @router.get("/groups/{group_id}/members", response_model=GroupMembersResponse)
    def list_members(
        group_id: str,
        request: Request,
        limit: int = Query(default=DEFAULT_GROUP_LIST_LIMIT, ge=1),
    ) -> GroupMembersResponse | JSONResponse:
        loaded = _load_accessible_group(
            services=services,
            security=security,
            request=request,
            capability="group.read",
            group_id=group_id,
        )
        if isinstance(loaded, JSONResponse):
            return loaded
        _group, _session = loaded
        repository = _require_repository(services, request)
        if isinstance(repository, JSONResponse):
            return repository
        effective_limit = _effective_limit(limit, MAX_GROUP_LIST_LIMIT)
        try:
            members = repository.list_members(group_id, limit=effective_limit)
        except GroupNotFound:
            return _group_not_found(request)
        return GroupMembersResponse(
            items=[_member_item(member) for member in members],
            limit=effective_limit,
        )

    @router.post("/groups/{group_id}/members", response_model=GroupMemberResponse)
    def add_member(
        group_id: str,
        body: GroupMemberRequest,
        request: Request,
    ) -> GroupMemberResponse | JSONResponse:
        loaded = _load_accessible_group(
            services=services,
            security=security,
            request=request,
            capability="group.manage",
            group_id=group_id,
            mutation=True,
        )
        if isinstance(loaded, JSONResponse):
            return loaded
        group, session = loaded
        idempotency_key = _require_idempotency_key(request)
        if isinstance(idempotency_key, JSONResponse):
            return idempotency_key
        repository = _require_repository(services, request)
        if isinstance(repository, JSONResponse):
            return repository
        idempotency = _member_idempotency_context(
            action="group.member.add",
            actor_id=session.subject.subject_id,
            group_id=group.group_id,
            member=body,
            idempotency_key=idempotency_key,
        )
        target_error = _validate_member_target(
            services=services,
            security=security,
            request=request,
            session=session,
            group=group,
            member=body,
        )
        if target_error is not None:
            return target_error
        idempotency_error = _reserve_member_idempotency_key(
            repository=repository,
            actor_id=session.subject.subject_id,
            group_id=group.group_id,
            action="group.member.add",
            context=idempotency,
            request=request,
        )
        if idempotency_error is not None:
            return idempotency_error

        try:
            member = repository.add_member(
                group_id=group.group_id,
                resource_type=body.resource_type,
                cloud_id=body.cloud_id,
                region_id=body.region_id,
                resource_id=body.resource_id,
                source="explicit",
                actor_id=session.subject.subject_id,
                idempotency_key_hash=idempotency.key_hash,
                request_hash=idempotency.request_hash,
                operation_id=idempotency.operation_id,
            )
        except GroupRevisionConflict:
            return _error(
                409,
                "group_revision_conflict",
                "Версия группы устарела",
                _request_id(request),
            )
        except GroupNotFound:
            return _group_not_found(request)

        _record_audit(
            security,
            request,
            action="group.member.add",
            event_type="group",
            outcome="success",
            target_type=body.resource_type,
            target_id=_member_target_id(body),
            subject=session.subject,
            session_reference=session.session_id,
            metadata={"group_id": group.group_id, "operation_id": idempotency.operation_id},
        )
        return GroupMemberResponse(
            member=_member_item(member),
            operation_id=idempotency.operation_id,
        )

    @router.delete(
        "/groups/{group_id}/members/{resource_type}/{cloud_id}/{region_id}/{resource_id}",
        response_model=GroupDeleteResponse,
    )
    def remove_member(
        group_id: str,
        resource_type: Literal["vm", "host"],
        cloud_id: str,
        region_id: str,
        resource_id: str,
        request: Request,
    ) -> GroupDeleteResponse | JSONResponse:
        loaded = _load_accessible_group(
            services=services,
            security=security,
            request=request,
            capability="group.manage",
            group_id=group_id,
            mutation=True,
        )
        if isinstance(loaded, JSONResponse):
            return loaded
        group, session = loaded
        idempotency_key = _require_idempotency_key(request)
        if isinstance(idempotency_key, JSONResponse):
            return idempotency_key
        repository = _require_repository(services, request)
        if isinstance(repository, JSONResponse):
            return repository
        target = GroupMemberRequest(
            resource_type=resource_type,
            cloud_id=cloud_id,
            region_id=region_id,
            resource_id=resource_id,
        )
        if not _group_accepts_member_type(group, resource_type):
            return _error(
                400,
                "resource_type_mismatch",
                "Тип ресурса не соответствует группе",
                _request_id(request),
            )
        if resource_type == "host" and not _is_portal_admin(session.subject):
            return _authorization_denied(
                security,
                request,
                session,
                target_type="host",
                target_id=_member_target_id(target),
                metadata={"reason": "host_member_requires_admin", "group_id": group.group_id},
            )
        idempotency = _member_idempotency_context(
            action="group.member.remove",
            actor_id=session.subject.subject_id,
            group_id=group.group_id,
            member=target,
            idempotency_key=idempotency_key,
        )
        idempotency_error = _reserve_member_idempotency_key(
            repository=repository,
            actor_id=session.subject.subject_id,
            group_id=group.group_id,
            action="group.member.remove",
            context=idempotency,
            request=request,
        )
        if idempotency_error is not None:
            return idempotency_error
        try:
            repository.remove_member(
                group_id=group.group_id,
                resource_type=resource_type,
                cloud_id=cloud_id,
                region_id=region_id,
                resource_id=resource_id,
                actor_id=session.subject.subject_id,
                idempotency_key_hash=idempotency.key_hash,
                request_hash=idempotency.request_hash,
                operation_id=idempotency.operation_id,
            )
        except GroupRevisionConflict:
            return _error(
                409,
                "group_revision_conflict",
                "Версия группы устарела",
                _request_id(request),
            )
        except GroupNotFound:
            return _group_not_found(request)
        _record_audit(
            security,
            request,
            action="group.member.remove",
            event_type="group",
            outcome="success",
            target_type=resource_type,
            target_id=_member_target_id(target),
            subject=session.subject,
            session_reference=session.session_id,
            metadata={"group_id": group.group_id, "operation_id": idempotency.operation_id},
        )
        return GroupDeleteResponse(status="deleted")

    @router.post("/groups/rules/validate", response_model=RuleValidationResponse)
    def validate_rule(
        body: GroupRuleValidationRequest,
        request: Request,
    ) -> RuleValidationResponse | JSONResponse:
        session = _require_session(security, request)
        if isinstance(session, JSONResponse):
            return session
        denied = _require_capability(
            security,
            request,
            session,
            "group.read",
            target_type="group_rule",
            target_id=None,
        )
        if denied is not None:
            return denied
        try:
            compiled = GroupRuleCompiler().compile(
                resource_type=body.resource_type,
                scope_type=session.subject.scope_type,
                scope_id=session.subject.scope_id,
                rule=body.rule,
            )
        except GroupRuleError as exc:
            return _error(400, exc.code, "Правило группы отклонено", _request_id(request))
        return RuleValidationResponse(valid=True, explain=compiled.explain)

    @router.post("/groups/{group_id}/preview", response_model=GroupPreviewResponse)
    def preview_group(
        group_id: str,
        body: GroupPreviewRequest,
        request: Request,
    ) -> GroupPreviewResponse | JSONResponse:
        loaded = _load_accessible_group(
            services=services,
            security=security,
            request=request,
            capability="group.read",
            group_id=group_id,
        )
        if isinstance(loaded, JSONResponse):
            return loaded
        group, session = loaded
        inventory_capability = _preview_inventory_capability(group.resource_type)
        if inventory_capability is None:
            return _error(
                400,
                "unknown_resource_type",
                "Тип группы не поддерживает preview",
                _request_id(request),
            )
        denied = _require_capability(
            security,
            request,
            session,
            inventory_capability,
            target_type="group",
            target_id=group.group_id,
        )
        if denied is not None:
            return denied
        inventory_repository = _require_inventory_repository(services, request)
        if isinstance(inventory_repository, JSONResponse):
            return inventory_repository
        try:
            compiled = GroupRuleCompiler().compile(
                resource_type=group.resource_type,
                scope_type=group.scope_type,
                scope_id=group.scope_id,
                rule=body.rule,
            )
        except GroupRuleError as exc:
            return _error(400, exc.code, "Правило группы отклонено", _request_id(request))

        limit = _effective_limit(body.limit, MAX_PREVIEW_LIMIT)
        try:
            preview = _preview_items(
                inventory_repository=inventory_repository,
                resource_type=group.resource_type,
                cloud_id=body.cloud_id,
                region_id=body.region_id,
                condition=compiled.condition,
                limit=limit,
            )
        except Exception:
            return _error(
                503,
                "inventory_unavailable",
                "Inventory API временно недоступен",
                _request_id(request),
            )

        _record_audit(
            security,
            request,
            action="group.preview",
            event_type="group",
            outcome="success",
            target_type="group",
            target_id=group.group_id,
            subject=session.subject,
            session_reference=session.session_id,
            metadata={"count_estimate": preview.count_estimate},
        )
        return GroupPreviewResponse(
            items=preview.items,
            count_estimate=preview.count_estimate,
            limit=limit,
            explain=compiled.explain,
            warnings=["preview_truncated"] if preview.truncated else [],
        )

    return router


@dataclass(frozen=True)
class _PreviewResult:
    items: list[InstanceItem | HypervisorItem]
    count_estimate: int
    truncated: bool


@dataclass(frozen=True)
class _MemberIdempotencyContext:
    key_hash: str
    request_hash: str
    operation_id: str


@dataclass(frozen=True)
class _MemberIdempotencyRecord:
    request_hash: str
    operation_id: str


def _load_accessible_group(
    *,
    services: GroupServices,
    security: SecurityServices,
    request: Request,
    capability: str,
    group_id: str,
    mutation: bool = False,
) -> tuple[ResourceGroup, SessionRecord] | JSONResponse:
    session = _require_session(security, request)
    if isinstance(session, JSONResponse):
        return session
    if mutation:
        guard = _require_mutation_guard(
            security,
            request,
            session,
            capability=capability,
            target_type="group",
            target_id=group_id,
        )
        if guard is not None:
            return guard
    else:
        denied = _require_capability(
            security,
            request,
            session,
            capability,
            target_type="group",
            target_id=group_id,
        )
        if denied is not None:
            return denied
    repository = _require_repository(services, request)
    if isinstance(repository, JSONResponse):
        return repository
    group = repository.get_group(group_id)
    if group is None:
        return _group_not_found(request)
    if not _can_access_group(session.subject, group):
        return _authorization_denied(
            security,
            request,
            session,
            target_type="group",
            target_id=group_id,
            metadata={"reason": "group_access_denied"},
            response_status=404,
            response_code="group_not_found",
            response_message="Группа не найдена",
        )
    return group, session


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


def _validate_member_target(
    *,
    services: GroupServices,
    security: SecurityServices,
    request: Request,
    session: SessionRecord,
    group: ResourceGroup,
    member: GroupMemberRequest,
) -> JSONResponse | None:
    if not _group_accepts_member_type(group, member.resource_type):
        return _error(
            400,
            "resource_type_mismatch",
            "Тип ресурса не соответствует группе",
            _request_id(request),
        )
    inventory_repository = _require_inventory_repository(services, request)
    if isinstance(inventory_repository, JSONResponse):
        return inventory_repository
    if member.resource_type == "vm":
        instance = inventory_repository.get_instance(
            member.cloud_id,
            member.region_id,
            member.resource_id,
        )
        if instance is None:
            return _error(404, "resource_not_found", "Ресурс не найден", _request_id(request))
        if instance.project_id != group.scope_id:
            return _authorization_denied(
                security,
                request,
                session,
                target_type="vm",
                target_id=_member_target_id(member),
                metadata={"reason": "resource_scope_forbidden", "group_id": group.group_id},
                response_status=403,
                response_code="resource_scope_forbidden",
                response_message="Ресурс вне области группы",
            )
        return None

    if not _is_portal_admin(session.subject):
        return _authorization_denied(
            security,
            request,
            session,
            target_type="host",
            target_id=_member_target_id(member),
            metadata={"reason": "host_member_requires_admin", "group_id": group.group_id},
        )
    hypervisor = inventory_repository.get_hypervisor(
        member.cloud_id,
        member.region_id,
        member.resource_id,
    )
    if hypervisor is None:
        return _error(404, "resource_not_found", "Ресурс не найден", _request_id(request))
    return None


def _preview_items(
    *,
    inventory_repository: InventoryRepository,
    resource_type: str,
    cloud_id: str,
    region_id: str,
    condition: sa.ColumnElement[bool],
    limit: int,
) -> _PreviewResult:
    if resource_type == "vm":
        return _preview_instances(
            inventory_repository=inventory_repository,
            cloud_id=cloud_id,
            region_id=region_id,
            condition=condition,
            limit=limit,
        )
    if resource_type == "host":
        return _preview_hypervisors(
            inventory_repository=inventory_repository,
            cloud_id=cloud_id,
            region_id=region_id,
            condition=condition,
            limit=limit,
        )
    raise GroupRuleError("unknown_resource_type")


def _preview_instances(
    *,
    inventory_repository: InventoryRepository,
    cloud_id: str,
    region_id: str,
    condition: sa.ColumnElement[bool],
    limit: int,
) -> _PreviewResult:
    table = inventory_schema.instances
    filters = [
        table.c.cloud_id == cloud_id,
        table.c.region_id == region_id,
        table.c.deleted_at.is_(None),
        condition,
    ]
    count_statement = sa.select(sa.func.count()).select_from(table).where(*filters)
    page_statement = (
        sa.select(table)
        .where(*filters)
        .order_by(table.c.name.asc(), table.c.instance_id.asc())
        .limit(limit + 1)
    )
    with inventory_repository.engine.connect() as connection:
        count_estimate = int(connection.execute(count_statement).scalar_one())
        rows = list(connection.execute(page_statement).mappings())
    page_rows = rows[:limit]
    return _PreviewResult(
        items=[_instance_item_from_row(row) for row in page_rows],
        count_estimate=count_estimate,
        truncated=count_estimate > limit or len(rows) > limit,
    )


def _preview_hypervisors(
    *,
    inventory_repository: InventoryRepository,
    cloud_id: str,
    region_id: str,
    condition: sa.ColumnElement[bool],
    limit: int,
) -> _PreviewResult:
    table = inventory_schema.hypervisors
    filters = [
        table.c.cloud_id == cloud_id,
        table.c.region_id == region_id,
        table.c.deleted_at.is_(None),
        condition,
    ]
    count_statement = sa.select(sa.func.count()).select_from(table).where(*filters)
    page_statement = (
        sa.select(table)
        .where(*filters)
        .order_by(table.c.host_name.asc(), table.c.hypervisor_id.asc())
        .limit(limit + 1)
    )
    with inventory_repository.engine.connect() as connection:
        count_estimate = int(connection.execute(count_statement).scalar_one())
        rows = list(connection.execute(page_statement).mappings())
    page_rows = rows[:limit]
    return _PreviewResult(
        items=[_hypervisor_item_from_row(row) for row in page_rows],
        count_estimate=count_estimate,
        truncated=count_estimate > limit or len(rows) > limit,
    )


def _group_scope_id_for_create(
    *,
    security: SecurityServices,
    request: Request,
    session: SessionRecord,
    body: GroupCreateRequest,
) -> str | JSONResponse:
    subject = session.subject
    if _is_portal_admin(subject):
        if body.scope_id is None or body.scope_id.strip() == "":
            return _error(
                400,
                "invalid_scope",
                "Для группы требуется project scope",
                _request_id(request),
            )
        return body.scope_id.strip()
    if subject.scope_type != "project" or subject.scope_id is None:
        return _authorization_denied(
            security,
            request,
            session,
            target_type="group",
            target_id=None,
            metadata={"reason": "project_scope_required"},
        )
    if body.scope_id is not None and body.scope_id != subject.scope_id:
        return _authorization_denied(
            security,
            request,
            session,
            target_type="group",
            target_id=None,
            metadata={"reason": "resource_scope_forbidden"},
            response_status=403,
            response_code="resource_scope_forbidden",
            response_message="Ресурс вне области группы",
        )
    return subject.scope_id


def _list_scope_type(subject: Subject) -> str:
    if _is_portal_admin(subject):
        return "project"
    return subject.scope_type


def _list_scope_id(subject: Subject) -> str | None:
    if _is_portal_admin(subject):
        return None
    return subject.scope_id


def _can_access_group(subject: Subject, group: ResourceGroup) -> bool:
    if _is_portal_admin(subject):
        return True
    return (
        group.owner_subject_id == subject.subject_id
        and group.scope_type == subject.scope_type
        and group.scope_id == subject.scope_id
    )


def _group_accepts_member_type(group: ResourceGroup, resource_type: str) -> bool:
    return group.resource_type == resource_type or group.resource_type == "mixed"


def _preview_inventory_capability(resource_type: str) -> str | None:
    if resource_type == "vm":
        return "instance.read"
    if resource_type == "host":
        return "hypervisor.read"
    return None


def _is_portal_admin(subject: Subject) -> bool:
    return "portal_admin" in subject.roles


def _require_repository(
    services: GroupServices,
    request: Request,
) -> GroupRepository | JSONResponse:
    if services.repository is not None:
        return services.repository
    return _error(503, "groups_unavailable", "Group API временно недоступен", _request_id(request))


def _require_inventory_repository(
    services: GroupServices,
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


def _authorization_denied(
    services: SecurityServices,
    request: Request,
    session: SessionRecord,
    *,
    target_type: str,
    target_id: str | None,
    metadata: dict[str, Any],
    response_status: int = 403,
    response_code: str = "forbidden",
    response_message: str = "Действие запрещено",
) -> JSONResponse:
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
        metadata=metadata,
    )
    return _error(response_status, response_code, response_message, _request_id(request))


def _effective_limit(limit: int, maximum: int) -> int:
    return max(1, min(limit, maximum))


def _group_response(group: ResourceGroup) -> GroupResponse:
    return GroupResponse(
        group_id=group.group_id,
        name=group.name,
        description=group.description,
        resource_type=group.resource_type,
        scope=ScopeResponse(type=group.scope_type, id=group.scope_id),
        membership_mode=group.membership_mode,
        rule_version=group.rule_version,
        rule_body_json=group.rule_body_json,
        owner_subject_id=group.owner_subject_id,
        revision=group.revision,
        created_at=group.created_at,
        updated_at=group.updated_at,
    )


def _member_item(member: GroupMember) -> GroupMemberItem:
    return GroupMemberItem(
        group_id=member.group_id,
        resource_type=member.resource_type,
        cloud_id=member.cloud_id,
        region_id=member.region_id,
        resource_id=member.resource_id,
        source=member.source,
        added_by=member.added_by,
        added_at=member.added_at,
        expires_at=member.expires_at,
    )


def _member_idempotency_context(
    *,
    action: str,
    actor_id: str,
    group_id: str,
    member: GroupMemberRequest,
    idempotency_key: str,
) -> _MemberIdempotencyContext:
    key_hash = _idempotency_key_hash(
        action=action,
        actor_id=actor_id,
        group_id=group_id,
        idempotency_key=idempotency_key,
    )
    return _MemberIdempotencyContext(
        key_hash=key_hash,
        request_hash=_member_request_hash(action=action, group_id=group_id, member=member),
        operation_id=_member_operation_id(
            action=action,
            actor_id=actor_id,
            group_id=group_id,
            key_hash=key_hash,
        ),
    )


def _reserve_member_idempotency_key(
    *,
    repository: GroupRepository,
    actor_id: str,
    group_id: str,
    action: str,
    context: _MemberIdempotencyContext,
    request: Request,
) -> JSONResponse | None:
    existing = _get_member_idempotency_record(
        repository=repository,
        actor_id=actor_id,
        group_id=group_id,
        action=action,
        key_hash=context.key_hash,
    )
    if existing is not None:
        return _idempotency_conflict(existing, context, request)

    try:
        with repository.engine.begin() as connection:
            connection.execute(
                group_schema.resource_group_idempotency_keys.insert().values(
                    group_id=group_id,
                    actor_id=actor_id,
                    action=action,
                    key_hash=context.key_hash,
                    request_hash=context.request_hash,
                    operation_id=context.operation_id,
                    created_at=datetime.now(UTC),
                )
            )
    except IntegrityError:
        existing_after_race = _get_member_idempotency_record(
            repository=repository,
            actor_id=actor_id,
            group_id=group_id,
            action=action,
            key_hash=context.key_hash,
        )
        if existing_after_race is None:
            raise
        return _idempotency_conflict(existing_after_race, context, request)
    return None


def _get_member_idempotency_record(
    *,
    repository: GroupRepository,
    actor_id: str,
    group_id: str,
    action: str,
    key_hash: str,
) -> _MemberIdempotencyRecord | None:
    statement = (
        sa.select(
            group_schema.resource_group_idempotency_keys.c.request_hash,
            group_schema.resource_group_idempotency_keys.c.operation_id,
        )
        .where(
            group_schema.resource_group_idempotency_keys.c.group_id == group_id,
            group_schema.resource_group_idempotency_keys.c.actor_id == actor_id,
            group_schema.resource_group_idempotency_keys.c.action == action,
            group_schema.resource_group_idempotency_keys.c.key_hash == key_hash,
        )
    )
    with repository.engine.connect() as connection:
        row = connection.execute(statement).mappings().one_or_none()
    if row is None:
        return None
    return _MemberIdempotencyRecord(
        request_hash=str(row["request_hash"]),
        operation_id=str(row["operation_id"]),
    )


def _idempotency_conflict(
    record: _MemberIdempotencyRecord | None,
    context: _MemberIdempotencyContext,
    request: Request,
) -> JSONResponse | None:
    if record is None or record.request_hash == context.request_hash:
        return None
    return _error(
        409,
        "idempotency_key_conflict",
        "Idempotency-Key уже использован для другого запроса",
        _request_id(request),
    )


def _idempotency_key_hash(
    *,
    action: str,
    actor_id: str,
    group_id: str,
    idempotency_key: str,
) -> str:
    return _hash_payload(
        {
            "action": action,
            "actor_id": actor_id,
            "group_id": group_id,
            "idempotency_key": idempotency_key,
        },
        key=b"resource-group-idempotency-key",
    )


def _member_request_hash(
    *,
    action: str,
    group_id: str,
    member: GroupMemberRequest,
) -> str:
    return _hash_payload(
        {
            "action": action,
            "cloud_id": member.cloud_id,
            "group_id": group_id,
            "region_id": member.region_id,
            "resource_id": member.resource_id,
            "resource_type": member.resource_type,
        },
        key=b"resource-group-idempotency-request",
    )


def _member_operation_id(
    *,
    action: str,
    actor_id: str,
    group_id: str,
    key_hash: str,
) -> str:
    digest = _hash_payload(
        {
            "action": action,
            "actor_id": actor_id,
            "group_id": group_id,
            "idempotency_key_hash": key_hash,
        },
        key=b"resource-group-membership-operation",
    )
    return f"group-member-{digest[:32]}"


def _hash_payload(payload: dict[str, Any], *, key: bytes) -> str:
    raw_payload = json.dumps(
        payload,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return hmac.new(key, raw_payload, hashlib.sha256).hexdigest()


def _member_target_id(member: GroupMemberRequest) -> str:
    return f"{member.cloud_id}/{member.region_id}/{member.resource_id}"


def _group_not_found(request: Request) -> JSONResponse:
    return _error(404, "group_not_found", "Группа не найдена", _request_id(request))


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


def _instance_item_from_row(row: RowMapping) -> InstanceItem:
    return InstanceItem(
        cloud_id=str(row["cloud_id"]),
        region_id=str(row["region_id"]),
        instance_id=str(row["instance_id"]),
        name=str(row["name"]),
        project_id=str(row["project_id"]),
        user_id=str(row["user_id"]),
        status=str(row["status"]),
        power_state=str(row["power_state"]),
        task_state=_optional_string(row["task_state"]),
        vm_state=str(row["vm_state"]),
        host_name=_optional_string(row["host_name"]),
        hypervisor_id=_optional_string(row["hypervisor_id"]),
        availability_zone=_optional_string(row["availability_zone"]),
        flavor_id=_optional_string(row["flavor_id"]),
        vcpus=int(row["vcpus"]),
        ram_mb=int(row["ram_mb"]),
        disk_gb=int(row["disk_gb"]),
        image_id=_optional_string(row["image_id"]),
        boot_volume_id=_optional_string(row["boot_volume_id"]),
        addresses=_dict_json(row["addresses_json"]),
        source_created_at=_as_utc(row["source_created_at"]),
        source_updated_at=_as_utc(row["source_updated_at"]),
        observed_at=_required_datetime(row["observed_at"]),
        sync_generation=int(row["sync_generation"]),
        sync_status=str(row["sync_status"]),
    )


def _hypervisor_item_from_row(row: RowMapping) -> HypervisorItem:
    return HypervisorItem(
        cloud_id=str(row["cloud_id"]),
        region_id=str(row["region_id"]),
        hypervisor_id=str(row["hypervisor_id"]),
        host_name=str(row["host_name"]),
        service_id=_optional_string(row["service_id"]),
        service_status=str(row["service_status"]),
        service_state=str(row["service_state"]),
        hypervisor_type=_optional_string(row["hypervisor_type"]),
        hypervisor_version=_optional_string(row["hypervisor_version"]),
        availability_zone=_optional_string(row["availability_zone"]),
        aggregates=_string_list_json(row["aggregates_json"]),
        vcpus_total=int(row["vcpus_total"]),
        vcpus_used=int(row["vcpus_used"]),
        ram_mb_total=int(row["ram_mb_total"]),
        ram_mb_used=int(row["ram_mb_used"]),
        disk_gb_total=int(row["disk_gb_total"]),
        disk_gb_used=int(row["disk_gb_used"]),
        running_vms=int(row["running_vms"]),
        disabled_reason=_optional_string(row["disabled_reason"]),
        maintenance_status=_optional_string(row["maintenance_status"]),
        observed_at=_required_datetime(row["observed_at"]),
        sync_generation=int(row["sync_generation"]),
        sync_status=str(row["sync_status"]),
    )


def _optional_string(value: object) -> str | None:
    if value is None:
        return None
    return str(value)


def _dict_json(value: object) -> dict[str, Any]:
    if isinstance(value, dict):
        return dict(value)
    return {}


def _string_list_json(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value]


def _required_datetime(value: object) -> datetime:
    timestamp = _as_utc(value)
    if timestamp is None:
        raise ValueError("required inventory timestamp is missing")
    return timestamp


def _as_utc(value: object) -> datetime | None:
    if value is None:
        return None
    if not isinstance(value, datetime):
        raise TypeError("expected datetime")
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)
