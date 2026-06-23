from __future__ import annotations

from collections.abc import Callable

from cloud_ui.secrets.errors import SecretProviderError
from cloud_ui.secrets.models import SecretReference, SecretSchema
from cloud_ui.secrets.provider import SecretProvider


def build_secret_readiness_probe(
    provider: SecretProvider,
    reference: SecretReference,
    schema: SecretSchema,
) -> Callable[[], str]:
    def probe() -> str:
        try:
            provider.get(reference, schema, correlation_id="readiness-vault")
        except SecretProviderError as exc:
            return f"vault unavailable: {exc.code}"
        return f"vault reachable: {reference.alias}"

    return probe
