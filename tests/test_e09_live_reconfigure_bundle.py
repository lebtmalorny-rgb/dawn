import re
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]

PLAYBOOK = "deploy/kolla/ansible/playbooks/cloud-ui-preflight.yml"
EXAMPLE_VARS = "deploy/kolla/ansible/examples/cloud-ui-vars.yml.example"
EVIDENCE = "docs/generated/e09-live-reconfigure-bundle.md"
EXECPLAN = "docs/execplans/E09-live-reconfigure-bundle.md"
README = "deploy/kolla/ansible/README.md"
TRACEABILITY = "docs/11_DKB_TRACEABILITY.md"
RISK_REGISTER = "docs/generated/risk-register.md"
TASK1_TARGET_ARTIFACTS = [
    PLAYBOOK,
    EXAMPLE_VARS,
    EVIDENCE,
    EXECPLAN,
    README,
    TRACEABILITY,
    RISK_REGISTER,
]
ZERO_SHA256_DIGEST = "sha256:0000000000000000000000000000000000000000000000000000000000000000"


def fixture_value(*parts: str) -> str:
    return "".join(parts)


def read_text(relative_path: str) -> str:
    return (ROOT / relative_path).read_text(encoding="utf-8")


def load_yaml(relative_path: str) -> Any:
    return yaml.safe_load(read_text(relative_path))


def load_play() -> dict[str, Any]:
    playbook = load_yaml(PLAYBOOK)
    assert isinstance(playbook, list)
    assert len(playbook) == 1
    play = playbook[0]
    assert isinstance(play, dict)
    return play


def load_tasks() -> list[dict[str, Any]]:
    tasks = load_play()["tasks"]
    assert isinstance(tasks, list)
    validated_tasks = []
    for task in tasks:
        assert isinstance(task, dict)
        validated_tasks.append(task)
    return validated_tasks


def playbook_assert_conditions() -> set[str]:
    conditions = set()
    for task in load_tasks():
        assert_args = task.get("ansible.builtin.assert")
        if not isinstance(assert_args, dict):
            continue
        task_conditions = assert_args.get("that", [])
        assert isinstance(task_conditions, list)
        for condition in task_conditions:
            assert isinstance(condition, str)
            conditions.add(condition)
    return conditions


def nested_strings(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        strings = []
        for item_key, item_value in value.items():
            strings.extend(nested_strings(item_key))
            strings.extend(nested_strings(item_value))
        return strings
    if isinstance(value, list):
        strings = []
        for item in value:
            strings.extend(nested_strings(item))
        return strings
    return []


def test_e09_live_reconfigure_bundle_files_exist() -> None:
    for relative_path in [
        PLAYBOOK,
        EXAMPLE_VARS,
        EVIDENCE,
        EXECPLAN,
    ]:
        assert (ROOT / relative_path).exists(), relative_path


def test_preflight_playbook_is_local_and_imports_only_validation() -> None:
    play = load_play()
    allowed_play_keys = {"name", "hosts", "connection", "gather_facts", "vars", "tasks"}
    unsafe_play_keys = {
        "become",
        "collections",
        "environment",
        "handlers",
        "import_playbook",
        "post_tasks",
        "pre_tasks",
        "roles",
        "strategy",
        "vars_files",
    }

    assert set(play) <= allowed_play_keys
    assert unsafe_play_keys.isdisjoint(play)
    assert play["hosts"] == "localhost"
    assert play["connection"] == "local"
    assert play["gather_facts"] is False
    assert play["vars"] == {"cloud_ui_enabled": True}

    tasks = load_tasks()
    conditions = playbook_assert_conditions()
    assert {
        "cloud_ui_test_stand | bool",
        "cloud_ui_rollback_window_open | bool",
        "cloud_ui_backend_image_digest is match('^sha256:[0-9a-f]{64}$')",
        "cloud_ui_frontend_image_digest is match('^sha256:[0-9a-f]{64}$')",
        "cloud_ui_database_url | length > 0",
        "cloud_ui_rabbitmq_url | length > 0",
    } <= conditions

    import_tasks = [task for task in tasks if "ansible.builtin.import_role" in task]
    assert len(import_tasks) == 1
    import_args = import_tasks[0]["ansible.builtin.import_role"]
    assert import_args == {"name": "cloud_ui", "tasks_from": "validate"}


def test_preflight_playbook_tasks_are_validation_only_modules() -> None:
    tasks = load_tasks()
    allowed_task_keys = {
        "name",
        "no_log",
        "ansible.builtin.assert",
        "ansible.builtin.import_role",
    }
    allowed_action_keys = {"ansible.builtin.assert", "ansible.builtin.import_role"}

    import_tasks = []
    for task in tasks:
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
    tasks = load_tasks()
    secret_assertions = {
        "cloud_ui_database_url | length > 0",
        "cloud_ui_rabbitmq_url | length > 0",
    }
    secret_assert_tasks = []
    for task in tasks:
        assert_args = task.get("ansible.builtin.assert")
        if not isinstance(assert_args, dict):
            continue
        assertions = assert_args.get("that", [])
        if isinstance(assertions, list) and secret_assertions.issubset(assertions):
            secret_assert_tasks.append(task)

    assert len(secret_assert_tasks) == 1
    assert secret_assert_tasks[0].get("no_log") is True

    for task in tasks:
        task_references = "\n".join(nested_strings(task))
        if "cloud_ui_database_url" in task_references or "cloud_ui_rabbitmq_url" in task_references:
            assert task.get("no_log") is True


def test_preflight_bundle_does_not_execute_live_or_mutating_commands() -> None:
    combined = "\n".join(read_text(path) for path in TASK1_TARGET_ARTIFACTS)
    lowered = combined.lower()

    for forbidden in [
        "kolla-ansible reconfigure",
        "kolla-ansible deploy",
        "kolla-ansible destroy",
        "kolla-ansible upgrade",
        "kolla_container:",
        "community.mysql",
        "community.rabbitmq",
        "shell:",
        "command:",
        "production approved",
        "12 live containers proven",
    ]:
        assert forbidden not in lowered


def test_task1_artifacts_do_not_contain_secret_canaries_or_credential_urls() -> None:
    credential_url_patterns = [
        r"mysql\+pymysql://[^\s'\"/@:]+:[^\s'\"/@]+@",
        r"amqps?://[^\s'\"/@:]+:[^\s'\"/@]+@",
    ]

    for relative_path in TASK1_TARGET_ARTIFACTS:
        text = read_text(relative_path)
        for forbidden in [
            fixture_value("admin", "123"),
            fixture_value("mysql+pymysql://", "cloud_ui", ":"),
            fixture_value("amqp://", "cloud_ui", ":"),
            fixture_value("BEGIN", " "),
            "clouds.yaml",
            "openrc",
        ]:
            assert forbidden not in text, relative_path
        for pattern in credential_url_patterns:
            assert re.search(pattern, text) is None, relative_path


def test_example_vars_are_placeholders_and_secret_safe() -> None:
    example = read_text(EXAMPLE_VARS)
    example_vars = load_yaml(EXAMPLE_VARS)
    assert isinstance(example_vars, dict)

    assert example_vars["cloud_ui_test_stand"] is True
    assert example_vars["cloud_ui_rollback_window_open"] is False
    assert example_vars["cloud_ui_enabled"] is True
    assert example_vars["cloud_ui_backend_image_digest"] == ZERO_SHA256_DIGEST
    assert example_vars["cloud_ui_frontend_image_digest"] == ZERO_SHA256_DIGEST
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
    readme = read_text(README)
    traceability = read_text(TRACEABILITY)
    risk_register = read_text(RISK_REGISTER)

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
