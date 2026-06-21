from __future__ import annotations

from typing import Any

from fastapi.testclient import TestClient

from cloud_ui.api import create_app
from cloud_ui.health import HealthReport
from cloud_ui.security.dependencies import build_security_services


def _client() -> tuple[TestClient, Any]:
    def check() -> HealthReport:
        return HealthReport(status="ok", dependencies={})

    security = build_security_services()
    app = create_app(readiness_check=check, security_services=security)
    return TestClient(app), security


def _login(client: TestClient, login: str = "operator", credential: str = "operator-code") -> str:
    response = client.post(
        "/api/v1/session/login",
        json={"login": login, "credential": credential},
        headers={"x-request-id": "login-request"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert "token" not in repr(payload).lower()
    assert payload["subject"]["subject_id"] == f"mock-user-{login}"
    assert "cloud_ui_session" in response.cookies
    assert "httponly" in response.headers["set-cookie"].lower()
    assert "samesite=lax" in response.headers["set-cookie"].lower()
    return str(payload["csrf"])


def test_login_current_session_and_capabilities_use_server_side_cookie() -> None:
    client, security = _client()

    csrf = _login(client)

    session_response = client.get("/api/v1/session", headers={"x-request-id": "session-request"})
    assert session_response.status_code == 200
    assert session_response.json()["subject"]["roles"] == ["cloud_operator"]

    capabilities_response = client.get("/api/v1/capabilities")
    assert capabilities_response.status_code == 200
    capabilities = capabilities_response.json()
    assert "workflow.execute.maintenance-host" in capabilities["capabilities"]
    assert "policy_expression" not in repr(capabilities)
    assert csrf
    assert any(event.action == "session.login" for event in security.audit_sink.events)


def test_session_and_capability_responses_have_security_headers() -> None:
    client, _security = _client()
    _login(client)

    session_response = client.get("/api/v1/session")
    capabilities_response = client.get("/api/v1/capabilities")

    for response in (session_response, capabilities_response):
        assert response.headers["x-content-type-options"] == "nosniff"
        assert response.headers["x-frame-options"] == "DENY"
        assert response.headers["cache-control"] == "no-store"


def test_login_failure_returns_safe_error_and_audit_event() -> None:
    client, security = _client()

    response = client.post(
        "/api/v1/session/login",
        json={"login": "operator", "credential": "bad-code"},
        headers={"x-request-id": "bad-login"},
    )

    assert response.status_code == 401
    assert response.json() == {
        "error": {
            "code": "authentication_failed",
            "message": "Не удалось выполнить вход",
            "request_id": "bad-login",
        }
    }
    assert "bad-code" not in repr(response.json())
    assert any(
        event.action == "session.login" and event.outcome == "failure"
        for event in security.audit_sink.events
    )


def test_protected_endpoint_denies_direct_request_without_session() -> None:
    client, security = _client()

    response = client.post(
        "/api/v1/admin/role-bindings",
        json={"subject_id": "mock-user-viewer", "subject_type": "human", "role": "service"},
        headers={"x-request-id": "direct-request", "x-csrf-token": "csrf"},
    )

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "not_authenticated"
    assert any(event.action == "session.required" for event in security.audit_sink.events)


def test_csrf_rejects_state_changing_request() -> None:
    client, security = _client()
    _login(client)

    response = client.post(
        "/api/v1/session/logout",
        headers={"x-request-id": "logout-request"},
    )

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "csrf_failed"
    assert any(event.action == "csrf.denied" for event in security.audit_sink.events)


def test_logout_revokes_session_with_valid_csrf() -> None:
    client, security = _client()
    csrf = _login(client)

    logout_response = client.post(
        "/api/v1/session/logout",
        headers={"x-request-id": "logout-request", "x-csrf-token": csrf},
    )
    assert logout_response.status_code == 204

    session_response = client.get("/api/v1/session")
    assert session_response.status_code == 401
    assert any(event.action == "session.logout" for event in security.audit_sink.events)


def test_session_limit_deny_policy_blocks_second_login() -> None:
    client, security = _client()
    _login(client)

    response = client.post(
        "/api/v1/session/login",
        json={"login": "operator", "credential": "operator-code"},
        headers={"x-request-id": "second-login"},
    )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "session_limit_reached"
    assert any(event.action == "session.limit_reached" for event in security.audit_sink.events)


def test_session_idle_timeout_returns_safe_unauthenticated_error() -> None:
    client, security = _client()
    _login(client)
    security.clock.advance(seconds=901)

    response = client.get("/api/v1/session", headers={"x-request-id": "expired-session"})

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "session_expired"
    assert any(event.action == "session.timeout" for event in security.audit_sink.events)


def test_role_binding_denies_service_role_for_human_subject() -> None:
    client, security = _client()
    csrf = _login(client, login="admin", credential="admin-code")

    response = client.post(
        "/api/v1/admin/role-bindings",
        json={"subject_id": "mock-user-viewer", "subject_type": "human", "role": "service"},
        headers={"x-request-id": "role-request", "x-csrf-token": csrf},
    )

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "service_role_for_human"
    assert any(event.action == "authorization.denied" for event in security.audit_sink.events)


def test_portal_allow_does_not_override_simulated_openstack_deny() -> None:
    client, security = _client()
    csrf = _login(client)

    response = client.post(
        "/api/v1/operations/simulated-openstack-action",
        json={"openstack_allowed": False},
        headers={"x-request-id": "openstack-deny", "x-csrf-token": csrf},
    )

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "openstack_forbidden"
    assert any(event.action == "openstack.denied" for event in security.audit_sink.events)
