from __future__ import annotations

import importlib
from typing import Any


class _FakeOp:
    def __init__(self) -> None:
        self.created_tables: list[str] = []
        self.dropped_tables: list[str] = []

    def create_table(self, name: str, *columns: Any, **kwargs: Any) -> None:
        self.created_tables.append(name)

    def drop_table(self, name: str) -> None:
        self.dropped_tables.append(name)


def test_security_foundation_migration_creates_and_drops_expected_tables(
    monkeypatch: Any,
) -> None:
    migration = importlib.import_module(
        "cloud_ui.migrations.versions.0002_security_foundation"
    )
    fake_op = _FakeOp()
    monkeypatch.setattr(migration, "op", fake_op)

    migration.upgrade()
    migration.downgrade()

    assert fake_op.created_tables == [
        "subjects",
        "sessions",
        "audit_events",
        "roles",
        "permissions",
        "role_bindings",
    ]
    assert fake_op.dropped_tables == [
        "role_bindings",
        "permissions",
        "roles",
        "audit_events",
        "sessions",
        "subjects",
    ]
