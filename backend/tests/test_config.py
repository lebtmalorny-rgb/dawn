import os

import pytest
from pydantic import ValidationError

from cloud_ui.config import Settings

_CLOUD_UI_ENVIRONMENT_NAMES = {
    "CLOUD_UI_DATABASE_URL",
    "CLOUD_UI_RABBITMQ_URL",
    "CLOUD_UI_API_BIND_HOST",
    "CLOUD_UI_API_PORT",
    "CLOUD_UI_LOG_LEVEL",
    "CLOUD_UI_CONFIG_VERSION",
    "CLOUD_UI_ENVIRONMENT",
    "CLOUD_UI_IDENTITY_PROVIDER",
    "CLOUD_UI_MOCK_IDENTITY_ENABLED",
    "CLOUD_UI_SESSION_IDLE_TIMEOUT_SECONDS",
    "CLOUD_UI_SESSION_ABSOLUTE_LIFETIME_SECONDS",
    "CLOUD_UI_SIMULTANEOUS_SESSION_LIMIT",
    "CLOUD_UI_SESSION_LIMIT_POLICY",
    "CLOUD_UI_SESSION_COOKIE_SECURE",
    "CLOUD_UI_SESSION_COOKIE_SAMESITE",
    "CLOUD_UI_TRUSTED_ORIGINS",
    "CLOUD_UI_OPENSTACK_TIMEOUT_SECONDS",
    "CLOUD_UI_OPENSTACK_MAX_ATTEMPTS",
    "CLOUD_UI_NOVA_MICROVERSION",
    "CLOUD_UI_PLACEMENT_MICROVERSION",
    "CLOUD_UI_INVENTORY_DEFAULT_LIMIT",
    "CLOUD_UI_INVENTORY_MAX_LIMIT",
    "CLOUD_UI_INVENTORY_CURSOR_SIGNING_KEY",
    "CLOUD_UI_OPERATION_CURSOR_SIGNING_KEY",
    "CLOUD_UI_INVENTORY_STALE_AFTER_SECONDS",
    "CLOUD_UI_INVENTORY_SYNTHETIC_INSTANCE_COUNT",
    "CLOUD_UI_INVENTORY_SYNTHETIC_HYPERVISOR_COUNT",
    "CLOUD_UI_AUDIT_SINK_TYPE",
    "CLOUD_UI_AUDIT_DELIVERY_MAX_ATTEMPTS",
    "CLOUD_UI_AUDIT_DELIVERY_RETRY_DELAY_SECONDS",
    "CLOUD_UI_AUDIT_DELIVERY_BATCH_SIZE",
    "CLOUD_UI_AUDIT_FLUENTD_HTTP_URL",
    "CLOUD_UI_AUDIT_DEFAULT_LIMIT",
    "CLOUD_UI_AUDIT_MAX_LIMIT",
    "CLOUD_UI_AUDIT_CURSOR_SIGNING_KEY",
    "CLOUD_UI_SECRETS_PROVIDER",
    "CLOUD_UI_VAULT_ADDR",
    "CLOUD_UI_VAULT_TOKEN_FILE",
    "CLOUD_UI_VAULT_CA_BUNDLE",
    "CLOUD_UI_VAULT_TIMEOUT_SECONDS",
    "CLOUD_UI_VAULT_MAX_ATTEMPTS",
    "CLOUD_UI_VAULT_ALLOWED_PREFIX",
}


@pytest.fixture(autouse=True)
def clear_cloud_ui_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in list(os.environ):
        if name.upper() in _CLOUD_UI_ENVIRONMENT_NAMES:
            monkeypatch.delenv(name, raising=False)


def test_settings_require_database_url() -> None:
    with pytest.raises(ValidationError):
        Settings(
            rabbitmq_url="amqp://guest:guest@localhost:5672/",
            # Covers the intentional container bind default.
            api_bind_host="0.0.0.0",  # noqa: S104
            api_port=8080,
        )


def test_settings_accept_dummy_dev_values() -> None:
    settings = Settings(
        database_url="mysql+pymysql://cloud_ui:cloud_ui_dev@db:3306/cloud_ui",
        rabbitmq_url="amqp://cloud_ui:cloud_ui_dev@rabbitmq:5672/%2Fcloud-ui",
        # Covers the intentional container bind default.
        api_bind_host="0.0.0.0",  # noqa: S104
        api_port=8080,
    )

    assert settings.api_port == 8080
    assert settings.database_url.unicode_string().startswith("mysql+pymysql://")
    assert settings.environment == "local"
    assert settings.openstack_timeout_seconds == 2.0
    assert settings.openstack_max_attempts == 2
    assert settings.nova_microversion == "2.96"
    assert settings.placement_microversion == "1.39"
    assert settings.inventory_default_limit == 50
    assert settings.inventory_max_limit == 200
    assert settings.inventory_cursor_signing_key == "dev-inventory-cursor-key"
    assert settings.operation_cursor_signing_key == "dev-operation-cursor-key"
    assert settings.inventory_stale_after_seconds == 900
    assert settings.inventory_synthetic_instance_count == 10_000
    assert settings.inventory_synthetic_hypervisor_count == 1_000
    assert settings.audit_sink_type == "local"
    assert settings.audit_delivery_max_attempts == 3
    assert settings.audit_delivery_retry_delay_seconds == 30
    assert settings.audit_delivery_batch_size == 20
    assert settings.audit_fluentd_http_url is None
    assert settings.audit_default_limit == 50
    assert settings.audit_max_limit == 200
    assert settings.audit_cursor_signing_key == "dev-audit-cursor-key"


def test_settings_reject_dev_inventory_cursor_key_in_production() -> None:
    with pytest.raises(ValidationError, match="development inventory cursor signing key"):
        Settings(
            database_url="mysql+pymysql://cloud_ui:cloud_ui_dev@db:3306/cloud_ui",
            rabbitmq_url="amqp://cloud_ui:cloud_ui_dev@rabbitmq:5672/%2Fcloud-ui",
            environment="production",
            identity_provider="external",
            mock_identity_enabled=False,
        )


def test_settings_reject_dev_operation_cursor_key_in_production() -> None:
    with pytest.raises(ValidationError, match="development operation cursor signing key"):
        Settings(
            database_url="mysql+pymysql://cloud_ui:cloud_ui_dev@db:3306/cloud_ui",
            rabbitmq_url="amqp://cloud_ui:cloud_ui_dev@rabbitmq:5672/%2Fcloud-ui",
            environment="production",
            identity_provider="external",
            mock_identity_enabled=False,
            inventory_cursor_signing_key="production-inventory-cursor-key",
        )


def test_settings_still_reject_mock_identity_in_production() -> None:
    with pytest.raises(ValidationError, match="Mock identity provider"):
        Settings(
            database_url="mysql+pymysql://cloud_ui:cloud_ui_dev@db:3306/cloud_ui",
            rabbitmq_url="amqp://cloud_ui:cloud_ui_dev@rabbitmq:5672/%2Fcloud-ui",
            environment="production",
            inventory_cursor_signing_key="production-inventory-cursor-key",
            operation_cursor_signing_key="production-operation-cursor-key",
        )


def test_settings_reject_dev_audit_cursor_key_in_production() -> None:
    with pytest.raises(ValidationError, match="development audit cursor signing key"):
        Settings(
            database_url="mysql+pymysql://cloud_ui:cloud_ui_dev@db:3306/cloud_ui",
            rabbitmq_url="amqp://cloud_ui:cloud_ui_dev@rabbitmq:5672/%2Fcloud-ui",
            environment="production",
            identity_provider="external",
            mock_identity_enabled=False,
            inventory_cursor_signing_key="production-inventory-cursor-key",
            operation_cursor_signing_key="production-operation-cursor-key",
        )


def test_settings_accept_vault_secret_provider(tmp_path) -> None:
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

    assert settings.secrets_provider == "vault"
    assert settings.vault_addr is not None
    assert settings.vault_addr.unicode_string() == "https://192.168.10.15:8200/"
    assert settings.vault_token_file == token_path
    assert settings.vault_allowed_prefix == "kv/data/cloud-ui/local/"


def test_settings_reject_local_secret_provider_in_production() -> None:
    with pytest.raises(ValidationError, match="local secret provider"):
        Settings(
            database_url="mysql+pymysql://cloud_ui:cloud_ui_dev@db:3306/cloud_ui",
            rabbitmq_url="amqp://cloud_ui:cloud_ui_dev@rabbitmq:5672/%2Fcloud-ui",
            environment="production",
            identity_provider="external",
            mock_identity_enabled=False,
            inventory_cursor_signing_key="production-inventory-cursor-key",
            operation_cursor_signing_key="production-operation-cursor-key",
            audit_cursor_signing_key="production-audit-cursor-key",
            secrets_provider="local",
        )


def test_settings_require_vault_endpoint_and_token_file_when_vault_enabled() -> None:
    with pytest.raises(ValidationError, match="Vault address and token file"):
        Settings(
            database_url="mysql+pymysql://cloud_ui:cloud_ui_dev@db:3306/cloud_ui",
            rabbitmq_url="amqp://cloud_ui:cloud_ui_dev@rabbitmq:5672/%2Fcloud-ui",
            secrets_provider="vault",
        )
