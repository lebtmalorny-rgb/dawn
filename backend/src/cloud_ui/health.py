from collections.abc import Callable
from typing import Literal

from pydantic import BaseModel

from cloud_ui.config import Settings
from cloud_ui.db import check_database
from cloud_ui.mq import check_rabbitmq
from cloud_ui.secrets.models import SecretReference, SecretSchema
from cloud_ui.secrets.readiness import build_secret_readiness_probe
from cloud_ui.secrets.vault import VaultSecretProvider

DependencyStatus = Literal["ok", "down"]
HealthStatus = Literal["ok", "degraded"]


class DependencyState(BaseModel):
    status: DependencyStatus
    detail: str


class HealthReport(BaseModel):
    status: HealthStatus
    dependencies: dict[str, DependencyState]


ReadinessCheck = Callable[[], HealthReport]


def build_readiness_check(settings: Settings) -> ReadinessCheck:
    vault_probe: Callable[[], str] | None = None
    if settings.secrets_provider == "vault":
        if settings.vault_addr is None or settings.vault_token_file is None:
            raise ValueError("Vault address and token file are required when Vault is enabled")
        vault_probe = build_secret_readiness_probe(
            provider=VaultSecretProvider(
                address=settings.vault_addr.unicode_string(),
                token_file=settings.vault_token_file,
                allowed_prefix=settings.vault_allowed_prefix,
                timeout_seconds=settings.vault_timeout_seconds,
                max_attempts=settings.vault_max_attempts,
                ca_bundle=settings.vault_ca_bundle,
            ),
            reference=SecretReference(
                path=f"{settings.vault_allowed_prefix}session",
                alias="session",
            ),
            schema=SecretSchema(required_keys=("value",)),
        )

    def check() -> HealthReport:
        dependencies = {
            "database": _probe_dependency(
                lambda: check_database(settings.database_url.unicode_string())
            ),
            "rabbitmq": _probe_dependency(
                lambda: check_rabbitmq(settings.rabbitmq_url.unicode_string())
            ),
        }
        if vault_probe is not None:
            dependencies["vault"] = _probe_vault_dependency(vault_probe)
        overall_status: HealthStatus = (
            "degraded"
            if any(dependency.status == "down" for dependency in dependencies.values())
            else "ok"
        )
        return HealthReport(status=overall_status, dependencies=dependencies)

    return check


def _probe_vault_dependency(probe: Callable[[], str]) -> DependencyState:
    detail = probe()
    status: DependencyStatus = "down" if detail.startswith("vault unavailable:") else "ok"
    return DependencyState(status=status, detail=detail)


def _probe_dependency(probe: Callable[[], str]) -> DependencyState:
    try:
        detail = probe()
    except Exception:
        return DependencyState(status="down", detail="unreachable")
    return DependencyState(status="ok", detail=detail)
