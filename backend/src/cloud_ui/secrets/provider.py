from __future__ import annotations

from typing import Protocol

from cloud_ui.secrets.errors import (
    SecretForbiddenError,
    SecretInvalidResponseError,
    SecretNotFoundError,
)
from cloud_ui.secrets.models import SecretDocument, SecretReference, SecretScalar, SecretSchema


class SecretProvider(Protocol):
    def get(
        self,
        reference: SecretReference,
        schema: SecretSchema,
        *,
        correlation_id: str,
    ) -> SecretDocument:
        raise NotImplementedError


class LocalSecretProvider:
    def __init__(
        self,
        *,
        documents: dict[str, dict[str, SecretScalar]],
        allowed_prefix: str,
    ) -> None:
        self._documents = documents
        self._allowed_prefix = allowed_prefix

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

        payload = self._documents.get(reference.path)
        if payload is None:
            raise SecretNotFoundError(
                message="Secret was not found",
                alias=reference.alias,
                correlation_id=correlation_id,
            )

        try:
            data = schema.validate_data(payload)
        except ValueError as exc:
            raise SecretInvalidResponseError(
                message="Secret document failed schema validation",
                alias=reference.alias,
                correlation_id=correlation_id,
                details={"exception": exc.__class__.__name__},
            ) from exc
        return SecretDocument(alias=reference.alias, data=data)
