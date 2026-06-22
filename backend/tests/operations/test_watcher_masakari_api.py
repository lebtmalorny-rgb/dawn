from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from cloud_ui.api import create_app
from cloud_ui.health import HealthReport
from cloud_ui.security.dependencies import SecurityServices, build_security_services


def test_watcher_recommendations_are_first_class_and_auto_apply_disabled() -> None:
    client, _security = _client()
    _login(client)

    goals = client.get("/api/v1/watcher/goals", headers={"x-request-id": "watcher-goals"})
    recommendations = client.get(
        "/api/v1/watcher/recommendations",
        headers={"x-request-id": "watcher-recommendations"},
    )

    assert goals.status_code == 200
    assert goals.json()["items"][0]["goal"] == "server_consolidation"
    assert recommendations.status_code == 200
    recommendation = recommendations.json()["items"][0]
    assert recommendation["action_plan_id"] == "watcher-action-plan-precheck"
    assert recommendation["automatic_apply"]["enabled"] is False
    assert recommendation["automatic_apply"]["reason"] == "disabled_by_default"
    assert recommendation["risk_markers"] == ["dry_run_only", "requires_operation_catalog"]


def test_watcher_direct_apply_endpoint_is_not_exposed() -> None:
    client, _security = _client()
    _login(client)

    response = client.post(
        "/api/v1/watcher/action-plans/watcher-action-plan-precheck/execute",
        headers={"x-request-id": "watcher-direct-apply"},
    )

    assert response.status_code == 404


def test_masakari_status_exposes_approval_conflict_and_consul_matrix() -> None:
    client, _security = _client()
    _login(client)

    segments = client.get("/api/v1/masakari/segments", headers={"x-request-id": "segments"})
    notifications = client.get(
        "/api/v1/masakari/notifications",
        headers={"x-request-id": "notifications"},
    )
    timeline = client.get(
        "/api/v1/masakari/recovery-timeline",
        headers={"x-request-id": "timeline"},
    )

    assert segments.status_code == 200
    segment = segments.json()["items"][0]
    assert segment["segment_id"] == "segment-precheck"
    assert segment["approval_gate"]["required"] is True
    assert segment["consul_matrix"]["status"] == "partial"
    assert segment["processmonitor"]["status"] == "unsupported"
    assert notifications.status_code == 200
    notification = notifications.json()["items"][0]
    assert notification["conflict_state"]["nova_masakari_conflict"] is True
    assert notification["direct_recovery_enabled"] is False
    assert timeline.status_code == 200
    assert timeline.json()["items"][0]["event_type"] == "diagnostic"


def test_masakari_direct_recovery_endpoint_is_not_exposed() -> None:
    client, _security = _client()
    _login(client)

    response = client.post(
        "/api/v1/masakari/notifications/notification-precheck/recover",
        headers={"x-request-id": "masakari-direct-recover"},
    )

    assert response.status_code == 404


def test_watcher_masakari_status_requires_operation_read() -> None:
    client, _security = _client()

    response = client.get("/api/v1/watcher/recommendations")

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "not_authenticated"


def _client() -> tuple[TestClient, SecurityServices]:
    app, security = _app()
    return TestClient(app), security


def _app() -> tuple[FastAPI, SecurityServices]:
    def check() -> HealthReport:
        return HealthReport(status="ok", dependencies={})

    security = build_security_services()
    app = create_app(readiness_check=check, security_services=security)
    return app, security


def _login(client: TestClient, login: str = "operator", credential: str = "operator-code") -> str:
    response = client.post(
        "/api/v1/session/login",
        json={"login": login, "credential": credential},
        headers={"x-request-id": f"login-{login}"},
    )
    assert response.status_code == 200
    return str(response.json()["csrf"])
