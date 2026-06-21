from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import httpx

from cloud_ui.integrations.base import (
    AdapterRequestContext,
    HttpMethod,
    OpenStackAdapterError,
    OpenStackAuthenticationError,
    OpenStackConflictError,
    OpenStackForbiddenError,
    OpenStackInvalidResponseError,
    OpenStackNotFoundError,
    OpenStackRateLimitError,
    OpenStackTemporaryError,
    OpenStackTimeoutError,
    RetryDecision,
    should_retry,
)


class OpenStackHttpClient:
    def __init__(
        self,
        *,
        service: str,
        endpoint: str,
        timeout_seconds: float,
        max_attempts: int,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self._service = service
        self._endpoint = endpoint.rstrip("/")
        self._max_attempts = max_attempts
        self._client = httpx.Client(
            base_url=self._endpoint,
            timeout=timeout_seconds,
            transport=transport,
            follow_redirects=False,
        )

    def get_json(
        self,
        path: str,
        *,
        context: AdapterRequestContext,
        microversion: str | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> dict[str, Any]:
        return self._request_json(
            "GET",
            path,
            context=context,
            microversion=microversion,
            headers=headers,
        )

    def _request_json(
        self,
        method: HttpMethod,
        path: str,
        *,
        context: AdapterRequestContext,
        microversion: str | None,
        headers: Mapping[str, str] | None,
    ) -> dict[str, Any]:
        attempt = 1
        while True:
            try:
                response = self._client.request(
                    method,
                    path,
                    headers=self._headers(context, microversion, headers),
                )
                self._raise_for_status(response, context)
                payload = response.json()
                if not isinstance(payload, dict):
                    raise ValueError("JSON payload is not an object")
                return payload
            except httpx.TimeoutException as exc:
                error: OpenStackAdapterError = OpenStackTimeoutError(
                    service=self._service,
                    message="OpenStack request timed out",
                    status_code=None,
                    request_id=context.request_id,
                    correlation_id=context.correlation_id,
                    details={"exception": exc.__class__.__name__},
                )
            except httpx.RequestError as exc:
                error = OpenStackTemporaryError(
                    service=self._service,
                    message="OpenStack request failed before a response was received",
                    status_code=None,
                    request_id=context.request_id,
                    correlation_id=context.correlation_id,
                    details={"exception": exc.__class__.__name__},
                )
            except ValueError as exc:
                raise OpenStackInvalidResponseError(
                    service=self._service,
                    message="OpenStack response is not a valid JSON object",
                    status_code=None,
                    request_id=context.request_id,
                    correlation_id=context.correlation_id,
                    details={"exception": exc.__class__.__name__},
                ) from exc
            except OpenStackAdapterError as exc:
                error = exc

            if (
                should_retry(
                    method,
                    error,
                    attempt=attempt,
                    max_attempts=self._max_attempts,
                )
                == RetryDecision.RETRY
            ):
                attempt += 1
                continue
            raise error

    def _headers(
        self,
        context: AdapterRequestContext,
        microversion: str | None,
        headers: Mapping[str, str] | None,
    ) -> dict[str, str]:
        result = dict(headers or {})
        result["accept"] = "application/json"
        result["x-openstack-request-id"] = context.request_id
        result["x-correlation-id"] = context.correlation_id
        if microversion is not None:
            result["openstack-api-version"] = microversion
        return result

    def _raise_for_status(self, response: httpx.Response, context: AdapterRequestContext) -> None:
        status = response.status_code
        if status < 400:
            return

        error_type: type[OpenStackAdapterError]
        if status == 401:
            error_type = OpenStackAuthenticationError
        elif status == 403:
            error_type = OpenStackForbiddenError
        elif status == 404:
            error_type = OpenStackNotFoundError
        elif status == 409:
            error_type = OpenStackConflictError
        elif status == 429:
            error_type = OpenStackRateLimitError
        elif status >= 500:
            error_type = OpenStackTemporaryError
        else:
            error_type = OpenStackInvalidResponseError

        raise error_type(
            service=self._service,
            message=f"OpenStack {self._service} returned HTTP {status}",
            status_code=status,
            request_id=context.request_id,
            correlation_id=context.correlation_id,
            details={"status_code": status},
        )
