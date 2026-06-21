from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, datetime, timedelta

import pytest
import sqlalchemy as sa
from sqlalchemy.engine import Engine

from cloud_ui.inventory import schema
from cloud_ui.inventory.cursor import CursorCodec, CursorTampered
from cloud_ui.inventory.models import HypervisorFilters, InstanceFilters, InventorySort
from cloud_ui.inventory.repository import InventoryRepository


@pytest.fixture()
def engine() -> Iterator[Engine]:
    engine = sa.create_engine("sqlite+pysqlite:///:memory:", future=True)
    schema.metadata.create_all(engine)
    _seed_inventory(engine)
    yield engine
    engine.dispose()


@pytest.fixture()
def repository(engine: Engine) -> InventoryRepository:
    return InventoryRepository(
        engine=engine,
        cursor_codec=CursorCodec(signing_key="dev-inventory-cursor-key"),
        default_limit=50,
        max_limit=200,
        stale_after_seconds=900,
    )


def test_instances_are_filtered_sorted_and_keyset_paginated(
    repository: InventoryRepository,
) -> None:
    filters = InstanceFilters(cloud_id="dev-cloud", region_id="RegionOne", status="ACTIVE")
    sort = InventorySort(field="name", direction="asc")

    first_page = repository.list_instances(filters=filters, sort=sort, limit=1, cursor=None)

    assert [item.name for item in first_page.items] == ["vm-a"]
    assert first_page.next_cursor is not None

    second_page = repository.list_instances(
        filters=filters,
        sort=sort,
        limit=1,
        cursor=first_page.next_cursor,
    )

    assert [item.name for item in second_page.items] == ["vm-c"]
    assert second_page.next_cursor is None


def test_cursor_with_different_filters_is_rejected(repository: InventoryRepository) -> None:
    sort = InventorySort(field="name", direction="asc")
    first_page = repository.list_instances(
        filters=InstanceFilters(cloud_id="dev-cloud", region_id="RegionOne", status="ACTIVE"),
        sort=sort,
        limit=1,
        cursor=None,
    )

    with pytest.raises(CursorTampered) as exc_info:
        repository.list_instances(
            filters=InstanceFilters(cloud_id="dev-cloud", region_id="RegionOne", status="ERROR"),
            sort=sort,
            limit=1,
            cursor=first_page.next_cursor,
        )

    assert exc_info.value.code == "cursor_tampered"


def test_hypervisors_are_filtered_by_service_status_and_sorted(
    repository: InventoryRepository,
) -> None:
    page = repository.list_hypervisors(
        filters=HypervisorFilters(
            cloud_id="dev-cloud",
            region_id="RegionOne",
            service_status="enabled",
        ),
        sort=InventorySort(field="host_name", direction="asc"),
        limit=50,
        cursor=None,
    )

    assert [item.host_name for item in page.items] == ["compute-a", "compute-z"]
    assert {item.service_status for item in page.items} == {"enabled"}


def test_detail_ignores_tombstoned_rows(repository: InventoryRepository) -> None:
    assert repository.get_instance("dev-cloud", "RegionOne", "instance-0002") is None


def _seed_inventory(engine: Engine) -> None:
    now = datetime(2026, 6, 21, 10, 0, tzinfo=UTC)
    with engine.begin() as connection:
        connection.execute(
            schema.clouds.insert(),
            {
                "cloud_id": "dev-cloud",
                "display_name": "Dev Cloud",
                "enabled": True,
                "created_at": now,
                "updated_at": now,
                "last_sync_at": now,
            },
        )
        connection.execute(
            schema.regions.insert(),
            {
                "cloud_id": "dev-cloud",
                "region_id": "RegionOne",
                "display_name": "Region One",
                "enabled": True,
                "last_successful_sync_at": now,
                "last_attempted_sync_at": now,
                "sync_status": "ok",
            },
        )
        connection.execute(
            schema.instances.insert(),
            [
                _instance_row(
                    now=now,
                    instance_id="instance-0001",
                    name="vm-a",
                    status="ACTIVE",
                    deleted_at=None,
                ),
                _instance_row(
                    now=now,
                    instance_id="instance-0002",
                    name="vm-b",
                    status="ERROR",
                    deleted_at=now + timedelta(minutes=1),
                ),
                _instance_row(
                    now=now,
                    instance_id="instance-0003",
                    name="vm-c",
                    status="ACTIVE",
                    deleted_at=None,
                ),
            ],
        )
        connection.execute(
            schema.hypervisors.insert(),
            [
                _hypervisor_row(
                    now=now,
                    hypervisor_id="hypervisor-0002",
                    host_name="compute-z",
                    service_status="enabled",
                ),
                _hypervisor_row(
                    now=now,
                    hypervisor_id="hypervisor-0001",
                    host_name="compute-a",
                    service_status="enabled",
                ),
            ],
        )


def _instance_row(
    *,
    now: datetime,
    instance_id: str,
    name: str,
    status: str,
    deleted_at: datetime | None,
) -> dict[str, object]:
    return {
        "cloud_id": "dev-cloud",
        "region_id": "RegionOne",
        "instance_id": instance_id,
        "name": name,
        "project_id": "project-0001",
        "user_id": "user-0001",
        "status": status,
        "power_state": "running",
        "task_state": None,
        "vm_state": "active",
        "host_name": "compute-a",
        "hypervisor_id": "hypervisor-0001",
        "availability_zone": "nova",
        "flavor_id": "flavor-small",
        "vcpus": 2,
        "ram_mb": 4096,
        "disk_gb": 40,
        "image_id": "image-0001",
        "boot_volume_id": None,
        "addresses_json": {"private": ["10.0.0.10"]},
        "source_created_at": now - timedelta(days=1),
        "source_updated_at": now,
        "observed_at": now,
        "sync_generation": 1,
        "sync_status": "ok",
        "deleted_at": deleted_at,
        "change_hash": f"hash-{instance_id}",
    }


def _hypervisor_row(
    *,
    now: datetime,
    hypervisor_id: str,
    host_name: str,
    service_status: str,
) -> dict[str, object]:
    return {
        "cloud_id": "dev-cloud",
        "region_id": "RegionOne",
        "hypervisor_id": hypervisor_id,
        "host_name": host_name,
        "service_id": f"service-{hypervisor_id}",
        "service_status": service_status,
        "service_state": "up",
        "hypervisor_type": "QEMU",
        "hypervisor_version": "9.0",
        "availability_zone": "nova",
        "aggregates_json": ["az-nova"],
        "vcpus_total": 64,
        "vcpus_used": 8,
        "ram_mb_total": 262144,
        "ram_mb_used": 32768,
        "disk_gb_total": 4000,
        "disk_gb_used": 1000,
        "running_vms": 4,
        "disabled_reason": None,
        "maintenance_status": None,
        "observed_at": now,
        "sync_generation": 1,
        "sync_status": "ok",
        "deleted_at": None,
        "change_hash": f"hash-{hypervisor_id}",
    }
