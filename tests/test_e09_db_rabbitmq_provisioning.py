import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
ROLE_ROOT = ROOT / "deploy/kolla/ansible/roles/cloud_ui_provisioning"

EXPECTED_FILES = [
    "deploy/kolla/ansible/roles/cloud_ui_provisioning/defaults/main.yml",
    "deploy/kolla/ansible/roles/cloud_ui_provisioning/tasks/main.yml",
    "deploy/kolla/ansible/roles/cloud_ui_provisioning/tasks/validate.yml",
    "deploy/kolla/ansible/roles/cloud_ui_provisioning/tasks/vault.yml",
    "deploy/kolla/ansible/roles/cloud_ui_provisioning/tasks/database.yml",
    "deploy/kolla/ansible/roles/cloud_ui_provisioning/tasks/rabbitmq.yml",
    "docs/generated/e09-db-rabbitmq-provisioning.md",
]


def read_text(relative_path: str) -> str:
    return (ROOT / relative_path).read_text(encoding="utf-8")


def load_yaml(relative_path: str) -> object:
    return yaml.safe_load(read_text(relative_path))


def load_yaml_list(relative_path: str) -> list[dict]:
    loaded = load_yaml(relative_path)
    if not isinstance(loaded, list):
        return []
    return loaded


def role_text() -> str:
    if not ROLE_ROOT.exists():
        return ""
    return "\n".join(
        path.read_text(encoding="utf-8")
        for path in ROLE_ROOT.rglob("*")
        if path.is_file()
    )


def test_e09_db_rabbitmq_files_exist() -> None:
    for relative_path in EXPECTED_FILES:
        assert (ROOT / relative_path).exists(), relative_path


def test_provisioning_defaults_define_non_secret_scope() -> None:
    defaults = load_yaml(
        "deploy/kolla/ansible/roles/cloud_ui_provisioning/defaults/main.yml"
    )
    assert isinstance(defaults, dict)

    assert defaults["cloud_ui_provisioning_enabled"] is False
    assert defaults["cloud_ui_vault_addr"] == "https://192.168.10.15:8200"
    assert defaults["cloud_ui_vault_kv_mount"] == "kv"
    assert defaults["cloud_ui_vault_secret_paths"] == {
        "mariadb_runtime": "cloud-ui/local/mariadb/runtime",
        "mariadb_migration": "cloud-ui/local/mariadb/migration",
        "rabbitmq_runtime": "cloud-ui/local/rabbitmq/runtime",
    }

    assert defaults["cloud_ui_database_name"] == "cloud_ui"
    assert defaults["cloud_ui_database_runtime_user"] == "cloud_ui"
    assert defaults["cloud_ui_database_migration_user"] == "cloud_ui_migration"
    assert defaults["cloud_ui_rabbitmq_vhost"] == "/cloud-ui"
    assert defaults["cloud_ui_rabbitmq_user"] == "cloud_ui"
    assert set(defaults["cloud_ui_rabbitmq_exchanges"]) == {
        "cloud-ui.events",
        "cloud-ui.jobs",
        "cloud-ui.audit",
        "cloud-ui.dlx",
    }
    assert set(defaults["cloud_ui_rabbitmq_queues"]) == {
        "cloud-ui.events",
        "cloud-ui.jobs",
        "cloud-ui.audit",
        "cloud-ui.dead",
    }

    serialized = yaml.safe_dump(defaults).lower()
    for forbidden in ["password:", "token:", "private_key", "secret_key", "clouds.yaml"]:
        assert forbidden not in serialized


def test_provisioning_tasks_are_separate_and_secret_safe() -> None:
    main_tasks = load_yaml_list(
        "deploy/kolla/ansible/roles/cloud_ui_provisioning/tasks/main.yml"
    )
    actual_includes = []
    for task in main_tasks:
        assert isinstance(task, dict)
        include_value = task.get("ansible.builtin.include_tasks") or task.get(
            "include_tasks"
        )
        assert include_value is not None
        actual_includes.append(str(include_value).strip())

    assert actual_includes == ["validate.yml", "vault.yml", "database.yml", "rabbitmq.yml"]

    combined = role_text().lower()
    for required in [
        "community.hashi_vault.vault_kv2_get",
        "community.mysql.mysql_db",
        "community.mysql.mysql_user",
        "community.rabbitmq.rabbitmq_vhost",
        "community.rabbitmq.rabbitmq_user",
        "cloud-ui.dlx",
    ]:
        assert required in combined

    for task_file in ["vault.yml", "database.yml", "rabbitmq.yml"]:
        tasks = load_yaml_list(
            f"deploy/kolla/ansible/roles/cloud_ui_provisioning/tasks/{task_file}"
        )
        assert tasks, task_file
        assert all(task.get("no_log") is True for task in tasks), task_file

    for forbidden in ["kolla_container:", "openstack rpc", "production approved"]:
        assert forbidden not in combined


def test_rabbitmq_user_permissions_are_exhaustive_and_rotatable() -> None:
    tasks = load_yaml_list(
        "deploy/kolla/ansible/roles/cloud_ui_provisioning/tasks/rabbitmq.yml"
    )
    rabbitmq_user_tasks = [
        task
        for task in tasks
        if "community.rabbitmq.rabbitmq_user" in task
    ]
    assert len(rabbitmq_user_tasks) == 1

    module_args = rabbitmq_user_tasks[0]["community.rabbitmq.rabbitmq_user"]
    assert "vhost" not in module_args
    assert "configure_priv" not in module_args
    assert "write_priv" not in module_args
    assert "read_priv" not in module_args
    expected_update_mode = "".join(("al", "ways"))
    assert module_args["update_password"] == expected_update_mode
    assert module_args["permissions"] == [
        {
            "vhost": "{{ cloud_ui_rabbitmq_vhost }}",
            "configure_priv": "{{ cloud_ui_rabbitmq_permission_configure }}",
            "write_priv": "{{ cloud_ui_rabbitmq_permission_write }}",
            "read_priv": "{{ cloud_ui_rabbitmq_permission_read }}",
        }
    ]


def test_e09_db_rabbitmq_evidence_records_live_scope_and_limits() -> None:
    evidence = read_text("docs/generated/e09-db-rabbitmq-provisioning.md")

    for expected in [
        "Stage: E09.3 Database/RabbitMQ provisioning",
        "Test Ansible host: 192.168.10.15",
        "Kolla inventory: /etc/kolla/all-in-one",
        "Vault/SecMan lab path",
        "cloud_ui",
        "cloud_ui_migration",
        "/cloud-ui",
        "pending_external_evidence",
        "ДКБ-55/56",
        "ДКБ-76/77/80",
    ]:
        assert expected in evidence

    assert "production approved" not in evidence.lower()
    assert "root token" not in evidence.lower()
    assert "unseal key" not in evidence.lower()
    assert "client token" not in evidence.lower()


def test_db_mq_auth_boundary_docs_do_not_blame_keystone() -> None:
    deploy_doc = read_text("docs/12_DEPLOY_ROCKY_KOLLA.md")
    provisioning_evidence = read_text("docs/generated/e09-db-rabbitmq-provisioning.md")
    smoke_evidence = read_text("docs/generated/e09-deployment-smoke-evidence.md")

    for text in (deploy_doc, provisioning_evidence):
        assert "Keystone" in text
        assert "MariaDB" in text
        assert "RabbitMQ" in text
        assert "oslo.messaging" in text
        assert "transport URL" in text
        assert "not Keystone" in text or "не Keystone" in text

    assert "not Keystone RBAC" in smoke_evidence
    assert "1045 Access denied" in smoke_evidence
    assert "403 ACCESS_REFUSED" in smoke_evidence


def test_risk_register_ids_are_unique_after_e09_3() -> None:
    risk_register = read_text("docs/generated/risk-register.md")
    risk_ids = re.findall(r"^\| (R-\d{3}) \|", risk_register, flags=re.MULTILINE)
    duplicate_ids = {risk_id for risk_id in risk_ids if risk_ids.count(risk_id) > 1}

    assert duplicate_ids == set()
