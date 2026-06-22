from __future__ import annotations

import importlib
from typing import Any


class _FakeOp:
    def __init__(self) -> None:
        self.created_tables: list[str] = []
        self.dropped_tables: list[str] = []
        self.created_indexes: list[tuple[str, str, tuple[str, ...]]] = []
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


def test_group_migration_creates_tables_indexes_and_reversible_order(
    monkeypatch: Any,
) -> None:
    migration = importlib.import_module("cloud_ui.migrations.versions.0004_resource_groups")
    fake_op = _FakeOp()
    monkeypatch.setattr(migration, "op", fake_op)

    migration.upgrade()
    migration.downgrade()

    assert fake_op.created_tables == [
        "resource_groups",
        "resource_group_members",
        "resource_group_revisions",
    ]
    assert fake_op.dropped_tables == [
        "resource_group_revisions",
        "resource_group_members",
        "resource_groups",
    ]
    assert (
        "ix_resource_groups_owner_scope_name",
        "resource_groups",
        ("owner_subject_id", "scope_type", "scope_id", "deleted_at", "name", "group_id"),
    ) in fake_op.created_indexes
    assert (
        "ix_resource_group_members_group_page",
        "resource_group_members",
        ("group_id", "resource_type", "cloud_id", "region_id", "resource_id"),
    ) in fake_op.created_indexes
