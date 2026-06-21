from __future__ import annotations

import httpx
import pytest

from cloud_ui.integrations.base import AdapterRequestContext, OpenStackForbiddenError
from cloud_ui.integrations.http import OpenStackHttpClient
from cloud_ui.integrations.keystone.adapter import KeystoneAdapter


def _context() -> AdapterRequestContext:
    return AdapterRequestContext(
        request_id="request-1",
        correlation_id="corr-1",
        cloud_id="lab",
        region_id="RegionOne",
    )


def test_keystone_adapter_maps_version_discovery() -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "version": {
                    "id": "v3.14",
                    "status": "stable",
                    "links": [{"rel": "self", "href": "https://keystone.example/v3/"}],
                }
            },
        )

    adapter = KeystoneAdapter(
        OpenStackHttpClient(
            service="keystone",
            endpoint="https://keystone.example/v3",
            timeout_seconds=1.0,
            max_attempts=1,
            transport=httpx.MockTransport(handler),
        )
    )

    version = adapter.discover_version(_context())

    assert version.id == "v3.14"
    assert version.status == "stable"
    assert version.self_url == "https://keystone.example/v3/"


def test_keystone_adapter_maps_service_catalog() -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "token": {
                    "project": {"id": "project-1", "name": "demo"},
                    "roles": [{"id": "role-1", "name": "reader"}],
                    "catalog": [
                        {
                            "id": "service-1",
                            "name": "nova",
                            "type": "compute",
                            "endpoints": [
                                {
                                    "id": "endpoint-1",
                                    "interface": "public",
                                    "region": "RegionOne",
                                    "url": "https://nova.example/v2.1",
                                }
                            ],
                        }
                    ],
                }
            },
        )

    adapter = KeystoneAdapter(
        OpenStackHttpClient(
            service="keystone",
            endpoint="https://keystone.example/v3",
            timeout_seconds=1.0,
            max_attempts=1,
            transport=httpx.MockTransport(handler),
        )
    )

    catalog = adapter.get_catalog(_context())

    assert catalog.project_id == "project-1"
    assert catalog.roles == ["reader"]
    assert catalog.services[0].service_type == "compute"
    assert catalog.services[0].endpoints[0].url == "https://nova.example/v2.1"


def test_keystone_adapter_preserves_forbidden_error() -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(403, json={"error": "denied"})

    adapter = KeystoneAdapter(
        OpenStackHttpClient(
            service="keystone",
            endpoint="https://keystone.example/v3",
            timeout_seconds=1.0,
            max_attempts=1,
            transport=httpx.MockTransport(handler),
        )
    )

    with pytest.raises(OpenStackForbiddenError) as exc_info:
        adapter.get_catalog(_context())

    assert exc_info.value.code == "openstack_forbidden"
