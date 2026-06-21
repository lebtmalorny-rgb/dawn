from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class KeystoneVersion(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str
    status: str
    self_url: str


class KeystoneEndpoint(BaseModel):
    model_config = ConfigDict(frozen=True)

    endpoint_id: str
    interface: str
    region: str
    url: str


class KeystoneService(BaseModel):
    model_config = ConfigDict(frozen=True)

    service_id: str
    name: str
    service_type: str
    endpoints: list[KeystoneEndpoint]


class KeystoneCatalog(BaseModel):
    model_config = ConfigDict(frozen=True)

    project_id: str
    project_name: str
    roles: list[str]
    services: list[KeystoneService]
