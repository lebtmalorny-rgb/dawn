# ruff: noqa: I001
from cloud_ui.api import create_app
from cloud_ui.config import Settings
from cloud_ui.health import DependencyState, HealthReport
from cloud_ui.secrets.errors import SecretUnavailableError
from cloud_ui.secrets.models import SecretDocument, SecretReference, SecretSchema
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


def test_api_v1_liveness_returns_ok() -> None:
    def check() -> HealthReport:
        return HealthReport(status="ok", dependencies={})

    app = create_app(readiness_check=check)
    client = TestClient(app)

    response = client.get("/api/v1/health/live")

    assert response.status_code == 200
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


def test_api_v1_readiness_returns_ok_status() -> None:
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

    response = client.get("/api/v1/health/ready")

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

    prefixed_responses = client.get("/openapi.json").json()["paths"][
        "/api/v1/health/ready"
    ]["get"]["responses"]

    assert prefixed_responses["200"]["content"]["application/json"]["schema"] == {
        "$ref": "#/components/schemas/HealthReport"
    }
    assert prefixed_responses["503"]["content"]["application/json"]["schema"] == {
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


def test_readiness_can_include_vault_dependency(monkeypatch, tmp_path) -> None:
    class _UnavailableVaultProvider:
        def __init__(self, **kwargs) -> None:
            pass

        def get(
            self,
            reference: SecretReference,
            schema: SecretSchema,
            *,
            correlation_id: str,
        ) -> SecretDocument:
            raise SecretUnavailableError(
                message="Vault unavailable DKB_CANARY",
                alias=reference.alias,
                correlation_id=correlation_id,
                details={"token": "synthetic-token", "path": reference.path},
            )

    token_path = tmp_path / "vault-token"
    token_path.write_text("synthetic-token", encoding="utf-8")
    settings = Settings(
        database_url="mysql+pymysql://cloud_ui:cloud_ui_dev@db:3306/cloud_ui",
        rabbitmq_url="amqp://cloud_ui:cloud_ui_dev@rabbitmq:5672/%2Fcloud-ui",
        secrets_provider="vault",
        vault_addr="https://192.168.10.15:8200",
        vault_token_file=token_path,
        vault_allowed_prefix="kv/data/cloud-ui/local/",
    )
    monkeypatch.setattr("cloud_ui.health.check_database", lambda url: "reachable")
    monkeypatch.setattr("cloud_ui.health.check_rabbitmq", lambda url: "reachable")
    monkeypatch.setattr("cloud_ui.health.VaultSecretProvider", _UnavailableVaultProvider)

    from cloud_ui.health import build_readiness_check

    app = create_app(readiness_check=build_readiness_check(settings))
    client = TestClient(app)

    response = client.get("/health/ready")

    assert response.status_code == 503
    payload = response.json()
    assert payload["status"] == "degraded"
    assert payload["dependencies"]["vault"] == {
        "status": "down",
        "detail": "vault unavailable: secret_unavailable",
    }
    assert "synthetic-token" not in response.text
    assert "DKB_CANARY" not in response.text
    assert "kv/data/cloud-ui/local/session" not in response.text


def test_readiness_reports_missing_vault_token_file_as_down(monkeypatch, tmp_path) -> None:
    missing_token_file = tmp_path / "missing-vault-token-DKB_CANARY"
    settings = Settings(
        database_url="mysql+pymysql://cloud_ui:cloud_ui_dev@db:3306/cloud_ui",
        rabbitmq_url="amqp://cloud_ui:cloud_ui_dev@rabbitmq:5672/%2Fcloud-ui",
        secrets_provider="vault",
        vault_addr="https://192.168.10.15:8200",
        vault_token_file=missing_token_file,
        vault_allowed_prefix="kv/data/cloud-ui/local/",
    )
    monkeypatch.setattr("cloud_ui.health.check_database", lambda url: "reachable")
    monkeypatch.setattr("cloud_ui.health.check_rabbitmq", lambda url: "reachable")

    from cloud_ui.health import build_readiness_check

    report = build_readiness_check(settings)()

    assert report.status == "degraded"
    assert report.dependencies["vault"].status == "down"
    assert report.dependencies["vault"].detail == "vault unavailable: secret_unavailable"
    assert str(missing_token_file) not in report.dependencies["vault"].detail
    assert "DKB_CANARY" not in report.dependencies["vault"].detail
    assert "kv/data/cloud-ui/local/session" not in report.dependencies["vault"].detail
