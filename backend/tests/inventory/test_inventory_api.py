from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, cast

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
from cloud_ui.inventory import schema
from cloud_ui.inventory.cursor import CursorCodec
from cloud_ui.inventory.repository import InventoryRepository
from cloud_ui.inventory.routes import InventoryServices
from cloud_ui.security.audit import InMemoryAuditSink
from cloud_ui.security.clock import ManualClock
from cloud_ui.security.dependencies import SecurityServices, build_security_services
from cloud_ui.security.identity import LoginRequest, LoginResult, Subject
from cloud_ui.security.rbac import PolicyService
from cloud_ui.security.sessions import SessionManager


def test_instance_list_requires_session() -> None:
    client, _security = _client()

    response = client.get("/api/v1/instances")

    assert response.status_code == 401


def test_auditor_without_instance_read_gets_403() -> None:
    client, security = _client()
    _login(client, "auditor", "auditor-code")

    response = client.get("/api/v1/instances", headers={"x-request-id": "auditor-denied"})

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "forbidden"
    assert any(
        event.action == "authorization.denied"
        and event.actor_id == "mock-user-auditor"
        and event.metadata["code"] == "forbidden"
        for event in security.audit_sink.events
    )


def test_instance_list_returns_page_freshness_and_cursor() -> None:
    client, _security = _client()
    _login(client, "viewer", "viewer-code")

    response = client.get("/api/v1/instances?limit=1&status=ACTIVE&sort=name.asc")

    assert response.status_code == 200
    payload = response.json()
    assert [item["name"] for item in payload["items"]] == ["vm-a"]
    assert payload["limit"] == 1
    assert payload["sort"] == "name.asc"
    assert payload["next_cursor"]
    assert payload["partial"] is False
    assert payload["freshness"]["observed_at"] == "2026-06-21T10:00:00Z"
    assert payload["freshness"]["last_successful_sync_at"] == "2026-06-21T10:00:00Z"


def test_instance_list_repository_failure_returns_safe_503_json() -> None:
    repository = cast(InventoryRepository, FailingInventoryRepository())
    client, _security = _client(repository=repository, raise_server_exceptions=False)
    _login(client, "viewer", "viewer-code")

    response = client.get("/api/v1/instances", headers={"x-request-id": "repo-failure"})

    assert response.status_code == 503
    assert response.json() == {
        "error": {
            "code": "inventory_unavailable",
            "message": "Inventory API временно недоступен",
            "request_id": "repo-failure",
        }
    }
    assert "raw database failure" not in response.text


def test_instance_detail_repository_failure_returns_safe_503_json() -> None:
    repository = cast(InventoryRepository, FailingInventoryRepository())
    client, _security = _client(repository=repository, raise_server_exceptions=False)
    _login(client, "viewer", "viewer-code")

    response = client.get(
        "/api/v1/instances/synthetic/RegionOne/instance-0001",
        headers={"x-request-id": "repo-detail-failure"},
    )

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "inventory_unavailable"
    assert response.json()["error"]["request_id"] == "repo-detail-failure"
    assert "raw database failure" not in response.text


def test_cursor_tampering_returns_safe_400() -> None:
    client, _security = _client()
    _login(client, "viewer", "viewer-code")

    response = client.get(
        "/api/v1/instances?cursor=not-valid",
        headers={"x-request-id": "tampered-cursor"},
    )

    assert response.status_code == 400
    assert response.json() == {
        "error": {
            "code": "cursor_tampered",
            "message": "Некорректный cursor",
            "request_id": "tampered-cursor",
        }
    }


def test_instance_list_filters_by_q_query_parameter() -> None:
    client, _security = _client()
    _login(client, "viewer", "viewer-code")

    response = client.get("/api/v1/instances?q=vm-a&limit=50")

    assert response.status_code == 200
    assert [item["name"] for item in response.json()["items"]] == ["vm-a"]


def test_hypervisor_list_filters_by_q_query_parameter() -> None:
    client, _security = _client()
    _login(client, "viewer", "viewer-code")

    response = client.get("/api/v1/hypervisors?q=COMPUTE-Z&limit=50")

    assert response.status_code == 200
    assert [item["host_name"] for item in response.json()["items"]] == ["compute-z"]


def test_instance_list_filters_by_authorized_group() -> None:
    client, _security = _client()
    _login(client, "operator", "operator-code")

    response = client.get(
        "/api/v1/instances?group_id=group-operator-vms&sort=name.asc",
        headers={"x-request-id": "instances-by-group"},
    )

    assert response.status_code == 200
    assert [item["instance_id"] for item in response.json()["items"]] == [
        "instance-0001",
        "instance-0003",
    ]


def test_instance_group_filter_requires_group_access() -> None:
    client, security = _client()
    _login(client, "operator", "operator-code")

    response = client.get(
        "/api/v1/instances?group_id=group-other-owner",
        headers={"x-request-id": "instances-group-denied"},
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "group_not_found"
    assert any(
        event.action == "authorization.denied"
        and event.actor_id == "mock-user-operator"
        and event.metadata["reason"] == "group_access_denied"
        for event in security.audit_sink.events
    )


def test_instance_group_filter_requires_group_read_capability() -> None:
    client, security = _client(
        subject=Subject(
            subject_id="mock-user-operator",
            display_name="Inventory Only",
            subject_type="human",
            scope_type="project",
            scope_id="project-a",
            roles=frozenset({"inventory_reader"}),
            capabilities=frozenset({"instance.read"}),
        )
    )
    _login(client, "custom", "custom-code")

    response = client.get(
        "/api/v1/instances?group_id=group-operator-vms",
        headers={"x-request-id": "instances-group-without-group-read"},
    )

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "forbidden"
    assert any(
        event.action == "authorization.denied"
        and event.actor_id == "mock-user-operator"
        and event.metadata["capability"] == "group.read"
        for event in security.audit_sink.events
    )


def test_hypervisor_group_filter_requires_group_read_capability() -> None:
    client, security = _client(
        subject=Subject(
            subject_id="mock-user-admin",
            display_name="Host Inventory Only",
            subject_type="human",
            scope_type="system",
            scope_id=None,
            roles=frozenset({"portal_admin"}),
            capabilities=frozenset({"hypervisor.read"}),
        )
    )
    _login(client, "custom", "custom-code")

    response = client.get(
        "/api/v1/hypervisors?group_id=group-admin-hosts",
        headers={"x-request-id": "hypervisors-group-without-group-read"},
    )

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "forbidden"
    assert any(
        event.action == "authorization.denied"
        and event.actor_id == "mock-user-admin"
        and event.metadata["capability"] == "group.read"
        for event in security.audit_sink.events
    )


def test_instance_group_filter_rejects_cursor_from_different_group() -> None:
    client, _security = _client()
    _login(client, "operator", "operator-code")
    first = client.get(
        "/api/v1/instances?group_id=group-operator-vms&limit=1&sort=name.asc",
        headers={"x-request-id": "instances-group-cursor-one"},
    )
    assert first.status_code == 200
    cursor = first.json()["next_cursor"]
    assert cursor

    response = client.get(
        f"/api/v1/instances?group_id=group-operator-other&limit=1&sort=name.asc&cursor={cursor}",
        headers={"x-request-id": "instances-group-cursor-two"},
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "cursor_tampered"


def test_instance_list_limit_response_matches_injected_service_max_limit() -> None:
    client, _security = _client(
        repository=_repository(_engine(), max_limit=1),
        inventory_max_limit=1,
    )
    _login(client, "viewer", "viewer-code")

    response = client.get("/api/v1/instances?limit=50&sort=name.asc")

    assert response.status_code == 200
    payload = response.json()
    assert payload["limit"] == 1
    assert len(payload["items"]) == 1


def test_instance_list_supports_source_updated_at_sort() -> None:
    client, _security = _client()
    _login(client, "viewer", "viewer-code")

    response = client.get("/api/v1/instances?limit=2&sort=source_updated_at.asc")

    assert response.status_code == 200
    payload = response.json()
    assert payload["sort"] == "source_updated_at.asc"
    assert [item["instance_id"] for item in payload["items"]] == [
        "instance-0002",
        "instance-0001",
    ]


def test_instance_refresh_requires_csrf_and_records_audit() -> None:
    client, security = _client()
    csrf = _login(client, "operator", "operator-code")
    idempotency_key = "refresh-key-secret-canary"

    csrf_missing_response = client.post(
        "/api/v1/instances/synthetic/RegionOne/instance-0001/refresh",
        headers={"x-request-id": "refresh-without-csrf"},
    )

    assert csrf_missing_response.status_code == 403
    assert csrf_missing_response.json()["error"]["code"] == "csrf_failed"

    missing_idempotency_response = client.post(
        "/api/v1/instances/synthetic/RegionOne/instance-0001/refresh",
        headers={"x-request-id": "refresh-without-idempotency", "x-csrf-token": csrf},
    )

    assert missing_idempotency_response.status_code == 400
    assert missing_idempotency_response.json()["error"]["code"] == "idempotency_key_required"
    assert (
        missing_idempotency_response.json()["error"]["request_id"]
        == "refresh-without-idempotency"
    )

    accepted_response = client.post(
        "/api/v1/instances/synthetic/RegionOne/instance-0001/refresh",
        headers={
            "x-request-id": "refresh-accepted",
            "x-csrf-token": csrf,
            "idempotency-key": idempotency_key,
        },
    )
    repeated_response = client.post(
        "/api/v1/instances/synthetic/RegionOne/instance-0001/refresh",
        headers={
            "x-request-id": "refresh-repeated",
            "x-csrf-token": csrf,
            "idempotency-key": idempotency_key,
        },
    )

    assert accepted_response.status_code == 200
    assert repeated_response.status_code == 200
    accepted_payload = accepted_response.json()
    repeated_payload = repeated_response.json()
    assert accepted_payload == {
        "status": "accepted",
        "operation_id": accepted_payload["operation_id"],
        "target": {
            "cloud_id": "synthetic",
            "region_id": "RegionOne",
            "instance_id": "instance-0001",
        },
    }
    assert accepted_payload["operation_id"]
    assert repeated_payload["operation_id"] == accepted_payload["operation_id"]
    audit_events = [
        event
        for event in security.audit_sink.events
        if event.action == "instance.refresh.requested"
        and event.actor_id == "mock-user-operator"
        and event.target_id == "synthetic/RegionOne/instance-0001"
    ]
    assert audit_events
    assert audit_events[-1].metadata["operation_id"] == accepted_payload["operation_id"]
    assert idempotency_key not in repr(audit_events[-1].metadata)


def test_instance_refresh_operation_id_is_actor_scoped() -> None:
    client, security = _client()
    idempotency_key = "shared-refresh-key-secret-canary"

    operator_csrf = _login(client, "operator", "operator-code")
    operator_response = client.post(
        "/api/v1/instances/synthetic/RegionOne/instance-0001/refresh",
        headers={
            "x-request-id": "operator-refresh",
            "x-csrf-token": operator_csrf,
            "idempotency-key": idempotency_key,
        },
    )

    client.cookies.clear()
    admin_csrf = _login(client, "admin", "admin-code")
    admin_response = client.post(
        "/api/v1/instances/synthetic/RegionOne/instance-0001/refresh",
        headers={
            "x-request-id": "admin-refresh",
            "x-csrf-token": admin_csrf,
            "idempotency-key": idempotency_key,
        },
    )

    assert operator_response.status_code == 200
    assert admin_response.status_code == 200
    operator_operation_id = operator_response.json()["operation_id"]
    admin_operation_id = admin_response.json()["operation_id"]
    assert operator_operation_id != admin_operation_id
    assert idempotency_key not in operator_response.text
    assert idempotency_key not in admin_response.text
    assert idempotency_key not in repr(
        [event.metadata for event in security.audit_sink.events]
    )


def test_instance_refresh_denies_viewer_without_refresh_capability() -> None:
    client, security = _client()
    csrf = _login(client, "viewer", "viewer-code")

    response = client.post(
        "/api/v1/instances/synthetic/RegionOne/instance-0001/refresh",
        headers={"x-request-id": "viewer-refresh-denied", "x-csrf-token": csrf},
    )

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "forbidden"
    assert any(
        event.action == "authorization.denied"
        and event.actor_id == "mock-user-viewer"
        and event.target_id == "synthetic/RegionOne/instance-0001"
        and event.metadata["code"] == "forbidden"
        and event.metadata["capability"] == "instance.refresh"
        for event in security.audit_sink.events
    )


def test_hypervisor_list_and_detail_require_hypervisor_read() -> None:
    client, security = _client()
    _login(client, "viewer", "viewer-code")

    list_response = client.get("/api/v1/hypervisors?limit=1&sort=host_name.asc")
    detail_response = client.get("/api/v1/hypervisors/synthetic/RegionOne/hypervisor-0001")

    assert list_response.status_code == 200
    list_payload = list_response.json()
    assert [item["host_name"] for item in list_payload["items"]] == ["compute-a"]
    assert list_payload["limit"] == 1
    assert list_payload["sort"] == "host_name.asc"
    assert detail_response.status_code == 200
    assert detail_response.json()["hypervisor_id"] == "hypervisor-0001"

    client.cookies.clear()
    _login(client, "auditor", "auditor-code")
    denied_response = client.get(
        "/api/v1/hypervisors",
        headers={"x-request-id": "auditor-hypervisor-denied"},
    )

    assert denied_response.status_code == 403
    assert denied_response.json()["error"]["code"] == "forbidden"
    assert any(
        event.action == "authorization.denied"
        and event.actor_id == "mock-user-auditor"
        and event.metadata["capability"] == "hypervisor.read"
        for event in security.audit_sink.events
    )

    detail_denied_response = client.get(
        "/api/v1/hypervisors/synthetic/RegionOne/hyp-0001",
        headers={"x-request-id": "auditor-hypervisor-detail-denied"},
    )

    assert detail_denied_response.status_code == 403
    assert detail_denied_response.json()["error"]["code"] == "forbidden"
    assert any(
        event.action == "authorization.denied"
        and event.actor_id == "mock-user-auditor"
        and event.target_id == "synthetic/RegionOne/hyp-0001"
        and event.metadata["code"] == "forbidden"
        and event.metadata["capability"] == "hypervisor.read"
        for event in security.audit_sink.events
    )


def test_openapi_contains_inventory_paths() -> None:
    app, _security = _app()

    openapi_schema = app.openapi()

    assert "/api/v1/instances" in openapi_schema["paths"]
    assert "/api/v1/hypervisors" in openapi_schema["paths"]
    instance_parameters = {
        parameter["name"]: parameter
        for parameter in openapi_schema["paths"]["/api/v1/instances"]["get"]["parameters"]
    }
    hypervisor_parameters = {
        parameter["name"]: parameter
        for parameter in openapi_schema["paths"]["/api/v1/hypervisors"]["get"]["parameters"]
    }
    assert instance_parameters["limit"]["schema"]["type"] == "integer"
    assert instance_parameters["limit"]["schema"]["minimum"] == 1
    assert hypervisor_parameters["limit"]["schema"]["type"] == "integer"
    assert hypervisor_parameters["limit"]["schema"]["minimum"] == 1
    instance_response = openapi_schema["components"]["schemas"]["InstanceListResponse"][
        "properties"
    ]
    hypervisor_response = openapi_schema["components"]["schemas"]["HypervisorListResponse"][
        "properties"
    ]
    assert instance_response["limit"]["type"] == "integer"
    assert instance_response["sort"]["type"] == "string"
    assert hypervisor_response["limit"]["type"] == "integer"
    assert hypervisor_response["sort"]["type"] == "string"


def test_inventory_disabled_module_descriptors_include_future_contract() -> None:
    client, _security = _client()
    _login(client, "viewer", "viewer-code")

    response = client.get("/api/v1/inventory/modules")

    assert response.status_code == 200
    modules = {module["key"]: module for module in response.json()["modules"]}
    disabled_contracts = {
        "compute_services": ("compute_service.read", "/api/v1/compute-services"),
        "network_agents": ("network_agent.read", "/api/v1/network-agents"),
        "volume_services": ("volume_service.read", "/api/v1/volume-services"),
        "image_tasks": ("image_task.read", "/api/v1/image-tasks"),
        "topology": ("topology.read", "/api/v1/topology"),
        "capacity": ("capacity.read", "/api/v1/capacity"),
    }
    for key, (required_capability, path) in disabled_contracts.items():
        descriptor = modules[key]
        assert descriptor["enabled"] is False
        assert descriptor["status"] == "disabled"
        assert descriptor["reason"] == "module_not_implemented"
        assert descriptor["required_capability"] == required_capability
        assert descriptor["path"] == path


def test_inventory_routes_do_not_import_openstack_http_transport() -> None:
    routes_path = Path(__file__).parents[2] / "src" / "cloud_ui" / "inventory" / "routes.py"

    routes_text = routes_path.read_text(encoding="utf-8")

    assert "httpx" not in routes_text
    assert "OpenStackHttpClient" not in routes_text


class FailingInventoryRepository:
    def list_instances(self, **_kwargs: Any) -> Any:
        raise RuntimeError("raw database failure should not leak")

    def get_instance(self, *_args: Any) -> Any:
        raise RuntimeError("raw database failure should not leak")

    def list_hypervisors(self, **_kwargs: Any) -> Any:
        raise RuntimeError("raw database failure should not leak")

    def get_hypervisor(self, *_args: Any) -> Any:
        raise RuntimeError("raw database failure should not leak")


def _client(
    *,
    repository: InventoryRepository | None = None,
    inventory_default_limit: int = 50,
    inventory_max_limit: int = 200,
    operation_signing_key: str = "dev-inventory-operation-signing-key",
    raise_server_exceptions: bool = True,
    subject: Subject | None = None,
) -> tuple[TestClient, SecurityServices]:
    app, security = _app(
        repository=repository,
        inventory_default_limit=inventory_default_limit,
        inventory_max_limit=inventory_max_limit,
        operation_signing_key=operation_signing_key,
        subject=subject,
    )
    return TestClient(app, raise_server_exceptions=raise_server_exceptions), security


def _app(
    *,
    repository: InventoryRepository | None = None,
    inventory_default_limit: int = 50,
    inventory_max_limit: int = 200,
    operation_signing_key: str = "dev-inventory-operation-signing-key",
    subject: Subject | None = None,
) -> tuple[FastAPI, SecurityServices]:
    def check() -> HealthReport:
        return HealthReport(status="ok", dependencies={})

    security = _custom_security(subject) if subject is not None else build_security_services()
    engine = _engine()
    inventory_repository = repository or _repository(engine)
    repository_engine = inventory_repository.engine if repository is None else None
    app = create_app(
        readiness_check=check,
        security_services=security,
        inventory_services=InventoryServices(
            repository=inventory_repository,
            engine=repository_engine,
            default_limit=inventory_default_limit,
            max_limit=inventory_max_limit,
            operation_signing_key=operation_signing_key,
        ),
        group_services=GroupServices(
            repository=GroupRepository(engine=engine),
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
    schema.metadata.create_all(engine)
    group_schema.metadata.create_all(engine)
    _seed_inventory(engine)
    return engine


def _repository(
    engine: Engine,
    *,
    default_limit: int = 50,
    max_limit: int = 200,
) -> InventoryRepository:
    return InventoryRepository(
        engine=engine,
        cursor_codec=CursorCodec(signing_key="dev-inventory-cursor-key"),
        default_limit=default_limit,
        max_limit=max_limit,
        stale_after_seconds=900,
    )


def _seed_inventory(engine: Engine) -> None:
    now = datetime(2026, 6, 21, 10, 0, tzinfo=UTC)
    with engine.begin() as connection:
        connection.execute(
            schema.clouds.insert(),
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
            schema.regions.insert(),
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
            schema.instances.insert(),
            [
                _instance_row(now=now, instance_id="instance-0001", name="vm-a"),
                _instance_row(
                    now=now,
                    instance_id="instance-0002",
                    name="vm-c",
                    source_updated_at=now - timedelta(hours=1),
                ),
                _instance_row(
                    now=now,
                    instance_id="instance-0003",
                    name="vm-error",
                    status="ERROR",
                ),
            ],
        )
        connection.execute(
            schema.hypervisors.insert(),
            [
                _hypervisor_row(
                    now=now,
                    hypervisor_id="hypervisor-0002",
                    host_name="compute-z",
                ),
                _hypervisor_row(
                    now=now,
                    hypervisor_id="hypervisor-0001",
                    host_name="compute-a",
                ),
            ],
        )
        connection.execute(
            group_schema.resource_groups.insert(),
            [
                _group_row("group-operator-vms", "mock-user-operator"),
                _group_row("group-operator-other", "mock-user-operator"),
                _group_row("group-other-owner", "mock-user-other"),
                _group_row(
                    "group-admin-hosts",
                    "mock-user-admin",
                    resource_type="host",
                    scope_id="project-a",
                ),
            ],
        )
        connection.execute(
            group_schema.resource_group_members.insert(),
            [
                _member_row("group-operator-vms", "vm", "instance-0001"),
                _member_row("group-operator-vms", "vm", "instance-0003"),
                _member_row("group-operator-other", "vm", "instance-0002"),
                _member_row("group-other-owner", "vm", "instance-0003"),
                _member_row("group-admin-hosts", "host", "hypervisor-0001"),
            ],
        )


def _instance_row(
    *,
    now: datetime,
    instance_id: str,
    name: str,
    status: str = "ACTIVE",
    source_updated_at: datetime | None = None,
) -> dict[str, Any]:
    return {
        "cloud_id": "synthetic",
        "region_id": "RegionOne",
        "instance_id": instance_id,
        "name": name,
        "project_id": "project-0001",
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
        "source_updated_at": source_updated_at or now,
        "observed_at": now,
        "sync_generation": 1,
        "sync_status": "ok",
        "deleted_at": None,
        "change_hash": f"hash-{instance_id}",
    }


def _group_row(
    group_id: str,
    owner_subject_id: str,
    *,
    resource_type: str = "vm",
    scope_id: str = "project-a",
) -> dict[str, Any]:
    now = datetime(2026, 6, 21, 10, 0, tzinfo=UTC)
    return {
        "group_id": group_id,
        "name": group_id,
        "description": None,
        "resource_type": resource_type,
        "scope_type": "project",
        "scope_id": scope_id,
        "membership_mode": "explicit",
        "rule_version": 1,
        "rule_body_json": None,
        "owner_subject_id": owner_subject_id,
        "revision": 1,
        "created_at": now,
        "updated_at": now,
        "deleted_at": None,
    }


def _member_row(group_id: str, resource_type: str, resource_id: str) -> dict[str, Any]:
    now = datetime(2026, 6, 21, 10, 0, tzinfo=UTC)
    return {
        "group_id": group_id,
        "resource_type": resource_type,
        "cloud_id": "synthetic",
        "region_id": "RegionOne",
        "resource_id": resource_id,
        "source": "explicit",
        "added_by": "mock-user-operator",
        "added_at": now,
        "expires_at": None,
    }


def _hypervisor_row(
    *,
    now: datetime,
    hypervisor_id: str,
    host_name: str,
) -> dict[str, Any]:
    return {
        "cloud_id": "synthetic",
        "region_id": "RegionOne",
        "hypervisor_id": hypervisor_id,
        "host_name": host_name,
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
