import configparser
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
        assert (ROOT / relative_path).is_file(), relative_path


def test_kolla_build_config_defines_two_custom_images() -> None:
    config = read_text("deploy/kolla/kolla-build.conf.example")
    parser = configparser.ConfigParser(interpolation=None)
    parser.read_string(config)

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
        "uid = 42580",
        "gid = 42580",
    ]:
        assert expected in config

    assert "profiles" in parser
    profile_mappings = {
        key: value
        for key, value in parser["profiles"].items()
        if key not in parser.defaults()
    }
    assert profile_mappings == {
        "cloud-ui-backend": "cloud-ui-backend",
        "cloud-ui-frontend": "cloud-ui-frontend",
    }

    custom_image_sections = {
        section for section in parser.sections() if section.startswith("cloud-ui-")
    }
    assert custom_image_sections == {
        "cloud-ui-backend",
        "cloud-ui-frontend",
    }

    assert "latest" not in config.lower()
    assert "uid = 42480" not in config
    assert "gid = 42480" not in config


def test_backend_template_keeps_one_backend_image_for_all_commands() -> None:
    template = read_text("deploy/kolla/docker/cloud-ui-backend/Dockerfile.j2")

    for expected in [
        "FROM {{ namespace }}/{{ image_prefix }}openstack-base:{{ tag }}",
        "python3.11",
        "python3.11 -m pip",
        "ADD cloud-ui-backend-archive /cloud-ui-backend-source",
        "/cloud-ui-backend-source/source/backend",
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


def test_backend_runtime_dependencies_follow_kolla_constraints() -> None:
    pyproject = read_text("backend/pyproject.toml")

    for expected in [
        '"alembic==1.14.1"',
        '"python-json-logger==3.2.1"',
        '"sqlalchemy==2.0.38"',
    ]:
        assert expected in pyproject

    for forbidden in [
        '"alembic==1.16.2"',
        '"python-json-logger==3.3.0"',
        '"sqlalchemy==2.0.41"',
    ]:
        assert forbidden not in pyproject


def test_backend_migration_resources_are_packaged_for_kolla_image() -> None:
    pyproject = read_text("backend/pyproject.toml")

    for relative_path in [
        "backend/src/cloud_ui/migrations/__init__.py",
        "backend/src/cloud_ui/migrations/versions/__init__.py",
    ]:
        assert (ROOT / relative_path).is_file(), relative_path

    assert "[tool.setuptools.package-data]" in pyproject
    assert '"cloud_ui.migrations" = ["script.py.mako"]' in pyproject


def test_frontend_template_uses_prebuilt_dist_without_node_runtime() -> None:
    template = read_text("deploy/kolla/docker/cloud-ui-frontend/Dockerfile.j2")

    for expected in [
        "FROM {{ namespace }}/{{ image_prefix }}base:{{ tag }}",
        "ADD cloud-ui-frontend-archive /cloud-ui-frontend-source",
        "/cloud-ui-frontend-source/source/frontend/dist",
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
        assert (ROOT / relative_path).is_file(), relative_path

    lab_file_contents = {
        relative_path: read_text(relative_path) for relative_path in expected_paths
    }
    deploy = lab_file_contents["deploy/kolla/lab/playbooks/deploy.yml"]
    rollback = lab_file_contents["deploy/kolla/lab/playbooks/rollback.yml"]
    group_vars = lab_file_contents["deploy/kolla/lab/group_vars/all.yml.example"]

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
    assert "cloud_ui_api_port: 18081" in group_vars
    assert "cloud_ui_api_port: 18080" not in group_vars

    forbidden_values = ["cloud_ui_dev", "admin" + "123"]
    for relative_path, content in lab_file_contents.items():
        for forbidden_value in forbidden_values:
            assert forbidden_value not in content, relative_path


def test_build_script_prepares_kolla_work_directories() -> None:
    script = read_text("deploy/kolla/scripts/build-images.sh")

    assert 'KOLLA_LOGS_DIR="${KOLLA_LOGS_DIR:-/tmp/dawn-kolla-build/logs}"' in script
    assert 'KOLLA_WORK_DIR="${KOLLA_WORK_DIR:-/tmp/dawn-kolla-build/work}"' in script
    assert 'mkdir -p "${KOLLA_LOGS_DIR}" "${KOLLA_WORK_DIR}"' in script
    assert '--logs-dir "${KOLLA_LOGS_DIR}"' in script
    assert '--work-dir "${KOLLA_WORK_DIR}"' in script
