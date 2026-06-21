from __future__ import annotations

from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict

from cloud_ui.logging import redact_mapping

HttpMethod = Literal["GET", "HEAD", "POST", "PUT", "PATCH", "DELETE"]


class AdapterRequestContext(BaseModel):
    model_config = ConfigDict(frozen=True)

    request_id: str
    correlation_id: str
    cloud_id: str
    region_id: str


class OpenStackAdapterError(Exception):
    code = "openstack_error"

    def __init__(
        self,
        *,
        service: str,
        message: str,
        status_code: int | None,
        request_id: str,
        correlation_id: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        self.service = service
        self.message = message
        self.status_code = status_code
        self.request_id = request_id
        self.correlation_id = correlation_id
        self.details = redact_mapping(details or {})
        super().__init__(message)

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}(code={self.code!r}, service={self.service!r}, "
            f"status_code={self.status_code!r}, request_id={self.request_id!r}, "
            f"correlation_id={self.correlation_id!r}, details={self.details!r})"
        )


class OpenStackAuthenticationError(OpenStackAdapterError):
    code = "openstack_authentication_failed"


class OpenStackForbiddenError(OpenStackAdapterError):
    code = "openstack_forbidden"


class OpenStackNotFoundError(OpenStackAdapterError):
    code = "openstack_not_found"


class OpenStackConflictError(OpenStackAdapterError):
    code = "openstack_conflict"


class OpenStackRateLimitError(OpenStackAdapterError):
    code = "openstack_rate_limited"


class OpenStackTemporaryError(OpenStackAdapterError):
    code = "openstack_temporary_error"


class OpenStackTimeoutError(OpenStackAdapterError):
    code = "openstack_timeout"


class OpenStackInvalidResponseError(OpenStackAdapterError):
    code = "openstack_invalid_response"


class RetryDecision(str, Enum):
    RETRY = "retry"
    STOP = "stop"


def should_retry(
    method: HttpMethod,
    error: OpenStackAdapterError,
    *,
    attempt: int,
    max_attempts: int,
) -> RetryDecision:
    if method not in {"GET", "HEAD"}:
        return RetryDecision.STOP
    if attempt >= max_attempts:
        return RetryDecision.STOP
    if isinstance(error, OpenStackTemporaryError | OpenStackTimeoutError | OpenStackRateLimitError):
        return RetryDecision.RETRY
    return RetryDecision.STOP
