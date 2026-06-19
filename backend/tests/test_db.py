from typing import Any

from pytest import MonkeyPatch

import cloud_ui.db as db


def test_mysql_engine_uses_bounded_probe_timeouts(monkeypatch: MonkeyPatch) -> None:
    captured: dict[str, Any] = {}
    engine: Any = object()

    def fake_create_engine(database_url: str, **kwargs: Any) -> Any:
        captured["database_url"] = database_url
        captured["kwargs"] = kwargs
        return engine

    monkeypatch.setattr(db, "create_engine", fake_create_engine)

    database_url = "mysql+pymysql://cloud_ui:cloud_ui_dev@db:3306/cloud_ui"

    result = db.create_db_engine(database_url)

    assert result is engine
    assert captured == {
        "database_url": database_url,
        "kwargs": {
            "pool_pre_ping": True,
            "pool_size": 2,
            "max_overflow": 2,
            "connect_args": {
                "connect_timeout": db.DB_PROBE_TIMEOUT_SECONDS,
                "read_timeout": db.DB_PROBE_TIMEOUT_SECONDS,
                "write_timeout": db.DB_PROBE_TIMEOUT_SECONDS,
            },
        },
    }
