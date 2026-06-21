from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from cloud_ui.integrations.base import AdapterRequestContext, OpenStackInvalidResponseError
from cloud_ui.integrations.http import OpenStackHttpClient
from cloud_ui.integrations.keystone.dto import (
    KeystoneCatalog,
    KeystoneEndpoint,
    KeystoneService,
    KeystoneVersion,
)


class KeystoneAdapter:
    def __init__(self, client: OpenStackHttpClient) -> None:
        self._client = client

    def discover_version(self, context: AdapterRequestContext) -> KeystoneVersion:
        payload = self._client.get_json("/", context=context)
        try:
            version = _mapping(payload["version"])
            links = _list(version["links"])
            self_url = next(
                str(_mapping(link)["href"])
                for link in links
                if _mapping(link).get("rel") == "self"
            )
            return KeystoneVersion(
                id=str(version["id"]),
                status=str(version["status"]),
                self_url=self_url,
            )
        except (KeyError, TypeError, StopIteration) as exc:
            raise _invalid_response(context, "Invalid Keystone version payload") from exc

    def get_catalog(self, context: AdapterRequestContext) -> KeystoneCatalog:
        payload = self._client.get_json("/auth/catalog-fixture", context=context)
        try:
            catalog_root = _mapping(payload["token"])
            project = _mapping(catalog_root["project"])
            roles = [str(_mapping(role)["name"]) for role in _list(catalog_root["roles"])]
            services = [
                _service_from_payload(_mapping(service))
                for service in _list(catalog_root["catalog"])
            ]
            return KeystoneCatalog(
                project_id=str(project["id"]),
                project_name=str(project["name"]),
                roles=roles,
                services=services,
            )
        except (KeyError, TypeError) as exc:
            raise _invalid_response(context, "Invalid Keystone catalog payload") from exc


def _service_from_payload(payload: Mapping[str, Any]) -> KeystoneService:
    endpoints = [
        KeystoneEndpoint(
            endpoint_id=str(endpoint["id"]),
            interface=str(endpoint["interface"]),
            region=str(endpoint["region"]),
            url=str(endpoint["url"]),
        )
        for endpoint in (_mapping(item) for item in _list(payload["endpoints"]))
    ]
    return KeystoneService(
        service_id=str(payload["id"]),
        name=str(payload["name"]),
        service_type=str(payload["type"]),
        endpoints=endpoints,
    )


def _mapping(value: object) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise TypeError("Expected mapping")
    return value


def _list(value: object) -> list[object]:
    if not isinstance(value, list):
        raise TypeError("Expected list")
    return value


def _invalid_response(
    context: AdapterRequestContext, message: str
) -> OpenStackInvalidResponseError:
    return OpenStackInvalidResponseError(
        service="keystone",
        message=message,
        status_code=None,
        request_id=context.request_id,
        correlation_id=context.correlation_id,
    )
