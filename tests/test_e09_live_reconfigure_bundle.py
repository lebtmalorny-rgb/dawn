import re
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]

PLAYBOOK = "deploy/kolla/ansible/playbooks/cloud-ui-preflight.yml"
VALIDATE_TASKS = "deploy/kolla/ansible/roles/cloud_ui/tasks/validate.yml"
EXAMPLE_VARS = "deploy/kolla/ansible/examples/cloud-ui-vars.yml.example"
EVIDENCE = "docs/generated/e09-live-reconfigure-bundle.md"
EXECPLAN = "docs/execplans/E09-live-reconfigure-bundle.md"
README = "deploy/kolla/ansible/README.md"
TRACEABILITY = "docs/11_DKB_TRACEABILITY.md"
RISK_REGISTER = "docs/generated/risk-register.md"
TASK1_NEW_ARTIFACTS = [
    PLAYBOOK,
    VALIDATE_TASKS,
    EXAMPLE_VARS,
    EVIDENCE,
    EXECPLAN,
]
PREFLIGHT_SECTION_HEADING = "E09 live reconfigure preflight bundle"
RISK_ID = "R-069"
PREFLIGHT_ASSERTIONS = {
    "cloud_ui_test_stand | bool",
    "cloud_ui_rollback_window_open | bool",
    "cloud_ui_backend_image_digest is match('^sha256:[0-9a-f]{64}$')",
    "cloud_ui_frontend_image_digest is match('^sha256:[0-9a-f]{64}$')",
    "cloud_ui_database_url | length > 0",
    "cloud_ui_rabbitmq_url | length > 0",
}
SECRET_REFERENCE_MARKERS = {
    "cloud_ui_database_url",
    "cloud_ui_rabbitmq_url",
    "CLOUD_UI_DATABASE_URL",
    "CLOUD_UI_RABBITMQ_URL",
}
ZERO_SHA256_DIGEST = "sha256:0000000000000000000000000000000000000000000000000000000000000000"


def fixture_value(*parts: str) -> str:
    return "".join(parts)


def read_text(relative_path: str) -> str:
    return (ROOT / relative_path).read_text(encoding="utf-8")


def load_yaml(relative_path: str) -> Any:
    return yaml.safe_load(read_text(relative_path))


def load_task_list(relative_path: str) -> list[dict[str, Any]]:
    tasks = load_yaml(relative_path)
    assert isinstance(tasks, list)
    validated_tasks = []
    for task in tasks:
        assert isinstance(task, dict)
        validated_tasks.append(task)
    return validated_tasks


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


def extract_markdown_section(relative_path: str, heading_text: str) -> str:
    lines = read_text(relative_path).splitlines()
    for start, line in enumerate(lines):
        match = re.match(r"^(#{1,6})\s+(.+?)\s*$", line)
        if not match or match.group(2).strip().lower() != heading_text.lower():
            continue

        heading_level = len(match.group(1))
        end = len(lines)
        for next_index in range(start + 1, len(lines)):
            next_match = re.match(r"^(#{1,6})\s+", lines[next_index])
            if next_match and len(next_match.group(1)) <= heading_level:
                end = next_index
                break
        return "\n".join(lines[start:end])

    raise AssertionError(f"{relative_path} missing section: {heading_text}")


def extract_risk_row(risk_id: str) -> str:
    for line in read_text(RISK_REGISTER).splitlines():
        if line.startswith(f"| {risk_id} |"):
            return line
    raise AssertionError(f"{RISK_REGISTER} missing row: {risk_id}")


def task1_contract_text_blocks() -> dict[str, str]:
    return {
        **{relative_path: read_text(relative_path) for relative_path in TASK1_NEW_ARTIFACTS},
        f"{README}#{PREFLIGHT_SECTION_HEADING}": extract_markdown_section(
            README,
            PREFLIGHT_SECTION_HEADING,
        ),
        f"{TRACEABILITY}#{PREFLIGHT_SECTION_HEADING}": extract_markdown_section(
            TRACEABILITY,
            PREFLIGHT_SECTION_HEADING,
        ),
        f"{RISK_REGISTER}#{RISK_ID}": extract_risk_row(RISK_ID),
    }


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


def task_references_secret_input(task: dict[str, Any]) -> bool:
    task_references = "\n".join(nested_strings(task))
    return any(marker in task_references for marker in SECRET_REFERENCE_MARKERS)


def test_e09_live_reconfigure_bundle_files_exist() -> None:
    for relative_path in [
        PLAYBOOK,
        VALIDATE_TASKS,
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
    assert conditions == PREFLIGHT_ASSERTIONS

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
        if task_references_secret_input(task):
            assert task.get("no_log") is True


def test_imported_role_validation_tasks_are_assert_only_and_secret_safe() -> None:
    tasks = load_task_list(VALIDATE_TASKS)
    assert tasks

    allowed_task_keys = {"name", "no_log", "ansible.builtin.assert"}
    for task in tasks:
        assert set(task) <= allowed_task_keys
        action_keys = [key for key in task if key == "ansible.builtin.assert"]
        assert action_keys == ["ansible.builtin.assert"]
        if task_references_secret_input(task):
            assert task.get("no_log") is True


def test_preflight_bundle_does_not_execute_live_or_mutating_commands() -> None:
    forbidden_patterns = [
        r"(?im)^\s*(?:[-*]\s+)?(?:`|\$|sudo\s+)?kolla-ansible"
        r"(?:\s+(?!deploy\b|reconfigure\b|destroy\b|upgrade\b)\S+)*"
        r"\s+(?:deploy|reconfigure|destroy|upgrade)\b",
        r"(?im)^\s*(?:[-*]\s+)?(?:ansible\.builtin\.)?shell\s*:",
        r"(?im)^\s*(?:[-*]\s+)?(?:ansible\.builtin\.)?command\s*:",
        r"(?im)^\s*(?:[-*]\s+)?kolla_container\s*:",
        r"(?im)^\s*(?:[-*]\s+)?community\.mysql(?:\.[A-Za-z_]+)?\s*:",
        r"(?im)^\s*(?:[-*]\s+)?community\.rabbitmq(?:\.[A-Za-z_]+)?\s*:",
    ]

    for label, text in task1_contract_text_blocks().items():
        for pattern in forbidden_patterns:
            assert re.search(pattern, text) is None, label


def test_task1_artifacts_do_not_contain_secret_canaries_or_credential_urls() -> None:
    credential_url_patterns = [
        r"mysql\+pymysql://[^\s'\"/@:]+:[^\s'\"/@]+@",
        r"amqps?://[^\s'\"/@:]+:[^\s'\"/@]+@",
    ]

    for label, text in task1_contract_text_blocks().items():
        for forbidden in [
            fixture_value("admin", "123"),
            fixture_value("mysql+pymysql://", "cloud_ui", ":"),
            fixture_value("amqp://", "cloud_ui", ":"),
            fixture_value("BEGIN", " "),
            "clouds.yaml",
            "openrc",
        ]:
            assert forbidden not in text, label
        for pattern in credential_url_patterns:
            assert re.search(pattern, text) is None, label


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
    readme = extract_markdown_section(README, PREFLIGHT_SECTION_HEADING)
    traceability = extract_markdown_section(TRACEABILITY, PREFLIGHT_SECTION_HEADING)
    risk_row = extract_risk_row(RISK_ID)

    for text in (evidence, readme, traceability):
        assert "E09 live reconfigure preflight bundle" in text
        assert "preflight only" in text.lower()
        assert "runtime secret value" in text

    for text in (evidence, traceability):
        assert "pending_external_evidence" in text

    assert RISK_ID in risk_row
    assert "preflight bundle mistaken for deployment acceptance" in risk_row

    risk_ids = re.findall(r"^\| (R-\d{3}) \|", read_text(RISK_REGISTER), flags=re.MULTILINE)
    duplicate_ids = {risk_id for risk_id in risk_ids if risk_ids.count(risk_id) > 1}
    assert duplicate_ids == set()
