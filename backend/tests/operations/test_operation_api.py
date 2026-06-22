from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import sqlalchemy as sa
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.engine import Engine
from sqlalchemy.pool import StaticPool

from cloud_ui.api import create_app
from cloud_ui.groups import schema as group_schema
from cloud_ui.groups.repository import GroupRepository
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


def test_operation_list_is_paginated_and_actor_scoped() -> None:
    client, _security, _repository = _client()
    csrf = _login(client, "operator", "operator-code")
    first = _submit_precheck(client, csrf, idempotency_key="list-key-1").json()
    second = _submit_precheck(client, csrf, idempotency_key="list-key-2").json()

    first_page = client.get(
        "/api/v1/operations?limit=1",
        headers={"x-request-id": "operation-list-1"},
    )
    first_payload = first_page.json()
    next_cursor = first_payload["next_cursor"]
    second_page = client.get(
        f"/api/v1/operations?limit=1&cursor={next_cursor}",
        headers={"x-request-id": "operation-list-2"},
    )
    second_payload = second_page.json()

    assert first_page.status_code == 200
    assert first_payload["limit"] == 1
    assert first_payload["sort"] == "updated_at.desc"
    assert len(first_payload["items"]) == 1
    assert next_cursor is not None
    assert second_page.status_code == 200
    assert len(second_payload["items"]) == 1
    assert second_payload["next_cursor"] is None
    assert {
        first_payload["items"][0]["operation_id"],
        second_payload["items"][0]["operation_id"],
    } == {first["operation_id"], second["operation_id"]}

    _login(client, "auditor", "auditor-code")
    auditor_response = client.get(
        "/api/v1/operations?limit=50",
        headers={"x-request-id": "operation-list-auditor"},
    )

    assert auditor_response.status_code == 200
    assert auditor_response.json()["items"] == []


def test_operation_list_rejects_tampered_cursor() -> None:
    client, _security, _repository = _client()
    _login(client, "operator", "operator-code")

    response = client.get(
        "/api/v1/operations?cursor=tampered",
        headers={"x-request-id": "operation-list-tampered-cursor"},
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "cursor_tampered"


def test_submit_group_target_expands_and_freezes_member_snapshot() -> None:
    client, security, repository = _client()
    group_repository = _group_repository_from_state(security)
    group = group_repository.create_group(
        actor_id="mock-user-operator",
        scope_type="project",
        scope_id="project-a",
        name="maintenance-hosts",
        description=None,
        resource_type="host",
        membership_mode="explicit",
    )
    group_repository.add_member(
        group_id=group.group_id,
        resource_type="host",
        cloud_id="synthetic",
        region_id="RegionOne",
        resource_id="hypervisor-0001",
        source="explicit",
        actor_id="mock-user-operator",
    )
    group_after_member = group_repository.get_group(group.group_id)
    assert group_after_member is not None
    csrf = _login(client, "operator", "operator-code")

    response = client.post(
        "/api/v1/operations",
        json=_operation_body(
            target_type="group",
            resource_id=group.group_id,
            expected_revision=group_after_member.revision,
        ),
        headers={
            "x-request-id": "operation-group-target",
            "x-csrf-token": csrf,
            "idempotency-key": "group-target-key",
        },
    )
    operation_id = response.json()["operation_id"]
    group_repository.add_member(
        group_id=group.group_id,
        resource_type="host",
        cloud_id="synthetic",
        region_id="RegionOne",
        resource_id="hypervisor-0002",
        source="explicit",
        actor_id="mock-user-operator",
    )

    operation = repository.get_operation(operation_id)
    assert response.status_code == 202
    assert operation is not None
    assert [target["resource_id"] for target in operation.target_snapshot_json] == [
        "hypervisor-0001"
    ]
    assert operation.target_snapshot_json[0]["snapshot"]["source_group_id"] == group.group_id
    assert operation.target_snapshot_json[0]["snapshot"]["source_group_revision"] == (
        group_after_member.revision
    )


def test_submit_group_target_rejects_stale_group_revision() -> None:
    client, security, _repository = _client()
    group_repository = _group_repository_from_state(security)
    group = group_repository.create_group(
        actor_id="mock-user-operator",
        scope_type="project",
        scope_id="project-a",
        name="maintenance-hosts",
        description=None,
        resource_type="host",
        membership_mode="explicit",
    )
    group_repository.add_member(
        group_id=group.group_id,
        resource_type="host",
        cloud_id="synthetic",
        region_id="RegionOne",
        resource_id="hypervisor-0001",
        source="explicit",
        actor_id="mock-user-operator",
    )
    csrf = _login(client, "operator", "operator-code")

    response = client.post(
        "/api/v1/operations",
        json=_operation_body(
            target_type="group",
            resource_id=group.group_id,
            expected_revision=1,
        ),
        headers={
            "x-request-id": "operation-stale-group",
            "x-csrf-token": csrf,
            "idempotency-key": "stale-group-key",
        },
    )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "stale_group_snapshot"


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
    group_repository = GroupRepository(engine=engine)
    security.audit_sink.test_engine = engine
    app = create_app(
        readiness_check=check,
        security_services=security,
        inventory_services=InventoryServices(repository=inventory_repository, engine=engine),
        operation_services=OperationServices(
            repository=operation_repository,
            inventory_repository=inventory_repository,
            group_repository=group_repository,
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
    target_type: str = "host",
    expected_revision: int | None = None,
) -> dict[str, Any]:
    target: dict[str, Any] = {
        "target_type": target_type,
        "cloud_id": "synthetic",
        "region_id": "RegionOne",
        "resource_id": resource_id,
    }
    if expected_revision is not None:
        target["expected_revision"] = expected_revision
    return {
        "workflow_key": "maintenance-host-precheck",
        "version": "1.0.0",
        "targets": [target],
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
    group_schema.metadata.create_all(engine)
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
            [
                _hypervisor_row("hypervisor-0001", "compute-a"),
                _hypervisor_row("hypervisor-0002", "compute-b"),
            ],
        )


def _group_repository_from_state(security: SecurityServices) -> GroupRepository:
    engine = security.audit_sink.test_engine
    assert isinstance(engine, Engine)
    return GroupRepository(engine=engine)


def _hypervisor_row(hypervisor_id: str, host_name: str) -> dict[str, Any]:
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
        "observed_at": _NOW,
        "sync_generation": 1,
        "sync_status": "ok",
        "deleted_at": None,
        "change_hash": f"hash-{hypervisor_id}",
    }


def _rows(engine: Engine, table: sa.Table) -> list[dict[str, Any]]:
    with engine.connect() as connection:
        rows = list(connection.execute(sa.select(table)).mappings())
    return [dict(row) for row in rows]


_NOW = datetime(2026, 6, 22, 10, 0, tzinfo=UTC)
