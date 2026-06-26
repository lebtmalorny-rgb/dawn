import re
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]

PLAYBOOK = "deploy/kolla/ansible/playbooks/cloud-ui-preflight.yml"
EXAMPLE_VARS = "deploy/kolla/ansible/examples/cloud-ui-vars.yml.example"
EVIDENCE = "docs/generated/e09-live-reconfigure-bundle.md"


def fixture_value(*parts: str) -> str:
    return "".join(parts)


def read_text(relative_path: str) -> str:
    return (ROOT / relative_path).read_text(encoding="utf-8")


def load_yaml(relative_path: str) -> Any:
    return yaml.safe_load(read_text(relative_path))


def test_e09_live_reconfigure_bundle_files_exist() -> None:
    for relative_path in [
        PLAYBOOK,
        EXAMPLE_VARS,
        EVIDENCE,
        "docs/execplans/E09-live-reconfigure-bundle.md",
    ]:
        assert (ROOT / relative_path).exists(), relative_path


def test_preflight_playbook_is_local_and_imports_only_validation() -> None:
    playbook = load_yaml(PLAYBOOK)
    assert isinstance(playbook, list)
    assert len(playbook) == 1

    play = playbook[0]
    assert play["hosts"] == "localhost"
    assert play["connection"] == "local"
    assert play["gather_facts"] is False

    tasks = play["tasks"]
    assert isinstance(tasks, list)
    text = read_text(PLAYBOOK)
    assert "tasks_from: validate" in text
    assert "cloud_ui_enabled: true" in text
    assert "cloud_ui_test_stand | bool" in text
    assert "cloud_ui_rollback_window_open | bool" in text
    assert "cloud_ui_backend_image_digest is match('^sha256:[0-9a-f]{64}$')" in text
    assert "cloud_ui_frontend_image_digest is match('^sha256:[0-9a-f]{64}$')" in text
    assert "cloud_ui_database_url | length > 0" in text
    assert "cloud_ui_rabbitmq_url | length > 0" in text

    import_tasks = [task for task in tasks if "ansible.builtin.import_role" in task]
    assert len(import_tasks) == 1
    import_args = import_tasks[0]["ansible.builtin.import_role"]
    assert import_args == {"name": "cloud_ui", "tasks_from": "validate"}


def test_preflight_playbook_tasks_are_validation_only_modules() -> None:
    playbook = load_yaml(PLAYBOOK)
    tasks = playbook[0]["tasks"]
    assert isinstance(tasks, list)

    allowed_task_keys = {
        "name",
        "no_log",
        "ansible.builtin.assert",
        "ansible.builtin.import_role",
    }
    allowed_action_keys = {"ansible.builtin.assert", "ansible.builtin.import_role"}

    import_tasks = []
    for task in tasks:
        assert isinstance(task, dict)
        assert set(task) <= allowed_task_keys
        action_keys = [key for key in task if key in allowed_action_keys]
        assert len(action_keys) == 1
        if action_keys[0] == "ansible.builtin.import_role":
            import_tasks.append(task)

    assert len(import_tasks) == 1
    assert import_tasks[0]["ansible.builtin.import_role"] == {
        "name": "cloud_ui",
        "tasks_from": "validate",
    }


def test_preflight_runtime_secret_assertion_is_no_log() -> None:
    playbook = load_yaml(PLAYBOOK)
    tasks = playbook[0]["tasks"]
    assert isinstance(tasks, list)

    secret_assertions = {
        "cloud_ui_database_url | length > 0",
        "cloud_ui_rabbitmq_url | length > 0",
    }
    secret_assert_tasks = []
    for task in tasks:
        assert isinstance(task, dict)
        assert_args = task.get("ansible.builtin.assert")
        if not isinstance(assert_args, dict):
            continue
        assertions = assert_args.get("that", [])
        if isinstance(assertions, list) and secret_assertions.issubset(assertions):
            secret_assert_tasks.append(task)

    assert len(secret_assert_tasks) == 1
    assert secret_assert_tasks[0].get("no_log") is True


def test_preflight_bundle_does_not_execute_live_or_mutating_commands() -> None:
    combined = "\n".join(
        read_text(path)
        for path in [
            PLAYBOOK,
            EXAMPLE_VARS,
            "deploy/kolla/ansible/README.md",
            EVIDENCE,
        ]
    )
    lowered = combined.lower()

    for forbidden in [
        "kolla-ansible reconfigure",
        "kolla-ansible deploy",
        "kolla-ansible destroy",
        "kolla_container:",
        "community.mysql",
        "community.rabbitmq",
        "shell:",
        "command:",
        "production approved",
        "12 live containers proven",
    ]:
        assert forbidden not in lowered


def test_example_vars_are_placeholders_and_secret_safe() -> None:
    example = read_text(EXAMPLE_VARS)
    example_vars = load_yaml(EXAMPLE_VARS)
    assert isinstance(example_vars, dict)

    assert example_vars["cloud_ui_test_stand"] is True
    assert example_vars["cloud_ui_rollback_window_open"] is False
    assert example_vars["cloud_ui_enabled"] is True
    assert re.match(
        r"^sha256:[0-9a-f]{64}$",
        example_vars["cloud_ui_backend_image_digest"],
    )
    assert re.match(
        r"^sha256:[0-9a-f]{64}$",
        example_vars["cloud_ui_frontend_image_digest"],
    )
    assert (
        example_vars["cloud_ui_database_url"]
        == "{{ lookup('ansible.builtin.env', 'CLOUD_UI_DATABASE_URL') }}"
    )
    assert (
        example_vars["cloud_ui_rabbitmq_url"]
        == "{{ lookup('ansible.builtin.env', 'CLOUD_UI_RABBITMQ_URL') }}"
    )

    for expected in [
        "cloud_ui_test_stand: true",
        "cloud_ui_rollback_window_open: false",
        "cloud_ui_enabled: true",
        "cloud_ui_backend_image_digest: \"sha256:",
        "cloud_ui_frontend_image_digest: \"sha256:",
        "lookup('ansible.builtin.env', 'CLOUD_UI_DATABASE_URL')",
        "lookup('ansible.builtin.env', 'CLOUD_UI_RABBITMQ_URL')",
    ]:
        assert expected in example

    for forbidden in [
        fixture_value("admin", "123"),
        fixture_value("mysql+pymysql://", "cloud_ui", ":"),
        fixture_value("amqp://", "cloud_ui", ":"),
        "BEGIN ",
        "clouds.yaml",
        "openrc",
        "production",
    ]:
        assert forbidden not in example


def test_docs_record_preflight_scope_and_pending_live_evidence() -> None:
    evidence = read_text(EVIDENCE)
    readme = read_text("deploy/kolla/ansible/README.md")
    traceability = read_text("docs/11_DKB_TRACEABILITY.md")
    risk_register = read_text("docs/generated/risk-register.md")

    for text in (evidence, readme, traceability):
        assert "E09 live reconfigure preflight bundle" in text
        assert "preflight only" in text.lower()
        assert "runtime secret value" in text

    for text in (evidence, traceability):
        assert "pending_external_evidence" in text

    assert "R-069" in risk_register
    assert "preflight bundle mistaken for deployment acceptance" in risk_register

    risk_ids = re.findall(r"^\| (R-\d{3}) \|", risk_register, flags=re.MULTILINE)
    duplicate_ids = {risk_id for risk_id in risk_ids if risk_ids.count(risk_id) > 1}
    assert duplicate_ids == set()
