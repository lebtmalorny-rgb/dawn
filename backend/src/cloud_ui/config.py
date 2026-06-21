from functools import lru_cache
from typing import Literal

from pydantic import AnyUrl, Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

EnvironmentName = Literal["local", "test", "production"]
IdentityProviderName = Literal["mock", "external"]
SessionLimitPolicyName = Literal["deny", "disconnect_oldest"]
SameSiteName = Literal["lax", "strict"]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="CLOUD_UI_", case_sensitive=False)

    database_url: AnyUrl
    rabbitmq_url: AnyUrl
    # Container API binds all interfaces intentionally.
    api_bind_host: str = Field(default="0.0.0.0")  # noqa: S104
    api_port: int = Field(default=8080, ge=1, le=65535)
    log_level: str = Field(default="INFO")
    config_version: str = Field(default="dev")
    environment: EnvironmentName = Field(default="local")
    identity_provider: IdentityProviderName = Field(default="mock")
    mock_identity_enabled: bool = Field(default=True)
    session_idle_timeout_seconds: int = Field(default=900, ge=60)
    session_absolute_lifetime_seconds: int = Field(default=28_800, ge=900)
    simultaneous_session_limit: int = Field(default=1, ge=1)
    session_limit_policy: SessionLimitPolicyName = Field(default="deny")
    session_cookie_secure: bool = Field(default=False)
    session_cookie_samesite: SameSiteName = Field(default="lax")
    trusted_origins: tuple[str, ...] = Field(
        default=("http://localhost", "http://127.0.0.1", "http://testserver")
    )

    @model_validator(mode="after")
    def reject_mock_identity_in_production(self) -> "Settings":
        if self.environment == "production" and (
            self.identity_provider == "mock" or self.mock_identity_enabled
        ):
            raise ValueError("Mock identity provider is not allowed in production")
        return self


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
