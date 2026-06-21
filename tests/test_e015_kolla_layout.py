from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read_text(relative_path: str) -> str:
    return (ROOT / relative_path).read_text(encoding="utf-8")


def test_kolla_build_files_exist() -> None:
    expected_paths = [
        "deploy/kolla/README.md",
        "deploy/kolla/kolla-build.conf.example",
        "deploy/kolla/docker/cloud-ui-backend/Dockerfile.j2",
        "deploy/kolla/docker/cloud-ui-frontend/Dockerfile.j2",
        "deploy/kolla/scripts/build-images.sh",
    ]

    for relative_path in expected_paths:
        assert (ROOT / relative_path).exists(), relative_path


def test_kolla_build_config_defines_two_custom_images() -> None:
    config = read_text("deploy/kolla/kolla-build.conf.example")

    for expected in [
        "engine = podman",
        "base = rocky",
        "base_tag = 9",
        "openstack_release = 2025.1",
        "tag = 2025.1-rocky-9",
        "cloud-ui-backend = cloud-ui-backend",
        "cloud-ui-frontend = cloud-ui-frontend",
        "[cloud-ui-backend]",
        "[cloud-ui-frontend]",
        "[cloudui-user]",
    ]:
        assert expected in config

    assert "latest" not in config.lower()


def test_backend_template_keeps_one_backend_image_for_all_commands() -> None:
    template = read_text("deploy/kolla/docker/cloud-ui-backend/Dockerfile.j2")

    for expected in [
        "FROM {{ namespace }}/{{ image_prefix }}openstack-base:{{ tag }}",
        "cloud-ui-backend-source",
        "cloud-ui api",
        "cloud-ui worker",
        "cloud-ui events",
        "cloud-ui db-upgrade",
        "cloud-ui smoke",
    ]:
        assert expected in template

    for forbidden in [
        "cloud-ui-api",
        "cloud-ui-worker",
        "cloud-ui-events",
    ]:
        assert forbidden not in template


def test_frontend_template_uses_prebuilt_dist_without_node_runtime() -> None:
    template = read_text("deploy/kolla/docker/cloud-ui-frontend/Dockerfile.j2")

    for expected in [
        "FROM {{ namespace }}/{{ image_prefix }}base:{{ tag }}",
        "cloud-ui-frontend-source/frontend/dist",
        "nginx",
    ]:
        assert expected in template

    normalized_template = template.lower()
    assert "node" not in normalized_template
    assert "npm" not in normalized_template


def test_lab_playbooks_are_reversible_and_use_no_committed_secrets() -> None:
    expected_paths = [
        "deploy/kolla/lab/inventory.ini.example",
        "deploy/kolla/lab/group_vars/all.yml.example",
        "deploy/kolla/lab/playbooks/bootstrap-registry.yml",
        "deploy/kolla/lab/playbooks/deploy.yml",
        "deploy/kolla/lab/playbooks/smoke.yml",
        "deploy/kolla/lab/playbooks/rollback.yml",
    ]

    for relative_path in expected_paths:
        assert (ROOT / relative_path).exists(), relative_path

    deploy = read_text("deploy/kolla/lab/playbooks/deploy.yml")
    rollback = read_text("deploy/kolla/lab/playbooks/rollback.yml")
    group_vars = read_text("deploy/kolla/lab/group_vars/all.yml.example")

    for service_name in [
        "cloud_ui_api",
        "cloud_ui_worker",
        "cloud_ui_events",
        "cloud_ui_frontend",
    ]:
        assert service_name in deploy
        assert service_name in rollback

    for image_name in [
        "cloud-ui",
        "cloud-ui-backend",
        "cloud-ui-frontend",
    ]:
        assert image_name in deploy

    assert "cloud_ui_database_url" in group_vars
    assert "cloud_ui_rabbitmq_url" in group_vars
    assert "cloud_ui_dev" not in group_vars
    assert "admin" + "123" not in group_vars
