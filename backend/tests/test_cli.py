from typing import Any

import pytest

from cloud_ui.cli import build_parser, main, run_db_upgrade, run_inventory_sync_synthetic


def test_cli_accepts_expected_commands() -> None:
    parser = build_parser()

    for command in ("api", "worker", "events", "db-upgrade", "inventory-sync-synthetic", "smoke"):
        args = parser.parse_args([command])
        assert args.command == command


def test_cli_accepts_worker_once_flag() -> None:
    parser = build_parser()

    args = parser.parse_args(["worker", "--once"])

    assert args.command == "worker"
    assert args.once is True


def test_smoke_does_not_require_runtime_settings(
    capsys: Any,
    monkeypatch: Any,
) -> None:
    def fail_if_called() -> None:
        raise AssertionError("smoke must not load runtime settings")

    monkeypatch.setattr("cloud_ui.cli.get_settings", fail_if_called)

    assert main(["smoke"]) == 0

    captured = capsys.readouterr()
    assert captured.out == "backend smoke ok\n"


def test_db_upgrade_sets_database_url_and_upgrades_head(monkeypatch: Any) -> None:
    class FakeUrl:
        def unicode_string(self) -> str:
            return "mysql+pymysql://user:pass@db:3306/cloud_ui"

    class FakeSettings:
        database_url = FakeUrl()

    class FakeConfig:
        def __init__(self, path: str) -> None:
            self.path = path
            self.options: dict[str, str] = {}

        def set_main_option(self, key: str, value: str) -> None:
            self.options[key] = value

    captured: dict[str, Any] = {}

    def fake_upgrade(cfg: FakeConfig, revision: str) -> None:
        captured["cfg"] = cfg
        captured["revision"] = revision

    monkeypatch.setattr("cloud_ui.cli.get_settings", lambda: FakeSettings())
    monkeypatch.setattr("cloud_ui.cli.Config", FakeConfig)
    monkeypatch.setattr("cloud_ui.cli.command.upgrade", fake_upgrade)

    run_db_upgrade()

    cfg = captured["cfg"]
    assert cfg.path == "alembic.ini"
    assert cfg.options["sqlalchemy.url"] == "mysql+pymysql://user:pass@db:3306/cloud_ui"
    assert captured["revision"] == "head"


def test_inventory_sync_synthetic_dispatches_to_runner(monkeypatch: Any) -> None:
    class FakeSettings:
        log_level = "INFO"

    called: list[str] = []

    def fake_run_inventory_sync_synthetic() -> int:
        called.append("inventory-sync-synthetic")
        return 2

    monkeypatch.setattr("cloud_ui.cli.get_settings", lambda: FakeSettings())
    monkeypatch.setattr("cloud_ui.cli.configure_logging", lambda _level: None)
    monkeypatch.setattr(
        "cloud_ui.cli.run_inventory_sync_synthetic",
        fake_run_inventory_sync_synthetic,
    )

    assert main(["inventory-sync-synthetic"]) == 2
    assert called == ["inventory-sync-synthetic"]


def test_worker_once_dispatches_to_bounded_runner(monkeypatch: Any) -> None:
    class FakeSettings:
        log_level = "INFO"

    called: list[str] = []

    def fake_run_operation_worker_once() -> int:
        called.append("worker-once")
        return 3

    monkeypatch.setattr("cloud_ui.cli.get_settings", lambda: FakeSettings())
    monkeypatch.setattr("cloud_ui.cli.configure_logging", lambda _level: None)
    monkeypatch.setattr("cloud_ui.cli.run_operation_worker_once", fake_run_operation_worker_once)

    assert main(["worker", "--once"]) == 3
    assert called == ["worker-once"]


def test_inventory_sync_synthetic_returns_nonzero_on_partial(
    capsys: Any,
    monkeypatch: Any,
) -> None:
    class FakeUrl:
        def unicode_string(self) -> str:
            return "sqlite+pysqlite:///:memory:"

    class FakeSettings:
        database_url = FakeUrl()
        environment = "local"
        inventory_cursor_signing_key = "dev-inventory-cursor-key"
        inventory_default_limit = 50
        inventory_max_limit = 200
        inventory_stale_after_seconds = 900
        inventory_synthetic_instance_count = 7
        inventory_synthetic_hypervisor_count = 2

    class FakeEngine:
        disposed = False

        def dispose(self) -> None:
            self.disposed = True

    class FakeInventoryRepository:
        def __init__(self, **_kwargs: Any) -> None:
            pass

    class FakeSyntheticInventorySource:
        def __init__(self, *, instance_count: int, hypervisor_count: int) -> None:
            assert instance_count == 7
            assert hypervisor_count == 2

    class FakeResult:
        status = "partial"
        instance_count = 7
        hypervisor_count = 2

    class FakeInventoryReconciler:
        def __init__(self, **_kwargs: Any) -> None:
            pass

        def run_full_sync(self, *, request_id: str, correlation_id: str) -> FakeResult:
            assert request_id == "cli-inventory-sync-synthetic"
            assert correlation_id == "cli-inventory-sync-synthetic"
            return FakeResult()

    fake_engine = FakeEngine()
    monkeypatch.setattr("cloud_ui.cli.get_settings", lambda: FakeSettings())
    monkeypatch.setattr("cloud_ui.cli.create_db_engine", lambda _url: fake_engine)
    monkeypatch.setattr("cloud_ui.cli.InventoryRepository", FakeInventoryRepository)
    monkeypatch.setattr("cloud_ui.cli.SyntheticInventorySource", FakeSyntheticInventorySource)
    monkeypatch.setattr("cloud_ui.cli.InventoryReconciler", FakeInventoryReconciler)

    assert run_inventory_sync_synthetic() == 2

    captured = capsys.readouterr()
    assert (
        captured.out
        == "inventory synthetic sync partial: instances=7 hypervisors=2 status=partial\n"
    )
    assert fake_engine.disposed is True


def test_inventory_sync_synthetic_is_blocked_in_production(monkeypatch: Any) -> None:
    class FakeSettings:
        environment = "production"

    def fail_if_engine_created(_database_url: str) -> object:
        raise AssertionError("production synthetic sync must not create a DB engine")

    monkeypatch.setattr("cloud_ui.cli.get_settings", lambda: FakeSettings())
    monkeypatch.setattr("cloud_ui.cli.create_db_engine", fail_if_engine_created)

    with pytest.raises(RuntimeError, match="Synthetic inventory sync is not allowed in production"):
        run_inventory_sync_synthetic()
