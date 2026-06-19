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
