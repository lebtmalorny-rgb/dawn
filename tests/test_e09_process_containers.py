import re
from collections import Counter
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]

EXPECTED_FILES = [
    "deploy/kolla/ansible/roles/cloud_ui/defaults/main.yml",
    "deploy/kolla/ansible/roles/cloud_ui/tasks/containers.yml",
    "deploy/kolla/ansible/roles/cloud_ui/tasks/validate.yml",
    "docs/generated/e09-process-containers.md",
]

EXPECTED_SERVICES = {
    "cloud_ui_frontend": {
        "process": "frontend",
        "image": "{{ cloud_ui_frontend_image_full }}",
        "command": "nginx -g 'daemon off;'",
        "config_dir": "cloud-ui-frontend",
    },
    "cloud_ui_api": {
        "process": "api",
        "image": "{{ cloud_ui_backend_image_full }}",
        "command": "cloud-ui api",
        "config_dir": "cloud-ui-backend",
    },
    "cloud_ui_worker": {
        "process": "worker",
        "image": "{{ cloud_ui_backend_image_full }}",
        "command": "cloud-ui worker",
        "config_dir": "cloud-ui-backend",
    },
    "cloud_ui_events": {
        "process": "events",
        "image": "{{ cloud_ui_backend_image_full }}",
        "command": "cloud-ui events",
        "config_dir": "cloud-ui-backend",
    },
}


def read_text(relative_path: str) -> str:
    return (ROOT / relative_path).read_text(encoding="utf-8")


def load_yaml(relative_path: str) -> object:
    return yaml.safe_load(read_text(relative_path))


def load_yaml_list(relative_path: str) -> list[dict[str, Any]]:
    loaded = load_yaml(relative_path)
    if not isinstance(loaded, list):
        return []
    return loaded


def test_e09_process_container_files_exist() -> None:
    for relative_path in EXPECTED_FILES:
        assert (ROOT / relative_path).exists(), relative_path


def test_process_topology_declares_three_nodes_and_twelve_permanent_containers() -> None:
    defaults = load_yaml("deploy/kolla/ansible/roles/cloud_ui/defaults/main.yml")
    assert isinstance(defaults, dict)

    nodes = defaults["cloud_ui_control_ui_nodes"]
    topology = defaults["cloud_ui_process_topology"]

    assert nodes == ["control-ui-01", "control-ui-02", "control-ui-03"]
    assert defaults["cloud_ui_expected_control_ui_node_count"] == 3
    assert defaults["cloud_ui_permanent_container_count_per_node"] == 4
    assert defaults["cloud_ui_expected_permanent_containers_total"] == 12
    assert len(topology) == 12

    node_counts = Counter(entry["node"] for entry in topology)
    assert node_counts == Counter(
        {"control-ui-01": 4, "control-ui-02": 4, "control-ui-03": 4}
    )

    service_counts = Counter(entry["service"] for entry in topology)
    assert service_counts == Counter(
        {
            "cloud_ui_frontend": 3,
            "cloud_ui_api": 3,
            "cloud_ui_worker": 3,
            "cloud_ui_events": 3,
        }
    )


def test_process_topology_preserves_two_images_and_distinct_backend_commands() -> None:
    defaults = load_yaml("deploy/kolla/ansible/roles/cloud_ui/defaults/main.yml")
    assert isinstance(defaults, dict)

    services = defaults["cloud_ui_services"]
    topology = defaults["cloud_ui_process_topology"]

    assert defaults["cloud_ui_backend_image"] == "cloud-ui-backend"
    assert defaults["cloud_ui_frontend_image"] == "cloud-ui-frontend"

    for entry in topology:
        service_name = entry["service"]
        expected = EXPECTED_SERVICES[service_name]
        service = services[service_name]
        assert entry["process"] == expected["process"]
        assert entry["image"] == expected["image"]
        assert entry["command"] == expected["command"]
        assert entry["config_dir"] == expected["config_dir"]
        assert entry["container_name"] == f"{service['container_name']}_{entry['node']}"
        assert entry["permanent"] is True

    backend_commands = {
        entry["command"]
        for entry in topology
        if entry["image"] == "{{ cloud_ui_backend_image_full }}"
    }
    assert backend_commands == {"cloud-ui api", "cloud-ui worker", "cloud-ui events"}


def test_process_topology_excludes_migration_and_secret_material() -> None:
    defaults = load_yaml("deploy/kolla/ansible/roles/cloud_ui/defaults/main.yml")
    assert isinstance(defaults, dict)

    serialized = yaml.safe_dump(defaults["cloud_ui_process_topology"]).lower()

    assert "cloud_ui_db_migrate" not in serialized
    assert "cloud-ui db-upgrade" not in serialized
    for forbidden in ["password", "token", "private_key", "secret_key", "clouds.yaml"]:
        assert forbidden not in serialized


def test_container_task_publishes_topology_facts_and_summary() -> None:
    tasks = load_yaml_list("deploy/kolla/ansible/roles/cloud_ui/tasks/containers.yml")

    fact_keys: set[str] = set()
    for task in tasks:
        set_fact = task.get("ansible.builtin.set_fact") or task.get("set_fact")
        if isinstance(set_fact, dict):
            fact_keys.update(set_fact)

    assert {
        "cloud_ui_container_definitions",
        "cloud_ui_process_topology_effective",
        "cloud_ui_process_topology_summary",
    }.issubset(fact_keys)

    text = read_text("deploy/kolla/ansible/roles/cloud_ui/tasks/containers.yml")
    assert "kolla_container:" not in text


def test_validation_enforces_three_by_four_equals_twelve_contract() -> None:
    tasks = load_yaml_list("deploy/kolla/ansible/roles/cloud_ui/tasks/validate.yml")
    validate_thats: list[str] = []
    for task in tasks:
        assert_block = task.get("ansible.builtin.assert") or task.get("assert")
        if isinstance(assert_block, dict):
            that = assert_block.get("that")
            if isinstance(that, list):
                validate_thats.extend([str(item) for item in that])

    for expected in [
        "cloud_ui_control_ui_nodes | length == cloud_ui_expected_control_ui_node_count",
        "cloud_ui_expected_control_ui_node_count == 3",
        "cloud_ui_expected_permanent_containers_total == 12",
        "cloud_ui_process_topology | length == cloud_ui_expected_permanent_containers_total",
    ]:
        assert expected in validate_thats


def test_e09_process_container_evidence_records_synthetic_scope_and_limits() -> None:
    evidence = read_text("docs/generated/e09-process-containers.md")

    for expected in [
        "Stage: E09.5 Process containers",
        "3 control/UI nodes",
        "12 permanent containers",
        "cloud_ui_frontend",
        "cloud_ui_api",
        "cloud_ui_worker",
        "cloud_ui_events",
        "cloud_ui_db_migrate",
        "not part of the permanent topology",
        "synthetic repository evidence",
        "pending_external_evidence",
        "ДКБ-69/70",
        "ДКБ-76/77/80",
        "ДКБ-82",
    ]:
        assert expected in evidence

    assert "12 live containers proven" not in evidence
    assert "production approved" not in evidence.lower()


def test_traceability_and_risk_register_reference_e09_5_without_live_deploy_claim() -> None:
    traceability = read_text("docs/11_DKB_TRACEABILITY.md")
    risk_register = read_text("docs/generated/risk-register.md")

    assert "E09.5" in traceability
    assert "12 permanent containers" in traceability
    assert "synthetic repository topology" in traceability
    assert "live container inspection remains pending" in traceability

    assert "R-065" in risk_register
    assert "process topology contract mistaken for live 12-container proof" in risk_register

    risk_ids = re.findall(r"^\| (R-\d{3}) \|", risk_register, flags=re.MULTILINE)
    duplicate_ids = {risk_id for risk_id in risk_ids if risk_ids.count(risk_id) > 1}
    assert duplicate_ids == set()
