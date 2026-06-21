from __future__ import annotations

import hashlib
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any


@dataclass(frozen=True)
class SyntheticInventorySource:
    instance_count: int
    hypervisor_count: int
    seed: str = "e04"
    cloud_id: str = "synthetic"
    region_id: str = "RegionOne"
    source_name: str = "synthetic"

    def __post_init__(self) -> None:
        if self.instance_count < 0:
            raise ValueError("instance_count must be non-negative")
        if self.hypervisor_count < 0:
            raise ValueError("hypervisor_count must be non-negative")
        if self.instance_count > 0 and self.hypervisor_count == 0:
            raise ValueError("hypervisor_count must be positive when instances are generated")

    def iter_instances(self, chunk_size: int) -> Iterator[list[dict[str, Any]]]:
        _validate_chunk_size(chunk_size)
        chunk: list[dict[str, Any]] = []
        for index in range(1, self.instance_count + 1):
            chunk.append(self._instance_row(index))
            if len(chunk) == chunk_size:
                yield chunk
                chunk = []
        if chunk:
            yield chunk

    def iter_hypervisors(self, chunk_size: int) -> Iterator[list[dict[str, Any]]]:
        _validate_chunk_size(chunk_size)
        chunk: list[dict[str, Any]] = []
        for index in range(1, self.hypervisor_count + 1):
            chunk.append(self._hypervisor_row(index))
            if len(chunk) == chunk_size:
                yield chunk
                chunk = []
        if chunk:
            yield chunk

    def _instance_row(self, index: int) -> dict[str, Any]:
        variant = _variant(self.seed, "instance", index)
        flavors = (
            ("flavor-small", 1, 2048, 20),
            ("flavor-medium", 2, 4096, 40),
            ("flavor-large", 4, 8192, 80),
            ("flavor-memory", 8, 32768, 120),
        )
        statuses = ("ACTIVE", "SHUTOFF", "ERROR", "BUILD")
        status = statuses[variant % len(statuses)]
        flavor_id, vcpus, ram_mb, disk_gb = flavors[variant % len(flavors)]
        host_index = ((index - 1) % self.hypervisor_count) + 1
        project_index = (variant % 5) + 1
        source_created_at = _BASE_TIME + timedelta(minutes=index)

        return {
            "cloud_id": self.cloud_id,
            "region_id": self.region_id,
            "instance_id": f"inst-{index:08d}",
            "name": f"synthetic-vm-{index:08d}",
            "project_id": f"project-{project_index:04d}",
            "user_id": f"user-{(variant % 7) + 1:04d}",
            "status": status,
            "power_state": _power_state(status),
            "task_state": "spawning" if status == "BUILD" else None,
            "vm_state": _vm_state(status),
            "host_name": f"compute-{host_index:04d}",
            "hypervisor_id": f"hyp-{host_index:04d}",
            "availability_zone": _availability_zone(variant),
            "flavor_id": flavor_id,
            "vcpus": vcpus,
            "ram_mb": ram_mb,
            "disk_gb": disk_gb,
            "image_id": f"image-{(variant % 6) + 1:04d}",
            "boot_volume_id": None if variant % 3 else f"volume-{index:08d}",
            "addresses_json": {"private": [_private_ip(index)]},
            "source_created_at": source_created_at,
            "source_updated_at": source_created_at + timedelta(hours=variant % 72),
        }

    def _hypervisor_row(self, index: int) -> dict[str, Any]:
        variant = _variant(self.seed, "hypervisor", index)
        vcpus_total = 64 + (variant % 4) * 16
        ram_mb_total = 262_144 + (variant % 5) * 65_536
        disk_gb_total = 4_000 + (variant % 6) * 500
        running_vms = self.instance_count // max(self.hypervisor_count, 1)
        if index <= self.instance_count % max(self.hypervisor_count, 1):
            running_vms += 1

        return {
            "cloud_id": self.cloud_id,
            "region_id": self.region_id,
            "hypervisor_id": f"hyp-{index:04d}",
            "host_name": f"compute-{index:04d}",
            "service_id": f"service-hyp-{index:04d}",
            "service_status": "disabled" if variant % 11 == 0 else "enabled",
            "service_state": "down" if variant % 13 == 0 else "up",
            "hypervisor_type": "QEMU",
            "hypervisor_version": f"9.{variant % 4}",
            "availability_zone": _availability_zone(variant),
            "aggregates_json": [f"aggregate-{(variant % 3) + 1}", _availability_zone(variant)],
            "vcpus_total": vcpus_total,
            "vcpus_used": min(vcpus_total, running_vms * 2),
            "ram_mb_total": ram_mb_total,
            "ram_mb_used": min(ram_mb_total, running_vms * 4096),
            "disk_gb_total": disk_gb_total,
            "disk_gb_used": min(disk_gb_total, running_vms * 40),
            "running_vms": running_vms,
            "disabled_reason": "synthetic maintenance" if variant % 11 == 0 else None,
            "maintenance_status": "maintenance" if variant % 17 == 0 else "normal",
        }


_BASE_TIME = datetime(2026, 1, 1, tzinfo=UTC)


def _validate_chunk_size(chunk_size: int) -> None:
    if chunk_size < 1:
        raise ValueError("chunk_size must be positive")


def _variant(seed: str, resource_type: str, index: int) -> int:
    digest = hashlib.sha256(f"{seed}:{resource_type}:{index}".encode()).hexdigest()
    return int(digest[:8], 16)


def _availability_zone(variant: int) -> str:
    return ("nova", "az-a", "az-b")[variant % 3]


def _power_state(status: str) -> str:
    if status == "ACTIVE":
        return "running"
    if status == "SHUTOFF":
        return "shutdown"
    return "pending" if status == "BUILD" else "error"


def _vm_state(status: str) -> str:
    if status == "ACTIVE":
        return "active"
    if status == "SHUTOFF":
        return "stopped"
    return "building" if status == "BUILD" else "error"


def _private_ip(index: int) -> str:
    second = (index // 65_536) % 256
    third = (index // 256) % 256
    fourth = index % 256
    return f"10.{second}.{third}.{fourth}"
