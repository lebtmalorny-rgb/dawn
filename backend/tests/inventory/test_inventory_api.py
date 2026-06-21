from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import sqlalchemy as sa
from fastapi.testclient import TestClient
from sqlalchemy.engine import Engine
from sqlalchemy.pool import StaticPool

from cloud_ui.api import create_app
from cloud_ui.health import HealthReport
from cloud_ui.inventory import schema
from cloud_ui.inventory.cursor import CursorCodec
from cloud_ui.inventory.repository import InventoryRepository
from cloud_ui.inventory.routes import InventoryServices
from cloud_ui.security.dependencies import SecurityServices, build_security_services


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
    assert payload["next_cursor"]
    assert payload["partial"] is False
    assert payload["freshness"]["observed_at"] == "2026-06-21T10:00:00Z"
    assert payload["freshness"]["last_successful_sync_at"] == "2026-06-21T10:00:00Z"


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


def test_instance_refresh_requires_csrf_and_records_audit() -> None:
    client, security = _client()
    csrf = _login(client, "operator", "operator-code")

    csrf_missing_response = client.post(
        "/api/v1/instances/synthetic/RegionOne/instance-0001/refresh",
        headers={"x-request-id": "refresh-without-csrf"},
    )

    assert csrf_missing_response.status_code == 403
    assert csrf_missing_response.json()["error"]["code"] == "csrf_failed"

    accepted_response = client.post(
        "/api/v1/instances/synthetic/RegionOne/instance-0001/refresh",
        headers={"x-request-id": "refresh-accepted", "x-csrf-token": csrf},
    )

    assert accepted_response.status_code == 200
    assert accepted_response.json() == {
        "status": "accepted",
        "target": {
            "cloud_id": "synthetic",
            "region_id": "RegionOne",
            "instance_id": "instance-0001",
        },
    }
    assert any(
        event.action == "instance.refresh.requested"
        and event.actor_id == "mock-user-operator"
        and event.target_id == "synthetic/RegionOne/instance-0001"
        for event in security.audit_sink.events
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
    assert [item["host_name"] for item in list_response.json()["items"]] == ["compute-a"]
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
    client, _security = _client()

    openapi_schema = client.app.openapi()

    assert "/api/v1/instances" in openapi_schema["paths"]
    assert "/api/v1/hypervisors" in openapi_schema["paths"]


def test_inventory_routes_do_not_import_openstack_http_transport() -> None:
    routes_path = Path(__file__).parents[2] / "src" / "cloud_ui" / "inventory" / "routes.py"

    routes_text = routes_path.read_text(encoding="utf-8")

    assert "httpx" not in routes_text
    assert "OpenStackHttpClient" not in routes_text


def _client() -> tuple[TestClient, SecurityServices]:
    def check() -> HealthReport:
        return HealthReport(status="ok", dependencies={})

    security = build_security_services()
    app = create_app(
        readiness_check=check,
        security_services=security,
        inventory_services=InventoryServices(repository=_repository(_engine())),
    )
    return TestClient(app), security


def _login(client: TestClient, login: str, credential: str) -> str:
    response = client.post(
        "/api/v1/session/login",
        json={"login": login, "credential": credential},
        headers={"x-request-id": f"login-{login}"},
    )
    assert response.status_code == 200
    return str(response.json()["csrf"])


def _engine() -> Engine:
    engine = sa.create_engine(
        "sqlite+pysqlite:///:memory:",
        future=True,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    schema.metadata.create_all(engine)
    _seed_inventory(engine)
    return engine


def _repository(engine: Engine) -> InventoryRepository:
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
                _instance_row(now=now, instance_id="instance-0002", name="vm-c"),
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


def _instance_row(
    *,
    now: datetime,
    instance_id: str,
    name: str,
    status: str = "ACTIVE",
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
        "source_updated_at": now,
        "observed_at": now,
        "sync_generation": 1,
        "sync_status": "ok",
        "deleted_at": None,
        "change_hash": f"hash-{instance_id}",
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
