import re
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
import yaml

from cloud_ui import cli

ROOT = Path(__file__).resolve().parents[1]
ROLE_ROOT = ROOT / "deploy/kolla/ansible/roles/cloud_ui"

EXPECTED_FILES = [
    "deploy/kolla/ansible/roles/cloud_ui/defaults/main.yml",
    "deploy/kolla/ansible/roles/cloud_ui/tasks/main.yml",
    "deploy/kolla/ansible/roles/cloud_ui/tasks/migration.yml",
    "backend/src/cloud_ui/cli.py",
    "docs/generated/e09-migration-job.md",
]


class _FakeDatabaseUrl:
    def unicode_string(self) -> str:
        return "sqlite:///cloud-ui-test.db"


def read_text(relative_path: str) -> str:
    return (ROOT / relative_path).read_text(encoding="utf-8")


def load_yaml(relative_path: str) -> object:
    return yaml.safe_load(read_text(relative_path))


def load_yaml_list(relative_path: str) -> list[dict[str, Any]]:
    loaded = load_yaml(relative_path)
    if not isinstance(loaded, list):
        return []
    return loaded


def fake_settings() -> SimpleNamespace:
    return SimpleNamespace(
        api_bind_host="127.0.0.1",
        api_port=18080,
        database_url=_FakeDatabaseUrl(),
        log_level="INFO",
    )


def test_e09_migration_job_files_exist() -> None:
    for relative_path in EXPECTED_FILES:
        assert (ROOT / relative_path).exists(), relative_path


def test_migration_job_uses_backend_image_and_is_not_permanent_service() -> None:
    defaults = load_yaml("deploy/kolla/ansible/roles/cloud_ui/defaults/main.yml")
    assert isinstance(defaults, dict)

    services = defaults["cloud_ui_services"]
    migration_job = defaults["cloud_ui_migration_job"]

    assert defaults["cloud_ui_migration_enabled"] is False
    assert set(services) == {
        "cloud_ui_frontend",
        "cloud_ui_api",
        "cloud_ui_worker",
        "cloud_ui_events",
    }
    assert "cloud_ui_db_migrate" not in services
    assert "cloud-ui db-upgrade" not in {
        service["command"] for service in services.values()
    }

    assert migration_job["container_name"] == "cloud_ui_db_migrate"
    assert migration_job["image"] == "{{ cloud_ui_backend_image_full }}"
    assert migration_job["command"] == "cloud-ui db-upgrade"
    assert migration_job["config_dir"] == "cloud-ui-backend"
    assert migration_job["restart_policy"] == "no"
    assert migration_job["run_once"] is True
    assert migration_job["dimensions"] == "{{ cloud_ui_backend_dimensions }}"

    serialized = yaml.safe_dump(migration_job).lower()
    for forbidden in ["password", "token", "private_key", "secret_key", "clouds.yaml"]:
        assert forbidden not in serialized


def test_migration_execution_policy_requires_precheck_lock_and_no_auto_api_migration() -> None:
    defaults = load_yaml("deploy/kolla/ansible/roles/cloud_ui/defaults/main.yml")
    assert isinstance(defaults, dict)

    policy = defaults["cloud_ui_migration_execution_policy"]

    assert policy["run_once"] is True
    assert policy["lock_required"] is True
    assert policy["precheck_required"] is True
    assert policy["api_auto_migration_allowed"] is False
    assert policy["rollback_window_required"] is True
    assert policy["retry_on_failure"] is False
    assert policy["max_attempts"] == 1
    assert policy["precheck_command"] == "cloud-ui db-upgrade --check"
    assert policy["upgrade_command"] == "cloud-ui db-upgrade"
    assert policy["log_path"] == "/var/log/kolla/cloud-ui/db-upgrade.log"


def test_migration_tasks_are_ordered_before_permanent_container_definitions() -> None:
    main_tasks = load_yaml_list("deploy/kolla/ansible/roles/cloud_ui/tasks/main.yml")
    actual_imports: list[str] = []
    for task in main_tasks:
        include_value = task.get("ansible.builtin.include_tasks") or task.get(
            "include_tasks"
        )
        if include_value is not None:
            actual_imports.append(str(include_value).strip())

    assert actual_imports == [
        "validate.yml",
        "config.yml",
        "migration.yml",
        "containers.yml",
    ]

    migration_tasks = load_yaml_list(
        "deploy/kolla/ansible/roles/cloud_ui/tasks/migration.yml"
    )
    set_fact_keys: set[str] = set()
    for task in migration_tasks:
        set_fact = task.get("ansible.builtin.set_fact") or task.get("set_fact")
        if isinstance(set_fact, dict):
            set_fact_keys.update(set_fact)

    assert {
        "cloud_ui_migration_job_definition",
        "cloud_ui_migration_execution_policy_effective",
    }.issubset(set_fact_keys)

    migration_text = read_text("deploy/kolla/ansible/roles/cloud_ui/tasks/migration.yml")
    assert "kolla_container:" not in migration_text
    assert "cloud_ui_services" not in migration_text


def test_backend_api_command_does_not_run_alembic_upgrade(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str] = []

    monkeypatch.setattr(cli, "get_settings", fake_settings)
    monkeypatch.setattr(cli, "configure_logging", lambda _level: None)
    monkeypatch.setattr(cli.uvicorn, "run", lambda *args, **kwargs: None)
    monkeypatch.setattr(cli.command, "upgrade", lambda *args, **kwargs: calls.append("upgrade"))

    assert cli.main(["api"]) == 0
    assert calls == []


def test_backend_db_upgrade_command_is_explicit_and_sanitized(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    calls: list[tuple[str, str | None]] = []

    def fake_upgrade(cfg: Any, revision: str) -> None:
        calls.append((revision, cfg.get_main_option("sqlalchemy.url")))

    monkeypatch.setattr(cli, "get_settings", fake_settings)
    monkeypatch.setattr(cli, "configure_logging", lambda _level: None)
    monkeypatch.setattr(cli.command, "upgrade", fake_upgrade)

    assert cli.main(["db-upgrade"]) == 0

    assert calls == [("head", "sqlite:///cloud-ui-test.db")]
    output = capsys.readouterr().out
    assert "db migration upgrade ok: revision=head" in output
    assert "sqlite" not in output


def test_backend_db_upgrade_check_does_not_apply_migration(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    calls: list[str] = []

    monkeypatch.setattr(cli, "get_settings", fake_settings)
    monkeypatch.setattr(cli, "configure_logging", lambda _level: None)
    monkeypatch.setattr(cli.command, "current", lambda _cfg: calls.append("current"))
    monkeypatch.setattr(
        cli.command,
        "upgrade",
        lambda *_args, **_kwargs: pytest.fail("precheck must not run upgrade"),
    )

    assert cli.main(["db-upgrade", "--check"]) == 0

    assert calls == ["current"]
    output = capsys.readouterr().out
    assert "db migration precheck ok" in output


def test_e09_migration_job_evidence_records_scope_and_limits() -> None:
    evidence = read_text("docs/generated/e09-migration-job.md")

    for expected in [
        "Stage: E09.4 Migration job",
        "cloud_ui_db_migrate",
        "cloud-ui db-upgrade",
        "one-shot",
        "API auto migration",
        "not executed in this slice",
        "pending_external_evidence",
        "ДКБ-55/56",
        "ДКБ-69/70",
        "ДКБ-82",
    ]:
        assert expected in evidence

    assert "production approved" not in evidence.lower()
    assert "root token" not in evidence.lower()
    assert "unseal key" not in evidence.lower()


def test_traceability_and_risk_register_reference_e09_4_without_overclaim() -> None:
    traceability = read_text("docs/11_DKB_TRACEABILITY.md")
    risk_register = read_text("docs/generated/risk-register.md")

    assert "E09.4" in traceability
    assert "cloud_ui_db_migrate" in traceability
    assert "API auto migration" in traceability
    assert "live migration execution remains pending" in traceability

    assert "R-064" in risk_register
    assert "migration job contract mistaken for live migration proof" in risk_register

    risk_ids = re.findall(r"^\| (R-\d{3}) \|", risk_register, flags=re.MULTILINE)
    duplicate_ids = {risk_id for risk_id in risk_ids if risk_ids.count(risk_id) > 1}
    assert duplicate_ids == set()
