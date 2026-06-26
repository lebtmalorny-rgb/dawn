import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "deploy/kolla/scripts/collect-e09-evidence.py"


def fixture_value(*parts: str) -> str:
    return "".join(parts)


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
    assert module.is_digest_ref("registry.test:5000/cloud-ui-backend@sha256:" + "a" * 64)
    assert not module.is_digest_ref("registry.test/cloud-ui-backend:2026.06.25")
    assert not module.is_digest_ref("registry.test/cloud-ui-backend:latest")
    assert not module.is_digest_ref("registry.test/cloud-ui-backend@sha256:" + "a" * 63)
    assert not module.is_digest_ref("registry.test/cloud-ui-backend@sha256:" + "z" * 64)
    assert not module.is_digest_ref("registry.test/cloud-ui-backend@sha256:")
    assert not module.is_digest_ref(
        "registry.test/cloud-ui-backend:tag@sha256:" + "a" * 64
    )


def test_preflight_rejects_production_inventory_filename(tmp_path: Path) -> None:
    module = load_module()
    inventory = tmp_path / "production-inventory.ini"
    inventory.write_text("cloud_ui_test_stand=true\n", encoding="utf-8")
    prod01_inventory = tmp_path / "cloud-ui-prod01.ini"
    prod01_inventory.write_text("cloud_ui_test_stand=true\n", encoding="utf-8")
    prdcontrol_inventory = tmp_path / "prdcontrol01.ini"
    prdcontrol_inventory.write_text("cloud_ui_test_stand=true\n", encoding="utf-8")
    prodblue_inventory = tmp_path / "prodblue01.ini"
    prodblue_inventory.write_text("cloud_ui_test_stand=true\n", encoding="utf-8")
    product_inventory = tmp_path / "product-lab.ini"
    product_inventory.write_text("cloud_ui_test_stand=true\n", encoding="utf-8")

    result = module.validate_inputs(
        inventory_path=inventory,
        output_path=ROOT / "docs/generated/e09-deployment-smoke-evidence.md",
        backend_image="registry.test/cloud-ui-backend@sha256:" + "a" * 64,
        frontend_image="registry.test/cloud-ui-frontend@sha256:" + "b" * 64,
        rollback_window_open=True,
    )

    assert result.ok is False
    assert "production" in " ".join(result.errors)

    prod01_result = module.validate_inputs(
        inventory_path=prod01_inventory,
        output_path=ROOT / "docs/generated/e09-deployment-smoke-evidence.md",
        backend_image="registry.test/cloud-ui-backend@sha256:" + "a" * 64,
        frontend_image="registry.test/cloud-ui-frontend@sha256:" + "b" * 64,
        rollback_window_open=True,
    )

    assert prod01_result.ok is False
    assert "production" in " ".join(prod01_result.errors)

    for production_inventory in (prdcontrol_inventory, prodblue_inventory):
        production_result = module.validate_inputs(
            inventory_path=production_inventory,
            output_path=ROOT / "docs/generated/e09-deployment-smoke-evidence.md",
            backend_image="registry.test/cloud-ui-backend@sha256:" + "a" * 64,
            frontend_image="registry.test/cloud-ui-frontend@sha256:" + "b" * 64,
            rollback_window_open=True,
        )

        assert production_result.ok is False
        assert "production" in " ".join(production_result.errors)

    product_result = module.validate_inputs(
        inventory_path=product_inventory,
        output_path=ROOT / "docs/generated/e09-deployment-smoke-evidence.md",
        backend_image="registry.test/cloud-ui-backend@sha256:" + "a" * 64,
        frontend_image="registry.test/cloud-ui-frontend@sha256:" + "b" * 64,
        rollback_window_open=True,
    )

    assert product_result.ok is True


def test_preflight_rejects_production_inventory_content(tmp_path: Path) -> None:
    module = load_module()
    inventory = tmp_path / "test-inventory.ini"
    inventory.write_text(
        "cloud_ui_test_stand=true\nenvironment=production\napi_host=cloud-ui.example.prod\n",
        encoding="utf-8",
    )
    prod01_inventory = tmp_path / "test-prod01-content.ini"
    prod01_inventory.write_text(
        "cloud_ui_test_stand=true\nenv=prod01\n",
        encoding="utf-8",
    )
    prefixed_inventory = tmp_path / "test-prefixed-prod-content.ini"
    prefixed_inventory.write_text(
        "cloud_ui_test_stand=true\nhost=prdcontrol01\nblue=prodblue01\nname=product-lab\n",
        encoding="utf-8",
    )

    result = module.validate_inputs(
        inventory_path=inventory,
        output_path=ROOT / "docs/generated/e09-deployment-smoke-evidence.md",
        backend_image="registry.test/cloud-ui-backend@sha256:" + "a" * 64,
        frontend_image="registry.test/cloud-ui-frontend@sha256:" + "b" * 64,
        rollback_window_open=True,
    )

    assert result.ok is False
    assert "production" in " ".join(result.errors)

    prod01_result = module.validate_inputs(
        inventory_path=prod01_inventory,
        output_path=ROOT / "docs/generated/e09-deployment-smoke-evidence.md",
        backend_image="registry.test/cloud-ui-backend@sha256:" + "a" * 64,
        frontend_image="registry.test/cloud-ui-frontend@sha256:" + "b" * 64,
        rollback_window_open=True,
    )

    assert prod01_result.ok is False
    assert "production" in " ".join(prod01_result.errors)

    prefixed_result = module.validate_inputs(
        inventory_path=prefixed_inventory,
        output_path=ROOT / "docs/generated/e09-deployment-smoke-evidence.md",
        backend_image="registry.test/cloud-ui-backend@sha256:" + "a" * 64,
        frontend_image="registry.test/cloud-ui-frontend@sha256:" + "b" * 64,
        rollback_window_open=True,
    )

    assert prefixed_result.ok is False
    assert "production" in " ".join(prefixed_result.errors)


def test_preflight_allows_kolla_producer_group_names(tmp_path: Path) -> None:
    module = load_module()
    inventory = tmp_path / "test-inventory.ini"
    inventory.write_text(
        "cloud_ui_test_stand=true\n[designate-producer:children]\ncontrol\n",
        encoding="utf-8",
    )

    result = module.validate_inputs(
        inventory_path=inventory,
        output_path=ROOT / "docs/generated/e09-deployment-smoke-evidence.md",
        backend_image="registry.test/cloud-ui-backend@sha256:" + "a" * 64,
        frontend_image="registry.test/cloud-ui-frontend@sha256:" + "b" * 64,
        rollback_window_open=True,
    )

    assert result.ok is True


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


def test_preflight_rejects_generated_docs_path_traversal(tmp_path: Path) -> None:
    module = load_module()
    inventory = tmp_path / "test-inventory.ini"
    inventory.write_text("cloud_ui_test_stand=true\n", encoding="utf-8")

    result = module.validate_inputs(
        inventory_path=inventory,
        output_path=ROOT / "docs/generated/../e09-escape.md",
        backend_image="registry.test/cloud-ui-backend@sha256:" + "a" * 64,
        frontend_image="registry.test/cloud-ui-frontend@sha256:" + "b" * 64,
        rollback_window_open=True,
    )

    assert result.ok is False
    assert "output path" in " ".join(result.errors)


def test_preflight_rejects_generated_docs_symlink_escape(tmp_path: Path) -> None:
    module = load_module()
    inventory = tmp_path / "test-inventory.ini"
    inventory.write_text("cloud_ui_test_stand=true\n", encoding="utf-8")
    escaped_output = tmp_path / "escaped.md"
    symlink_path = ROOT / "docs/generated/e09-symlink-escape-test.md"

    try:
        try:
            symlink_path.symlink_to(escaped_output)
        except (NotImplementedError, OSError) as exc:
            pytest.skip(f"symlink creation is unsupported: {exc}")

        result = module.validate_inputs(
            inventory_path=inventory,
            output_path=symlink_path,
            backend_image="registry.test/cloud-ui-backend@sha256:" + "a" * 64,
            frontend_image="registry.test/cloud-ui-frontend@sha256:" + "b" * 64,
            rollback_window_open=True,
        )

        assert result.ok is False
        assert "output path" in " ".join(result.errors)

        calls = []

        def fake_executor(*args, **kwargs):
            calls.append((args, kwargs))
            return "unexpected command output"

        exit_code = module.main(
            [
                "--inventory",
                str(inventory),
                "--output",
                str(symlink_path),
                "--backend-image",
                "registry.test/cloud-ui-backend@sha256:" + "a" * 64,
                "--frontend-image",
                "registry.test/cloud-ui-frontend@sha256:" + "b" * 64,
                "--rollback-window-open",
            ],
            command_executor=fake_executor,
        )

        assert exit_code != 0
        assert calls == []
        assert not escaped_output.exists()
    finally:
        if symlink_path.is_symlink():
            symlink_path.unlink()


def test_preflight_rejects_digest_refs_for_wrong_image_names(tmp_path: Path) -> None:
    module = load_module()
    inventory = tmp_path / "test-inventory.ini"
    inventory.write_text("cloud_ui_test_stand=true\n", encoding="utf-8")

    result = module.validate_inputs(
        inventory_path=inventory,
        output_path=ROOT / "docs/generated/e09-deployment-smoke-evidence.md",
        backend_image="registry.test/not-cloud-ui-backend@sha256:" + "a" * 64,
        frontend_image="registry.test/not-cloud-ui-frontend@sha256:" + "b" * 64,
        rollback_window_open=True,
    )

    assert result.ok is False
    assert "backend image" in " ".join(result.errors)
    assert "frontend image" in " ".join(result.errors)


def test_preflight_rejects_swapped_frontend_and_backend_images(tmp_path: Path) -> None:
    module = load_module()
    inventory = tmp_path / "test-inventory.ini"
    inventory.write_text("cloud_ui_test_stand=true\n", encoding="utf-8")

    result = module.validate_inputs(
        inventory_path=inventory,
        output_path=ROOT / "docs/generated/e09-deployment-smoke-evidence.md",
        backend_image="registry.test/cloud-ui-frontend@sha256:" + "a" * 64,
        frontend_image="registry.test/cloud-ui-backend@sha256:" + "b" * 64,
        rollback_window_open=True,
    )

    assert result.ok is False
    assert "backend image" in " ".join(result.errors)
    assert "frontend image" in " ".join(result.errors)


def test_preflight_rejects_production_image_registry_refs(tmp_path: Path) -> None:
    module = load_module()
    inventory = tmp_path / "test-inventory.ini"
    inventory.write_text("cloud_ui_test_stand=true\n", encoding="utf-8")

    backend_result = module.validate_inputs(
        inventory_path=inventory,
        output_path=ROOT / "docs/generated/e09-deployment-smoke-evidence.md",
        backend_image="registry.prod.example/cloud-ui-backend@sha256:" + "a" * 64,
        frontend_image="registry.test/cloud-ui-frontend@sha256:" + "b" * 64,
        rollback_window_open=True,
    )
    frontend_result = module.validate_inputs(
        inventory_path=inventory,
        output_path=ROOT / "docs/generated/e09-deployment-smoke-evidence.md",
        backend_image="registry.test/cloud-ui-backend@sha256:" + "a" * 64,
        frontend_image="registry.prd01.example/cloud-ui-frontend@sha256:" + "b" * 64,
        rollback_window_open=True,
    )
    test_result = module.validate_inputs(
        inventory_path=inventory,
        output_path=ROOT / "docs/generated/e09-deployment-smoke-evidence.md",
        backend_image="registry.test.example/cloud-ui-backend@sha256:" + "a" * 64,
        frontend_image="registry.test.example/cloud-ui-frontend@sha256:" + "b" * 64,
        rollback_window_open=True,
    )

    assert backend_result.ok is False
    assert "production" in " ".join(backend_result.errors)
    assert frontend_result.ok is False
    assert "production" in " ".join(frontend_result.errors)
    assert test_result.ok is True


def test_cli_preflight_fails_closed_without_running_commands_or_writing_output(
    tmp_path: Path,
) -> None:
    module = load_module()
    inventory = tmp_path / "test-inventory.ini"
    inventory.write_text("environment=production\n", encoding="utf-8")
    output_path = tmp_path / "e09-deployment-smoke-evidence.md"
    calls = []

    def fake_executor(*args, **kwargs):
        calls.append((args, kwargs))
        return "unexpected command output"

    exit_code = module.main(
        [
            "--inventory",
            str(inventory),
            "--output",
            str(output_path),
            "--backend-image",
            "registry.test/cloud-ui-backend@sha256:" + "a" * 64,
            "--frontend-image",
            "registry.test/cloud-ui-frontend@sha256:" + "b" * 64,
            "--rollback-window-open",
        ],
        command_executor=fake_executor,
    )

    assert exit_code != 0
    assert calls == []
    assert not output_path.exists()


def test_rendered_evidence_contains_required_rows_and_no_secret_values() -> None:
    module = load_module()
    evidence = module.render_evidence(
        inventory_name="test-inventory.ini",
        backend_image="registry.test/cloud-ui-backend@sha256:" + "a" * 64,
        frontend_image="registry.test/cloud-ui-frontend@sha256:" + "b" * 64,
        live_status="pending_external_evidence",
        command_summaries=[
            module.CommandSummary(
                "preflight",
                "passed",
                fixture_value(
                    "to",
                    "ken=abc123 OS_",
                    "PASS",
                    "WORD=swordfish OS_",
                    "TO",
                    "KEN=os-token OS_APPLICATION_CREDENTIAL_",
                    "SEC",
                    "RET=app-secret ",
                    '"to',
                    'ken": "json-secret"',
                ),
            ),
            module.CommandSummary(
                "bearer",
                "passed",
                "Authorization: Bearer eyJsecret",
            ),
            module.CommandSummary(
                "authorization_schemes",
                "passed",
                (
                    "Authorization: Basic dXNlcjpwYXNz "
                    "Proxy-Authorization: Basic proxy-secret "
                    "Authorization: Token token-secret "
                    "Authorization: Custom custom-secret"
                ),
            ),
            module.CommandSummary(
                "xauth",
                "passed",
                fixture_value("X-Auth-", "Token: xauth-secret"),
            ),
            module.CommandSummary(
                "spaces",
                "passed",
                "password=very secret value",
            ),
            module.CommandSummary(
                "json",
                "passed",
                '{"token": {"id": "nested-secret"}}',
            ),
            module.CommandSummary(
                "keystone",
                "passed",
                '{"access": {"token": {"id": "keystone-secret"}}}',
            ),
            module.CommandSummary(
                "json_strings",
                "passed",
                (
                    '{"headers": {"Authorization": "Bearer supersecret"}, '
                    '"url": "mysql://user:pass@host/db", '
                    f'"stdout": "{fixture_value("X-Auth-", "Token: xauth-secret")}", '
                    '"set_cookie": "session=abc"}'
                ),
            ),
            module.CommandSummary(
                "urls",
                "passed",
                (
                    "mysql+pymysql://user:pass@host/db "
                    "amqp://user:pass@host/vhost "
                    "https://user:pass@example.invalid/path"
                ),
            ),
            module.CommandSummary(
                "pem",
                "passed",
                fixture_value(
                    "-----BEGIN PRIVATE ",
                    "KEY-----\nPEMSECRET\n-----END PRIVATE ",
                    "KEY-----",
                ),
            ),
            module.CommandSummary(
                "cookies",
                "passed",
                (
                    "Cookie: session=abc; csrf=csrf-secret; auth=auth-secret "
                    "Set-Cookie: session=abc; Path=/; HttpOnly"
                ),
            ),
            module.CommandSummary("container_count", "pending", "12 expected"),
        ],
    )

    assert "Stage: E09.8 Deployment smoke/evidence" in evidence
    assert "cloud-ui-backend@sha256:" in evidence
    assert "cloud-ui-frontend@sha256:" in evidence
    assert "12 expected" in evidence
    assert "pending_external_evidence" in evidence
    assert "abc123" not in evidence
    assert "swordfish" not in evidence
    assert "os-token" not in evidence
    assert "app-secret" not in evidence
    assert "json-secret" not in evidence
    assert "eyJsecret" not in evidence
    assert "dXNlcjpwYXNz" not in evidence
    assert "proxy-secret" not in evidence
    assert "token-secret" not in evidence
    assert "custom-secret" not in evidence
    assert "xauth-secret" not in evidence
    assert "very secret value" not in evidence
    assert "nested-secret" not in evidence
    assert "keystone-secret" not in evidence
    assert "supersecret" not in evidence
    assert "user:pass@" not in evidence
    assert "xauth-secret" not in evidence
    assert "PEMSECRET" not in evidence
    assert "session=abc" not in evidence
    assert "csrf-secret" not in evidence
    assert "auth-secret" not in evidence
    assert "[REDACTED]" in evidence
    assert "ДКБ-69/70" in evidence


def test_rendered_evidence_escapes_inline_code_fields() -> None:
    module = load_module()
    evidence = module.render_evidence(
        inventory_name="test`inventory\nname.ini",
        backend_image="registry.test/cloud-ui-backend@sha256:" + "a" * 64,
        frontend_image="registry.test/cloud-ui-frontend@sha256:" + "b" * 64,
        live_status="pending`status\nnext",
        command_summaries=[],
    )

    assert "test`inventory" not in evidence
    assert "pending`status" not in evidence
    assert "name.ini" in evidence
    assert "pending\\`status next" in evidence


def test_rendered_evidence_escapes_markdown_table_cells() -> None:
    module = load_module()
    evidence = module.render_evidence(
        inventory_name="test-inventory.ini",
        backend_image="registry.test/cloud-ui-backend@sha256:" + "a" * 64,
        frontend_image="registry.test/cloud-ui-frontend@sha256:" + "b" * 64,
        live_status="pending_external_evidence",
        command_summaries=[
            module.CommandSummary("pipe|name", "passed\nlater", "first|second\nthird"),
        ],
    )

    assert "pipe\\|name" in evidence
    assert "first\\|second third" in evidence
    assert "| pipe|name |" not in evidence
    assert "passed\nlater" not in evidence


def test_rendered_evidence_states_acceptance_rows_and_partial_scope() -> None:
    module = load_module()
    evidence = module.render_evidence(
        inventory_name="test-inventory.ini",
        backend_image="registry.test/cloud-ui-backend@sha256:" + "a" * 64,
        frontend_image="registry.test/cloud-ui-frontend@sha256:" + "b" * 64,
        live_status="pending_external_evidence",
        command_summaries=[],
    )
    normalized = evidence.lower()

    assert "one-shot migration" in normalized
    assert "db/rabbitmq" in normalized
    assert "haproxy/tls" in normalized
    assert (
        "container hardening" in normalized
        or "user/caps/mounts/selinux" in normalized
    )
    assert "api/ui smoke" in normalized
    assert "rollback pending" in normalized
    assert "partial" in normalized
    assert "test-stand" in normalized


def test_generated_evidence_traceability_and_risk_register_are_updated() -> None:
    evidence = (ROOT / "docs/generated/e09-deployment-smoke-evidence.md").read_text(
        encoding="utf-8"
    )
    traceability = (ROOT / "docs/11_DKB_TRACEABILITY.md").read_text(encoding="utf-8")
    risk_register = (ROOT / "docs/generated/risk-register.md").read_text(encoding="utf-8")
    normalized = evidence.lower()

    assert "Stage: E09.8 Deployment smoke/evidence" in evidence
    assert "pending_external_evidence" in evidence
    assert "partial" in normalized
    assert "test-stand" in normalized
    assert "rollback pending" in normalized
    assert "one-shot migration" in normalized
    assert "DB/RabbitMQ" in evidence
    assert "HAProxy/TLS" in evidence
    assert (
        "container hardening" in normalized
        or "user/caps/mounts/selinux" in normalized
    )
    assert "API/UI smoke" in evidence
    assert "ДКБ-69/70" in evidence
    assert "R-068" in risk_register
    assert "E09.8 Deployment smoke/evidence" in traceability
    assert "production approved" not in normalized
