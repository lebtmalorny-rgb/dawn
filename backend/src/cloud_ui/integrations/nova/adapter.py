from __future__ import annotations

from collections.abc import Mapping
from typing import Any
from urllib.parse import parse_qs, quote, urlencode, urlparse

from cloud_ui.integrations.base import AdapterRequestContext, OpenStackInvalidResponseError
from cloud_ui.integrations.http import OpenStackHttpClient
from cloud_ui.integrations.nova.dto import (
    NovaAggregate,
    NovaComputeService,
    NovaHypervisor,
    NovaServer,
    NovaServerGroup,
    NovaServerPage,
)


class NovaAdapter:
    def __init__(self, *, client: OpenStackHttpClient, microversion: str) -> None:
        self._client = client
        self._microversion = f"compute {microversion}"

    def list_servers(
        self, context: AdapterRequestContext, *, limit: int, marker: str | None = None
    ) -> NovaServerPage:
        query = {"limit": str(limit)}
        if marker is not None:
            query["marker"] = marker
        payload = self._client.get_json(
            f"/servers/detail?{urlencode(query)}",
            context=context,
            microversion=self._microversion,
        )
        try:
            return NovaServerPage(
                items=[_server(_mapping(server)) for server in _list(payload["servers"])],
                next_marker=_next_marker(payload.get("servers_links", [])),
            )
        except (KeyError, TypeError) as exc:
            raise _invalid(context, "Invalid Nova server list payload") from exc

    def get_server(self, context: AdapterRequestContext, server_id: str) -> NovaServer:
        encoded_server_id = quote(server_id, safe="")
        payload = self._client.get_json(
            f"/servers/{encoded_server_id}",
            context=context,
            microversion=self._microversion,
        )
        try:
            return _server(_mapping(payload["server"]))
        except (KeyError, TypeError) as exc:
            raise _invalid(context, "Invalid Nova server detail payload") from exc

    def list_hypervisors(self, context: AdapterRequestContext) -> list[NovaHypervisor]:
        payload = self._client.get_json(
            "/os-hypervisors/detail",
            context=context,
            microversion=self._microversion,
        )
        try:
            return [
                NovaHypervisor(
                    hypervisor_id=str(item["id"]),
                    hostname=str(item["hypervisor_hostname"]),
                    state=str(item["state"]),
                    status=str(item["status"]),
                )
                for item in (_mapping(value) for value in _list(payload["hypervisors"]))
            ]
        except (KeyError, TypeError) as exc:
            raise _invalid(context, "Invalid Nova hypervisor payload") from exc

    def list_compute_services(self, context: AdapterRequestContext) -> list[NovaComputeService]:
        payload = self._client.get_json(
            "/os-services",
            context=context,
            microversion=self._microversion,
        )
        try:
            return [
                NovaComputeService(
                    service_id=str(item["id"]),
                    binary=str(item["binary"]),
                    host=str(item["host"]),
                    state=str(item["state"]),
                    status=str(item["status"]),
                )
                for item in (_mapping(value) for value in _list(payload["services"]))
            ]
        except (KeyError, TypeError) as exc:
            raise _invalid(context, "Invalid Nova compute service payload") from exc

    def list_aggregates(self, context: AdapterRequestContext) -> list[NovaAggregate]:
        payload = self._client.get_json(
            "/os-aggregates",
            context=context,
            microversion=self._microversion,
        )
        try:
            return [
                NovaAggregate(
                    aggregate_id=str(item["id"]),
                    name=str(item["name"]),
                    availability_zone=(
                        str(item["availability_zone"])
                        if item.get("availability_zone") is not None
                        else None
                    ),
                )
                for item in (_mapping(value) for value in _list(payload["aggregates"]))
            ]
        except (KeyError, TypeError) as exc:
            raise _invalid(context, "Invalid Nova aggregate payload") from exc

    def list_server_groups(self, context: AdapterRequestContext) -> list[NovaServerGroup]:
        payload = self._client.get_json(
            "/os-server-groups",
            context=context,
            microversion=self._microversion,
        )
        try:
            return [
                NovaServerGroup(
                    group_id=str(item["id"]),
                    name=str(item["name"]),
                    policies=[str(policy) for policy in _list(item["policies"])],
                )
                for item in (_mapping(value) for value in _list(payload["server_groups"]))
            ]
        except (KeyError, TypeError) as exc:
            raise _invalid(context, "Invalid Nova server group payload") from exc


def _server(payload: Mapping[str, Any]) -> NovaServer:
    host = payload.get("OS-EXT-SRV-ATTR:host")
    return NovaServer(
        server_id=str(payload["id"]),
        name=str(payload["name"]),
        status=str(payload["status"]),
        project_id=str(payload["tenant_id"]),
        user_id=str(payload["user_id"]),
        created_at=str(payload["created"]),
        updated_at=str(payload["updated"]),
        host=host if isinstance(host, str) else None,
    )


def _next_marker(links: object) -> str | None:
    if not isinstance(links, list):
        return None
    for link in links:
        if not isinstance(link, Mapping):
            continue
        if link.get("rel") != "next" or not isinstance(link.get("href"), str):
            continue
        marker = parse_qs(urlparse(str(link["href"])).query).get("marker")
        return marker[0] if marker else None
    return None


def _mapping(value: object) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise TypeError("Expected mapping")
    return value


def _list(value: object) -> list[object]:
    if not isinstance(value, list):
        raise TypeError("Expected list")
    return value


def _invalid(context: AdapterRequestContext, message: str) -> OpenStackInvalidResponseError:
    return OpenStackInvalidResponseError(
        service="nova",
        message=message,
        status_code=None,
        request_id=context.request_id,
        correlation_id=context.correlation_id,
    )
