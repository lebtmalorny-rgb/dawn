from __future__ import annotations

import httpx
import pytest

from cloud_ui.integrations.base import AdapterRequestContext, OpenStackTemporaryError
from cloud_ui.integrations.http import OpenStackHttpClient
from cloud_ui.integrations.placement.adapter import PlacementAdapter


def _context() -> AdapterRequestContext:
    return AdapterRequestContext(
        request_id="request-1",
        correlation_id="corr-1",
        cloud_id="lab",
        region_id="RegionOne",
    )


def _adapter(handler: httpx.MockTransport) -> PlacementAdapter:
    return PlacementAdapter(
        client=OpenStackHttpClient(
            service="placement",
            endpoint="https://placement.example",
            timeout_seconds=1.0,
            max_attempts=1,
            transport=handler,
        ),
        microversion="1.39",
    )


def test_placement_lists_resource_providers_with_microversion() -> None:
    seen_microversion = ""

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal seen_microversion
        seen_microversion = request.headers["openstack-api-version"]
        return httpx.Response(
            200,
            json={"resource_providers": [{"uuid": "rp-1", "name": "compute-1", "generation": 7}]},
        )

    providers = _adapter(httpx.MockTransport(handler)).list_resource_providers(_context())

    assert seen_microversion == "placement 1.39"
    assert providers[0].provider_uuid == "rp-1"
    assert providers[0].generation == 7


def test_placement_gets_inventory_and_usage() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/inventories"):
            return httpx.Response(
                200,
                json={
                    "inventories": {
                        "VCPU": {"total": 16, "reserved": 2, "allocation_ratio": 1.0}
                    }
                },
            )
        if request.url.path.endswith("/usages"):
            return httpx.Response(200, json={"usages": {"VCPU": 4}})
        return httpx.Response(404)

    adapter = _adapter(httpx.MockTransport(handler))

    inventory = adapter.get_inventory(_context(), "rp-1")
    usage = adapter.get_usage(_context(), "rp-1")

    assert inventory["VCPU"].total == 16
    assert inventory["VCPU"].reserved == 2
    assert usage["VCPU"] == 4


def test_placement_url_encodes_provider_uuid_path_segment() -> None:
    seen_paths: list[bytes] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen_paths.append(request.url.raw_path)
        if request.url.path.endswith("/inventories"):
            return httpx.Response(
                200,
                json={
                    "inventories": {
                        "VCPU": {"total": 16, "reserved": 2, "allocation_ratio": 1.0}
                    }
                },
            )
        return httpx.Response(404)

    inventory = _adapter(httpx.MockTransport(handler)).get_inventory(_context(), "rp/1")

    assert seen_paths == [b"/resource_providers/rp%2F1/inventories"]
    assert inventory["VCPU"].total == 16


def test_placement_preserves_temporary_error_for_graceful_degradation() -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(503, json={"error": "temporary"})

    with pytest.raises(OpenStackTemporaryError) as exc_info:
        _adapter(httpx.MockTransport(handler)).list_resource_providers(_context())

    assert exc_info.value.code == "openstack_temporary_error"
