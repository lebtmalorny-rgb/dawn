import importlib.util
import sys
from pathlib import Path
from typing import Any

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "deploy/kolla/scripts/run-cloud-ui-aio-kolla.py"
PLAYBOOK = ROOT / "deploy/kolla/ansible/playbooks/cloud-ui-aio-reconfigure.yml"
PREFLIGHT = ROOT / "deploy/kolla/ansible/playbooks/cloud-ui-preflight.yml"
LIVE_TASKS = ROOT / "deploy/kolla/ansible/roles/cloud_ui/tasks/live-aio.yml"
EXAMPLE_VARS = ROOT / "deploy/kolla/ansible/examples/cloud-ui-aio-kolla-vars.yml.example"


def load_module():
    spec = importlib.util.spec_from_file_location("run_cloud_ui_aio_kolla", SCRIPT)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def load_yaml(path: Path) -> Any:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def create_inventory(tmp_path: Path, name: str = "all-in-one") -> Path:
    inventory = tmp_path / name
    inventory.write_text(
        "cloud_ui_test_stand=true\n[openstack-aio]\nopenstack-aio\n",
        encoding="utf-8",
    )
    return inventory


def create_bundle(tmp_path: Path) -> Path:
    bundle = tmp_path / "cloud-ui-sync-bundle"
    (bundle / "playbooks").mkdir(parents=True)
    (bundle / "roles").mkdir()
    (bundle / "playbooks/cloud-ui-aio-reconfigure.yml").write_text("---\n", encoding="utf-8")
    (bundle / "playbooks/cloud-ui-preflight.yml").write_text("---\n", encoding="utf-8")
    return bundle


def test_wrapper_script_and_non_secret_example_exist() -> None:
    assert SCRIPT.exists()
    assert EXAMPLE_VARS.exists()

    example = EXAMPLE_VARS.read_text(encoding="utf-8")
    assert "cloud_ui_test_stand: true" in example
    assert "cloud_ui_rollback_window_open: true" in example
    assert "cloud_ui_registry:" in example
    assert "cloud_ui_backend_image_digest:" in example
    assert "cloud_ui_frontend_image_digest:" in example
    assert "cloud_ui_database_url:" not in example
    assert "cloud_ui_rabbitmq_url:" not in example
    assert "mysql+pymysql://" not in example
    assert "amqp://" not in example
    assert "admin" + "123" not in example


def test_reconfigure_command_uses_kolla_cli_custom_playbook(tmp_path: Path) -> None:
    module = load_module()
    inventory = create_inventory(tmp_path)
    bundle = create_bundle(tmp_path)
    runtime_vars = tmp_path / "runtime-vars.yml"
    runtime_vars.write_text("---\n", encoding="utf-8")

    config = module.InvocationConfig(
        mode="reconfigure-no-migration",
        inventory=inventory,
        bundle_dir=bundle,
        runtime_vars=runtime_vars,
        registry="192.168.10.15:5000/kolla/cloud-ui-test",
        backend_digest="sha256:" + "a" * 64,
        frontend_digest="sha256:" + "b" * 64,
        kolla_ansible=Path("/root/venvs/kolla-epoxy/bin/kolla-ansible"),
        rollback_window_open=True,
    )

    plan = module.build_invocation(config)

    assert plan.argv[:2] == ["/root/venvs/kolla-epoxy/bin/kolla-ansible", "reconfigure"]
    assert ["-i", str(inventory)] == [plan.argv[2], plan.argv[3]]
    assert "-p" in plan.argv
    assert str(bundle / "playbooks/cloud-ui-aio-reconfigure.yml") in plan.argv
    assert ["-t", "cloud-ui"] == [plan.argv[plan.argv.index("-t")], plan.argv[plan.argv.index("-t") + 1]]
    assert f"@{runtime_vars}" in plan.argv
    assert "cloud_ui_aio_run_migration=false" in plan.argv
    assert plan.env["ANSIBLE_ROLES_PATH"] == str(bundle / "roles")
    assert "mysql+pymysql://" not in plan.redacted_command
    assert "amqp://" not in plan.redacted_command


def test_preflight_uses_kolla_cli_custom_preflight_playbook(tmp_path: Path) -> None:
    module = load_module()
    inventory = create_inventory(tmp_path)
    bundle = create_bundle(tmp_path)
    runtime_vars = tmp_path / "runtime-vars.yml"
    runtime_vars.write_text("---\n", encoding="utf-8")

    config = module.InvocationConfig(
        mode="preflight",
        inventory=inventory,
        bundle_dir=bundle,
        runtime_vars=runtime_vars,
        registry="192.168.10.15:5000/kolla/cloud-ui-test",
        backend_digest="sha256:" + "a" * 64,
        frontend_digest="sha256:" + "b" * 64,
        kolla_ansible=Path("kolla-ansible"),
        rollback_window_open=True,
    )

    plan = module.build_invocation(config)

    assert plan.argv[:2] == ["kolla-ansible", "reconfigure"]
    assert str(bundle / "playbooks/cloud-ui-preflight.yml") in plan.argv
    assert ["-t", "cloud-ui"] == [plan.argv[plan.argv.index("-t")], plan.argv[plan.argv.index("-t") + 1]]


def test_wrapper_adds_kolla_venv_to_path_for_ansible_playbook_lookup(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = load_module()
    inventory = create_inventory(tmp_path)
    bundle = create_bundle(tmp_path)
    runtime_vars = tmp_path / "runtime-vars.yml"
    runtime_vars.write_text("---\n", encoding="utf-8")
    monkeypatch.setenv("PATH", "/usr/bin")

    config = module.InvocationConfig(
        mode="preflight",
        inventory=inventory,
        bundle_dir=bundle,
        runtime_vars=runtime_vars,
        registry="192.168.10.15:5000/kolla/cloud-ui-test",
        backend_digest="sha256:" + "a" * 64,
        frontend_digest="sha256:" + "b" * 64,
        kolla_ansible=Path("/root/venvs/kolla-epoxy/bin/kolla-ansible"),
        rollback_window_open=True,
    )

    plan = module.build_invocation(config)

    assert plan.env["PATH"].split(":")[:2] == [
        "/root/venvs/kolla-epoxy/bin",
        "/usr/bin",
    ]


@pytest.mark.parametrize("mode", ["deploy", "destroy", "upgrade", "shell"])
def test_wrapper_rejects_unsafe_modes(tmp_path: Path, mode: str) -> None:
    module = load_module()
    inventory = create_inventory(tmp_path)
    bundle = create_bundle(tmp_path)
    runtime_vars = tmp_path / "runtime-vars.yml"
    runtime_vars.write_text("---\n", encoding="utf-8")

    config = module.InvocationConfig(
        mode=mode,
        inventory=inventory,
        bundle_dir=bundle,
        runtime_vars=runtime_vars,
        registry="192.168.10.15:5000/kolla/cloud-ui-test",
        backend_digest="sha256:" + "a" * 64,
        frontend_digest="sha256:" + "b" * 64,
        kolla_ansible=Path("kolla-ansible"),
        rollback_window_open=True,
    )

    result = module.validate_config(config)

    assert result.ok is False
    assert "mode" in " ".join(result.errors)


def test_wrapper_rejects_production_inventory_and_latest_image(tmp_path: Path) -> None:
    module = load_module()
    inventory = create_inventory(tmp_path, name="prod.ini")
    bundle = create_bundle(tmp_path)
    runtime_vars = tmp_path / "runtime-vars.yml"
    runtime_vars.write_text("---\n", encoding="utf-8")

    config = module.InvocationConfig(
        mode="reconfigure",
        inventory=inventory,
        bundle_dir=bundle,
        runtime_vars=runtime_vars,
        registry="registry.example/cloud-ui-test",
        backend_digest="latest",
        frontend_digest="sha256:" + "b" * 64,
        kolla_ansible=Path("kolla-ansible"),
        rollback_window_open=False,
    )

    result = module.validate_config(config)

    assert result.ok is False
    joined = " ".join(result.errors)
    assert "production" in joined
    assert "backend digest" in joined
    assert "rollback window" in joined


def test_cloud_ui_playbooks_and_live_tasks_are_tagged_for_kolla_cli() -> None:
    aio_play = load_yaml(PLAYBOOK)[0]
    preflight_play = load_yaml(PREFLIGHT)[0]
    live_tasks = load_yaml(LIVE_TASKS)

    assert aio_play["tags"] == ["cloud-ui"]
    assert preflight_play["tags"] == ["cloud-ui"]
    assert aio_play["roles"] == [{"role": "cloud_ui", "tags": ["cloud-ui"]}]

    for task in live_tasks:
        assert task.get("tags") == ["cloud-ui"]
