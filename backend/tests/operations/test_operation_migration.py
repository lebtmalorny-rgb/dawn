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
        self.created_indexes: list[tuple[str, str, tuple[str, ...], bool]] = []
        self.operations: list[tuple[str, str]] = []

    def create_table(self, name: str, *columns: Any, **_kwargs: Any) -> None:
        self.created_tables.append(name)
        self.created_table_items[name] = columns
        self.created_table_definitions[name] = sa.Table(name, sa.MetaData(), *columns)
        self.operations.append(("create_table", name))

    def drop_table(self, name: str) -> None:
        self.dropped_tables.append(name)
        self.operations.append(("drop_table", name))

    def create_index(
        self,
        name: str,
        table_name: str,
        columns: list[str],
        unique: bool = False,
    ) -> None:
        self.created_indexes.append((name, table_name, tuple(columns), unique))
        self.operations.append(("create_index", name))

    def drop_index(self, name: str, table_name: str) -> None:
        self.operations.append(("drop_index", name))


EXPECTED_TABLES = [
    "workflow_definitions",
    "operations",
    "operation_targets",
    "operation_events",
    "operation_attempts",
    "operation_outbox",
    "operation_idempotency_keys",
]

EXPECTED_DROP_TABLES = [
    "operation_idempotency_keys",
    "operation_outbox",
    "operation_attempts",
    "operation_events",
    "operation_targets",
    "operations",
    "workflow_definitions",
]

EXPECTED_PRIMARY_KEYS = {
    "workflow_definitions": ("workflow_key", "version"),
    "operations": ("operation_id",),
    "operation_targets": ("operation_id", "target_type", "cloud_id", "region_id", "resource_id"),
    "operation_events": ("event_id",),
    "operation_attempts": ("attempt_id",),
    "operation_outbox": ("outbox_id",),
    "operation_idempotency_keys": (
        "actor_subject_id",
        "workflow_key",
        "workflow_version",
        "scope_hash",
        "key_hash",
    ),
}

EXPECTED_INDEXES = {
    "ix_workflow_definitions_enabled": (
        "workflow_definitions",
        ("enabled", "workflow_key", "version"),
        False,
    ),
    "ix_operations_actor_status_created": (
        "operations",
        ("actor_subject_id", "status", "created_at", "operation_id"),
        False,
    ),
    "ix_operations_correlation": ("operations", ("correlation_id",), True),
    "ix_operations_external_execution": ("operations", ("external_execution_id",), False),
    "ix_operation_events_operation_created": (
        "operation_events",
        ("operation_id", "created_at", "event_id"),
        False,
    ),
    "ix_operation_attempts_operation_created": (
        "operation_attempts",
        ("operation_id", "created_at", "attempt_id"),
        False,
    ),
    "ix_operation_outbox_state_created": (
        "operation_outbox",
        ("state", "created_at", "outbox_id"),
        False,
    ),
    "ix_operation_idempotency_created": (
        "operation_idempotency_keys",
        ("created_at", "operation_id"),
        False,
    ),
}

EXPECTED_DROP_INDEX_OPERATIONS = [
    ("drop_index", "ix_operation_idempotency_created"),
    ("drop_index", "ix_operation_outbox_state_created"),
    ("drop_index", "ix_operation_attempts_operation_created"),
    ("drop_index", "ix_operation_events_operation_created"),
    ("drop_index", "ix_operations_external_execution"),
    ("drop_index", "ix_operations_correlation"),
    ("drop_index", "ix_operations_actor_status_created"),
    ("drop_index", "ix_workflow_definitions_enabled"),
]

EXPECTED_JSON_COLUMNS = {
    "workflow_definitions": {
        "input_schema_json",
        "ui_schema_json",
        "enabled_environments_json",
    },
    "operations": {"target_snapshot_json", "input_json"},
    "operation_targets": {"snapshot_json"},
    "operation_events": {"metadata_json"},
    "operation_attempts": {"metadata_json"},
}


def test_operation_migration_creates_tables_indexes_and_reversible_order(
    monkeypatch: Any,
) -> None:
    migration = importlib.import_module("cloud_ui.migrations.versions.0005_operations")
    fake_op = _FakeOp()
    monkeypatch.setattr(migration, "op", fake_op)

    migration.upgrade()
    migration.downgrade()

    assert fake_op.created_tables == EXPECTED_TABLES
    assert fake_op.dropped_tables == EXPECTED_DROP_TABLES
    assert _primary_key_columns(fake_op) == EXPECTED_PRIMARY_KEYS
    assert _runtime_index_specs(fake_op) == EXPECTED_INDEXES
    assert _drop_index_operations(fake_op) == EXPECTED_DROP_INDEX_OPERATIONS
    _assert_datetime_columns_are_timezone_aware(fake_op)
    _assert_json_columns(fake_op)
    _assert_foreign_keys(fake_op)


def _primary_key_columns(fake_op: _FakeOp) -> dict[str, tuple[str, ...]]:
    return {
        table_name: tuple(table.primary_key.columns.keys())
        for table_name, table in fake_op.created_table_definitions.items()
    }


def _runtime_index_specs(fake_op: _FakeOp) -> dict[str, tuple[str, tuple[str, ...], bool]]:
    return {
        name: (table_name, columns, unique)
        for name, table_name, columns, unique in fake_op.created_indexes
    }


def _drop_index_operations(fake_op: _FakeOp) -> list[tuple[str, str]]:
    return [
        (operation, name)
        for operation, name in fake_op.operations
        if operation == "drop_index"
    ]


def _assert_datetime_columns_are_timezone_aware(fake_op: _FakeOp) -> None:
    for table_name in EXPECTED_TABLES:
        columns = _table_columns(fake_op, table_name)
        for column_name, column in columns.items():
            if column_name.endswith("_at"):
                assert isinstance(column.type, sa.DateTime)
                assert column.type.timezone is True


def _assert_json_columns(fake_op: _FakeOp) -> None:
    for table_name, column_names in EXPECTED_JSON_COLUMNS.items():
        columns = _table_columns(fake_op, table_name)
        for column_name in column_names:
            assert isinstance(columns[column_name].type, sa.JSON)


def _assert_foreign_keys(fake_op: _FakeOp) -> None:
    assert _foreign_key_specs(fake_op, "operation_targets") == [
        (("operation_id",), ("operations.operation_id",), "CASCADE")
    ]
    assert _foreign_key_specs(fake_op, "operation_events") == [
        (("operation_id",), ("operations.operation_id",), "CASCADE")
    ]
    assert _foreign_key_specs(fake_op, "operation_attempts") == [
        (("operation_id",), ("operations.operation_id",), "CASCADE")
    ]
    assert _foreign_key_specs(fake_op, "operation_outbox") == [
        (("operation_id",), ("operations.operation_id",), "CASCADE")
    ]
    assert _foreign_key_specs(fake_op, "operation_idempotency_keys") == [
        (("operation_id",), ("operations.operation_id",), "CASCADE")
    ]


def _table_columns(fake_op: _FakeOp, table_name: str) -> dict[str, sa.Column[Any]]:
    return {
        item.name: item
        for item in fake_op.created_table_items[table_name]
        if isinstance(item, sa.Column)
    }


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
