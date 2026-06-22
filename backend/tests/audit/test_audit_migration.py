from __future__ import annotations

import importlib
from typing import Any

import sqlalchemy as sa


class _FakeOp:
    def __init__(self) -> None:
        self.added_columns: dict[str, list[str]] = {}
        self.dropped_columns: dict[str, list[str]] = {}
        self.created_tables: list[str] = []
        self.dropped_tables: list[str] = []
        self.created_table_items: dict[str, tuple[Any, ...]] = {}
        self.created_table_definitions: dict[str, sa.Table] = {}
        self.created_indexes: list[tuple[str, str, tuple[str, ...], bool]] = []
        self.operations: list[tuple[str, str]] = []

    def add_column(self, table_name: str, column: sa.Column[Any]) -> None:
        self.added_columns.setdefault(table_name, []).append(column.name)
        self.operations.append(("add_column", f"{table_name}.{column.name}"))

    def drop_column(self, table_name: str, column_name: str) -> None:
        self.dropped_columns.setdefault(table_name, []).append(column_name)
        self.operations.append(("drop_column", f"{table_name}.{column_name}"))

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


EXPECTED_ADDED_AUDIT_EVENT_COLUMNS = [
    "actor_display",
    "authentication_method",
    "session_reference",
    "cloud_id",
    "region_id",
    "project_id",
    "scope_type",
    "scope_id",
    "source_ip",
    "trusted_proxy_chain_json",
    "operation_id",
    "external_execution_id",
    "component",
    "safe_error_code",
    "delivery_state",
    "event_hash",
    "created_at",
]

EXPECTED_TABLES = [
    "audit_outbox",
    "audit_delivery_attempts",
    "audit_heartbeats",
]

EXPECTED_INDEXES = {
    "ix_audit_events_occurred_event": ("audit_events", ("occurred_at", "event_id"), False),
    "ix_audit_events_action_occurred": ("audit_events", ("action", "occurred_at"), False),
    "ix_audit_events_correlation": ("audit_events", ("correlation_id",), False),
    "ix_audit_outbox_state_not_before": (
        "audit_outbox",
        ("state", "not_before_at", "outbox_id"),
        False,
    ),
    "ix_audit_delivery_attempts_outbox_created": (
        "audit_delivery_attempts",
        ("outbox_id", "created_at", "attempt_id"),
        False,
    ),
}


def test_audit_delivery_migration_expands_audit_events_and_creates_outbox_tables(
    monkeypatch: Any,
) -> None:
    migration = importlib.import_module("cloud_ui.migrations.versions.0006_audit_delivery")
    fake_op = _FakeOp()
    monkeypatch.setattr(migration, "op", fake_op)

    migration.upgrade()
    migration.downgrade()

    assert fake_op.added_columns["audit_events"] == EXPECTED_ADDED_AUDIT_EVENT_COLUMNS
    assert fake_op.created_tables == EXPECTED_TABLES
    assert fake_op.dropped_tables == list(reversed(EXPECTED_TABLES))
    assert _runtime_index_specs(fake_op) == EXPECTED_INDEXES
    _assert_datetime_columns_are_timezone_aware(fake_op)
    _assert_json_columns(fake_op)


def _runtime_index_specs(fake_op: _FakeOp) -> dict[str, tuple[str, tuple[str, ...], bool]]:
    return {
        name: (table_name, columns, unique)
        for name, table_name, columns, unique in fake_op.created_indexes
    }


def _assert_datetime_columns_are_timezone_aware(fake_op: _FakeOp) -> None:
    for table_name in EXPECTED_TABLES:
        columns = _table_columns(fake_op, table_name)
        for column_name, column in columns.items():
            if column_name.endswith("_at"):
                assert isinstance(column.type, sa.DateTime)
                assert column.type.timezone is True


def _assert_json_columns(fake_op: _FakeOp) -> None:
    assert isinstance(_table_columns(fake_op, "audit_outbox")["envelope_json"].type, sa.JSON)
    assert isinstance(
        _table_columns(fake_op, "audit_delivery_attempts")["metadata_json"].type,
        sa.JSON,
    )


def _table_columns(fake_op: _FakeOp, table_name: str) -> dict[str, sa.Column[Any]]:
    return {
        item.name: item
        for item in fake_op.created_table_items[table_name]
        if isinstance(item, sa.Column)
    }
