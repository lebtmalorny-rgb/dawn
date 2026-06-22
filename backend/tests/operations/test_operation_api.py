from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import sqlalchemy as sa
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.engine import Engine
from sqlalchemy.pool import StaticPool

from cloud_ui.api import create_app
from cloud_ui.health import HealthReport
from cloud_ui.inventory import schema as inventory_schema
from cloud_ui.inventory.cursor import CursorCodec
from cloud_ui.inventory.repository import InventoryRepository
from cloud_ui.inventory.routes import InventoryServices
from cloud_ui.operations import schema as operation_schema
from cloud_ui.operations.catalog import build_builtin_workflow_catalog
from cloud_ui.operations.repository import OperationRepository
from cloud_ui.operations.routes import OperationServices
from cloud_ui.security.dependencies import SecurityServices, build_security_services


def test_lists_allowlisted_workflow_definitions() -> None:
    client, _security, _repository = _client()
    _login(client, "operator", "operator-code")

    response = client.get(
        "/api/v1/workflow-definitions",
        headers={"x-request-id": "workflow-list"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert [item["workflow_key"] for item in payload["items"]] == [
        "maintenance-host-precheck"
    ]
    assert payload["items"][0]["mistral_workflow_name"] is None
    assert payload["items"][0]["required_capability"] == "workflow.execute.maintenance-host"


def test_submit_host_precheck_returns_202_after_durable_operation() -> None:
    client, security, repository = _client()
    csrf = _login(client, "operator", "operator-code")

    response = _submit_precheck(client, csrf, idempotency_key="precheck-key")

    assert response.status_code == 202
    payload = response.json()
    assert payload["status"] == "accepted"
    assert payload["operation_id"].startswith("operation-")
    operation = repository.get_operation(payload["operation_id"])
    assert operation is not None
    assert operation.status == "accepted"
    assert operation.workflow_key == "maintenance-host-precheck"
    assert operation.input_json == {"reason": "replace host firmware", "dry_run": True}
    assert operation.target_snapshot_json[0]["snapshot"]["host_name"] == "compute-a"
    outbox_rows = _rows(repository.engine, operation_schema.operation_outbox)
    assert [row["operation_id"] for row in outbox_rows] == [payload["operation_id"]]
    assert any(
        event.action == "operation.accepted"
        and event.target_id == payload["operation_id"]
        and "precheck-key" not in repr(event.metadata)
        for event in security.audit_sink.events
    )


def test_submit_replays_same_idempotency_key_and_body() -> None:
    client, _security, _repository = _client()
    csrf = _login(client, "operator", "operator-code")

    first = _submit_precheck(client, csrf, idempotency_key="same-key")
    second = _submit_precheck(client, csrf, idempotency_key="same-key")

    assert first.status_code == 202
    assert second.status_code == 202
    assert second.json() == first.json()


def test_submit_same_idempotency_key_with_different_body_returns_409() -> None:
    client, _security, _repository = _client()
    csrf = _login(client, "operator", "operator-code")
    first = _submit_precheck(client, csrf, idempotency_key="conflict-key")

    second = client.post(
        "/api/v1/operations",
        json=_operation_body(reason="different maintenance reason"),
        headers={
            "x-request-id": "operation-conflict",
            "x-csrf-token": csrf,
            "idempotency-key": "conflict-key",
        },
    )

    assert first.status_code == 202
    assert second.status_code == 409
    assert second.json()["error"]["code"] == "idempotency_key_conflict"


def test_submit_rejects_arbitrary_workflow_input_property() -> None:
    client, _security, _repository = _client()
    csrf = _login(client, "operator", "operator-code")
    body = _operation_body()
    body["input"]["mistral_workflow_name"] = "evil.workflow"

    response = client.post(
        "/api/v1/operations",
        json=body,
        headers={
            "x-request-id": "operation-arbitrary-workflow",
            "x-csrf-token": csrf,
            "idempotency-key": "arbitrary-key",
        },
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "invalid_workflow_input"


def test_submit_requires_csrf_and_idempotency_key() -> None:
    client, _security, _repository = _client()
    csrf = _login(client, "operator", "operator-code")

    missing_csrf = client.post(
        "/api/v1/operations",
        json=_operation_body(),
        headers={"x-request-id": "operation-no-csrf", "idempotency-key": "key"},
    )
    missing_idempotency = client.post(
        "/api/v1/operations",
        json=_operation_body(),
        headers={"x-request-id": "operation-no-idempotency", "x-csrf-token": csrf},
    )

    assert missing_csrf.status_code == 403
    assert missing_csrf.json()["error"]["code"] == "csrf_failed"
    assert missing_idempotency.status_code == 400
    assert missing_idempotency.json()["error"]["code"] == "idempotency_key_required"


def test_auditor_without_execute_capability_cannot_submit_operation() -> None:
    client, security, _repository = _client()
    csrf = _login(client, "auditor", "auditor-code")

    response = _submit_precheck(client, csrf, idempotency_key="auditor-key")

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "forbidden"
    assert any(
        event.action == "authorization.denied"
        and event.actor_id == "mock-user-auditor"
        and event.metadata["capability"] == "workflow.execute.maintenance-host"
        for event in security.audit_sink.events
    )


def test_submit_missing_host_target_returns_safe_404() -> None:
    client, _security, _repository = _client()
    csrf = _login(client, "operator", "operator-code")
    body = _operation_body(resource_id="missing-hypervisor")

    response = client.post(
        "/api/v1/operations",
        json=body,
        headers={
            "x-request-id": "operation-missing-target",
            "x-csrf-token": csrf,
            "idempotency-key": "missing-target-key",
        },
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "target_not_found"


def test_operation_detail_returns_timeline_for_authorized_actor() -> None:
    client, _security, _repository = _client()
    csrf = _login(client, "operator", "operator-code")
    submit = _submit_precheck(client, csrf, idempotency_key="detail-key")
    operation_id = submit.json()["operation_id"]

    response = client.get(
        f"/api/v1/operations/{operation_id}",
        headers={"x-request-id": "operation-detail"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["operation_id"] == operation_id
    assert payload["status"] == "accepted"
    assert payload["events"][0]["event_type"] == "operation.accepted"
    assert payload["external_execution_id"] is None


def _client() -> tuple[TestClient, SecurityServices, OperationRepository]:
    app, security, repository = _app()
    return TestClient(app), security, repository


def _app() -> tuple[FastAPI, SecurityServices, OperationRepository]:
    def check() -> HealthReport:
        return HealthReport(status="ok", dependencies={})

    security = build_security_services()
    engine = _engine()
    inventory_repository = _inventory_repository(engine)
    operation_repository = OperationRepository(engine=engine, clock=lambda: _NOW)
    security.audit_sink.test_engine = engine
    app = create_app(
        readiness_check=check,
        security_services=security,
        inventory_services=InventoryServices(repository=inventory_repository, engine=engine),
        operation_services=OperationServices(
            repository=operation_repository,
            inventory_repository=inventory_repository,
            catalog=build_builtin_workflow_catalog(environment="local"),
        ),
    )
    return app, security, operation_repository


def _login(client: TestClient, login: str, credential: str) -> str:
    response = client.post(
        "/api/v1/session/login",
        json={"login": login, "credential": credential},
        headers={"x-request-id": f"login-{login}"},
    )
    assert response.status_code == 200
    return str(response.json()["csrf"])


def _submit_precheck(client: TestClient, csrf: str, *, idempotency_key: str) -> Any:
    return client.post(
        "/api/v1/operations",
        json=_operation_body(),
        headers={
            "x-request-id": f"submit-{idempotency_key}",
            "x-csrf-token": csrf,
            "idempotency-key": idempotency_key,
        },
    )


def _operation_body(
    *,
    reason: str = "replace host firmware",
    resource_id: str = "hypervisor-0001",
) -> dict[str, Any]:
    return {
        "workflow_key": "maintenance-host-precheck",
        "version": "1.0.0",
        "targets": [
            {
                "target_type": "host",
                "cloud_id": "synthetic",
                "region_id": "RegionOne",
                "resource_id": resource_id,
            }
        ],
        "input": {"reason": reason, "dry_run": True},
    }


def _engine() -> Engine:
    engine = sa.create_engine(
        "sqlite+pysqlite:///:memory:",
        future=True,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    inventory_schema.metadata.create_all(engine)
    operation_schema.metadata.create_all(engine)
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
    with engine.begin() as connection:
        connection.execute(
            inventory_schema.clouds.insert(),
            {
                "cloud_id": "synthetic",
                "display_name": "synthetic",
                "enabled": True,
                "created_at": _NOW,
                "updated_at": _NOW,
                "last_sync_at": _NOW,
            },
        )
        connection.execute(
            inventory_schema.regions.insert(),
            {
                "cloud_id": "synthetic",
                "region_id": "RegionOne",
                "display_name": "RegionOne",
                "enabled": True,
                "last_successful_sync_at": _NOW,
                "last_attempted_sync_at": _NOW,
                "sync_status": "ok",
            },
        )
        connection.execute(
            inventory_schema.hypervisors.insert(),
            {
                "cloud_id": "synthetic",
                "region_id": "RegionOne",
                "hypervisor_id": "hypervisor-0001",
                "host_name": "compute-a",
                "service_id": "service-hypervisor-0001",
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
                "observed_at": _NOW,
                "sync_generation": 1,
                "sync_status": "ok",
                "deleted_at": None,
                "change_hash": "hash-hypervisor-0001",
            },
        )


def _rows(engine: Engine, table: sa.Table) -> list[dict[str, Any]]:
    with engine.connect() as connection:
        rows = list(connection.execute(sa.select(table)).mappings())
    return [dict(row) for row in rows]


_NOW = datetime(2026, 6, 22, 10, 0, tzinfo=UTC)
