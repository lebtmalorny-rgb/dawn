from __future__ import annotations

from pathlib import Path
from typing import Any

import httpx

from cloud_ui.secrets.errors import (
    SecretForbiddenError,
    SecretInvalidResponseError,
    SecretNotFoundError,
    SecretTimeoutError,
    SecretUnavailableError,
)
from cloud_ui.secrets.models import SecretDocument, SecretReference, SecretScalar, SecretSchema

_RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}
_SEALED_ERROR_MARKERS = ("sealed", "not initialized", "uninitialized")


class _RetryableSecretUnavailableError(SecretUnavailableError):
    pass


class VaultSecretProvider:
    def __init__(
        self,
        *,
        address: str,
        token_file: Path,
        allowed_prefix: str,
        timeout_seconds: float,
        max_attempts: int,
        ca_bundle: Path | None = None,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self._token_file = token_file
        self._allowed_prefix = allowed_prefix
        self._max_attempts = max(1, max_attempts)
        self._client = httpx.Client(
            base_url=address.rstrip("/"),
            timeout=timeout_seconds,
            verify=str(ca_bundle) if ca_bundle else True,
            transport=transport,
            follow_redirects=False,
        )

    def get(
        self,
        reference: SecretReference,
        schema: SecretSchema,
        *,
        correlation_id: str,
    ) -> SecretDocument:
        if not reference.is_allowed(self._allowed_prefix):
            raise SecretForbiddenError(
                message="Secret path is outside the allowed prefix",
                alias=reference.alias,
                correlation_id=correlation_id,
                details={"path_alias": reference.alias},
            )

        token = self._read_token()
        attempt = 1
        while True:
            try:
                response = self._client.get(
                    f"/v1/{reference.path}",
                    headers={
                        "accept": "application/json",
                        "x-vault-token": token,
                        "x-correlation-id": correlation_id,
                    },
                )
                self._raise_for_status(response, reference, correlation_id)
                return self._document_from_response(response, reference, schema, correlation_id)
            except SecretTimeoutError as exc:
                error: SecretTimeoutError | SecretUnavailableError = exc
            except _RetryableSecretUnavailableError as exc:
                error = exc
            except httpx.TimeoutException as exc:
                error = SecretTimeoutError(
                    message="Vault request timed out",
                    alias=reference.alias,
                    correlation_id=correlation_id,
                    details={
                        "path_alias": reference.alias,
                        "attempt": attempt,
                        "exception": exc.__class__.__name__,
                    },
                )
            except httpx.RequestError as exc:
                error = _RetryableSecretUnavailableError(
                    message="Vault request failed before a response was received",
                    alias=reference.alias,
                    correlation_id=correlation_id,
                    details={
                        "path_alias": reference.alias,
                        "attempt": attempt,
                        "exception": exc.__class__.__name__,
                    },
                )

            if attempt >= self._max_attempts:
                raise error
            attempt += 1

    def _read_token(self) -> str:
        return self._token_file.read_text(encoding="utf-8").strip()

    def _raise_for_status(
        self,
        response: httpx.Response,
        reference: SecretReference,
        correlation_id: str,
    ) -> None:
        status = response.status_code
        if status < 400:
            return

        details = {"path_alias": reference.alias, "status_code": status}
        if status == 403:
            raise SecretForbiddenError(
                message="Vault denied secret access",
                alias=reference.alias,
                correlation_id=correlation_id,
                details=details,
            )
        if status == 404:
            raise SecretNotFoundError(
                message="Vault secret was not found",
                alias=reference.alias,
                correlation_id=correlation_id,
                details=details,
            )
        if status in _RETRYABLE_STATUS_CODES:
            error_type: type[SecretUnavailableError]
            error_type = (
                SecretUnavailableError
                if self._is_permanent_unavailable_response(response)
                else _RetryableSecretUnavailableError
            )
            raise error_type(
                message="Vault is temporarily unavailable",
                alias=reference.alias,
                correlation_id=correlation_id,
                details=details,
            )
        raise SecretInvalidResponseError(
            message="Vault returned an unexpected error status",
            alias=reference.alias,
            correlation_id=correlation_id,
            details=details,
        )

    def _document_from_response(
        self,
        response: httpx.Response,
        reference: SecretReference,
        schema: SecretSchema,
        correlation_id: str,
    ) -> SecretDocument:
        try:
            payload = response.json()
            data = self._extract_kv_v2_data(payload)
            validated = schema.validate_data(data)
        except (ValueError, TypeError) as exc:
            raise SecretInvalidResponseError(
                message="Vault response did not match the expected secret schema",
                alias=reference.alias,
                correlation_id=correlation_id,
                details={"path_alias": reference.alias, "exception": exc.__class__.__name__},
            ) from exc
        return SecretDocument(alias=reference.alias, data=validated)

    def _is_permanent_unavailable_response(self, response: httpx.Response) -> bool:
        try:
            payload = response.json()
        except ValueError:
            return False
        if not isinstance(payload, dict):
            return False
        errors = payload.get("errors")
        if not isinstance(errors, list):
            return False
        for item in errors:
            if isinstance(item, str) and self._is_permanent_unavailable_message(item):
                return True
        return False

    def _is_permanent_unavailable_message(self, message: str) -> bool:
        normalized = message.lower()
        return any(marker in normalized for marker in _SEALED_ERROR_MARKERS)

    def _extract_kv_v2_data(self, payload: Any) -> dict[str, SecretScalar]:
        if not isinstance(payload, dict):
            raise ValueError("Vault JSON payload is not an object")
        envelope = payload.get("data")
        if not isinstance(envelope, dict):
            raise ValueError("Vault KV v2 data envelope is missing")
        raw_data = envelope.get("data")
        if not isinstance(raw_data, dict):
            raise ValueError("Vault KV v2 secret data is missing")

        data: dict[str, SecretScalar] = {}
        for key, value in raw_data.items():
            if not isinstance(key, str):
                raise ValueError("Vault secret key is not a string")
            if not isinstance(value, str | int | float | bool):
                raise ValueError("Vault secret value is not scalar")
            data[key] = value
        return data
