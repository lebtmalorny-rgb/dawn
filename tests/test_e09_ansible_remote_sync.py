import hashlib
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "deploy/kolla/scripts/sync-ansible-remote-bundle.py"
EXPORTER = ROOT / "deploy/kolla/scripts/export-ansible-bundle.py"
EVIDENCE = ROOT / "docs/generated/e09-ansible-remote-sync.md"
TRACEABILITY = ROOT / "docs/11_DKB_TRACEABILITY.md"
RISK_REGISTER = ROOT / "docs/generated/risk-register.md"

EXPECTED_REQUIRED_PATHS = {
    "manifest.json",
    "roles/cloud_ui/defaults/main.yml",
    "roles/cloud_ui/tasks/main.yml",
    "roles/cloud_ui/templates/cloud-ui-backend.env.j2",
    "playbooks/cloud-ui-preflight.yml",
    "examples/cloud-ui-vars.yml.example",
}


def load_module(path: Path, module_name: str) -> Any:
    spec = importlib.util.spec_from_file_location(module_name, path)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def make_bundle(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    exporter = load_module(EXPORTER, "export_ansible_bundle_for_remote_sync_test")
    generated_docs = tmp_path / "generated"
    generated_docs.mkdir()
    monkeypatch.setattr(exporter, "GENERATED_DOCS", generated_docs.resolve())
    bundle_dir = tmp_path / "bundle"
    evidence_path = generated_docs / "local-evidence.md"
    result = exporter.export_bundle(
        output_dir=bundle_dir,
        evidence_path=evidence_path,
        source_commit="remote-sync-test",
    )
    assert result.ok, result.errors
    return bundle_dir


def extract_markdown_section(path: Path, heading_text: str) -> str:
    lines = path.read_text(encoding="utf-8").splitlines()
    for start, line in enumerate(lines):
        if not line.startswith("#"):
            continue
        marker, _, title = line.partition(" ")
        if title.strip().lower() != heading_text.lower():
            continue
        heading_level = len(marker)
        end = len(lines)
        for next_index in range(start + 1, len(lines)):
            next_line = lines[next_index]
            if not next_line.startswith("#"):
                continue
            next_marker, _, _ = next_line.partition(" ")
            if len(next_marker) <= heading_level:
                end = next_index
                break
        return "\n".join(lines[start:end])
    raise AssertionError(f"{path} missing section {heading_text}")


def risk_row(risk_id: str) -> str:
    for line in RISK_REGISTER.read_text(encoding="utf-8").splitlines():
        if line.startswith(f"| {risk_id} |"):
            return line
    raise AssertionError(f"missing {risk_id}")


def assert_error_mentions(result: Any, *needles: str) -> None:
    error_text = " ".join(result.errors).lower()
    assert any(needle.lower() in error_text for needle in needles), error_text


def assert_same_line_contains(text: str, *needles: str) -> None:
    normalized_needles = [needle.lower() for needle in needles]
    for line in text.splitlines():
        normalized_line = line.replace("`", "").lower()
        if all(needle in normalized_line for needle in normalized_needles):
            return
    raise AssertionError(f"missing same-line markers: {needles}")


def test_sync_script_exists() -> None:
    assert SCRIPT.exists()


def test_validates_local_bundle_manifest(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    module = load_module(SCRIPT, "sync_ansible_remote_bundle")
    bundle_dir = make_bundle(monkeypatch, tmp_path)

    result = module.validate_local_bundle(bundle_dir)

    assert result.ok, result.errors
    summary = result.summary
    assert summary is not None
    assert summary["file_count"] == 13
    assert EXPECTED_REQUIRED_PATHS.issubset(set(summary["paths"]))
    for item in summary["files"]:
        path = bundle_dir / item["path"]
        assert item["sha256"] == hashlib.sha256(path.read_bytes()).hexdigest()
        assert item["bytes"] == path.stat().st_size


def test_rejects_tampered_bundle_file(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    module = load_module(SCRIPT, "sync_ansible_remote_bundle")
    bundle_dir = make_bundle(monkeypatch, tmp_path)
    target = bundle_dir / "roles/cloud_ui/tasks/main.yml"
    target.write_text(target.read_text(encoding="utf-8") + "\n# tamper\n", encoding="utf-8")

    result = module.validate_local_bundle(bundle_dir)

    assert result.ok is False
    assert "sha256 mismatch" in " ".join(result.errors)


def test_rejects_unmanifested_extra_bundle_file(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    module = load_module(SCRIPT, "sync_ansible_remote_bundle")
    bundle_dir = make_bundle(monkeypatch, tmp_path)
    (bundle_dir / "notes.txt").write_text("operator scratch note\n", encoding="utf-8")

    result = module.validate_local_bundle(bundle_dir)

    assert result.ok is False
    assert_error_mentions(result, "unmanifested", "extra bundle file")


def test_rejects_forbidden_credential_bundle_filename(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    module = load_module(SCRIPT, "sync_ansible_remote_bundle")
    bundle_dir = make_bundle(monkeypatch, tmp_path)
    (bundle_dir / "clouds.yaml").write_text("clouds: {}\n", encoding="utf-8")

    result = module.validate_local_bundle(bundle_dir)

    assert result.ok is False
    assert_error_mentions(result, "forbidden", "credential")


def test_rejects_manifest_byte_count_mismatch(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    module = load_module(SCRIPT, "sync_ansible_remote_bundle")
    bundle_dir = make_bundle(monkeypatch, tmp_path)
    manifest_path = bundle_dir / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["files"][0]["bytes"] = int(manifest["files"][0]["bytes"]) + 1
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    result = module.validate_local_bundle(bundle_dir)

    assert result.ok is False
    assert_error_mentions(result, "byte", "size")


def test_rejects_manifest_path_traversal(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    module = load_module(SCRIPT, "sync_ansible_remote_bundle")
    bundle_dir = make_bundle(monkeypatch, tmp_path)
    manifest_path = bundle_dir / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["files"][0]["path"] = "../clouds.yaml"
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    result = module.validate_local_bundle(bundle_dir)

    assert result.ok is False
    assert_error_mentions(result, "traversal", "escape", "unsafe", "forbidden")


def test_rejects_unapproved_remote_host_and_path(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    module = load_module(SCRIPT, "sync_ansible_remote_bundle")
    bundle_dir = make_bundle(monkeypatch, tmp_path)

    bad_host = module.validate_sync_request(
        bundle_dir=bundle_dir,
        remote_host="192.168.10.14",
        remote_path=Path("/etc/kolla/cloud-ui-sync-bundle"),
    )
    bad_path = module.validate_sync_request(
        bundle_dir=bundle_dir,
        remote_host="192.168.10.15",
        remote_path=Path("/usr/share/kolla-ansible/roles/cloud_ui"),
    )

    assert bad_host.ok is False
    assert "approved host" in " ".join(bad_host.errors)
    assert bad_path.ok is False
    assert "approved remote path" in " ".join(bad_path.errors)


def test_builds_safe_remote_commands(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    module = load_module(SCRIPT, "sync_ansible_remote_bundle")
    bundle_dir = make_bundle(monkeypatch, tmp_path)

    request = module.build_sync_request(
        bundle_dir=bundle_dir,
        remote_host="192.168.10.15",
        remote_user="root",
        remote_path=Path("/etc/kolla/cloud-ui-sync-bundle"),
        timestamp="20260626T101112Z",
    )

    assert request.target == "root@192.168.10.15"
    assert request.remote_path == "/etc/kolla/cloud-ui-sync-bundle"
    assert request.staging_path == "/etc/kolla/.cloud-ui-sync-bundle.20260626T101112Z.staging"
    assert request.backup_path == "/etc/kolla/cloud-ui-sync-bundle.backup-20260626T101112Z"
    assert request.rsync_args == (
        "rsync",
        "-a",
        "--delete",
        str(bundle_dir.resolve()) + "/",
        "root@192.168.10.15:/etc/kolla/.cloud-ui-sync-bundle.20260626T101112Z.staging/",
    )
    assert request.remote_commands == (
        "mkdir -p '/etc/kolla'",
        "rm -rf '/etc/kolla/.cloud-ui-sync-bundle.20260626T101112Z.staging'",
        "mkdir -p '/etc/kolla/.cloud-ui-sync-bundle.20260626T101112Z.staging'",
        "if [ -e '/etc/kolla/cloud-ui-sync-bundle' ]; then mv "
        "'/etc/kolla/cloud-ui-sync-bundle' "
        "'/etc/kolla/cloud-ui-sync-bundle.backup-20260626T101112Z'; fi",
        "mv '/etc/kolla/.cloud-ui-sync-bundle.20260626T101112Z.staging' "
        "'/etc/kolla/cloud-ui-sync-bundle'",
    )
    assert all("/usr/share/kolla-ansible" not in command for command in request.remote_commands)
    assert all("kolla-ansible" not in command for command in request.remote_commands)
    assert all("reconfigure" not in command for command in request.remote_commands)


def test_renders_sanitized_evidence(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    module = load_module(SCRIPT, "sync_ansible_remote_bundle")
    bundle_dir = make_bundle(monkeypatch, tmp_path)
    local_result = module.validate_local_bundle(bundle_dir)
    assert local_result.ok, local_result.errors

    evidence = module.render_evidence(
        local_summary=local_result.summary,
        remote_host="192.168.10.15",
        remote_path="/etc/kolla/cloud-ui-sync-bundle",
        backup_path="/etc/kolla/cloud-ui-sync-bundle.backup-20260626T101112Z",
        remote_verified=True,
        remote_file_count=14,
        source_commit="remote-sync-test",
    )

    assert "# E09 Ansible remote sync" in evidence
    assert "remote-sync-only" in evidence
    assert "192.168.10.15" in evidence
    assert "/etc/kolla/cloud-ui-sync-bundle" in evidence
    assert "ANSIBLE_ROLES_PATH=/etc/kolla/cloud-ui-sync-bundle/roles" in evidence
    assert "pending_external_evidence" in evidence
    assert "runtime secret value" in evidence
    assert "kolla-ansible reconfigure" not in evidence
    assert "password" not in evidence.lower()
    assert all(line == line.rstrip() for line in evidence.splitlines())


def test_compares_remote_summary_to_local_bundle(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    module = load_module(SCRIPT, "sync_ansible_remote_bundle")
    bundle_dir = make_bundle(monkeypatch, tmp_path)
    local_result = module.validate_local_bundle(bundle_dir)
    assert local_result.ok, local_result.errors

    remote_summary = json.loads(json.dumps(local_result.summary))
    ok_result = module.compare_remote_summary(local_result.summary, remote_summary)
    assert ok_result.ok, ok_result.errors

    remote_summary["files"][0]["sha256"] = "0" * 64
    bad_result = module.compare_remote_summary(local_result.summary, remote_summary)

    assert bad_result.ok is False
    assert "remote sha256 mismatch" in " ".join(bad_result.errors)


def test_committed_docs_record_remote_sync_scope_and_risk() -> None:
    assert EVIDENCE.exists()
    evidence = EVIDENCE.read_text(encoding="utf-8")
    traceability_section = extract_markdown_section(TRACEABILITY, "E09 Ansible remote sync")
    row = risk_row("R-071")

    for text in (evidence, traceability_section, row):
        assert "E09 Ansible remote sync" in text
        assert "remote-sync-only" in text
        assert "192.168.10.15" in text
        assert "/etc/kolla/cloud-ui-sync-bundle" in text
        assert "pending_external_evidence" in text

    assert "DB/MQ auth remediation" in evidence
    assert "live reconfigure" in evidence
    assert "mistaken for live deployment" in row
    for overclaim in (
        "live reconfigure completed",
        "DB/MQ auth remediation completed",
        "migration completed",
        "12 containers running",
        "HAProxy/TLS completed",
        "SELinux hardening completed",
        "rollback completed",
        "production approved",
    ):
        assert overclaim not in evidence
    assert_same_line_contains(evidence, "live reconfigure", "remains", "pending_external_evidence")
    assert_same_line_contains(
        evidence,
        "DB/MQ auth remediation",
        "remains",
        "pending_external_evidence",
    )
    assert_same_line_contains(evidence, "migration", "remains", "pending_external_evidence")
    assert_same_line_contains(
        evidence,
        "12-container inspection",
        "remains",
        "pending_external_evidence",
    )
    assert_same_line_contains(evidence, "HAProxy/TLS", "remains", "pending_external_evidence")
    assert_same_line_contains(
        evidence,
        "SELinux hardening",
        "remains",
        "pending_external_evidence",
    )
    assert_same_line_contains(evidence, "rollback", "remains", "pending_external_evidence")
    assert_same_line_contains(evidence, "production deployment", "out of scope")

    risk_ids = [
        line.split("|")[1].strip()
        for line in RISK_REGISTER.read_text(encoding="utf-8").splitlines()
        if line.startswith("| R-")
    ]
    assert len(risk_ids) == len(set(risk_ids))
