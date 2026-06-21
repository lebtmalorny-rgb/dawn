from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class NovaServer(BaseModel):
    model_config = ConfigDict(frozen=True)

    server_id: str
    name: str
    status: str
    project_id: str
    user_id: str
    created_at: str
    updated_at: str
    host: str | None


class NovaServerPage(BaseModel):
    model_config = ConfigDict(frozen=True)

    items: list[NovaServer]
    next_marker: str | None


class NovaHypervisor(BaseModel):
    model_config = ConfigDict(frozen=True)

    hypervisor_id: str
    hostname: str
    state: str
    status: str


class NovaComputeService(BaseModel):
    model_config = ConfigDict(frozen=True)

    service_id: str
    binary: str
    host: str
    state: str
    status: str


class NovaAggregate(BaseModel):
    model_config = ConfigDict(frozen=True)

    aggregate_id: str
    name: str
    availability_zone: str | None


class NovaServerGroup(BaseModel):
    model_config = ConfigDict(frozen=True)

    group_id: str
    name: str
    policies: list[str]
