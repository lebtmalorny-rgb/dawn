from __future__ import annotations

from pathlib import Path

import httpx
import pytest

from cloud_ui.secrets.errors import (
    SecretForbiddenError,
    SecretInvalidResponseError,
    SecretNotFoundError,
    SecretTimeoutError,
    SecretUnavailableError,
)
from cloud_ui.secrets.models import SecretReference, SecretSchema
from cloud_ui.secrets.vault import VaultSecretProvider


def _canary_value() -> str:
    return "vault-token-" + "DKB_CANARY"


def _token_file(tmp_path: Path, value: str) -> Path:
    path = tmp_path / "vault-token"
    path.write_text(f"{value}\n", encoding="utf-8")
    return path


def _provider(
    tmp_path: Path,
    transport: httpx.BaseTransport,
    token_value: str,
    *,
    max_attempts: int = 1,
    allowed_prefix: str = "kv/data/cloud-ui/local/",
) -> VaultSecretProvider:
    return VaultSecretProvider(
        address="https://vault.example/",
        token_file=_token_file(tmp_path, token_value),
        allowed_prefix=allowed_prefix,
        timeout_seconds=1.0,
        max_attempts=max_attempts,
        transport=transport,
    )


def _reference(path: str = "kv/data/cloud-ui/local/session") -> SecretReference:
    return SecretReference(path=path, alias="session")


def _schema() -> SecretSchema:
    return SecretSchema(required_keys=("signing_key", "active"))


def test_vault_provider_reads_kv_v2_secret_with_token_and_correlation_headers(
    tmp_path: Path,
) -> None:
    seen: dict[str, str] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url_path"] = request.url.path
        seen["accept"] = request.headers["accept"]
        seen["x-vault-token"] = request.headers["x-vault-token"]
        seen["x-correlation-id"] = request.headers["x-correlation-id"]
        return httpx.Response(
            200,
            json={
                "data": {
                    "data": {
                        "signing_key": "synthetic-session-key",
                        "active": True,
                    }
                }
            },
        )

    provider = _provider(tmp_path, httpx.MockTransport(handler), "vault-token")

    document = provider.get(_reference(), _schema(), correlation_id="corr-1")

    assert document.alias == "session"
    assert document.data == {"signing_key": "synthetic-session-key", "active": True}
    assert seen == {
        "url_path": "/v1/kv/data/cloud-ui/local/session",
        "accept": "application/json",
        "x-vault-token": "vault-token",
        "x-correlation-id": "corr-1",
    }


def test_vault_provider_denies_path_outside_allowed_prefix_before_reading_token(
    tmp_path: Path,
) -> None:
    calls = 0
    missing_token_file = tmp_path / "missing-token"

    def handler(_request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(200, json={"data": {"data": {"value": "DKB_CANARY"}}})

    provider = VaultSecretProvider(
        address="https://vault.example",
        token_file=missing_token_file,
        allowed_prefix="kv/data/cloud-ui/local/",
        timeout_seconds=1.0,
        max_attempts=1,
        transport=httpx.MockTransport(handler),
    )

    with pytest.raises(SecretForbiddenError) as exc_info:
        provider.get(
            SecretReference(path="kv/data/other-service/local/session", alias="other"),
            SecretSchema(required_keys=("value",)),
            correlation_id="corr-denied-local",
        )

    assert calls == 0
    rendered = repr(exc_info.value)
    assert "DKB_CANARY" not in rendered
    assert "kv/data/other-service" not in rendered


def test_vault_provider_maps_403_without_retry_or_secret_leak(tmp_path: Path) -> None:
    calls = 0

    def handler(_request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(403, json={"errors": ["denied DKB_CANARY"]})

    provider = _provider(tmp_path, httpx.MockTransport(handler), _canary_value(), max_attempts=3)

    with pytest.raises(SecretForbiddenError) as exc_info:
        provider.get(_reference(), _schema(), correlation_id="corr-403")

    assert calls == 1
    rendered = repr(exc_info.value)
    assert "DKB_CANARY" not in rendered
    assert "vault-token" not in rendered
    assert "kv/data/cloud-ui/local/session" not in rendered


def test_vault_provider_maps_404_to_not_found(tmp_path: Path) -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, json={"errors": ["missing"]})

    provider = _provider(tmp_path, httpx.MockTransport(handler), _canary_value())

    with pytest.raises(SecretNotFoundError) as exc_info:
        provider.get(_reference(), _schema(), correlation_id="corr-404")

    assert exc_info.value.code == "secret_not_found"


def test_vault_provider_retries_503_then_succeeds_within_max_attempts(
    tmp_path: Path,
) -> None:
    calls = 0

    def handler(_request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        if calls == 1:
            return httpx.Response(503, json={"errors": ["temporary backend unavailable"]})
        return httpx.Response(
            200,
            json={"data": {"data": {"signing_key": "after-retry", "active": True}}},
        )

    provider = _provider(tmp_path, httpx.MockTransport(handler), _canary_value(), max_attempts=2)

    document = provider.get(_reference(), _schema(), correlation_id="corr-retry")

    assert calls == 2
    assert document.data == {"signing_key": "after-retry", "active": True}


def test_vault_provider_does_not_retry_sealed_503_or_leak_details(tmp_path: Path) -> None:
    calls = 0

    def handler(_request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(503, json={"errors": ["Vault is sealed DKB_CANARY"]})

    provider = _provider(tmp_path, httpx.MockTransport(handler), _canary_value(), max_attempts=3)

    with pytest.raises(SecretUnavailableError) as exc_info:
        provider.get(_reference(), _schema(), correlation_id="corr-sealed")

    assert calls == 1
    rendered = repr(exc_info.value)
    assert "DKB_CANARY" not in rendered
    assert "vault-token" not in rendered
    assert "kv/data/cloud-ui/local/session" not in rendered


def test_vault_provider_does_not_retry_uninitialized_503(tmp_path: Path) -> None:
    calls = 0

    def handler(_request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(503, json={"errors": ["Vault is not initialized"]})

    provider = _provider(tmp_path, httpx.MockTransport(handler), _canary_value(), max_attempts=3)

    with pytest.raises(SecretUnavailableError) as exc_info:
        provider.get(_reference(), _schema(), correlation_id="corr-uninitialized")

    assert calls == 1
    assert exc_info.value.code == "secret_unavailable"


def test_vault_provider_maps_timeout_after_attempts(tmp_path: Path) -> None:
    calls = 0

    def handler(_request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        raise httpx.ReadTimeout("timeout DKB_CANARY")

    provider = _provider(tmp_path, httpx.MockTransport(handler), _canary_value(), max_attempts=2)

    with pytest.raises(SecretTimeoutError) as exc_info:
        provider.get(_reference(), _schema(), correlation_id="corr-timeout")

    assert calls == 2
    rendered = repr(exc_info.value)
    assert "DKB_CANARY" not in rendered
    assert "vault-token" not in rendered


@pytest.mark.parametrize(
    "payload",
    [
        {"data": {"metadata": {"version": 1}}},
        {"data": {"data": {"signing_key": "ok", "active": {"nested": True}}}},
        {"data": {"data": {"signing_key": "ok"}}},
        ["not", "an", "object"],
    ],
)
def test_vault_provider_maps_malformed_kv_v2_payload_to_invalid_response(
    tmp_path: Path,
    payload: object,
) -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=payload)

    provider = _provider(tmp_path, httpx.MockTransport(handler), _canary_value())

    with pytest.raises(SecretInvalidResponseError) as exc_info:
        provider.get(_reference(), _schema(), correlation_id="corr-malformed")

    assert exc_info.value.code == "secret_invalid_response"


def test_vault_provider_maps_transport_tls_failure_without_token_leak(tmp_path: Path) -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("TLS handshake failed DKB_CANARY")

    provider = _provider(tmp_path, httpx.MockTransport(handler), _canary_value(), max_attempts=1)

    with pytest.raises(SecretUnavailableError) as exc_info:
        provider.get(_reference(), _schema(), correlation_id="corr-tls")

    rendered = repr(exc_info.value)
    assert exc_info.value.code == "secret_unavailable"
    assert "DKB_CANARY" not in rendered
    assert "vault-token" not in rendered
