from __future__ import annotations

from cloud_ui.secrets.errors import SecretUnavailableError
from cloud_ui.secrets.models import SecretDocument, SecretReference, SecretSchema
from cloud_ui.secrets.readiness import build_secret_readiness_probe


class _OkProvider:
    def get(
        self,
        reference: SecretReference,
        schema: SecretSchema,
        *,
        correlation_id: str,
    ) -> SecretDocument:
        return SecretDocument(alias=reference.alias, data={"value": "synthetic"})


class _FailingProvider:
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
            details={"token": "synthetic-token"},
        )


def test_secret_readiness_probe_returns_safe_ok_detail() -> None:
    probe = build_secret_readiness_probe(
        provider=_OkProvider(),
        reference=SecretReference(path="kv/data/cloud-ui/local/session", alias="session"),
        schema=SecretSchema(required_keys=("value",)),
    )

    assert probe() == "vault reachable: session"


def test_secret_readiness_probe_returns_safe_failure_detail() -> None:
    probe = build_secret_readiness_probe(
        provider=_FailingProvider(),
        reference=SecretReference(path="kv/data/cloud-ui/local/session", alias="session"),
        schema=SecretSchema(required_keys=("value",)),
    )

    assert probe() == "vault unavailable: secret_unavailable"
