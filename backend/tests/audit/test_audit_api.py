from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

import sqlalchemy as sa
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.engine import Engine
from sqlalchemy.pool import StaticPool

from cloud_ui.api import create_app
from cloud_ui.audit import schema
from cloud_ui.audit.models import AuditEvent
from cloud_ui.audit.repository import AuditRepository
from cloud_ui.health import HealthReport
from cloud_ui.inventory.routes import InventoryServices
from cloud_ui.security.dependencies import SecurityServices, build_security_services


def test_audit_list_requires_audit_read() -> None:
    client, security, _repository = _client()

    unauthenticated = client.get(
        "/api/v1/audit/events",
        headers={"x-request-id": "audit-list-no-session"},
    )
    _login(client, "operator", "operator-code")
    forbidden = client.get(
        "/api/v1/audit/events",
        headers={"x-request-id": "audit-list-forbidden"},
    )

    assert unauthenticated.status_code == 401
    assert unauthenticated.json()["error"]["code"] == "not_authenticated"
    assert forbidden.status_code == 403
    assert forbidden.json()["error"]["code"] == "forbidden"
    assert any(
        event.action == "authorization.denied"
        and event.actor_id == "mock-user-operator"
        and event.metadata["capability"] == "audit.read"
        for event in security.audit_sink.events
    )


def test_audit_list_returns_sanitized_page_and_audits_access() -> None:
    client, security, repository = _client()
    repository.record_event(
        _event(
            event_id="event-old",
            occurred_at=_NOW - timedelta(minutes=1),
            action="session.login",
            target_type="session",
            target_id="session-old",
            metadata={"normal": "old"},
        ),
        queue_delivery=False,
    )
    repository.record_event(
        _event(
            event_id="event-new",
            occurred_at=_NOW,
            action="session.login",
            target_type="session",
            target_id="session-new",
            metadata={"normal": "visible", "token": "DKB_CANARY_TOKEN"},
        ),
        queue_delivery=False,
    )
    _login(client, "auditor", "auditor-code")

    response = client.get(
        "/api/v1/audit/events?action=session.login&limit=1",
        headers={"x-request-id": "audit-list-success"},
    )
    second_page = client.get(
        f"/api/v1/audit/events?action=session.login&limit=1&cursor={response.json().get('next_cursor')}",
        headers={"x-request-id": "audit-list-second-page"},
    )

    assert response.status_code == 200
    payload = response.json()
    second_payload = second_page.json()
    assert payload["limit"] == 1
    assert payload["sort"] == "occurred_at.desc,event_id.desc"
    assert payload["next_cursor"]
    assert second_page.status_code == 200
    assert second_payload["items"][0]["event_id"] == "event-old"
    assert second_payload["next_cursor"] is None
    assert payload["items"][0]["event_id"] == "event-new"
    assert payload["items"][0]["actor"]["id"] == "mock-user-actor"
    assert payload["items"][0]["target"] == {"type": "session", "id": "session-new"}
    assert payload["items"][0]["metadata"] == {"normal": "visible", "token": "***"}
    assert "DKB_CANARY" not in repr(payload)
    assert any(
        event.action == "audit.events.list"
        and event.actor_id == "mock-user-auditor"
        and event.metadata["filter_count"] == 1
        for event in security.audit_sink.events
    )


def test_audit_detail_returns_sanitized_event_and_audits_access() -> None:
    client, security, repository = _client()
    repository.record_event(
        _event(event_id="event-detail", metadata={"cookie": "DKB_CANARY_COOKIE"}),
        queue_delivery=False,
    )
    _login(client, "auditor", "auditor-code")

    response = client.get(
        "/api/v1/audit/events/event-detail",
        headers={"x-request-id": "audit-detail-success"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["event_id"] == "event-detail"
    assert payload["metadata"] == {}
    assert "DKB_CANARY" not in repr(payload)
    assert any(
        event.action == "audit.event.detail"
        and event.target_id == "event-detail"
        and event.actor_id == "mock-user-auditor"
        for event in security.audit_sink.events
    )


def test_audit_list_rejects_tampered_cursor() -> None:
    client, _security, _repository = _client()
    _login(client, "auditor", "auditor-code")

    response = client.get(
        "/api/v1/audit/events?cursor=tampered",
        headers={"x-request-id": "audit-list-tampered"},
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "cursor_tampered"


def test_audit_export_requires_separate_capability_and_csrf() -> None:
    client, security, _repository = _client()
    auditor_csrf = _login(client, "auditor", "auditor-code")

    auditor_response = client.post(
        "/api/v1/audit/export",
        json={"from": "2026-06-22T00:00:00Z", "to": "2026-06-23T00:00:00Z", "limit": 100},
        headers={"x-request-id": "audit-export-auditor", "x-csrf-token": auditor_csrf},
    )
    admin_csrf = _login(client, "admin", "admin-code")
    missing_csrf = client.post(
        "/api/v1/audit/export",
        json={"from": "2026-06-22T00:00:00Z", "to": "2026-06-23T00:00:00Z", "limit": 100},
        headers={"x-request-id": "audit-export-no-csrf"},
    )
    success = client.post(
        "/api/v1/audit/export",
        json={"from": "2026-06-22T00:00:00Z", "to": "2026-06-23T00:00:00Z", "limit": 100},
        headers={"x-request-id": "audit-export-admin", "x-csrf-token": admin_csrf},
    )

    assert auditor_response.status_code == 403
    assert auditor_response.json()["error"]["code"] == "forbidden"
    assert missing_csrf.status_code == 403
    assert missing_csrf.json()["error"]["code"] == "csrf_failed"
    assert success.status_code == 202
    assert success.json()["status"] == "accepted"
    assert success.json()["export_request_id"].startswith("audit-export-")
    assert any(
        event.action == "audit.export.requested"
        and event.actor_id == "mock-user-admin"
        and event.metadata["limit"] == 100
        for event in security.audit_sink.events
    )


def _client() -> tuple[TestClient, SecurityServices, AuditRepository]:
    app, security, repository = _app()
    return TestClient(app), security, repository


def _app() -> tuple[FastAPI, SecurityServices, AuditRepository]:
    def check() -> HealthReport:
        return HealthReport(status="ok", dependencies={})

    security = build_security_services()
    engine = _engine()
    repository = AuditRepository(engine=engine, clock=lambda: _NOW)
    app = create_app(
        readiness_check=check,
        security_services=security,
        inventory_services=InventoryServices(repository=None, engine=engine),
    )
    return app, security, repository


def _engine() -> Engine:
    engine = sa.create_engine(
        "sqlite+pysqlite:///:memory:",
        future=True,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    schema.metadata.create_all(engine)
    return engine


def _login(client: TestClient, login: str, credential: str) -> str:
    response = client.post(
        "/api/v1/session/login",
        json={"login": login, "credential": credential},
        headers={"x-request-id": f"login-{login}"},
    )
    assert response.status_code == 200
    return str(response.json()["csrf"])


def _event(**overrides: Any) -> AuditEvent:
    values: dict[str, Any] = {
        "event_id": "event-1",
        "event_version": "1.0",
        "occurred_at": _NOW,
        "actor_type": "human",
        "actor_id": "mock-user-actor",
        "actor_display": "Actor",
        "authentication_method": "mock",
        "session_reference": "session-actor",
        "action": "session.login",
        "event_type": "auth",
        "outcome": "success",
        "target_type": "session",
        "target_id": "session-actor",
        "request_id": "request-1",
        "correlation_id": "correlation-1",
        "service": "cloud-ui-api",
        "component": "security",
        "metadata": {"normal": "visible"},
    }
    values.update(overrides)
    return AuditEvent(**values)


_NOW = datetime(2026, 6, 22, 14, 0, tzinfo=UTC)
