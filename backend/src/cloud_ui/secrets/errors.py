from __future__ import annotations

from typing import Any

from cloud_ui.logging import redact_mapping


class SecretProviderError(Exception):
    code = "secret_provider_error"

    def __init__(
        self,
        *,
        message: str,
        alias: str,
        correlation_id: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        self.message = message
        self.alias = alias
        self.correlation_id = correlation_id
        self.details = redact_mapping(details or {})
        super().__init__(message)

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}(code={self.code!r}, alias={self.alias!r}, "
            f"correlation_id={self.correlation_id!r}, details={self.details!r})"
        )


class SecretForbiddenError(SecretProviderError):
    code = "secret_forbidden"


class SecretNotFoundError(SecretProviderError):
    code = "secret_not_found"


class SecretUnavailableError(SecretProviderError):
    code = "secret_unavailable"


class SecretTimeoutError(SecretProviderError):
    code = "secret_timeout"


class SecretInvalidResponseError(SecretProviderError):
    code = "secret_invalid_response"
