import errno
import hashlib
import importlib.util
import json
import shutil
import sys
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "deploy/kolla/scripts/export-ansible-bundle.py"
EVIDENCE = ROOT / "docs/generated/e09-ansible-sync-bundle.md"
README = ROOT / "deploy/kolla/ansible/README.md"
TRACEABILITY = ROOT / "docs/11_DKB_TRACEABILITY.md"
RISK_REGISTER = ROOT / "docs/generated/risk-register.md"

EXPECTED_BUNDLE_FILES = {
    "examples/cloud-ui-vars.yml.example",
    "manifest.json",
    "playbooks/cloud-ui-preflight.yml",
    "roles/cloud_ui/defaults/main.yml",
    "roles/cloud_ui/handlers/main.yml",
    "roles/cloud_ui/tasks/config.yml",
    "roles/cloud_ui/tasks/containers.yml",
    "roles/cloud_ui/tasks/lifecycle.yml",
    "roles/cloud_ui/tasks/main.yml",
    "roles/cloud_ui/tasks/migration.yml",
    "roles/cloud_ui/tasks/validate.yml",
    "roles/cloud_ui/templates/cloud-ui-backend.env.j2",
    "roles/cloud_ui/templates/cloud-ui-frontend.conf.j2",
    "roles/cloud_ui/templates/cloud-ui-haproxy.cfg.j2",
}


def fixture_value(*parts: str) -> str:
    return "".join(parts)


def load_module():
    spec = importlib.util.spec_from_file_location("export_ansible_bundle", SCRIPT)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def read(relative_path: str) -> str:
    return (ROOT / relative_path).read_text(encoding="utf-8")


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


def generated_docs_tmp(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, module: Any) -> Path:
    generated_docs = tmp_path / "generated"
    generated_docs.mkdir()
    monkeypatch.setattr(module, "GENERATED_DOCS", generated_docs.resolve())
    return generated_docs


def produced_bundle_files(output_dir: Path) -> set[str]:
    if not output_dir.exists():
        return set()
    return {
        path.relative_to(output_dir).as_posix()
        for path in output_dir.rglob("*")
        if path.is_file()
    }


def assert_no_export_side_effects(
    output_dir: Path,
    evidence_path: Path,
    *,
    allowed_existing_files: set[str] | None = None,
) -> None:
    allowed_existing_files = allowed_existing_files or set()
    produced_files = produced_bundle_files(output_dir)

    assert not evidence_path.exists()
    assert "manifest.json" not in produced_files
    assert produced_files == allowed_existing_files


def assert_path_available(path: Path) -> None:
    assert not path.exists()
    assert not path.is_symlink()


def remove_created_path(path: Path) -> None:
    if path.is_symlink() or path.is_file():
        path.unlink()
    elif path.exists():
        shutil.rmtree(path)


def run_export(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    module = load_module()
    generated_docs = generated_docs_tmp(monkeypatch, tmp_path, module)
    output_dir = tmp_path / "bundle"
    evidence_path = generated_docs / "e09-ansible-sync-bundle.md"

    result = module.export_bundle(
        output_dir=output_dir,
        evidence_path=evidence_path,
        source_commit="test-commit",
    )

    assert result.ok, result.errors
    return module, output_dir, evidence_path


def test_exporter_file_exists() -> None:
    assert SCRIPT.exists()


def test_exporter_creates_allowlisted_bundle_and_manifest(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _, output_dir, evidence_path = run_export(monkeypatch, tmp_path)

    produced_files = {
        path.relative_to(output_dir).as_posix()
        for path in output_dir.rglob("*")
        if path.is_file()
    }

    assert produced_files == EXPECTED_BUNDLE_FILES
    assert evidence_path.exists()
    generated_evidence = evidence_path.read_text(encoding="utf-8")
    assert "runtime secret value" in generated_evidence
    assert "Runtime secret value" not in generated_evidence
    assert all(line == line.rstrip() for line in generated_evidence.splitlines())

    manifest = json.loads((output_dir / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["schema_version"] == "e09-ansible-sync-bundle/v1"
    assert manifest["source_commit"] == "test-commit"
    assert manifest["role_path_note"] == "Set ANSIBLE_ROLES_PATH=roles or configure an equivalent Ansible roles path."
    assert {item["path"] for item in manifest["files"]} == EXPECTED_BUNDLE_FILES - {"manifest.json"}

    for item in manifest["files"]:
        bundle_file = output_dir / item["path"]
        digest = hashlib.sha256(bundle_file.read_bytes()).hexdigest()
        assert item["sha256"] == digest
        assert item["bytes"] == bundle_file.stat().st_size


def test_exporter_rejects_output_inside_repository(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    module = load_module()
    generated_docs = generated_docs_tmp(monkeypatch, tmp_path, module)
    output_dir = ROOT / "docs/generated/e09-unsafe-bundle-test-ansible-sync"
    evidence_path = generated_docs / "e09-ansible-sync-bundle.md"
    assert_path_available(output_dir)

    try:
        result = module.export_bundle(
            output_dir=output_dir,
            evidence_path=evidence_path,
            source_commit="test-commit",
        )

        assert result.ok is False
        assert "outside repository" in " ".join(result.errors)
        assert_no_export_side_effects(output_dir, evidence_path)
    finally:
        if output_dir.exists() or output_dir.is_symlink():
            remove_created_path(output_dir)


def test_exporter_rejects_existing_non_empty_output(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    module = load_module()
    generated_docs = generated_docs_tmp(monkeypatch, tmp_path, module)
    output_dir = tmp_path / "bundle"
    evidence_path = generated_docs / "e09-ansible-sync-bundle.md"
    output_dir.mkdir()
    (output_dir / "stale.txt").write_text("stale", encoding="utf-8")

    result = module.export_bundle(
        output_dir=output_dir,
        evidence_path=evidence_path,
        source_commit="test-commit",
    )

    assert result.ok is False
    assert "empty" in " ".join(result.errors)
    assert_no_export_side_effects(
        output_dir,
        evidence_path,
        allowed_existing_files={"stale.txt"},
    )


def test_exporter_rejects_evidence_path_escape(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    module = load_module()
    generated_docs_tmp(monkeypatch, tmp_path, module)
    output_dir = tmp_path / "bundle"
    evidence_path = tmp_path / "evidence.md"

    result = module.export_bundle(
        output_dir=output_dir,
        evidence_path=evidence_path,
        source_commit="test-commit",
    )

    assert result.ok is False
    assert "docs/generated" in " ".join(result.errors)
    assert_no_export_side_effects(output_dir, evidence_path)


def test_exporter_rejects_symlink_source_escape(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    module = load_module()
    generated_docs = generated_docs_tmp(monkeypatch, tmp_path, module)
    output_dir = tmp_path / "bundle"
    evidence_path = generated_docs / "e09-ansible-sync-bundle.md"
    escaped = tmp_path / "escaped.txt"
    escaped.write_text("safe-looking", encoding="utf-8")
    symlink = (
        ROOT
        / "deploy/kolla/ansible/roles/cloud_ui/templates/"
        / "e09-ansible-sync-bundle-symlink-source-escape.j2"
    )
    assert_path_available(symlink)
    created = False

    try:
        try:
            symlink.symlink_to(escaped)
            created = True
        except NotImplementedError as exc:
            pytest.skip(f"symlink creation unsupported: {exc}")
        except OSError as exc:
            if exc.errno in {errno.EPERM, errno.ENOTSUP, errno.EOPNOTSUPP}:
                pytest.skip(f"symlink creation unsupported: {exc}")
            raise

        result = module.export_bundle(
            output_dir=output_dir,
            evidence_path=evidence_path,
            source_commit="test-commit",
        )

        assert result.ok is False
        assert "symlink" in " ".join(result.errors)
        assert_no_export_side_effects(output_dir, evidence_path)
    finally:
        if created:
            symlink.unlink()


def test_exporter_rejects_secret_like_source_content(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    module = load_module()
    generated_docs = generated_docs_tmp(monkeypatch, tmp_path, module)
    output_dir = tmp_path / "bundle"
    evidence_path = generated_docs / "e09-ansible-sync-bundle.md"
    injected = (
        ROOT
        / "deploy/kolla/ansible/roles/cloud_ui/templates/"
        / "e09-ansible-sync-bundle-secret-like-source.j2"
    )
    assert_path_available(injected)
    created = False

    try:
        injected.write_text(
            "\n".join(
                [
                    fixture_value("mysql+pymysql://", "cloud_ui", ":", "bad", "@db/cloud_ui"),
                    fixture_value("-----BEGIN ", "PRIVATE KEY-----x-----END ", "PRIVATE KEY-----"),
                ]
            ),
            encoding="utf-8",
        )
        created = True

        result = module.export_bundle(
            output_dir=output_dir,
            evidence_path=evidence_path,
            source_commit="test-commit",
        )

        assert result.ok is False
        assert "secret-like" in " ".join(result.errors)
        assert_no_export_side_effects(output_dir, evidence_path)
    finally:
        if created:
            injected.unlink()


def test_exporter_rejects_live_mutating_kolla_source_content(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    module = load_module()
    generated_docs = generated_docs_tmp(monkeypatch, tmp_path, module)
    output_dir = tmp_path / "bundle"
    evidence_path = generated_docs / "e09-ansible-sync-bundle.md"
    injected = (
        ROOT
        / "deploy/kolla/ansible/roles/cloud_ui/tasks/"
        / "e09-ansible-sync-bundle-live-mutating-source.yml"
    )
    assert_path_available(injected)
    created = False

    try:
        injected.write_text(
            "- name: unsafe\n  ansible.builtin.shell: ./venv/bin/kolla-ansible deploy\n",
            encoding="utf-8",
        )
        created = True

        result = module.export_bundle(
            output_dir=output_dir,
            evidence_path=evidence_path,
            source_commit="test-commit",
        )

        assert result.ok is False
        assert "live mutating" in " ".join(result.errors)
        assert_no_export_side_effects(output_dir, evidence_path)
    finally:
        if created:
            injected.unlink()


def test_committed_docs_record_local_only_scope_and_risk() -> None:
    assert EVIDENCE.exists()
    evidence = EVIDENCE.read_text(encoding="utf-8")
    readme_section = extract_markdown_section(README, "E09 Ansible sync bundle")
    traceability_section = extract_markdown_section(TRACEABILITY, "E09 Ansible sync bundle")
    row = risk_row("R-070")

    for text in (evidence, readme_section, traceability_section, row):
        assert "E09 Ansible sync bundle" in text
        assert "local-only" in text
        assert "pending_external_evidence" in text
        assert "runtime secret value" in text

    assert "remote sync remains separately approved" in evidence
    assert "DB/MQ auth remediation" in evidence
    assert "mistaken for live deployment" in row

    risk_ids = [
        line.split("|")[1].strip()
        for line in RISK_REGISTER.read_text(encoding="utf-8").splitlines()
        if line.startswith("| R-")
    ]
    assert len(risk_ids) == len(set(risk_ids))
