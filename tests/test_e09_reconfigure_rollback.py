import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
ROLE_ROOT = ROOT / "deploy/kolla/ansible/roles/cloud_ui"


def read_text(relative_path: str) -> str:
    return (ROOT / relative_path).read_text(encoding="utf-8")


def load_yaml(relative_path: str) -> dict:
    return yaml.safe_load(read_text(relative_path))


def load_yaml_list(relative_path: str) -> list[dict]:
    loaded = yaml.safe_load(read_text(relative_path))
    if not isinstance(loaded, list):
        return []
    return loaded


def task_imports(relative_path: str) -> list[str]:
    imports: list[str] = []
    for task in load_yaml_list(relative_path):
        assert isinstance(task, dict)
        include_value = task.get("include_tasks") or task.get(
            "ansible.builtin.include_tasks"
        )
        if include_value is not None:
            imports.append(str(include_value).strip())
    return imports


def phase_names(phases: list[dict]) -> list[str]:
    return [str(phase["name"]) for phase in phases]


def test_lifecycle_defaults_define_dry_run_contract_and_evidence_gates() -> None:
    defaults = load_yaml("deploy/kolla/ansible/roles/cloud_ui/defaults/main.yml")

    assert defaults["cloud_ui_lifecycle_contract_version"] == (
        "e09.7-reconfigure-rollback"
    )
    assert defaults["cloud_ui_lifecycle_dry_run_only"] is True
    assert defaults["cloud_ui_lifecycle_live_execution_status"] == (
        "pending_external_evidence"
    )
    assert defaults["cloud_ui_lifecycle_required_evidence"] == [
        "test_inventory_approved",
        "registry_digest_pull",
        "migration_precheck_and_run_once",
        "reconfigure_idempotency",
        "rolling_update",
        "failed_update_rollback",
        "disable_uninstall",
        "container_inspection",
    ]

    serialized = yaml.safe_dump(defaults, sort_keys=True).lower()
    for forbidden in [
        "inventory.ini",
        "admin" + "123",
        "begin private key",
        "clouds.yaml",
        "openrc",
        "production approved",
    ]:
        assert forbidden not in serialized


def test_deploy_reconfigure_phases_are_ordered_and_idempotent() -> None:
    defaults = load_yaml("deploy/kolla/ansible/roles/cloud_ui/defaults/main.yml")

    expected_order = [
        "precheck",
        "confirm_backup_and_rollback_window",
        "pull_images_by_digest",
        "migration_precheck",
        "migration_run_once",
        "render_config",
        "apply_permanent_containers",
        "apply_haproxy_route",
        "smoke",
        "reconfigure_idempotency_check",
        "record_evidence",
    ]
    phases = defaults["cloud_ui_deploy_reconfigure_phases"]

    assert phase_names(phases) == expected_order
    assert defaults["cloud_ui_deploy_reconfigure_phase_order"] == expected_order
    assert phases[2]["requires"] == ["cloud_ui_backend_image_digest", "cloud_ui_frontend_image_digest"]
    assert phases[3]["command"] == "cloud-ui db-upgrade --check"
    assert phases[4]["command"] == "cloud-ui db-upgrade"
    assert phases[4]["run_once"] is True
    assert phases[6]["target"] == "cloud_ui_process_topology"
    assert phases[9]["expected_change"] == 0
    assert phases[-1]["evidence"] == "docs/generated/e09-reconfigure-rollback.md"


def test_rolling_upgrade_and_failed_rollback_phase_contracts_are_safe() -> None:
    defaults = load_yaml("deploy/kolla/ansible/roles/cloud_ui/defaults/main.yml")

    upgrade_order = [
        "precheck",
        "assert_rollback_window",
        "pull_new_images_by_digest",
        "run_expand_migration",
        "roll_backend_api",
        "roll_backend_worker_events",
        "roll_frontend",
        "haproxy_health_gate",
        "compatibility_smoke",
        "hold_contract_migration",
        "record_upgrade_evidence",
    ]
    rollback_order = [
        "stop_new_rollout",
        "restore_previous_config_commit",
        "rollback_frontend_image",
        "rollback_backend_image",
        "rerun_reconfigure",
        "smoke_previous_version",
        "preserve_operations_and_audit",
        "record_rollback_evidence",
    ]

    upgrade_phases = defaults["cloud_ui_rolling_upgrade_phases"]
    rollback_phases = defaults["cloud_ui_failed_update_rollback_phases"]

    assert phase_names(upgrade_phases) == upgrade_order
    assert defaults["cloud_ui_rolling_upgrade_phase_order"] == upgrade_order
    assert upgrade_order.index("run_expand_migration") < upgrade_order.index(
        "roll_backend_api"
    )
    assert upgrade_order.index("roll_backend_api") < upgrade_order.index("roll_frontend")
    assert upgrade_phases[9]["contract_migration_allowed"] is False

    assert phase_names(rollback_phases) == rollback_order
    assert defaults["cloud_ui_failed_update_rollback_phase_order"] == rollback_order
    assert rollback_phases[0]["requires"] == ["failed_health_gate_or_operator_abort"]
    assert rollback_phases[6]["preserve"] == [
        "operations",
        "audit_events",
        "read_model",
        "queued_messages",
    ]


def test_rollback_decision_table_and_disable_policy_are_data_preserving() -> None:
    defaults = load_yaml("deploy/kolla/ansible/roles/cloud_ui/defaults/main.yml")

    decision_table = {
        row["condition"]: row
        for row in defaults["cloud_ui_rollback_decision_table"]
    }
    assert decision_table["schema_expand_only"]["rollback_allowed"] is True
    assert decision_table["image_pull_failed"]["rollback_allowed"] is True
    assert decision_table["haproxy_smoke_failed"]["rollback_allowed"] is True
    assert decision_table["contract_migration_applied"]["rollback_allowed"] is False
    assert decision_table["contract_migration_applied"]["required_action"] == (
        "restore_from_approved_backup_or_forward_fix"
    )

    disable_policy = defaults["cloud_ui_disable_uninstall_policy"]
    assert disable_policy == {
        "disable_flag": "cloud_ui_enabled=false",
        "stop_order": [
            "remove_haproxy_route",
            "stop_frontend",
            "stop_api",
            "stop_worker",
            "stop_events",
        ],
        "preserve_database": True,
        "preserve_rabbitmq": True,
        "preserve_vault_paths": True,
        "preserve_logs": True,
        "destructive_cleanup_requires_approval": True,
        "cleanup_status": "pending_external_approval",
    }


def test_lifecycle_task_is_included_and_publishes_dry_run_facts() -> None:
    assert "lifecycle.yml" in task_imports(
        "deploy/kolla/ansible/roles/cloud_ui/tasks/main.yml"
    )
    assert task_imports("deploy/kolla/ansible/roles/cloud_ui/tasks/main.yml") == [
        "validate.yml",
        "lifecycle.yml",
        "config.yml",
        "migration.yml",
        "containers.yml",
        "live-aio.yml",
    ]

    lifecycle_tasks = load_yaml_list(
        "deploy/kolla/ansible/roles/cloud_ui/tasks/lifecycle.yml"
    )
    lifecycle_text = read_text("deploy/kolla/ansible/roles/cloud_ui/tasks/lifecycle.yml")

    for expected_fact in [
        "cloud_ui_lifecycle_plan",
        "cloud_ui_reconfigure_plan",
        "cloud_ui_rolling_upgrade_plan",
        "cloud_ui_failed_update_rollback_plan",
        "cloud_ui_disable_uninstall_plan",
    ]:
        assert expected_fact in lifecycle_text

    assert "kolla-ansible reconfigure" not in lifecycle_text
    assert "kolla-ansible deploy" not in lifecycle_text
    assert "kolla-ansible destroy" not in lifecycle_text
    assert "shell:" not in lifecycle_text
    assert "command:" not in lifecycle_text
    assert all(isinstance(task, dict) for task in lifecycle_tasks)


def test_validate_task_checks_lifecycle_phase_order_and_gates() -> None:
    validate_text = read_text("deploy/kolla/ansible/roles/cloud_ui/tasks/validate.yml")

    for expected in [
        "cloud_ui_lifecycle_dry_run_only | bool",
        "cloud_ui_lifecycle_live_execution_status == 'pending_external_evidence'",
        "cloud_ui_deploy_reconfigure_phases | map(attribute='name') | list == cloud_ui_deploy_reconfigure_phase_order",
        "cloud_ui_rolling_upgrade_phases | map(attribute='name') | list == cloud_ui_rolling_upgrade_phase_order",
        "cloud_ui_failed_update_rollback_phases | map(attribute='name') | list == cloud_ui_failed_update_rollback_phase_order",
        "not cloud_ui_rolling_upgrade_phases[9].contract_migration_allowed",
        "cloud_ui_disable_uninstall_policy.preserve_database | bool",
        "cloud_ui_disable_uninstall_policy.destructive_cleanup_requires_approval | bool",
    ]:
        assert expected in validate_text


def test_e09_role_tests_recognize_lifecycle_as_current_scope() -> None:
    role_test = read_text("tests/test_e09_kolla_ansible_role.py")

    assert "deploy/kolla/ansible/roles/cloud_ui/tasks/lifecycle.yml" in role_test
    assert '"lifecycle.yml"' in role_test
    forbidden_block = re.search(
        r"for forbidden in \[(?P<body>.*?)\]:",
        role_test,
        flags=re.DOTALL,
    )
    assert forbidden_block is not None
    assert '"rollback"' not in forbidden_block.group("body")
    assert '"reconfigure"' not in forbidden_block.group("body")


def test_e09_reconfigure_rollback_evidence_and_risks_are_recorded() -> None:
    evidence = read_text("docs/generated/e09-reconfigure-rollback.md")
    risk_register = read_text("docs/generated/risk-register.md")
    dkb_traceability = read_text("docs/11_DKB_TRACEABILITY.md")

    for expected in [
        "Stage: E09.7 Reconfigure/upgrade/rollback",
        "repository-side lifecycle contract",
        "not a live Kolla reconfigure",
        "pending_external_evidence",
        "clean deploy/reconfigure",
        "rolling upgrade",
        "failed update rollback",
        "disable/uninstall",
        "contract migration is held",
        "ДКБ-82",
    ]:
        assert expected in evidence

    assert "R-067" in risk_register
    assert "E09.7 Reconfigure/upgrade/rollback" in dkb_traceability
    assert "production approved" not in evidence.lower()
