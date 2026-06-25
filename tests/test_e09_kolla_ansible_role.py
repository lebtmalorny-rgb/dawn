import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
ROLE_ROOT = ROOT / "deploy/kolla/ansible/roles/cloud_ui"

EXPECTED_ROLE_FILES = [
    "deploy/kolla/ansible/README.md",
    "deploy/kolla/ansible/roles/cloud_ui/defaults/main.yml",
    "deploy/kolla/ansible/roles/cloud_ui/handlers/main.yml",
    "deploy/kolla/ansible/roles/cloud_ui/tasks/main.yml",
    "deploy/kolla/ansible/roles/cloud_ui/tasks/validate.yml",
    "deploy/kolla/ansible/roles/cloud_ui/tasks/config.yml",
    "deploy/kolla/ansible/roles/cloud_ui/tasks/migration.yml",
    "deploy/kolla/ansible/roles/cloud_ui/tasks/containers.yml",
    "deploy/kolla/ansible/roles/cloud_ui/templates/cloud-ui-backend.env.j2",
    "deploy/kolla/ansible/roles/cloud_ui/templates/cloud-ui-frontend.conf.j2",
    "deploy/kolla/ansible/roles/cloud_ui/templates/cloud-ui-haproxy.cfg.j2",
    "docs/generated/e09-kolla-ansible-role.md",
]

EXPECTED_SERVICES = {
    "cloud_ui_frontend",
    "cloud_ui_api",
    "cloud_ui_worker",
    "cloud_ui_events",
}


def read_text(relative_path: str) -> str:
    return (ROOT / relative_path).read_text(encoding="utf-8")


def load_yaml(relative_path: str) -> dict:
    return yaml.safe_load(read_text(relative_path))


def load_yaml_list(relative_path: str) -> list[dict]:
    loaded = yaml.safe_load(read_text(relative_path))
    if not isinstance(loaded, list):
        return []
    return loaded


def role_texts() -> dict[str, str]:
    if not ROLE_ROOT.exists():
        return {}

    return {
        str(path.relative_to(ROLE_ROOT)):
        path.read_text(encoding="utf-8")
        for path in ROLE_ROOT.rglob("*")
        if path.is_file()
    }


def test_e09_ansible_role_files_exist() -> None:
    for relative_path in EXPECTED_ROLE_FILES:
        assert (ROOT / relative_path).exists(), relative_path


def test_defaults_declare_four_permanent_services_and_two_images() -> None:
    defaults = load_yaml("deploy/kolla/ansible/roles/cloud_ui/defaults/main.yml")
    services = defaults["cloud_ui_services"]

    assert set(services) == EXPECTED_SERVICES
    assert defaults["cloud_ui_backend_image"] == "cloud-ui-backend"
    assert defaults["cloud_ui_frontend_image"] == "cloud-ui-frontend"
    assert defaults["cloud_ui_backend_image_tag"] != "latest"
    assert defaults["cloud_ui_frontend_image_tag"] != "latest"
    assert defaults["cloud_ui_permanent_container_count_per_node"] == 4

    assert services["cloud_ui_frontend"]["image"] == "{{ cloud_ui_frontend_image_full }}"
    for service_name in ["cloud_ui_api", "cloud_ui_worker", "cloud_ui_events"]:
        assert services[service_name]["image"] == "{{ cloud_ui_backend_image_full }}"

    assert services["cloud_ui_api"]["command"] == "cloud-ui api"
    assert services["cloud_ui_worker"]["command"] == "cloud-ui worker"
    assert services["cloud_ui_events"]["command"] == "cloud-ui events"
    assert "cloud-ui db-upgrade" not in {
        service["command"] for service in services.values()
    }


def test_tasks_are_skeleton_only_and_import_expected_steps() -> None:
    main_tasks = load_yaml_list("deploy/kolla/ansible/roles/cloud_ui/tasks/main.yml")
    containers_tasks = load_yaml_list(
        "deploy/kolla/ansible/roles/cloud_ui/tasks/containers.yml"
    )
    containers_tasks_text = read_text(
        "deploy/kolla/ansible/roles/cloud_ui/tasks/containers.yml"
    )
    validate_tasks = load_yaml_list(
        "deploy/kolla/ansible/roles/cloud_ui/tasks/validate.yml"
    )

    assert isinstance(main_tasks, list)
    actual_imports: list[str] = []
    for task in main_tasks:
        assert isinstance(task, dict)
        assert (
            "include_tasks" in task or "ansible.builtin.include_tasks" in task
        ), "Only include_tasks entries are allowed in main.yml"
        if "include_tasks" in task:
            actual_imports.append(str(task["include_tasks"]).strip())
        elif "ansible.builtin.include_tasks" in task:
            actual_imports.append(
                str(task["ansible.builtin.include_tasks"]).strip()
            )

    assert len(main_tasks) == len(actual_imports)
    assert actual_imports == ["validate.yml", "config.yml", "migration.yml", "containers.yml"]

    assert isinstance(containers_tasks, list)
    set_fact_value = None
    for task in containers_tasks:
        assert isinstance(task, dict)
        fact_task = task.get("ansible.builtin.set_fact") or task.get("set_fact")
        if isinstance(fact_task, dict) and "cloud_ui_container_definitions" in fact_task:
            set_fact_value = fact_task["cloud_ui_container_definitions"]
            break

    assert set_fact_value is not None
    assert set_fact_value == "{{ cloud_ui_services }}"

    assert isinstance(validate_tasks, list)
    validate_thats = []
    for task in validate_tasks:
        assert isinstance(task, dict)
        assert_block = task.get("ansible.builtin.assert") or task.get("assert")
        assert isinstance(assert_block, dict)
        that = assert_block.get("that")
        assert isinstance(that, list)
        validate_thats.extend([str(item) for item in that])

    for expected in [
        "cloud_ui_backend_image_tag != 'latest'",
        "cloud_ui_frontend_image_tag != 'latest'",
    ]:
        assert expected in validate_thats

    assert "kolla_container:" not in containers_tasks_text


def test_role_templates_contain_only_non_secret_config() -> None:
    backend_template = read_text(
        "deploy/kolla/ansible/roles/cloud_ui/templates/cloud-ui-backend.env.j2"
    )
    frontend_template = read_text(
        "deploy/kolla/ansible/roles/cloud_ui/templates/cloud-ui-frontend.conf.j2"
    )
    haproxy_template = read_text(
        "deploy/kolla/ansible/roles/cloud_ui/templates/cloud-ui-haproxy.cfg.j2"
    )

    for expected in [
        "CLOUD_UI_CONFIG_VERSION",
        "CLOUD_UI_PUBLIC_BASE_URL",
        "CLOUD_UI_LOG_LEVEL",
        "CLOUD_UI_BACKEND_ROLE",
    ]:
        assert expected in backend_template

    assert "listen {{ cloud_ui_frontend_listen_port }};" in frontend_template

    combined_templates = f"{backend_template}\n{frontend_template}\n{haproxy_template}".lower()
    for forbidden in ["password", "token", "private_key", "secret_key"]:
        assert forbidden not in combined_templates


def test_role_scope_excludes_later_e09_work() -> None:
    assert ROLE_ROOT.exists(), ROLE_ROOT
    combined_role = "\n".join(role_texts().values()).lower()

    for forbidden in [
        "mysql_user",
        "rabbitmq_user",
        "rabbitmq_vhost",
        "community.mysql",
        "community.rabbitmq",
        "tls_private",
        "production",
        "inventory.ini",
        "kolla_container:",
    ]:
        assert forbidden not in combined_role

    defaults = load_yaml("deploy/kolla/ansible/roles/cloud_ui/defaults/main.yml")
    services = defaults["cloud_ui_services"]
    assert "cloud-ui db-upgrade" not in {
        service["command"] for service in services.values()
    }

    assert "pending_external_evidence" in read_text(
        "docs/generated/e09-kolla-ansible-role.md"
    )


def test_e09_role_evidence_records_limits_and_dkb_scope() -> None:
    evidence = read_text("docs/generated/e09-kolla-ansible-role.md")

    for expected in [
        "Stage: E09.2 Ansible role skeleton",
        "cloud_ui_frontend",
        "cloud_ui_api",
        "cloud_ui_worker",
        "cloud_ui_events",
        "repository-side role skeleton",
        "pending_external_evidence",
        "ДКБ-69",
        "ДКБ-70",
        "ДКБ-76/77/80",
    ]:
        assert expected in evidence

    assert "12 live containers proven" not in evidence
    assert "production approved" not in evidence.lower()


def test_risk_register_ids_are_unique() -> None:
    risk_register = read_text("docs/generated/risk-register.md")
    risk_ids = re.findall(r"^\| (R-\d{3}) \|", risk_register, flags=re.MULTILINE)
    duplicate_ids = {
        risk_id
        for risk_id in risk_ids
        if risk_ids.count(risk_id) > 1
    }

    assert duplicate_ids == set()
