from cloud_ui.api import create_app
from cloud_ui.health import DependencyState, HealthReport
from fastapi.testclient import TestClient


def test_liveness_returns_ok() -> None:
    def check() -> HealthReport:
        return HealthReport(status="ok", dependencies={})

    app = create_app(readiness_check=check)
    client = TestClient(app)

    response = client.get("/health/live", headers={"x-request-id": "request-123"})

    assert response.status_code == 200
    assert response.headers["x-request-id"] == "request-123"
    assert response.json()["status"] == "ok"


def test_liveness_generates_request_id_when_missing() -> None:
    def check() -> HealthReport:
        return HealthReport(status="ok", dependencies={})

    app = create_app(readiness_check=check)
    client = TestClient(app)

    response = client.get("/health/live")

    assert response.status_code == 200
    assert response.headers["x-request-id"]


def test_readiness_returns_ok_status() -> None:
    def check() -> HealthReport:
        return HealthReport(
            status="ok",
            dependencies={
                "database": DependencyState(status="ok", detail="reachable"),
                "rabbitmq": DependencyState(status="ok", detail="reachable"),
            },
        )

    app = create_app(readiness_check=check)
    client = TestClient(app)

    response = client.get("/health/ready")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "dependencies": {
            "database": {"status": "ok", "detail": "reachable"},
            "rabbitmq": {"status": "ok", "detail": "reachable"},
        },
    }


def test_readiness_openapi_documents_health_report() -> None:
    def check() -> HealthReport:
        return HealthReport(status="ok", dependencies={})

    app = create_app(readiness_check=check)
    client = TestClient(app)

    responses = client.get("/openapi.json").json()["paths"]["/health/ready"]["get"][
        "responses"
    ]

    assert responses["200"]["content"]["application/json"]["schema"] == {
        "$ref": "#/components/schemas/HealthReport"
    }
    assert responses["503"]["content"]["application/json"]["schema"] == {
        "$ref": "#/components/schemas/HealthReport"
    }


def test_readiness_reports_dependency_failure() -> None:
    def check() -> HealthReport:
        return HealthReport(
            status="degraded",
            dependencies={
                "database": DependencyState(status="down", detail="connection failed"),
                "rabbitmq": DependencyState(status="ok", detail="reachable"),
            },
        )

    app = create_app(readiness_check=check)
    client = TestClient(app)

    response = client.get("/health/ready")

    assert response.status_code == 503
    payload = response.json()
    assert payload["status"] == "degraded"
    assert payload["dependencies"]["database"]["status"] == "down"
