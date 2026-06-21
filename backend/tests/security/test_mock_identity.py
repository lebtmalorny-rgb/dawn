from __future__ import annotations

import pytest

from cloud_ui.config import Settings
from cloud_ui.security.identity import AuthenticationFailed, LoginRequest
from cloud_ui.security.mock_identity import build_mock_identity_provider


def test_mock_identity_authenticates_known_operator_without_browser_secrets() -> None:
    provider = build_mock_identity_provider()

    result = provider.authenticate(LoginRequest(login="operator", credential="operator-code"))

    assert result.subject.subject_id == "mock-user-operator"
    assert result.subject.display_name == "Оператор облака"
    assert result.subject.subject_type == "human"
    assert result.subject.roles == frozenset({"cloud_operator"})
    assert result.subject.capabilities == frozenset(
        {
            "instance.read",
            "instance.refresh",
            "hypervisor.read",
            "group.read",
            "operation.read",
            "workflow.execute.maintenance-host",
        }
    )
    assert result.authentication_method == "mock"
    serialized = result.model_dump()
    assert "operator-code" not in repr(serialized)
    assert "token" not in repr(serialized).lower()


def test_mock_identity_rejects_unknown_credential() -> None:
    provider = build_mock_identity_provider()

    with pytest.raises(AuthenticationFailed):
        provider.authenticate(LoginRequest(login="operator", credential="wrong-code"))


def test_mock_identity_cannot_be_enabled_in_production_settings() -> None:
    with pytest.raises(ValueError, match="Mock identity provider is not allowed in production"):
        Settings(
            database_url="mysql+pymysql://cloud_ui:cloud_ui_dev@db:3306/cloud_ui",
            rabbitmq_url="amqp://cloud_ui:cloud_ui_dev@rabbitmq:5672/%2Fcloud-ui",
            environment="production",
            identity_provider="mock",
            mock_identity_enabled=True,
        )
