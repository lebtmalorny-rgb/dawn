from __future__ import annotations

import httpx
import pytest

from cloud_ui.integrations.base import (
    AdapterRequestContext,
    OpenStackForbiddenError,
    OpenStackInvalidResponseError,
    OpenStackTemporaryError,
    OpenStackTimeoutError,
)
from cloud_ui.integrations.http import OpenStackHttpClient


def _context() -> AdapterRequestContext:
    return AdapterRequestContext(
        request_id="request-1",
        correlation_id="corr-1",
        cloud_id="lab",
        region_id="RegionOne",
    )


def test_http_client_sends_correlation_and_microversion_headers() -> None:
    seen_headers: dict[str, str] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen_headers["x-openstack-request-id"] = request.headers["x-openstack-request-id"]
        seen_headers["x-correlation-id"] = request.headers["x-correlation-id"]
        seen_headers["openstack-api-version"] = request.headers["openstack-api-version"]
        return httpx.Response(200, json={"ok": True})

    client = OpenStackHttpClient(
        service="nova",
        endpoint="https://nova.example/v2.1",
        transport=httpx.MockTransport(handler),
        timeout_seconds=1.0,
        max_attempts=1,
    )

    payload = client.get_json("/servers/detail", context=_context(), microversion="compute 2.96")

    assert payload == {"ok": True}
    assert seen_headers == {
        "x-openstack-request-id": "request-1",
        "x-correlation-id": "corr-1",
        "openstack-api-version": "compute 2.96",
    }


def test_http_client_does_not_allow_custom_headers_to_override_context_headers() -> None:
    seen_headers: dict[str, str] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen_headers["x-openstack-request-id"] = request.headers["x-openstack-request-id"]
        seen_headers["x-correlation-id"] = request.headers["x-correlation-id"]
        seen_headers["openstack-api-version"] = request.headers["openstack-api-version"]
        seen_headers["x-extra"] = request.headers["x-extra"]
        return httpx.Response(200, json={"ok": True})

    client = OpenStackHttpClient(
        service="nova",
        endpoint="https://nova.example/v2.1",
        transport=httpx.MockTransport(handler),
        timeout_seconds=1.0,
        max_attempts=1,
    )

    payload = client.get_json(
        "/servers/detail",
        context=_context(),
        microversion="compute 2.96",
        headers={
            "x-openstack-request-id": "bad-request-id",
            "x-correlation-id": "bad-correlation-id",
            "openstack-api-version": "compute 2.1",
            "x-extra": "visible",
        },
    )

    assert payload == {"ok": True}
    assert seen_headers == {
        "x-openstack-request-id": "request-1",
        "x-correlation-id": "corr-1",
        "openstack-api-version": "compute 2.96",
        "x-extra": "visible",
    }


def test_http_client_does_not_retry_permanent_403() -> None:
    calls = 0

    def handler(_request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(403, json={"forbidden": {"message": "denied"}})

    client = OpenStackHttpClient(
        service="nova",
        endpoint="https://nova.example/v2.1",
        transport=httpx.MockTransport(handler),
        timeout_seconds=1.0,
        max_attempts=3,
    )

    with pytest.raises(OpenStackForbiddenError) as exc_info:
        client.get_json("/servers/detail", context=_context())

    assert exc_info.value.status_code == 403
    assert calls == 1


def test_http_client_retries_temporary_503_then_succeeds() -> None:
    calls = 0

    def handler(_request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        if calls == 1:
            return httpx.Response(503, json={"error": "temporary"})
        return httpx.Response(200, json={"ok": True})

    client = OpenStackHttpClient(
        service="placement",
        endpoint="https://placement.example",
        transport=httpx.MockTransport(handler),
        timeout_seconds=1.0,
        max_attempts=2,
    )

    assert client.get_json("/resource_providers", context=_context()) == {"ok": True}
    assert calls == 2


def test_http_client_rejects_malformed_json() -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=b"{not-json")

    client = OpenStackHttpClient(
        service="keystone",
        endpoint="https://keystone.example/v3",
        transport=httpx.MockTransport(handler),
        timeout_seconds=1.0,
        max_attempts=1,
    )

    with pytest.raises(OpenStackInvalidResponseError):
        client.get_json("/", context=_context())


def test_http_client_maps_timeout_to_distinct_error_after_retries() -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("timeout")

    client = OpenStackHttpClient(
        service="nova",
        endpoint="https://nova.example/v2.1",
        transport=httpx.MockTransport(handler),
        timeout_seconds=1.0,
        max_attempts=1,
    )

    with pytest.raises(OpenStackTimeoutError) as exc_info:
        client.get_json("/servers/detail", context=_context())

    assert exc_info.value.code == "openstack_timeout"


def test_http_client_maps_transport_error_to_temporary_error_after_retries() -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("network unavailable")

    client = OpenStackHttpClient(
        service="nova",
        endpoint="https://nova.example/v2.1",
        transport=httpx.MockTransport(handler),
        timeout_seconds=1.0,
        max_attempts=1,
    )

    with pytest.raises(OpenStackTemporaryError) as exc_info:
        client.get_json("/servers/detail", context=_context())

    assert exc_info.value.code == "openstack_temporary_error"
