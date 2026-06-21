from typing import Any

from cloud_ui.cli import build_parser, main, run_db_upgrade


def test_cli_accepts_expected_commands() -> None:
    parser = build_parser()

    for command in ("api", "worker", "events", "db-upgrade", "smoke"):
        args = parser.parse_args([command])
        assert args.command == command


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
        def __init__(self) -> None:
            self.path = None
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
    monkeypatch.setattr(
        "cloud_ui.cli.migration_script_location",
        lambda: "/installed/cloud_ui/migrations",
        raising=False,
    )

    run_db_upgrade()

    cfg = captured["cfg"]
    assert cfg.path is None
    assert cfg.options["script_location"] == "/installed/cloud_ui/migrations"
    assert cfg.options["sqlalchemy.url"] == "mysql+pymysql://user:pass@db:3306/cloud_ui"
    assert captured["revision"] == "head"
