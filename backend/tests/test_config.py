import pytest
from pydantic import ValidationError

from cloud_ui.config import Settings


def test_settings_require_database_url() -> None:
    with pytest.raises(ValidationError):
        Settings(
            rabbitmq_url="amqp://guest:guest@localhost:5672/",
            api_bind_host="0.0.0.0",
            api_port=8080,
        )


def test_settings_accept_dummy_dev_values() -> None:
    settings = Settings(
        database_url="mysql+pymysql://cloud_ui:cloud_ui_dev@db:3306/cloud_ui",
        rabbitmq_url="amqp://cloud_ui:cloud_ui_dev@rabbitmq:5672/%2Fcloud-ui",
        api_bind_host="0.0.0.0",
        api_port=8080,
    )

    assert settings.api_port == 8080
    assert settings.database_url.unicode_string().startswith("mysql+pymysql://")
