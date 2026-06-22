from __future__ import annotations

from datetime import datetime
from typing import Any, Generic, Literal, TypeVar

from pydantic import BaseModel, ConfigDict, Field

SortDirection = Literal["asc", "desc"]
T = TypeVar("T")


class InventoryWarning(BaseModel):
    model_config = ConfigDict(frozen=True)

    code: str
    title: str
    detail: str
    source: str


class InventoryFreshness(BaseModel):
    model_config = ConfigDict(frozen=True)

    observed_at: datetime | None
    last_successful_sync_at: datetime | None
    stale_after_seconds: int
    is_stale: bool


class InstanceItem(BaseModel):
    model_config = ConfigDict(frozen=True)

    cloud_id: str
    region_id: str
    instance_id: str
    name: str
    project_id: str
    user_id: str
    status: str
    power_state: str
    task_state: str | None
    vm_state: str
    host_name: str | None
    hypervisor_id: str | None
    availability_zone: str | None
    flavor_id: str | None
    vcpus: int
    ram_mb: int
    disk_gb: int
    image_id: str | None
    boot_volume_id: str | None
    addresses: dict[str, Any] = Field(default_factory=dict)
    source_created_at: datetime | None
    source_updated_at: datetime | None
    observed_at: datetime
    sync_generation: int
    sync_status: str


class HypervisorItem(BaseModel):
    model_config = ConfigDict(frozen=True)

    cloud_id: str
    region_id: str
    hypervisor_id: str
    host_name: str
    service_id: str | None
    service_status: str
    service_state: str
    hypervisor_type: str | None
    hypervisor_version: str | None
    availability_zone: str | None
    aggregates: list[str] = Field(default_factory=list)
    vcpus_total: int
    vcpus_used: int
    ram_mb_total: int
    ram_mb_used: int
    disk_gb_total: int
    disk_gb_used: int
    running_vms: int
    disabled_reason: str | None
    maintenance_status: str | None
    observed_at: datetime
    sync_generation: int
    sync_status: str


class InventoryPage(BaseModel, Generic[T]):
    model_config = ConfigDict(frozen=True)

    items: list[T]
    next_cursor: str | None = None
    partial: bool = False
    warnings: list[InventoryWarning] = Field(default_factory=list)
    freshness: InventoryFreshness | None = None


class InventorySort(BaseModel):
    model_config = ConfigDict(frozen=True)

    field: str
    direction: SortDirection


class InstanceFilters(BaseModel):
    model_config = ConfigDict(frozen=True)

    cloud_id: str
    region_id: str
    q: str | None = None
    project_id: str | None = None
    status: str | None = None
    host_name: str | None = None
    hypervisor_id: str | None = None
    availability_zone: str | None = None
    group_id: str | None = None


class HypervisorFilters(BaseModel):
    model_config = ConfigDict(frozen=True)

    cloud_id: str
    region_id: str
    q: str | None = None
    service_status: str | None = None
    service_state: str | None = None
    host_name: str | None = None
    availability_zone: str | None = None
    maintenance_status: str | None = None
    group_id: str | None = None
