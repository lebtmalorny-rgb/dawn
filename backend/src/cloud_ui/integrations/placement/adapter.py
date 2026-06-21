from __future__ import annotations

from collections.abc import Mapping
from typing import Any
from urllib.parse import quote

from cloud_ui.integrations.base import AdapterRequestContext, OpenStackInvalidResponseError
from cloud_ui.integrations.http import OpenStackHttpClient
from cloud_ui.integrations.placement.dto import (
    PlacementInventory,
    PlacementResourceProvider,
)


class PlacementAdapter:
    def __init__(self, *, client: OpenStackHttpClient, microversion: str) -> None:
        self._client = client
        self._microversion = f"placement {microversion}"

    def list_resource_providers(
        self, context: AdapterRequestContext
    ) -> list[PlacementResourceProvider]:
        payload = self._client.get_json(
            "/resource_providers",
            context=context,
            microversion=self._microversion,
        )
        try:
            return [
                PlacementResourceProvider(
                    provider_uuid=str(item["uuid"]),
                    name=str(item["name"]),
                    generation=int(item["generation"]),
                )
                for item in (_mapping(value) for value in _list(payload["resource_providers"]))
            ]
        except (KeyError, TypeError, ValueError) as exc:
            raise _invalid(context, "Invalid Placement resource provider payload") from exc

    def get_inventory(
        self, context: AdapterRequestContext, provider_uuid: str
    ) -> dict[str, PlacementInventory]:
        encoded_provider_uuid = quote(provider_uuid, safe="")
        payload = self._client.get_json(
            f"/resource_providers/{encoded_provider_uuid}/inventories",
            context=context,
            microversion=self._microversion,
        )
        try:
            inventories = _mapping(payload["inventories"])
            return {
                resource_class: PlacementInventory(
                    total=int(values["total"]),
                    reserved=int(values["reserved"]),
                    allocation_ratio=float(values["allocation_ratio"]),
                )
                for resource_class, values in (
                    (str(resource_class), _mapping(values))
                    for resource_class, values in inventories.items()
                )
            }
        except (KeyError, TypeError, ValueError) as exc:
            raise _invalid(context, "Invalid Placement inventory payload") from exc

    def get_usage(self, context: AdapterRequestContext, provider_uuid: str) -> dict[str, int]:
        encoded_provider_uuid = quote(provider_uuid, safe="")
        payload = self._client.get_json(
            f"/resource_providers/{encoded_provider_uuid}/usages",
            context=context,
            microversion=self._microversion,
        )
        try:
            usages = _mapping(payload["usages"])
            return {str(resource_class): int(value) for resource_class, value in usages.items()}
        except (KeyError, TypeError, ValueError) as exc:
            raise _invalid(context, "Invalid Placement usage payload") from exc


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
        service="placement",
        message=message,
        status_code=None,
        request_id=context.request_id,
        correlation_id=context.correlation_id,
    )
