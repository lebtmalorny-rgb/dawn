from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

import sqlalchemy as sa
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.engine import Engine
from sqlalchemy.pool import StaticPool

from cloud_ui.api import create_app
from cloud_ui.groups import schema as group_schema
from cloud_ui.groups.repository import GroupRepository
from cloud_ui.groups.routes import GroupServices
from cloud_ui.health import HealthReport
from cloud_ui.inventory import schema as inventory_schema
from cloud_ui.inventory.cursor import CursorCodec
from cloud_ui.inventory.repository import InventoryRepository
from cloud_ui.inventory.routes import InventoryServices
from cloud_ui.security.audit import InMemoryAuditSink
from cloud_ui.security.clock import ManualClock
from cloud_ui.security.dependencies import SecurityServices, build_security_services
from cloud_ui.security.identity import LoginRequest, LoginResult, Subject
from cloud_ui.security.rbac import PolicyService
from cloud_ui.security.sessions import SessionManager


def test_operator_creates_vm_group_with_initial_revision() -> None:
    client, _security = _client()
    csrf = _login(client, "operator", "operator-code")

    response = client.post(
        "/api/v1/groups",
        json={
            "name": "tenant-a",
            "description": "Tenant A production VMs",
            "resource_type": "vm",
            "membership_mode": "explicit",
        },
        headers={"x-request-id": "group-create", "x-csrf-token": csrf},
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["name"] == "tenant-a"
    assert payload["resource_type"] == "vm"
    assert payload["scope"] == {"type": "project", "id": "project-a"}
    assert payload["owner_subject_id"] == "mock-user-operator"
    assert payload["revision"] == 1


def test_stale_group_patch_revision_returns_409() -> None:
    client, _security = _client()
    csrf = _login(client, "operator", "operator-code")
    group_id = _create_group(client, csrf)["group_id"]
    updated = client.patch(
        f"/api/v1/groups/{group_id}",
        json={"revision": 1, "name": "renamed", "description": "renamed"},
        headers={"x-request-id": "group-update", "x-csrf-token": csrf},
    )
    assert updated.status_code == 200

    response = client.patch(
        f"/api/v1/groups/{group_id}",
        json={"revision": 1, "name": "stale", "description": "stale"},
        headers={"x-request-id": "group-stale", "x-csrf-token": csrf},
    )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "group_revision_conflict"


def test_auditor_without_group_read_gets_403_and_audit_denial() -> None:
    client, security = _client()
    _login(client, "auditor", "auditor-code")

    response = client.get("/api/v1/groups", headers={"x-request-id": "auditor-groups"})

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "forbidden"
    assert any(
        event.action == "authorization.denied"
        and event.actor_id == "mock-user-auditor"
        and event.metadata["capability"] == "group.read"
        for event in security.audit_sink.events
    )


def test_group_create_requires_csrf() -> None:
    client, _security = _client()
    _login(client, "operator", "operator-code")

    response = client.post(
        "/api/v1/groups",
        json={"name": "tenant-a", "resource_type": "vm", "membership_mode": "explicit"},
        headers={"x-request-id": "group-create-no-csrf"},
    )

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "csrf_failed"


def test_add_vm_member_from_other_project_is_denied() -> None:
    client, _security = _client()
    csrf = _login(client, "operator", "operator-code")
    group_id = _create_group(client, csrf)["group_id"]

    response = client.post(
        f"/api/v1/groups/{group_id}/members",
        json={
            "resource_type": "vm",
            "cloud_id": "synthetic",
            "region_id": "RegionOne",
            "resource_id": "instance-project-b",
        },
        headers={
            "x-request-id": "member-cross-project",
            "x-csrf-token": csrf,
            "idempotency-key": "member-cross-project-key",
        },
    )

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "resource_scope_forbidden"


def test_add_missing_or_deleted_vm_member_returns_safe_error() -> None:
    client, _security = _client()
    csrf = _login(client, "operator", "operator-code")
    group_id = _create_group(client, csrf)["group_id"]

    missing = client.post(
        f"/api/v1/groups/{group_id}/members",
        json={
            "resource_type": "vm",
            "cloud_id": "synthetic",
            "region_id": "RegionOne",
            "resource_id": "does-not-exist",
        },
        headers={
            "x-request-id": "member-missing",
            "x-csrf-token": csrf,
            "idempotency-key": "member-missing-key",
        },
    )
    deleted = client.post(
        f"/api/v1/groups/{group_id}/members",
        json={
            "resource_type": "vm",
            "cloud_id": "synthetic",
            "region_id": "RegionOne",
            "resource_id": "instance-deleted",
        },
        headers={
            "x-request-id": "member-deleted",
            "x-csrf-token": csrf,
            "idempotency-key": "member-deleted-key",
        },
    )

    assert missing.status_code == 404
    assert missing.json()["error"]["code"] == "resource_not_found"
    assert deleted.status_code == 404
    assert deleted.json()["error"]["code"] == "resource_not_found"


def test_member_add_with_same_idempotency_key_returns_stable_result() -> None:
    client, security = _client()
    csrf = _login(client, "operator", "operator-code")
    group_id = _create_group(client, csrf)["group_id"]
    body = {
        "resource_type": "vm",
        "cloud_id": "synthetic",
        "region_id": "RegionOne",
        "resource_id": "instance-project-a",
    }
    headers = {
        "x-request-id": "member-idempotent",
        "x-csrf-token": csrf,
        "idempotency-key": "member-secret-canary",
    }

    first = client.post(f"/api/v1/groups/{group_id}/members", json=body, headers=headers)
    second = client.post(f"/api/v1/groups/{group_id}/members", json=body, headers=headers)

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json() == second.json()
    assert first.json()["member"]["resource_id"] == "instance-project-a"
    event_metadata = [event.metadata for event in security.audit_sink.events]
    assert "member-secret-canary" not in repr(event_metadata)


def test_preview_returns_bounded_items_and_explain() -> None:
    client, _security = _client()
    csrf = _login(client, "operator", "operator-code")
    group_id = _create_group(client, csrf)["group_id"]

    response = client.post(
        f"/api/v1/groups/{group_id}/preview",
        json={
            "rule": {"field": "status", "op": "eq", "value": "ACTIVE"},
            "limit": 1,
            "cloud_id": "synthetic",
            "region_id": "RegionOne",
        },
        headers={"x-request-id": "group-preview", "x-csrf-token": csrf},
    )

    assert response.status_code == 200
    payload = response.json()
    assert [item["instance_id"] for item in payload["items"]] == ["instance-project-a"]
    assert payload["count_estimate"] == 2
    assert payload["explain"] == ["status eq ACTIVE"]
    assert payload["warnings"] == ["preview_truncated"]


def test_rule_validate_rejects_arbitrary_field_and_operator() -> None:
    client, _security = _client()
    _login(client, "operator", "operator-code")

    field_response = client.post(
        "/api/v1/groups/rules/validate",
        json={
            "resource_type": "vm",
            "rule": {"field": "name", "op": "eq", "value": "vm-a"},
        },
        headers={"x-request-id": "rule-field"},
    )
    operator_response = client.post(
        "/api/v1/groups/rules/validate",
        json={
            "resource_type": "vm",
            "rule": {"field": "status", "op": "regex", "value": "ACTIVE"},
        },
        headers={"x-request-id": "rule-operator"},
    )

    assert field_response.status_code == 400
    assert field_response.json()["error"]["code"] == "unknown_field"
    assert operator_response.status_code == 400
    assert operator_response.json()["error"]["code"] == "unknown_operator"


def test_preview_requires_matching_inventory_read_capability() -> None:
    client, security = _client(
        subject=Subject(
            subject_id="mock-user-group-only",
            display_name="Group Only",
            subject_type="human",
            scope_type="project",
            scope_id="project-a",
            roles=frozenset({"group_reader"}),
            capabilities=frozenset({"group.read"}),
        )
    )
    csrf = _login(client, "custom", "custom-code")
    group_id = _repository_create_group(
        security,
        resource_type="vm",
        actor_id="mock-user-group-only",
    )

    response = client.post(
        f"/api/v1/groups/{group_id}/preview",
        json={"rule": {"field": "status", "op": "eq", "value": "ACTIVE"}},
        headers={"x-request-id": "preview-without-instance-read", "x-csrf-token": csrf},
    )

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "forbidden"
    assert any(
        event.action == "authorization.denied"
        and event.actor_id == "mock-user-group-only"
        and event.metadata["capability"] == "instance.read"
        for event in security.audit_sink.events
    )


def test_same_idempotency_key_with_different_member_does_not_mutate_second_target() -> None:
    client, _security = _client()
    csrf = _login(client, "operator", "operator-code")
    group_id = _create_group(client, csrf)["group_id"]
    headers = {
        "x-request-id": "member-idempotency-conflict",
        "x-csrf-token": csrf,
        "idempotency-key": "same-key-conflict-secret",
    }

    first = client.post(
        f"/api/v1/groups/{group_id}/members",
        json={
            "resource_type": "vm",
            "cloud_id": "synthetic",
            "region_id": "RegionOne",
            "resource_id": "instance-project-a",
        },
        headers=headers,
    )
    second = client.post(
        f"/api/v1/groups/{group_id}/members",
        json={
            "resource_type": "vm",
            "cloud_id": "synthetic",
            "region_id": "RegionOne",
            "resource_id": "instance-project-a-2",
        },
        headers=headers,
    )
    members = client.get(
        f"/api/v1/groups/{group_id}/members",
        headers={"x-request-id": "members-after-conflict"},
    )

    assert first.status_code == 200
    assert second.status_code == 409
    assert second.json()["error"]["code"] == "idempotency_key_conflict"
    assert [item["resource_id"] for item in members.json()["items"]] == ["instance-project-a"]


def test_idempotency_key_is_bound_when_add_is_already_a_noop() -> None:
    client, security = _client()
    csrf = _login(client, "operator", "operator-code")
    group_id = _create_group(client, csrf)["group_id"]
    repository = _group_repository_from_state(security)
    repository.add_member(
        group_id=group_id,
        resource_type="vm",
        cloud_id="synthetic",
        region_id="RegionOne",
        resource_id="instance-project-a",
        source="explicit",
        actor_id="mock-user-operator",
    )
    headers = {
        "x-request-id": "member-add-noop-idempotency",
        "x-csrf-token": csrf,
        "idempotency-key": "add-noop-key-secret",
    }

    first = client.post(
        f"/api/v1/groups/{group_id}/members",
        json={
            "resource_type": "vm",
            "cloud_id": "synthetic",
            "region_id": "RegionOne",
            "resource_id": "instance-project-a",
        },
        headers=headers,
    )
    second = client.post(
        f"/api/v1/groups/{group_id}/members",
        json={
            "resource_type": "vm",
            "cloud_id": "synthetic",
            "region_id": "RegionOne",
            "resource_id": "instance-project-a-2",
        },
        headers=headers,
    )

    assert first.status_code == 200
    assert second.status_code == 409
    assert second.json()["error"]["code"] == "idempotency_key_conflict"
    assert [
        member.resource_id for member in repository.list_members(group_id, limit=50)
    ] == ["instance-project-a"]


def test_idempotency_key_is_bound_when_remove_is_already_a_noop() -> None:
    client, security = _client()
    csrf = _login(client, "operator", "operator-code")
    group_id = _create_group(client, csrf)["group_id"]
    repository = _group_repository_from_state(security)
    headers = {
        "x-request-id": "member-remove-noop-idempotency",
        "x-csrf-token": csrf,
        "idempotency-key": "remove-noop-key-secret",
    }

    first = client.delete(
        f"/api/v1/groups/{group_id}/members/vm/synthetic/RegionOne/instance-project-a",
        headers=headers,
    )
    repository.add_member(
        group_id=group_id,
        resource_type="vm",
        cloud_id="synthetic",
        region_id="RegionOne",
        resource_id="instance-project-a-2",
        source="explicit",
        actor_id="mock-user-operator",
    )
    second = client.delete(
        f"/api/v1/groups/{group_id}/members/vm/synthetic/RegionOne/instance-project-a-2",
        headers=headers,
    )

    assert first.status_code == 200
    assert second.status_code == 409
    assert second.json()["error"]["code"] == "idempotency_key_conflict"
    assert [
        member.resource_id for member in repository.list_members(group_id, limit=50)
    ] == ["instance-project-a-2"]


def test_non_admin_cannot_remove_host_member_from_preexisting_group() -> None:
    client, security = _client()
    csrf = _login(client, "operator", "operator-code")
    group_id = _repository_create_group(
        security,
        resource_type="host",
        actor_id="mock-user-operator",
    )
    repository = _group_repository_from_state(security)
    repository.add_member(
        group_id=group_id,
        resource_type="host",
        cloud_id="synthetic",
        region_id="RegionOne",
        resource_id="hypervisor-0001",
        source="explicit",
        actor_id="mock-user-admin",
    )

    response = client.delete(
        f"/api/v1/groups/{group_id}/members/host/synthetic/RegionOne/hypervisor-0001",
        headers={
            "x-request-id": "host-remove-denied",
            "x-csrf-token": csrf,
            "idempotency-key": "host-remove-denied-key",
        },
    )

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "forbidden"
    assert repository.list_members(group_id, limit=50)[0].resource_id == "hypervisor-0001"


def test_mixed_dynamic_group_is_rejected_until_rule_semantics_exist() -> None:
    client, _security = _client()
    csrf = _login(client, "admin", "admin-code")

    response = client.post(
        "/api/v1/groups",
        json={
            "name": "mixed-dynamic",
            "resource_type": "mixed",
            "membership_mode": "dynamic",
            "scope_id": "project-a",
        },
        headers={"x-request-id": "mixed-dynamic", "x-csrf-token": csrf},
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "unsupported_group_mode"


def _client(subject: Subject | None = None) -> tuple[TestClient, SecurityServices]:
    app, security = _app(subject=subject)
    return TestClient(app), security


def _app(subject: Subject | None = None) -> tuple[FastAPI, SecurityServices]:
    def check() -> HealthReport:
        return HealthReport(status="ok", dependencies={})

    security = _custom_security(subject) if subject is not None else build_security_services()
    engine = _engine()
    inventory_repository = _inventory_repository(engine)
    group_repository = GroupRepository(engine=engine)
    security.audit_sink.test_engine = engine
    app = create_app(
        readiness_check=check,
        security_services=security,
        inventory_services=InventoryServices(repository=inventory_repository, engine=engine),
        group_services=GroupServices(
            repository=group_repository,
            inventory_repository=inventory_repository,
        ),
    )
    return app, security


def _login(client: TestClient, login: str, credential: str) -> str:
    response = client.post(
        "/api/v1/session/login",
        json={"login": login, "credential": credential},
        headers={"x-request-id": f"login-{login}"},
    )
    assert response.status_code == 200
    return str(response.json()["csrf"])


def _create_group(client: TestClient, csrf: str) -> dict[str, Any]:
    response = client.post(
        "/api/v1/groups",
        json={"name": "tenant-a", "resource_type": "vm", "membership_mode": "explicit"},
        headers={"x-request-id": "group-create-helper", "x-csrf-token": csrf},
    )
    assert response.status_code == 201
    return dict(response.json())


def _repository_create_group(
    security: SecurityServices,
    *,
    resource_type: str,
    actor_id: str,
) -> str:
    repository = _group_repository_from_state(security)
    group = repository.create_group(
        actor_id=actor_id,
        scope_type="project",
        scope_id="project-a",
        name=f"{resource_type}-group",
        description=None,
        resource_type=resource_type,
        membership_mode="explicit",
    )
    return group.group_id


def _group_repository_from_state(security: SecurityServices) -> GroupRepository:
    engine = security.audit_sink.test_engine
    assert isinstance(engine, Engine)
    return GroupRepository(engine=engine)


class _CustomIdentityProvider:
    def __init__(self, subject: Subject) -> None:
        self._subject = subject

    def authenticate(self, request: LoginRequest) -> LoginResult:
        assert request.login == "custom"
        assert request.credential == "custom-code"
        return LoginResult(subject=self._subject, authentication_method="mock")


def _custom_security(subject: Subject) -> SecurityServices:
    clock = ManualClock()
    return SecurityServices(
        identity_provider=_CustomIdentityProvider(subject),
        session_manager=SessionManager(clock=clock),
        audit_sink=InMemoryAuditSink(),
        policy_service=PolicyService(),
        clock=clock,
        session_cookie_secure=False,
        session_cookie_samesite="lax",
        trusted_origins=frozenset({"http://localhost", "http://127.0.0.1", "http://testserver"}),
    )


def _engine() -> Engine:
    engine = sa.create_engine(
        "sqlite+pysqlite:///:memory:",
        future=True,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    inventory_schema.metadata.create_all(engine)
    group_schema.metadata.create_all(engine)
    _seed_inventory(engine)
    return engine


def _inventory_repository(engine: Engine) -> InventoryRepository:
    return InventoryRepository(
        engine=engine,
        cursor_codec=CursorCodec(signing_key="dev-inventory-cursor-key"),
        default_limit=50,
        max_limit=200,
        stale_after_seconds=900,
    )


def _seed_inventory(engine: Engine) -> None:
    now = datetime(2026, 6, 21, 10, 0, tzinfo=UTC)
    with engine.begin() as connection:
        connection.execute(
            inventory_schema.clouds.insert(),
            {
                "cloud_id": "synthetic",
                "display_name": "synthetic",
                "enabled": True,
                "created_at": now,
                "updated_at": now,
                "last_sync_at": now,
            },
        )
        connection.execute(
            inventory_schema.regions.insert(),
            {
                "cloud_id": "synthetic",
                "region_id": "RegionOne",
                "display_name": "RegionOne",
                "enabled": True,
                "last_successful_sync_at": now,
                "last_attempted_sync_at": now,
                "sync_status": "ok",
            },
        )
        connection.execute(
            inventory_schema.instances.insert(),
            [
                _instance_row(
                    now=now,
                    instance_id="instance-project-a",
                    name="vm-a",
                    project_id="project-a",
                ),
                _instance_row(
                    now=now,
                    instance_id="instance-project-a-2",
                    name="vm-a-2",
                    project_id="project-a",
                ),
                _instance_row(
                    now=now,
                    instance_id="instance-project-a-error",
                    name="vm-a-error",
                    project_id="project-a",
                    status="ERROR",
                ),
                _instance_row(
                    now=now,
                    instance_id="instance-project-b",
                    name="vm-b",
                    project_id="project-b",
                ),
                _instance_row(
                    now=now,
                    instance_id="instance-deleted",
                    name="vm-deleted",
                    project_id="project-a",
                    deleted_at=now,
                ),
            ],
        )
        connection.execute(
            inventory_schema.hypervisors.insert(),
            _hypervisor_row(now=now, hypervisor_id="hypervisor-0001"),
        )


def _instance_row(
    *,
    now: datetime,
    instance_id: str,
    name: str,
    project_id: str,
    status: str = "ACTIVE",
    deleted_at: datetime | None = None,
) -> dict[str, Any]:
    return {
        "cloud_id": "synthetic",
        "region_id": "RegionOne",
        "instance_id": instance_id,
        "name": name,
        "project_id": project_id,
        "user_id": "user-0001",
        "status": status,
        "power_state": "running",
        "task_state": None,
        "vm_state": "active",
        "host_name": "compute-a",
        "hypervisor_id": "hypervisor-0001",
        "availability_zone": "nova",
        "flavor_id": "flavor-small",
        "vcpus": 2,
        "ram_mb": 4096,
        "disk_gb": 40,
        "image_id": "image-0001",
        "boot_volume_id": None,
        "addresses_json": {"private": ["10.0.0.10"]},
        "source_created_at": now - timedelta(days=1),
        "source_updated_at": now,
        "observed_at": now,
        "sync_generation": 1,
        "sync_status": "ok",
        "deleted_at": deleted_at,
        "change_hash": f"hash-{instance_id}",
    }


def _hypervisor_row(*, now: datetime, hypervisor_id: str) -> dict[str, Any]:
    return {
        "cloud_id": "synthetic",
        "region_id": "RegionOne",
        "hypervisor_id": hypervisor_id,
        "host_name": "compute-a",
        "service_id": f"service-{hypervisor_id}",
        "service_status": "enabled",
        "service_state": "up",
        "hypervisor_type": "QEMU",
        "hypervisor_version": "9.0",
        "availability_zone": "nova",
        "aggregates_json": ["az-nova"],
        "vcpus_total": 64,
        "vcpus_used": 8,
        "ram_mb_total": 262144,
        "ram_mb_used": 32768,
        "disk_gb_total": 4000,
        "disk_gb_used": 1000,
        "running_vms": 4,
        "disabled_reason": None,
        "maintenance_status": None,
        "observed_at": now,
        "sync_generation": 1,
        "sync_status": "ok",
        "deleted_at": None,
        "change_hash": f"hash-{hypervisor_id}",
    }
