from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]

DEFAULTS = "deploy/kolla/ansible/roles/cloud_ui/defaults/main.yml"
MAIN_TASKS = "deploy/kolla/ansible/roles/cloud_ui/tasks/main.yml"
LIVE_TASKS = "deploy/kolla/ansible/roles/cloud_ui/tasks/live-aio.yml"
LIVE_PLAYBOOK = "deploy/kolla/ansible/playbooks/cloud-ui-aio-reconfigure.yml"
CONFIG_TASKS = "deploy/kolla/ansible/roles/cloud_ui/tasks/config.yml"


def read_text(relative_path: str) -> str:
    return (ROOT / relative_path).read_text(encoding="utf-8")


def load_yaml(relative_path: str) -> Any:
    return yaml.safe_load(read_text(relative_path))


def load_tasks(relative_path: str) -> list[dict[str, Any]]:
    loaded = load_yaml(relative_path)
    assert isinstance(loaded, list)
    for task in loaded:
        assert isinstance(task, dict)
    return loaded


def nested_strings(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        result: list[str] = []
        for key, item in value.items():
            result.extend(nested_strings(key))
            result.extend(nested_strings(item))
        return result
    if isinstance(value, list):
        result = []
        for item in value:
            result.extend(nested_strings(item))
        return result
    return []


def task_modules(tasks: list[dict[str, Any]]) -> set[str]:
    ignored_keys = {"name", "when", "loop", "vars", "no_log", "register", "changed_when"}
    modules = set()
    for task in tasks:
        modules.update(key for key in task if key not in ignored_keys)
    return modules


def test_aio_live_role_files_and_defaults_exist() -> None:
    assert (ROOT / LIVE_TASKS).exists()
    assert (ROOT / LIVE_PLAYBOOK).exists()

    defaults = load_yaml(DEFAULTS)
    assert defaults["cloud_ui_aio_live_reconfigure_enabled"] is False
    assert defaults["cloud_ui_aio_network_name"] == "cloud-ui"
    assert defaults["cloud_ui_aio_api_network_alias"] == "api"
    assert defaults["cloud_ui_aio_frontend_host_port"] == 13080
    assert defaults["cloud_ui_aio_api_host_port"] == 18081
    assert defaults["cloud_ui_aio_tmpfs"] == ["/tmp:rw,nosuid,nodev,size=64m"]
    assert defaults["cloud_ui_aio_security_opts"] == ["no-new-privileges:true"]
    assert defaults["cloud_ui_aio_cap_drop"] == ["ALL"]
    assert defaults["cloud_ui_aio_read_only"] is True
    assert defaults["cloud_ui_aio_run_migration"] is True


def test_main_role_imports_aio_live_mode_only_when_enabled() -> None:
    tasks = load_tasks(MAIN_TASKS)
    live_imports = [
        task
        for task in tasks
        if task.get("ansible.builtin.include_tasks") == "live-aio.yml"
    ]

    assert len(live_imports) == 1
    assert live_imports[0]["when"] == "cloud_ui_aio_live_reconfigure_enabled | bool"


def test_aio_live_playbook_targets_only_openstack_aio_and_imports_role() -> None:
    playbook = load_yaml(LIVE_PLAYBOOK)
    assert isinstance(playbook, list)
    assert len(playbook) == 1
    play = playbook[0]

    assert play["hosts"] == "openstack-aio"
    assert play["gather_facts"] is False
    assert play["vars"]["cloud_ui_enabled"] is True
    assert play["vars"]["cloud_ui_aio_live_reconfigure_enabled"] is True
    assert play["tags"] == ["cloud-ui"]
    assert play["roles"] == [{"role": "cloud_ui", "tags": ["cloud-ui"]}]


def test_aio_live_tasks_use_docker_modules_without_shell_or_secret_output() -> None:
    tasks = load_tasks(LIVE_TASKS)
    modules = task_modules(tasks)

    assert "community.docker.docker_network" in modules
    assert "community.docker.docker_volume" in modules
    assert "community.docker.docker_container" in modules
    assert "ansible.builtin.command" not in modules
    assert "ansible.builtin.shell" not in modules
    assert "kolla_container" not in modules

    task_text = read_text(LIVE_TASKS)
    for expected in [
        "read_only: \"{{ cloud_ui_aio_read_only }}\"",
        "cap_drop: \"{{ cloud_ui_aio_cap_drop }}\"",
        "security_opts: \"{{ cloud_ui_aio_security_opts }}\"",
        "tmpfs: \"{{ cloud_ui_aio_tmpfs }}\"",
        "published_ports:",
        "aliases:",
        "cloud-ui db-upgrade",
    ]:
        assert expected in task_text

    sensitive_input_markers = {"cloud_ui_database_url", "cloud_ui_rabbitmq_url"}
    for task in tasks:
        uses_sensitive_runtime_input = any(
            marker in "\n".join(nested_strings(task))
            for marker in sensitive_input_markers
        )
        if uses_sensitive_runtime_input:
            assert task.get("no_log") is True


def test_haproxy_contract_render_is_skipped_when_haproxy_disabled() -> None:
    tasks = load_tasks(CONFIG_TASKS)
    haproxy_tasks = [
        task
        for task in tasks
        if task.get("ansible.builtin.template", {})
        .get("dest", "")
        .endswith("cloud-ui-haproxy.cfg")
    ]

    assert len(haproxy_tasks) == 1
    assert haproxy_tasks[0]["when"] == "cloud_ui_haproxy_enabled | bool"


def test_aio_live_migration_can_be_disabled_for_idempotent_reconfigure() -> None:
    tasks = load_tasks(LIVE_TASKS)
    migration_tasks = [
        task
        for task in tasks
        if task.get("community.docker.docker_container", {}).get("name")
        == "{{ cloud_ui_migration_job.container_name }}"
    ]

    assert len(migration_tasks) == 1
    assert migration_tasks[0]["when"] == "cloud_ui_aio_run_migration | bool"
