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


def test_limit_is_clamped_to_repository_maximum(engine: Engine) -> None:
    repository = InventoryRepository(
        engine=engine,
        cursor_codec=CursorCodec(signing_key="dev-inventory-cursor-key"),
        default_limit=50,
        max_limit=2,
        stale_after_seconds=900,
    )
    _insert_instances(
        engine,
        [
            _instance_row(
                now=datetime(2026, 6, 21, 10, 0, tzinfo=UTC),
                instance_id="limit-0001",
                name="limit-a",
                status="LIMITED",
                deleted_at=None,
            ),
            _instance_row(
                now=datetime(2026, 6, 21, 10, 0, tzinfo=UTC),
                instance_id="limit-0002",
                name="limit-b",
                status="LIMITED",
                deleted_at=None,
            ),
            _instance_row(
                now=datetime(2026, 6, 21, 10, 0, tzinfo=UTC),
                instance_id="limit-0003",
                name="limit-c",
                status="LIMITED",
                deleted_at=None,
            ),
        ],
    )

    first_page = repository.list_instances(
        filters=InstanceFilters(cloud_id="dev-cloud", region_id="RegionOne", status="LIMITED"),
        sort=InventorySort(field="name", direction="asc"),
        limit=99,
        cursor=None,
    )

    assert [item.name for item in first_page.items] == ["limit-a", "limit-b"]
    assert first_page.next_cursor is not None

    second_page = repository.list_instances(
        filters=InstanceFilters(cloud_id="dev-cloud", region_id="RegionOne", status="LIMITED"),
        sort=InventorySort(field="name", direction="asc"),
        limit=99,
        cursor=first_page.next_cursor,
    )

    assert [item.name for item in second_page.items] == ["limit-c"]
    assert second_page.next_cursor is None


def test_cursor_with_different_sort_is_rejected(repository: InventoryRepository) -> None:
    filters = InstanceFilters(cloud_id="dev-cloud", region_id="RegionOne", status="ACTIVE")
    first_page = repository.list_instances(
        filters=filters,
        sort=InventorySort(field="name", direction="asc"),
        limit=1,
        cursor=None,
    )

    with pytest.raises(CursorTampered) as exc_info:
        repository.list_instances(
            filters=filters,
            sort=InventorySort(field="instance_id", direction="asc"),
            limit=1,
            cursor=first_page.next_cursor,
        )

    assert exc_info.value.code == "cursor_tampered"


def test_duplicate_sort_values_use_deterministic_id_tie_breaker(
    repository: InventoryRepository,
    engine: Engine,
) -> None:
    now = datetime(2026, 6, 21, 10, 0, tzinfo=UTC)
    _insert_instances(
        engine,
        [
            _instance_row(
                now=now,
                instance_id="duplicate-0002",
                name="dupe",
                status="DUPLICATE",
                deleted_at=None,
            ),
            _instance_row(
                now=now,
                instance_id="duplicate-0001",
                name="dupe",
                status="DUPLICATE",
                deleted_at=None,
            ),
        ],
    )
    filters = InstanceFilters(cloud_id="dev-cloud", region_id="RegionOne", status="DUPLICATE")
    sort = InventorySort(field="name", direction="asc")

    first_page = repository.list_instances(filters=filters, sort=sort, limit=1, cursor=None)
    second_page = repository.list_instances(
        filters=filters,
        sort=sort,
        limit=1,
        cursor=first_page.next_cursor,
    )

    assert [item.instance_id for item in first_page.items] == ["duplicate-0001"]
    assert [item.instance_id for item in second_page.items] == ["duplicate-0002"]


def test_descending_pagination_uses_descending_id_tie_breaker(
    repository: InventoryRepository,
    engine: Engine,
) -> None:
    now = datetime(2026, 6, 21, 10, 0, tzinfo=UTC)
    _insert_instances(
        engine,
        [
            _instance_row(
                now=now,
                instance_id="desc-0001",
                name="desc-a",
                status="DESCENDING",
                deleted_at=None,
            ),
            _instance_row(
                now=now,
                instance_id="desc-0002",
                name="desc-b",
                status="DESCENDING",
                deleted_at=None,
            ),
            _instance_row(
                now=now,
                instance_id="desc-0003",
                name="desc-b",
                status="DESCENDING",
                deleted_at=None,
            ),
        ],
    )
    filters = InstanceFilters(cloud_id="dev-cloud", region_id="RegionOne", status="DESCENDING")
    sort = InventorySort(field="name", direction="desc")

    first_page = repository.list_instances(filters=filters, sort=sort, limit=1, cursor=None)
    second_page = repository.list_instances(
        filters=filters,
        sort=sort,
        limit=1,
        cursor=first_page.next_cursor,
    )
    third_page = repository.list_instances(
        filters=filters,
        sort=sort,
        limit=1,
        cursor=second_page.next_cursor,
    )

    assert [item.instance_id for item in first_page.items] == ["desc-0003"]
    assert [item.instance_id for item in second_page.items] == ["desc-0002"]
    assert [item.instance_id for item in third_page.items] == ["desc-0001"]


def test_nullable_instance_sort_ascending_pages_past_null_bucket(
    repository: InventoryRepository,
    engine: Engine,
) -> None:
    now = datetime(2026, 6, 21, 10, 0, tzinfo=UTC)
    _insert_instances(
        engine,
        [
            _instance_row(
                now=now,
                instance_id="null-asc-0002",
                name="vm-null-b",
                status="NULL_ASC",
                host_name=None,
                deleted_at=None,
            ),
            _instance_row(
                now=now,
                instance_id="null-asc-0001",
                name="vm-null-a",
                status="NULL_ASC",
                host_name=None,
                deleted_at=None,
            ),
            _instance_row(
                now=now,
                instance_id="null-asc-0003",
                name="vm-hosted",
                status="NULL_ASC",
                host_name="compute-z",
                deleted_at=None,
            ),
        ],
    )
    filters = InstanceFilters(cloud_id="dev-cloud", region_id="RegionOne", status="NULL_ASC")
    sort = InventorySort(field="host_name", direction="asc")

    first_page = repository.list_instances(filters=filters, sort=sort, limit=1, cursor=None)
    second_page = repository.list_instances(
        filters=filters,
        sort=sort,
        limit=1,
        cursor=first_page.next_cursor,
    )
    third_page = repository.list_instances(
        filters=filters,
        sort=sort,
        limit=1,
        cursor=second_page.next_cursor,
    )

    assert [item.instance_id for item in first_page.items] == ["null-asc-0001"]
    assert [item.instance_id for item in second_page.items] == ["null-asc-0002"]
    assert [item.instance_id for item in third_page.items] == ["null-asc-0003"]


def test_nullable_instance_sort_descending_pages_into_null_bucket(
    repository: InventoryRepository,
    engine: Engine,
) -> None:
    now = datetime(2026, 6, 21, 10, 0, tzinfo=UTC)
    _insert_instances(
        engine,
        [
            _instance_row(
                now=now,
                instance_id="null-desc-0001",
                name="vm-null-low",
                status="NULL_DESC",
                host_name=None,
                deleted_at=None,
            ),
            _instance_row(
                now=now,
                instance_id="null-desc-0002",
                name="vm-null-high",
                status="NULL_DESC",
                host_name=None,
                deleted_at=None,
            ),
            _instance_row(
                now=now,
                instance_id="null-desc-0003",
                name="vm-hosted",
                status="NULL_DESC",
                host_name="compute-z",
                deleted_at=None,
            ),
        ],
    )
    filters = InstanceFilters(cloud_id="dev-cloud", region_id="RegionOne", status="NULL_DESC")
    sort = InventorySort(field="host_name", direction="desc")

    first_page = repository.list_instances(filters=filters, sort=sort, limit=1, cursor=None)
    second_page = repository.list_instances(
        filters=filters,
        sort=sort,
        limit=1,
        cursor=first_page.next_cursor,
    )
    third_page = repository.list_instances(
        filters=filters,
        sort=sort,
        limit=1,
        cursor=second_page.next_cursor,
    )

    assert [item.instance_id for item in first_page.items] == ["null-desc-0003"]
    assert [item.instance_id for item in second_page.items] == ["null-desc-0002"]
    assert [item.instance_id for item in third_page.items] == ["null-desc-0001"]


def test_sync_failures_return_bounded_recent_warnings_and_stale_freshness(
    repository: InventoryRepository,
    engine: Engine,
) -> None:
    now = datetime(2026, 6, 21, 10, 0, tzinfo=UTC)
    stale_observed_at = datetime(2000, 1, 1, tzinfo=UTC)
    _seed_cloud_region(
        engine,
        cloud_id="stale-cloud",
        region_id="RegionStale",
        now=now,
        last_successful_sync_at=stale_observed_at,
    )
    with engine.begin() as connection:
        connection.execute(
            schema.instances.insert(),
            _instance_row(
                now=stale_observed_at,
                cloud_id="stale-cloud",
                region_id="RegionStale",
                instance_id="stale-0001",
                name="vm-stale",
                status="STALE",
                deleted_at=None,
            ),
        )
        connection.execute(
            schema.inventory_sync_runs.insert(),
            {
                "run_id": "run-stale-instances",
                "cloud_id": "stale-cloud",
                "region_id": "RegionStale",
                "resource_type": "instances",
                "sync_mode": "full",
                "generation": 1,
                "status": "failed",
                "started_at": now - timedelta(minutes=10),
                "completed_at": now - timedelta(minutes=5),
                "request_id": "request-stale",
                "correlation_id": "correlation-stale",
                "items_seen": 1,
                "items_upserted": 1,
                "items_deleted": 0,
                "error_count": 6,
            },
        )
        connection.execute(
            schema.inventory_sync_failures.insert(),
            [
                {
                    "failure_id": f"failure-{index}",
                    "run_id": "run-stale-instances",
                    "cloud_id": "stale-cloud",
                    "region_id": "RegionStale",
                    "resource_type": "instances",
                    "source": "nova",
                    "chunk_cursor": None,
                    "error_code": f"error-{index}",
                    "safe_message": f"failure {index}",
                    "occurred_at": now + timedelta(seconds=index),
                }
                for index in range(6)
            ],
        )

    page = repository.list_instances(
        filters=InstanceFilters(cloud_id="stale-cloud", region_id="RegionStale", status="STALE"),
        sort=InventorySort(field="name", direction="asc"),
        limit=50,
        cursor=None,
    )

    assert page.partial is True
    assert [warning.code for warning in page.warnings] == [
        "error-5",
        "error-4",
        "error-3",
        "error-2",
        "error-1",
    ]
    assert page.freshness is not None
    assert page.freshness.observed_at == stale_observed_at
    assert page.freshness.is_stale is True


def test_replace_rows_updates_instances_and_hypervisors(
    repository: InventoryRepository,
) -> None:
    now = datetime(2026, 6, 21, 10, 0, tzinfo=UTC)

    repository.replace_instance_rows(
        [
            _instance_row(
                now=now,
                instance_id="instance-0001",
                name="vm-replaced",
                status="ACTIVE",
                deleted_at=None,
            )
        ]
    )
    repository.replace_hypervisor_rows(
        [
            _hypervisor_row(
                now=now,
                hypervisor_id="hypervisor-0001",
                host_name="compute-replaced",
                service_status="disabled",
            )
        ]
    )

    instance = repository.get_instance("dev-cloud", "RegionOne", "instance-0001")
    hypervisor = repository.get_hypervisor("dev-cloud", "RegionOne", "hypervisor-0001")

    assert instance is not None
    assert instance.name == "vm-replaced"
    assert hypervisor is not None
    assert hypervisor.host_name == "compute-replaced"
    assert hypervisor.service_status == "disabled"


def _seed_inventory(engine: Engine) -> None:
    now = datetime(2026, 6, 21, 10, 0, tzinfo=UTC)
    with engine.begin() as connection:
        _seed_cloud_region_in_connection(
            connection,
            cloud_id="dev-cloud",
            region_id="RegionOne",
            now=now,
            last_successful_sync_at=now,
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
    instance_id: str = "instance-0001",
    name: str = "vm-a",
    status: str = "ACTIVE",
    cloud_id: str = "dev-cloud",
    region_id: str = "RegionOne",
    host_name: str | None = "compute-a",
    deleted_at: datetime | None = None,
) -> dict[str, object]:
    return {
        "cloud_id": cloud_id,
        "region_id": region_id,
        "instance_id": instance_id,
        "name": name,
        "project_id": "project-0001",
        "user_id": "user-0001",
        "status": status,
        "power_state": "running",
        "task_state": None,
        "vm_state": "active",
        "host_name": host_name,
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


def _insert_instances(engine: Engine, rows: list[dict[str, object]]) -> None:
    with engine.begin() as connection:
        connection.execute(schema.instances.insert(), rows)


def _seed_cloud_region(
    engine: Engine,
    *,
    cloud_id: str,
    region_id: str,
    now: datetime,
    last_successful_sync_at: datetime,
) -> None:
    with engine.begin() as connection:
        _seed_cloud_region_in_connection(
            connection,
            cloud_id=cloud_id,
            region_id=region_id,
            now=now,
            last_successful_sync_at=last_successful_sync_at,
        )


def _seed_cloud_region_in_connection(
    connection: sa.Connection,
    *,
    cloud_id: str,
    region_id: str,
    now: datetime,
    last_successful_sync_at: datetime,
) -> None:
    connection.execute(
        schema.clouds.insert(),
        {
            "cloud_id": cloud_id,
            "display_name": cloud_id,
            "enabled": True,
            "created_at": now,
            "updated_at": now,
            "last_sync_at": last_successful_sync_at,
        },
    )
    connection.execute(
        schema.regions.insert(),
        {
            "cloud_id": cloud_id,
            "region_id": region_id,
            "display_name": region_id,
            "enabled": True,
            "last_successful_sync_at": last_successful_sync_at,
            "last_attempted_sync_at": now,
            "sync_status": "ok",
        },
    )
