from functools import lru_cache

from pydantic import AnyUrl, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="CLOUD_UI_", case_sensitive=False)

    database_url: AnyUrl
    rabbitmq_url: AnyUrl
    # Container API binds all interfaces intentionally.
    api_bind_host: str = Field(default="0.0.0.0")  # noqa: S104
    api_port: int = Field(default=8080, ge=1, le=65535)
    log_level: str = Field(default="INFO")
    config_version: str = Field(default="dev")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
