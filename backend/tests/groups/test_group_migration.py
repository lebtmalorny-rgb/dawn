from __future__ import annotations

import importlib
from typing import Any

import sqlalchemy as sa


class _FakeOp:
    def __init__(self) -> None:
        self.created_tables: list[str] = []
        self.created_table_items: dict[str, tuple[Any, ...]] = {}
        self.dropped_tables: list[str] = []
        self.created_indexes: list[tuple[str, str, tuple[str, ...]]] = []
        self.operations: list[tuple[str, str]] = []

    def create_table(self, name: str, *columns: Any, **kwargs: Any) -> None:
        self.created_tables.append(name)
        self.created_table_items[name] = columns
        self.operations.append(("create_table", name))

    def drop_table(self, name: str) -> None:
        self.dropped_tables.append(name)
        self.operations.append(("drop_table", name))

    def create_index(self, name: str, table_name: str, columns: list[str]) -> None:
        self.created_indexes.append((name, table_name, tuple(columns)))
        self.operations.append(("create_index", name))

    def drop_index(self, name: str, table_name: str) -> None:
        self.operations.append(("drop_index", name))


def _table_columns(fake_op: _FakeOp, table_name: str) -> dict[str, sa.Column[Any]]:
    return {
        item.name: item
        for item in fake_op.created_table_items[table_name]
        if isinstance(item, sa.Column)
    }


def _foreign_key_constraints(fake_op: _FakeOp, table_name: str) -> list[sa.ForeignKeyConstraint]:
    return [
        item
        for item in fake_op.created_table_items[table_name]
        if isinstance(item, sa.ForeignKeyConstraint)
    ]


def _assert_datetime_timezone(column: sa.Column[Any]) -> None:
    assert isinstance(column.type, sa.DateTime)
    assert column.type.timezone is True


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
    resource_group_columns = _table_columns(fake_op, "resource_groups")
    assert resource_group_columns["scope_type"].nullable is False
    assert resource_group_columns["scope_id"].nullable is False
    assert isinstance(resource_group_columns["rule_body_json"].type, sa.JSON)
    _assert_datetime_timezone(resource_group_columns["created_at"])
    _assert_datetime_timezone(resource_group_columns["updated_at"])
    _assert_datetime_timezone(resource_group_columns["deleted_at"])

    member_columns = _table_columns(fake_op, "resource_group_members")
    _assert_datetime_timezone(member_columns["added_at"])
    _assert_datetime_timezone(member_columns["expires_at"])

    revision_columns = _table_columns(fake_op, "resource_group_revisions")
    assert isinstance(revision_columns["change_json"].type, sa.JSON)
    _assert_datetime_timezone(revision_columns["created_at"])

    assert any(
        constraint.ondelete == "CASCADE"
        for constraint in _foreign_key_constraints(fake_op, "resource_group_members")
    )
    assert any(
        constraint.ondelete == "CASCADE"
        for constraint in _foreign_key_constraints(fake_op, "resource_group_revisions")
    )

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
    assert (
        "ix_resource_group_members_resource_lookup",
        "resource_group_members",
        ("resource_type", "cloud_id", "region_id", "resource_id", "group_id"),
    ) in fake_op.created_indexes
    assert (
        "ix_resource_group_revisions_group_revision",
        "resource_group_revisions",
        ("group_id", "revision", "revision_id"),
    ) in fake_op.created_indexes
    assert fake_op.operations.index(
        ("drop_index", "ix_resource_group_revisions_group_revision")
    ) < fake_op.operations.index(("drop_table", "resource_group_revisions"))
    assert fake_op.operations.index(
        ("drop_index", "ix_resource_group_members_resource_lookup")
    ) < fake_op.operations.index(("drop_table", "resource_group_members"))
    assert fake_op.operations.index(
        ("drop_index", "ix_resource_group_members_group_page")
    ) < fake_op.operations.index(("drop_table", "resource_group_members"))
    assert fake_op.operations.index(
        ("drop_index", "ix_resource_groups_owner_scope_name")
    ) < fake_op.operations.index(("drop_table", "resource_groups"))


def test_group_schema_requires_project_scope_id() -> None:
    schema = importlib.import_module("cloud_ui.groups.schema")

    assert schema.resource_groups.c.scope_type.nullable is False
    assert schema.resource_groups.c.scope_id.nullable is False
