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


def _login_with_cookie(
    client: TestClient, login: str = "operator", credential: str = "operator-code"
) -> tuple[str, str]:
    response = client.post(
        "/api/v1/session/login",
        json={"login": login, "credential": credential},
        headers={"x-request-id": f"login-{login}"},
    )
    assert response.status_code == 200
    session_id = response.cookies.get("cloud_ui_session")
    assert session_id is not None
    return str(response.json()["csrf"]), session_id


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


def test_admin_lists_and_revokes_active_sessions_with_audit_event() -> None:
    client, security = _client()
    operator_csrf, operator_session_id = _login_with_cookie(client)

    client.cookies.clear()
    admin_csrf, admin_session_id = _login_with_cookie(
        client, login="admin", credential="admin-code"
    )

    list_response = client.get("/api/v1/session/active")
    assert list_response.status_code == 200
    payload = list_response.json()
    assert payload["sessions"] == [
        {
            "session_id": operator_session_id,
            "subject_id": "mock-user-operator",
            "display_name": "Оператор облака",
            "created_at": "2026-06-21T07:00:00Z",
            "last_seen_at": "2026-06-21T07:00:00Z",
            "idle_expires_at": "2026-06-21T07:15:00Z",
            "absolute_expires_at": "2026-06-21T15:00:00Z",
        },
        {
            "session_id": admin_session_id,
            "subject_id": "mock-user-admin",
            "display_name": "Администратор портала",
            "created_at": "2026-06-21T07:00:00Z",
            "last_seen_at": "2026-06-21T07:00:00Z",
            "idle_expires_at": "2026-06-21T07:15:00Z",
            "absolute_expires_at": "2026-06-21T15:00:00Z",
        },
    ]
    assert operator_csrf

    revoke_response = client.delete(
        f"/api/v1/session/active/{operator_session_id}",
        headers={"x-request-id": "admin-revoke", "x-csrf-token": admin_csrf},
    )
    assert revoke_response.status_code == 204
    assert any(
        event.action == "session.revoke" and event.target_id == operator_session_id
        for event in security.audit_sink.events
    )

    client.cookies.set("cloud_ui_session", operator_session_id)
    revoked_response = client.get("/api/v1/session")
    assert revoked_response.status_code == 401


def test_audit_reader_cannot_use_mutating_role_management_endpoint() -> None:
    client, security = _client()
    csrf = _login(client, login="auditor", credential="auditor-code")

    response = client.post(
        "/api/v1/admin/role-bindings",
        json={"subject_id": "mock-user-viewer", "subject_type": "human", "role": "cloud_viewer"},
        headers={"x-request-id": "auditor-denied", "x-csrf-token": csrf},
    )

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "forbidden"
    assert any(
        event.action == "authorization.denied"
        and event.actor_id == "mock-user-auditor"
        and event.metadata["code"] == "forbidden"
        for event in security.audit_sink.events
    )


def test_mutating_endpoint_rejects_untrusted_origin_before_csrf() -> None:
    client, security = _client()
    csrf = _login(client)

    response = client.post(
        "/api/v1/session/logout",
        headers={
            "origin": "https://evil.example",
            "x-request-id": "bad-origin",
            "x-csrf-token": csrf,
        },
    )

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "origin_forbidden"
    assert any(event.action == "origin.denied" for event in security.audit_sink.events)


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
