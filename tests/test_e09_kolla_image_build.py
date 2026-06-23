import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CUSTOM_IMAGES = {"cloud-ui-backend", "cloud-ui-frontend"}


def read_text(relative_path: str) -> str:
    return (ROOT / relative_path).read_text(encoding="utf-8")


def test_kolla_image_build_files_exist() -> None:
    expected_paths = [
        "deploy/kolla/README.md",
        "deploy/kolla/kolla-build.conf.example",
        "deploy/kolla/docker/cloud-ui-backend/Dockerfile.j2",
        "deploy/kolla/docker/cloud-ui-frontend/Dockerfile.j2",
        "deploy/kolla/scripts/build-images.sh",
        "docs/generated/e09-kolla-image-build.md",
    ]

    for relative_path in expected_paths:
        assert (ROOT / relative_path).exists(), relative_path


def test_kolla_build_config_declares_exactly_two_custom_images() -> None:
    config = read_text("deploy/kolla/kolla-build.conf.example")

    assert "engine = podman" in config
    assert "base = rocky" in config
    assert "base_tag = 9" in config
    assert "openstack_release = 2025.1" in config
    assert "profile = cloud-ui" in config
    assert "cloud-ui = cloud-ui-backend,cloud-ui-frontend" in config
    assert "[cloudui-user]" in config
    assert "uid = 42424" in config
    assert "gid = 42424" in config

    image_sections = set(
        re.findall(r"^\[(cloud-ui-(?:backend|frontend))\]$", config, re.MULTILINE)
    )
    assert image_sections == CUSTOM_IMAGES
    assert "latest" not in config.lower()


def test_backend_template_keeps_one_backend_image_for_all_commands() -> None:
    template = read_text("deploy/kolla/docker/cloud-ui-backend/Dockerfile.j2")

    for expected in [
        "FROM {{ namespace }}/{{ image_prefix }}openstack-base:{{ tag }}",
        "ARG CLOUD_UI_SOURCE_PIN",
        "cloud-ui-backend-source",
        "{{ macros.configure_user(name='cloudui') }}",
        "org.opencontainers.image.title=\"cloud-ui-backend\"",
        "cloud-ui api",
        "cloud-ui worker",
        "cloud-ui events",
        "cloud-ui db-upgrade",
        "cloud-ui smoke",
    ]:
        assert expected in template

    for forbidden in [
        "name=\"cloud-ui-api\"",
        "name=\"cloud-ui-worker\"",
        "name=\"cloud-ui-events\"",
        "cloud-ui-api-source",
        "cloud-ui-worker-source",
        "cloud-ui-events-source",
    ]:
        assert forbidden not in template


def test_frontend_template_uses_prebuilt_dist_without_node_runtime() -> None:
    template = read_text("deploy/kolla/docker/cloud-ui-frontend/Dockerfile.j2")

    for expected in [
        "FROM {{ namespace }}/{{ image_prefix }}base:{{ tag }}",
        "ARG CLOUD_UI_SOURCE_PIN",
        "cloud-ui-frontend-source/frontend/dist",
        "{{ macros.configure_user(name='cloudui') }}",
        "org.opencontainers.image.title=\"cloud-ui-frontend\"",
        "nginx",
    ]:
        assert expected in template

    normalized_template = template.lower()
    assert "node" not in normalized_template
    assert "npm" not in normalized_template


def test_build_script_requires_test_registry_pin_and_rejects_latest() -> None:
    script = read_text("deploy/kolla/scripts/build-images.sh")

    for expected in [
        "require_var CLOUD_UI_TEST_REGISTRY",
        "require_var CLOUD_UI_IMAGE_TAG",
        "require_var CLOUD_UI_SOURCE_PIN",
        "CLOUD_UI_IMAGE_TAG must not be latest",
        "--config-file \"$CONFIG_FILE\"",
        "--docker-dir \"$DOCKER_DIR\"",
        "--profile cloud-ui",
        "--tag \"$CLOUD_UI_IMAGE_TAG\"",
        "--build-args \"CLOUD_UI_SOURCE_PIN=$CLOUD_UI_SOURCE_PIN\"",
        "--registry \"$CLOUD_UI_TEST_REGISTRY\"",
        "--push",
        "cloud-ui-backend",
        "cloud-ui-frontend",
    ]:
        assert expected in script

    assert "example.com" not in script
    assert "password" not in script.lower()
    assert "token" not in script.lower()


def test_e09_evidence_records_scope_and_pending_external_proofs() -> None:
    evidence = read_text("docs/generated/e09-kolla-image-build.md")

    for expected in [
        "Stage: E09.1 Kolla image build",
        "Exactly two custom images",
        "cloud-ui-backend",
        "cloud-ui-frontend",
        "pending_external_evidence",
        "corporate test registry push",
        "vulnerability scan",
        "image signature",
        "ДКБ-69",
        "ДКБ-70",
    ]:
        assert expected in evidence

    assert "12 permanent containers proven" not in evidence
    assert "production approved" not in evidence.lower()
