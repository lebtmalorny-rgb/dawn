from __future__ import annotations

import pytest

from cloud_ui.secrets.errors import SecretForbiddenError, SecretNotFoundError
from cloud_ui.secrets.models import SecretReference, SecretSchema
from cloud_ui.secrets.provider import LocalSecretProvider


def test_package_exports_secret_provider_contract() -> None:
    from cloud_ui.secrets import (
        LocalSecretProvider,
        SecretDocument,
        SecretForbiddenError,
        SecretInvalidResponseError,
        SecretNotFoundError,
        SecretProvider,
        SecretProviderError,
        SecretReference,
        SecretScalar,
        SecretSchema,
        SecretTimeoutError,
        SecretUnavailableError,
    )

    assert LocalSecretProvider.__name__ == "LocalSecretProvider"
    assert SecretDocument.__name__ == "SecretDocument"
    assert SecretProvider.__name__ == "SecretProvider"
    assert SecretProviderError.code == "secret_provider_error"
    assert SecretForbiddenError.code == "secret_forbidden"
    assert SecretNotFoundError.code == "secret_not_found"
    assert SecretUnavailableError.code == "secret_unavailable"
    assert SecretTimeoutError.code == "secret_timeout"
    assert SecretInvalidResponseError.code == "secret_invalid_response"
    assert SecretReference(path="kv/data/cloud-ui/local/session", alias="session")
    assert SecretSchema(required_keys=("value",))
    assert SecretScalar


def test_local_provider_reads_allowed_secret_with_schema() -> None:
    provider = LocalSecretProvider(
        documents={
            "kv/data/cloud-ui/local/session": {
                "signing_key": "synthetic-session-key",
                "active": True,
            }
        },
        allowed_prefix="kv/data/cloud-ui/local/",
    )

    document = provider.get(
        SecretReference(path="kv/data/cloud-ui/local/session", alias="session"),
        SecretSchema(required_keys=("signing_key", "active")),
        correlation_id="corr-1",
    )

    assert document.alias == "session"
    assert document.data == {"signing_key": "synthetic-session-key", "active": True}


def test_local_provider_denies_path_outside_allowed_prefix() -> None:
    provider = LocalSecretProvider(
        documents={"kv/data/other-service/local/test": {"value": "DKB_CANARY"}},
        allowed_prefix="kv/data/cloud-ui/local/",
    )

    with pytest.raises(SecretForbiddenError) as exc_info:
        provider.get(
            SecretReference(path="kv/data/other-service/local/test", alias="other"),
            SecretSchema(required_keys=("value",)),
            correlation_id="corr-2",
        )

    assert exc_info.value.code == "secret_forbidden"
    assert "DKB_CANARY" not in repr(exc_info.value)
    assert "kv/data/other-service" not in repr(exc_info.value)


def test_local_provider_reports_missing_secret_without_value_leak() -> None:
    provider = LocalSecretProvider(documents={}, allowed_prefix="kv/data/cloud-ui/local/")

    with pytest.raises(SecretNotFoundError) as exc_info:
        provider.get(
            SecretReference(path="kv/data/cloud-ui/local/session", alias="session"),
            SecretSchema(required_keys=("signing_key",)),
            correlation_id="corr-3",
        )

    assert exc_info.value.code == "secret_not_found"
    assert "session" in repr(exc_info.value)
    assert "signing_key" not in repr(exc_info.value)
