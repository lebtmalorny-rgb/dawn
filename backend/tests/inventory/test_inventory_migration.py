from __future__ import annotations

import importlib
from typing import Any


class _FakeOp:
    def __init__(self) -> None:
        self.created_tables: list[str] = []
        self.dropped_tables: list[str] = []
        self.created_indexes: list[tuple[str, str, object]] = []
        self.operations: list[tuple[str, str]] = []

    def create_table(self, name: str, *columns: Any, **kwargs: Any) -> None:
        self.created_tables.append(name)
        self.operations.append(("create_table", name))

    def drop_table(self, name: str) -> None:
        self.dropped_tables.append(name)
        self.operations.append(("drop_table", name))

    def create_index(self, name: str, table_name: str, columns: list[str]) -> None:
        self.created_indexes.append((name, table_name, tuple(columns)))
        self.operations.append(("create_index", name))

    def drop_index(self, name: str, table_name: str) -> None:
        self.operations.append(("drop_index", name))


def test_inventory_migration_creates_and_drops_expected_tables(monkeypatch: Any) -> None:
    migration = importlib.import_module("cloud_ui.migrations.versions.0003_inventory_read_model")
    fake_op = _FakeOp()
    monkeypatch.setattr(migration, "op", fake_op)

    migration.upgrade()
    migration.downgrade()

    assert fake_op.created_tables == [
        "clouds",
        "regions",
        "inventory_sync_runs",
        "inventory_sync_cursors",
        "inventory_sync_failures",
        "instances",
        "hypervisors",
    ]
    assert fake_op.dropped_tables == [
        "hypervisors",
        "instances",
        "inventory_sync_failures",
        "inventory_sync_cursors",
        "inventory_sync_runs",
        "regions",
        "clouds",
    ]
    assert (
        "ix_instances_name_page",
        "instances",
        ("cloud_id", "region_id", "deleted_at", "name", "instance_id"),
    ) in fake_op.created_indexes
    assert (
        "ix_hypervisors_host_page",
        "hypervisors",
        ("cloud_id", "region_id", "deleted_at", "host_name", "hypervisor_id"),
    ) in fake_op.created_indexes
    assert (
        "ix_inventory_sync_failures_recent",
        "inventory_sync_failures",
        ("cloud_id", "region_id", "resource_type", "occurred_at", "failure_id"),
    ) in fake_op.created_indexes
    assert fake_op.operations.index(
        ("drop_index", "ix_inventory_sync_failures_recent")
    ) < fake_op.operations.index(("drop_table", "inventory_sync_failures"))
