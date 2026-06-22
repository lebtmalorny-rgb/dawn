from __future__ import annotations

import importlib
from typing import Any

import sqlalchemy as sa


class _FakeOp:
    def __init__(self) -> None:
        self.created_tables: list[str] = []
        self.created_table_items: dict[str, tuple[Any, ...]] = {}
        self.created_table_definitions: dict[str, sa.Table] = {}
        self.dropped_tables: list[str] = []
        self.created_indexes: list[tuple[str, str, tuple[str, ...]]] = []
        self.operations: list[tuple[str, str]] = []

    def create_table(self, name: str, *columns: Any, **kwargs: Any) -> None:
        self.created_tables.append(name)
        self.created_table_items[name] = columns
        self.created_table_definitions[name] = sa.Table(name, sa.MetaData(), *columns)
        self.operations.append(("create_table", name))

    def drop_table(self, name: str) -> None:
        self.dropped_tables.append(name)
        self.operations.append(("drop_table", name))

    def create_index(self, name: str, table_name: str, columns: list[str]) -> None:
        self.created_indexes.append((name, table_name, tuple(columns)))
        self.operations.append(("create_index", name))

    def drop_index(self, name: str, table_name: str) -> None:
        self.operations.append(("drop_index", name))


EXPECTED_NULLABILITY = {
    "resource_groups": {
        "group_id": False,
        "name": False,
        "description": True,
        "resource_type": False,
        "scope_type": False,
        "scope_id": False,
        "membership_mode": False,
        "rule_version": False,
        "rule_body_json": True,
        "owner_subject_id": False,
        "revision": False,
        "created_at": False,
        "updated_at": False,
        "deleted_at": True,
    },
    "resource_group_members": {
        "group_id": False,
        "resource_type": False,
        "cloud_id": False,
        "region_id": False,
        "resource_id": False,
        "source": False,
        "added_by": False,
        "added_at": False,
        "expires_at": True,
    },
    "resource_group_revisions": {
        "revision_id": False,
        "group_id": False,
        "revision": False,
        "actor_id": False,
        "change_type": False,
        "change_json": False,
        "created_at": False,
    },
}

EXPECTED_PRIMARY_KEYS = {
    "resource_groups": ("group_id",),
    "resource_group_members": (
        "group_id",
        "resource_type",
        "cloud_id",
        "region_id",
        "resource_id",
    ),
    "resource_group_revisions": ("revision_id",),
}

EXPECTED_INDEXES = {
    "ix_resource_groups_owner_scope_name": (
        "resource_groups",
        ("owner_subject_id", "scope_type", "scope_id", "deleted_at", "name", "group_id"),
    ),
    "ix_resource_group_members_group_page": (
        "resource_group_members",
        ("group_id", "added_at", "resource_type", "cloud_id", "region_id", "resource_id"),
    ),
    "ix_resource_group_members_resource_lookup": (
        "resource_group_members",
        ("resource_type", "cloud_id", "region_id", "resource_id", "group_id"),
    ),
    "ix_resource_group_revisions_group_revision": (
        "resource_group_revisions",
        ("group_id", "revision", "revision_id"),
    ),
}

EXPECTED_DROP_INDEX_OPERATIONS = [
    ("drop_index", "ix_resource_group_revisions_group_revision"),
    ("drop_index", "ix_resource_group_members_resource_lookup"),
    ("drop_index", "ix_resource_group_members_group_page"),
    ("drop_index", "ix_resource_groups_owner_scope_name"),
]


def _table_columns(fake_op: _FakeOp, table_name: str) -> dict[str, sa.Column[Any]]:
    return {
        item.name: item
        for item in fake_op.created_table_items[table_name]
        if isinstance(item, sa.Column)
    }


def _primary_key_columns(fake_op: _FakeOp, table_name: str) -> tuple[str, ...]:
    table = fake_op.created_table_definitions[table_name]
    return tuple(table.primary_key.columns.keys())


def _foreign_key_specs(
    fake_op: _FakeOp,
    table_name: str,
) -> list[tuple[tuple[str, ...], tuple[str, ...], str | None]]:
    table = fake_op.created_table_definitions[table_name]
    return [
        (
            tuple(constraint.column_keys),
            tuple(element.target_fullname for element in constraint.elements),
            constraint.ondelete,
        )
        for constraint in table.foreign_key_constraints
    ]


def _assert_datetime_timezone(column: sa.Column[Any]) -> None:
    assert isinstance(column.type, sa.DateTime)
    assert column.type.timezone is True


def _assert_table_nullability(fake_op: _FakeOp, table_name: str) -> None:
    columns = _table_columns(fake_op, table_name)

    assert {name: columns[name].nullable for name in EXPECTED_NULLABILITY[table_name]} == (
        EXPECTED_NULLABILITY[table_name]
    )


def _runtime_index_specs(schema: Any) -> dict[str, tuple[str, tuple[str, ...]]]:
    tables = [
        schema.resource_groups,
        schema.resource_group_members,
        schema.resource_group_revisions,
    ]

    return {
        index.name: (
            index.table.name,
            tuple(column.name for column in index.expressions),
        )
        for table in tables
        for index in table.indexes
        if index.name is not None
    }


def _runtime_nullability(schema: Any, table_name: str) -> dict[str, bool]:
    table = getattr(schema, table_name)

    return {
        column_name: table.c[column_name].nullable
        for column_name in EXPECTED_NULLABILITY[table_name]
    }


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
    for table_name, primary_key_columns in EXPECTED_PRIMARY_KEYS.items():
        assert _primary_key_columns(fake_op, table_name) == primary_key_columns
        _assert_table_nullability(fake_op, table_name)

    resource_group_columns = _table_columns(fake_op, "resource_groups")
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

    assert _foreign_key_specs(fake_op, "resource_group_members") == [
        (("group_id",), ("resource_groups.group_id",), "CASCADE")
    ]
    assert _foreign_key_specs(fake_op, "resource_group_revisions") == [
        (("group_id",), ("resource_groups.group_id",), "CASCADE")
    ]

    assert {
        name: (table_name, columns)
        for name, table_name, columns in fake_op.created_indexes
    } == EXPECTED_INDEXES
    assert [
        operation for operation in fake_op.operations if operation[0] == "drop_index"
    ] == EXPECTED_DROP_INDEX_OPERATIONS
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

    assert _runtime_index_specs(schema) == EXPECTED_INDEXES
    assert _runtime_nullability(schema, "resource_groups") == EXPECTED_NULLABILITY[
        "resource_groups"
    ]
    assert _runtime_nullability(schema, "resource_group_members") == EXPECTED_NULLABILITY[
        "resource_group_members"
    ]
    assert _runtime_nullability(schema, "resource_group_revisions") == EXPECTED_NULLABILITY[
        "resource_group_revisions"
    ]
