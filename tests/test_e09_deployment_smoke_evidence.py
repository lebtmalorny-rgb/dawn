import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "deploy/kolla/scripts/collect-e09-evidence.py"


def load_module():
    spec = importlib.util.spec_from_file_location("collect_e09_evidence", SCRIPT)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_e09_evidence_runner_file_exists() -> None:
    assert SCRIPT.exists()


def test_digest_validation_accepts_sha256_and_rejects_tags() -> None:
    module = load_module()

    assert module.is_digest_ref("registry.test/cloud-ui-backend@sha256:" + "a" * 64)
    assert not module.is_digest_ref("registry.test/cloud-ui-backend:2026.06.25")
    assert not module.is_digest_ref("registry.test/cloud-ui-backend:latest")


def test_preflight_requires_test_marker_and_rejects_production_inventory(tmp_path: Path) -> None:
    module = load_module()
    inventory = tmp_path / "production-inventory.ini"
    inventory.write_text("cloud_ui_test_stand=true\n", encoding="utf-8")

    result = module.validate_inputs(
        inventory_path=inventory,
        output_path=ROOT / "docs/generated/e09-deployment-smoke-evidence.md",
        backend_image="registry.test/cloud-ui-backend@sha256:" + "a" * 64,
        frontend_image="registry.test/cloud-ui-frontend@sha256:" + "b" * 64,
        rollback_window_open=True,
    )

    assert result.ok is False
    assert "production" in " ".join(result.errors)


def test_preflight_rejects_missing_marker_and_non_digest_images(tmp_path: Path) -> None:
    module = load_module()
    inventory = tmp_path / "test-inventory.ini"
    inventory.write_text("[cloud-ui]\ncontrol-ui-01\n", encoding="utf-8")

    result = module.validate_inputs(
        inventory_path=inventory,
        output_path=ROOT / "docs/generated/e09-deployment-smoke-evidence.md",
        backend_image="registry.test/cloud-ui-backend:tag",
        frontend_image="registry.test/cloud-ui-frontend:tag",
        rollback_window_open=False,
    )

    assert result.ok is False
    assert "test marker" in " ".join(result.errors)
    assert "backend image" in " ".join(result.errors)
    assert "frontend image" in " ".join(result.errors)
    assert "rollback window" in " ".join(result.errors)


def test_preflight_rejects_output_path_outside_generated_docs(tmp_path: Path) -> None:
    module = load_module()
    inventory = tmp_path / "test-inventory.ini"
    inventory.write_text("cloud_ui_test_stand=true\n", encoding="utf-8")

    result = module.validate_inputs(
        inventory_path=inventory,
        output_path=tmp_path / "evidence.md",
        backend_image="registry.test/cloud-ui-backend@sha256:" + "a" * 64,
        frontend_image="registry.test/cloud-ui-frontend@sha256:" + "b" * 64,
        rollback_window_open=True,
    )

    assert result.ok is False
    assert "output path" in " ".join(result.errors)


def test_rendered_evidence_contains_required_rows_and_no_secret_values() -> None:
    module = load_module()
    evidence = module.render_evidence(
        inventory_name="test-inventory.ini",
        backend_image="registry.test/cloud-ui-backend@sha256:" + "a" * 64,
        frontend_image="registry.test/cloud-ui-frontend@sha256:" + "b" * 64,
        live_status="pending_external_evidence",
        command_summaries=[
            module.CommandSummary("preflight", "passed", "token=abc123"),
            module.CommandSummary("container_count", "pending", "12 expected"),
        ],
    )

    assert "Stage: E09.8 Deployment smoke/evidence" in evidence
    assert "cloud-ui-backend@sha256:" in evidence
    assert "cloud-ui-frontend@sha256:" in evidence
    assert "12 expected" in evidence
    assert "pending_external_evidence" in evidence
    assert "abc123" not in evidence
    assert "[REDACTED]" in evidence
    assert "ДКБ-69/70" in evidence


def test_rendered_evidence_states_acceptance_rows_and_partial_scope() -> None:
    module = load_module()
    evidence = module.render_evidence(
        inventory_name="test-inventory.ini",
        backend_image="registry.test/cloud-ui-backend@sha256:" + "a" * 64,
        frontend_image="registry.test/cloud-ui-frontend@sha256:" + "b" * 64,
        live_status="pending_external_evidence",
        command_summaries=[
            module.CommandSummary("migration", "pending", "one-shot migration pending"),
            module.CommandSummary("db_rabbitmq", "pending", "DB/RabbitMQ access pending"),
            module.CommandSummary("haproxy_tls", "pending", "HAProxy/TLS smoke pending"),
            module.CommandSummary(
                "container_hardening",
                "pending",
                "user/caps/mounts/SELinux inspection pending",
            ),
            module.CommandSummary("api_ui_smoke", "pending", "API/UI smoke pending"),
            module.CommandSummary("rollback", "pending", "rollback pending"),
        ],
    )
    normalized = evidence.lower()

    assert "one-shot migration" in normalized or "migration" in normalized
    assert "db/rabbitmq" in normalized
    assert "haproxy/tls" in normalized
    assert (
        "container hardening" in normalized
        or "user/caps/mounts/selinux" in normalized
    )
    assert "api/ui smoke" in normalized
    assert "rollback" in normalized
    assert "partial" in normalized or "pending_external_evidence" in evidence
    assert "not production approval" in normalized or "test-stand" in normalized


def test_generated_evidence_traceability_and_risk_register_are_updated() -> None:
    evidence = (ROOT / "docs/generated/e09-deployment-smoke-evidence.md").read_text(encoding="utf-8")
    traceability = (ROOT / "docs/11_DKB_TRACEABILITY.md").read_text(encoding="utf-8")
    risk_register = (ROOT / "docs/generated/risk-register.md").read_text(encoding="utf-8")

    assert "Stage: E09.8 Deployment smoke/evidence" in evidence
    assert "R-068" in risk_register
    assert "E09.8 Deployment smoke/evidence" in traceability
    assert "production approved" not in evidence.lower()
