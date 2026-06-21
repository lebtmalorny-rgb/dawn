from __future__ import annotations

import httpx
import pytest

from cloud_ui.integrations.base import AdapterRequestContext, OpenStackForbiddenError
from cloud_ui.integrations.http import OpenStackHttpClient
from cloud_ui.integrations.nova.adapter import NovaAdapter


def _context() -> AdapterRequestContext:
    return AdapterRequestContext(
        request_id="request-1",
        correlation_id="corr-1",
        cloud_id="lab",
        region_id="RegionOne",
    )


def _adapter(handler: httpx.MockTransport) -> NovaAdapter:
    return NovaAdapter(
        client=OpenStackHttpClient(
            service="nova",
            endpoint="https://nova.example/v2.1",
            timeout_seconds=1.0,
            max_attempts=1,
            transport=handler,
        ),
        microversion="2.96",
    )


def test_nova_adapter_lists_servers_with_microversion_and_pagination() -> None:
    seen_microversion = ""
    seen_query = ""

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal seen_microversion, seen_query
        seen_microversion = request.headers["openstack-api-version"]
        seen_query = request.url.query.decode("ascii")
        return httpx.Response(
            200,
            json={
                "servers": [
                    {
                        "id": "server-1",
                        "name": "vm-1",
                        "status": "ACTIVE",
                        "tenant_id": "project-1",
                        "user_id": "user-1",
                        "created": "2026-06-21T07:00:00Z",
                        "updated": "2026-06-21T07:05:00Z",
                        "OS-EXT-SRV-ATTR:host": "compute-1",
                    }
                ],
                "servers_links": [
                    {
                        "rel": "next",
                        "href": "https://nova.example/v2.1/servers/detail?marker=server-1",
                    }
                ],
            },
        )

    page = _adapter(httpx.MockTransport(handler)).list_servers(
        _context(), limit=1, marker="previous"
    )

    assert seen_microversion == "compute 2.96"
    assert seen_query == "limit=1&marker=previous"
    assert page.next_marker == "server-1"
    assert page.items[0].server_id == "server-1"
    assert page.items[0].host == "compute-1"


def test_nova_adapter_gets_server_detail() -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "server": {
                    "id": "server-1",
                    "name": "vm-1",
                    "status": "SHUTOFF",
                    "tenant_id": "project-1",
                    "user_id": "user-1",
                    "created": "2026-06-21T07:00:00Z",
                    "updated": "2026-06-21T07:05:00Z",
                    "OS-EXT-SRV-ATTR:host": "compute-1",
                }
            },
        )

    server = _adapter(httpx.MockTransport(handler)).get_server(_context(), "server-1")

    assert server.server_id == "server-1"
    assert server.status == "SHUTOFF"


def test_nova_adapter_url_encodes_server_id_path_segment() -> None:
    seen_path = b""

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal seen_path
        seen_path = request.url.raw_path
        return httpx.Response(
            200,
            json={
                "server": {
                    "id": "server/1",
                    "name": "vm-1",
                    "status": "ACTIVE",
                    "tenant_id": "project-1",
                    "user_id": "user-1",
                    "created": "2026-06-21T07:00:00Z",
                    "updated": "2026-06-21T07:05:00Z",
                }
            },
        )

    server = _adapter(httpx.MockTransport(handler)).get_server(_context(), "server/1")

    assert seen_path.endswith(b"/servers/server%2F1")
    assert server.server_id == "server/1"


def test_nova_adapter_lists_hypervisors_services_aggregates_and_server_groups() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if path.endswith("/os-hypervisors/detail"):
            return httpx.Response(
                200,
                json={
                    "hypervisors": [
                        {
                            "id": 1,
                            "hypervisor_hostname": "compute-1",
                            "state": "up",
                            "status": "enabled",
                        }
                    ]
                },
            )
        if path.endswith("/os-services"):
            return httpx.Response(
                200,
                json={
                    "services": [
                        {
                            "id": 10,
                            "binary": "nova-compute",
                            "host": "compute-1",
                            "state": "up",
                            "status": "enabled",
                        }
                    ]
                },
            )
        if path.endswith("/os-aggregates"):
            return httpx.Response(
                200,
                json={"aggregates": [{"id": 20, "name": "az-a", "availability_zone": "az-a"}]},
            )
        if path.endswith("/os-server-groups"):
            return httpx.Response(
                200,
                json={
                    "server_groups": [
                        {"id": "group-1", "name": "anti-affinity", "policies": ["anti-affinity"]}
                    ]
                },
            )
        return httpx.Response(404)

    adapter = _adapter(httpx.MockTransport(handler))

    assert adapter.list_hypervisors(_context())[0].hostname == "compute-1"
    assert adapter.list_compute_services(_context())[0].binary == "nova-compute"
    assert adapter.list_aggregates(_context())[0].name == "az-a"
    assert adapter.list_server_groups(_context())[0].policies == ["anti-affinity"]


def test_nova_adapter_preserves_forbidden() -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(403, json={"forbidden": "denied"})

    with pytest.raises(OpenStackForbiddenError):
        _adapter(httpx.MockTransport(handler)).list_servers(_context(), limit=10)
