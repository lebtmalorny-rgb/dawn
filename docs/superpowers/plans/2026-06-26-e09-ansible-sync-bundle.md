# E09 Ansible Sync Bundle Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a repository-side exporter that builds a safe local Cloud UI Kolla-Ansible bundle for a later, separately approved test-host sync.

**Architecture:** A standalone Python script copies only allowlisted Cloud UI Ansible artifacts into a local output directory, writes a checksum manifest, scans bundled text for secrets/live-mutation patterns and writes sanitized evidence under `docs/generated/`. Tests drive the contract before implementation; docs keep all remote sync, reconfigure, DB/MQ remediation and rollback evidence pending.

**Tech Stack:** Python standard library, pytest, YAML/Markdown repository contracts.

---

## Files

- Create: `tests/test_e09_ansible_sync_bundle.py`
- Create: `deploy/kolla/scripts/export-ansible-bundle.py`
- Create: `docs/generated/e09-ansible-sync-bundle.md`
- Create: `docs/execplans/E09-ansible-sync-bundle.md`
- Modify: `deploy/kolla/ansible/README.md`
- Modify: `docs/11_DKB_TRACEABILITY.md`
- Modify: `docs/generated/risk-register.md`

## Task 1: RED Contract Tests

**Files:**
- Create: `tests/test_e09_ansible_sync_bundle.py`

- [ ] **Step 1: Create the failing test file**

Create `tests/test_e09_ansible_sync_bundle.py`:

```python
import hashlib
import importlib.util
import json
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

    result = module.export_bundle(
        output_dir=ROOT / "docs/generated/e09-unsafe-bundle",
        evidence_path=generated_docs / "e09-ansible-sync-bundle.md",
        source_commit="test-commit",
    )

    assert result.ok is False
    assert "outside repository" in " ".join(result.errors)


def test_exporter_rejects_existing_non_empty_output(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    module = load_module()
    generated_docs = generated_docs_tmp(monkeypatch, tmp_path, module)
    output_dir = tmp_path / "bundle"
    output_dir.mkdir()
    (output_dir / "stale.txt").write_text("stale", encoding="utf-8")

    result = module.export_bundle(
        output_dir=output_dir,
        evidence_path=generated_docs / "e09-ansible-sync-bundle.md",
        source_commit="test-commit",
    )

    assert result.ok is False
    assert "empty" in " ".join(result.errors)


def test_exporter_rejects_evidence_path_escape(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    module = load_module()
    generated_docs_tmp(monkeypatch, tmp_path, module)

    result = module.export_bundle(
        output_dir=tmp_path / "bundle",
        evidence_path=tmp_path / "evidence.md",
        source_commit="test-commit",
    )

    assert result.ok is False
    assert "docs/generated" in " ".join(result.errors)


def test_exporter_rejects_symlink_source_escape(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    module = load_module()
    generated_docs = generated_docs_tmp(monkeypatch, tmp_path, module)
    escaped = tmp_path / "escaped.txt"
    escaped.write_text("safe-looking", encoding="utf-8")
    symlink = ROOT / "deploy/kolla/ansible/roles/cloud_ui/templates/e09-symlink-test.j2"

    try:
        try:
            symlink.symlink_to(escaped)
        except (NotImplementedError, OSError) as exc:
            pytest.skip(f"symlink creation unsupported: {exc}")

        result = module.export_bundle(
            output_dir=tmp_path / "bundle",
            evidence_path=generated_docs / "e09-ansible-sync-bundle.md",
            source_commit="test-commit",
        )
    finally:
        symlink.unlink(missing_ok=True)

    assert result.ok is False
    assert "symlink" in " ".join(result.errors)


def test_exporter_rejects_secret_like_source_content(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    module = load_module()
    generated_docs = generated_docs_tmp(monkeypatch, tmp_path, module)
    injected = ROOT / "deploy/kolla/ansible/roles/cloud_ui/templates/e09-secret-test.j2"
    injected.write_text(
        "\n".join(
            [
                fixture_value("mysql+pymysql://", "cloud_ui", ":", "bad", "@db/cloud_ui"),
                fixture_value("-----BEGIN ", "PRIVATE KEY-----x-----END ", "PRIVATE KEY-----"),
            ]
        ),
        encoding="utf-8",
    )

    try:
        result = module.export_bundle(
            output_dir=tmp_path / "bundle",
            evidence_path=generated_docs / "e09-ansible-sync-bundle.md",
            source_commit="test-commit",
        )
    finally:
        injected.unlink(missing_ok=True)

    assert result.ok is False
    assert "secret-like" in " ".join(result.errors)


def test_exporter_rejects_live_mutating_kolla_source_content(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    module = load_module()
    generated_docs = generated_docs_tmp(monkeypatch, tmp_path, module)
    injected = ROOT / "deploy/kolla/ansible/roles/cloud_ui/tasks/e09-live-command-test.yml"
    injected.write_text(
        "- name: unsafe\n  ansible.builtin.shell: ./venv/bin/kolla-ansible deploy\n",
        encoding="utf-8",
    )

    try:
        result = module.export_bundle(
            output_dir=tmp_path / "bundle",
            evidence_path=generated_docs / "e09-ansible-sync-bundle.md",
            source_commit="test-commit",
        )
    finally:
        injected.unlink(missing_ok=True)

    assert result.ok is False
    assert "live mutating" in " ".join(result.errors)


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
```

- [ ] **Step 2: Run RED test**

Run:

```bash
UV_CACHE_DIR=/tmp/dawn-uv-cache UV_PYTHON_INSTALL_DIR=/tmp/dawn-uv-python UV_PROJECT_ENVIRONMENT=/tmp/dawn-e09-sync-bundle-venv uv run --python 3.11 --project backend --extra dev pytest tests/test_e09_ansible_sync_bundle.py -q
```

Expected: fails because `deploy/kolla/scripts/export-ansible-bundle.py`, generated evidence, README section, traceability section and `R-070` do not exist.

- [ ] **Step 3: Commit RED tests**

Run:

```bash
git add tests/test_e09_ansible_sync_bundle.py
git commit -m "test: add E09 ansible sync bundle contract"
```

Expected: commit contains only the new test file.

## Task 2: Exporter Script

**Files:**
- Create: `deploy/kolla/scripts/export-ansible-bundle.py`

- [ ] **Step 1: Implement exporter**

Create `deploy/kolla/scripts/export-ansible-bundle.py` with these public functions and constants:

```python
#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
GENERATED_DOCS = (ROOT / "docs/generated").resolve()

BUNDLE_SCHEMA_VERSION = "e09-ansible-sync-bundle/v1"
BUNDLE_SOURCES = (
    ("deploy/kolla/ansible/roles/cloud_ui", "roles/cloud_ui"),
    ("deploy/kolla/ansible/playbooks/cloud-ui-preflight.yml", "playbooks/cloud-ui-preflight.yml"),
    ("deploy/kolla/ansible/examples/cloud-ui-vars.yml.example", "examples/cloud-ui-vars.yml.example"),
)
ROLE_PATH_NOTE = "Set ANSIBLE_ROLES_PATH=roles or configure an equivalent Ansible roles path."

CREDENTIAL_URL_RE = re.compile(r"(?i)\\b[a-z][a-z0-9+.-]*://[^/\\s:@]+:[^@\\s/]+@")
PEM_PRIVATE_KEY_RE = re.compile(r"(?is)-----BEGIN [A-Z ]*PRIVATE KEY-----.*?-----END [A-Z ]*PRIVATE KEY-----")
SECRET_ASSIGNMENT_RE = re.compile(
    r"(?i)\\b(?:[A-Za-z0-9_-]+_)?(?:password|passwd|token|private[_-]?key|"
    r"application_credential(?:_secret)?)(?:_[A-Za-z0-9_-]+)?\\s*[:=]\\s*"
    r"(?:\\\"[^\\\"]+\\\"|'[^']+'|[^\\n#]+)"
)
FORBIDDEN_TEXT_RE = re.compile(r"(?i)(clouds\\.yaml|\\bopenrc\\b|\\.env\\b)")
LIVE_MUTATION_RE = re.compile(
    r"^\\s*(?:(?:[-*]|\\d+\\.)\\s+)?(?:`|\\$\\s*)?(?:sudo\\s+)?"
    r"(?:\\S*/)?kolla-ansible"
    r"(?:\\s+(?!deploy\\b|reconfigure\\b|destroy\\b|upgrade\\b)\\S+)*"
    r"\\s+(?:deploy|reconfigure|destroy|upgrade)\\b|"
    r"^\\s*(?:[-*]\\s+)?(?:ansible\\.builtin\\.)?shell\\s*:|"
    r"^\\s*(?:[-*]\\s+)?(?:ansible\\.builtin\\.)?command\\s*:|"
    r"^\\s*(?:[-*]\\s+)?kolla_container\\s*:|"
    r"^\\s*(?:[-*]\\s+)?community\\.mysql(?:\\.[A-Za-z_]+)?\\s*:|"
    r"^\\s*(?:[-*]\\s+)?community\\.rabbitmq(?:\\.[A-Za-z_]+)?\\s*:",
    flags=re.IGNORECASE | re.MULTILINE,
)


@dataclass(frozen=True)
class ValidationResult:
    ok: bool
    errors: tuple[str, ...]


def _path_is_inside(child: Path, parent: Path) -> bool:
    try:
        child.resolve(strict=False).relative_to(parent.resolve(strict=False))
    except (OSError, ValueError):
        return False
    return True


def _evidence_path_is_allowed(path: Path) -> bool:
    if path.is_symlink():
        return False
    if not _path_is_inside(path, GENERATED_DOCS):
        return False
    if path.exists():
        return _path_is_inside(path.resolve(strict=True), GENERATED_DOCS)
    return True


def _output_dir_is_allowed(path: Path) -> bool:
    if _path_is_inside(path, ROOT):
        return False
    if path.exists() and path.is_symlink():
        return False
    if path.exists() and any(path.iterdir()):
        return False
    return True


def _source_files() -> tuple[tuple[Path, Path], ...]:
    files: list[tuple[Path, Path]] = []
    for source_relative, bundle_relative in BUNDLE_SOURCES:
        source = ROOT / source_relative
        target = Path(bundle_relative)
        if source.is_file():
            files.append((source, target))
            continue
        for item in sorted(source.rglob("*")):
            if item.is_file() or item.is_symlink():
                files.append((item, target / item.relative_to(source)))
    return tuple(files)


def _scan_text(path: Path, text: str) -> tuple[str, ...]:
    errors: list[str] = []
    if CREDENTIAL_URL_RE.search(text) or PEM_PRIVATE_KEY_RE.search(text) or SECRET_ASSIGNMENT_RE.search(text):
        errors.append(f"{path}: secret-like value found")
    if FORBIDDEN_TEXT_RE.search(text):
        errors.append(f"{path}: forbidden credential file reference found")
    if LIVE_MUTATION_RE.search(text):
        errors.append(f"{path}: live mutating command pattern found")
    return tuple(errors)


def _validate_sources() -> ValidationResult:
    errors: list[str] = []
    for source_relative, _ in BUNDLE_SOURCES:
        source = ROOT / source_relative
        if not source.exists():
            errors.append(f"missing source path: {source_relative}")
        elif not _path_is_inside(source, ROOT):
            errors.append(f"source path escapes repository: {source_relative}")

    for source, bundle_relative in _source_files():
        if source.is_symlink():
            errors.append(f"{source.relative_to(ROOT)}: symlink source is not allowed")
            continue
        if not _path_is_inside(source, ROOT):
            errors.append(f"{source}: source path escapes repository")
            continue
        if "__pycache__" in source.parts or source.suffix == ".pyc":
            errors.append(f"{source.relative_to(ROOT)}: generated Python cache is not allowed")
            continue
        if bundle_relative.is_absolute() or ".." in bundle_relative.parts:
            errors.append(f"{bundle_relative}: bundle path escapes output")
            continue
        text = source.read_text(encoding="utf-8", errors="replace")
        errors.extend(_scan_text(source.relative_to(ROOT), text))
    return ValidationResult(ok=not errors, errors=tuple(errors))


def _copy_sources(output_dir: Path) -> list[dict[str, object]]:
    manifest_files: list[dict[str, object]] = []
    output_dir.mkdir(parents=True, exist_ok=True)
    resolved_output = output_dir.resolve(strict=True)

    for source, bundle_relative in _source_files():
        destination = output_dir / bundle_relative
        if not _path_is_inside(destination, resolved_output):
            raise ValueError(f"bundle destination escapes output: {bundle_relative}")
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
        data = destination.read_bytes()
        manifest_files.append(
            {
                "path": bundle_relative.as_posix(),
                "sha256": hashlib.sha256(data).hexdigest(),
                "bytes": len(data),
            }
        )
    return manifest_files


def _source_commit(explicit: str | None) -> str:
    if explicit:
        return explicit
    try:
        completed = subprocess.run(
            ["git", "rev-parse", "--short=12", "HEAD"],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return "unknown"
    return completed.stdout.strip()


def _write_json_atomic(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w",
        encoding="utf-8",
        dir=path.parent,
        prefix=f".{path.name}.",
        suffix=".tmp",
        delete=False,
    ) as temporary:
        json.dump(payload, temporary, indent=2, sort_keys=True)
        temporary.write("\\n")
        temporary_path = Path(temporary.name)
    temporary_path.replace(path)


def _write_text_atomic(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w",
        encoding="utf-8",
        dir=path.parent,
        prefix=f".{path.name}.",
        suffix=".tmp",
        delete=False,
    ) as temporary:
        temporary.write(text)
        temporary_path = Path(temporary.name)
    temporary_path.replace(path)


def render_evidence(manifest: dict[str, object]) -> str:
    files = manifest["files"]
    assert isinstance(files, list)
    return "\\n".join(
        [
            "# E09 Ansible sync bundle",
            "",
            "- Stage: E09 Ansible sync bundle",
            "- Status: local-only export; remote sync remains separately approved",
            "- Live execution status: `pending_external_evidence`",
            f"- Source commit: `{manifest['source_commit']}`",
            f"- Bundle schema: `{manifest['schema_version']}`",
            "- Runtime secret value: absent; DB/MQ URLs are external runtime inputs only",
            "",
            "## Bundle contents",
            "",
            "| Path | Bytes | SHA256 |",
            "|---|---:|---|",
            *[
                f"| `{item['path']}` | {item['bytes']} | `{item['sha256']}` |"
                for item in files
            ],
            "",
            "## Operator note",
            "",
            "Use `ANSIBLE_ROLES_PATH=roles` or equivalent role path configuration after copying the",
            "bundle in a separately approved remote-sync step. This repository slice does not copy the",
            "bundle to a host, run live mutating Kolla actions, remediate DB/MQ auth, inspect containers",
            "or execute rollback.",
            "",
            "## Remaining blockers",
            "",
            "- remote sync remains separately approved;",
            "- DB/MQ auth remediation remains `pending_external_evidence`; ",
            "- live reconfigure, 12-container inspection, HAProxy/TLS, SELinux and rollback remain pending.",
            "",
        ]
    )


def export_bundle(output_dir: Path, evidence_path: Path, source_commit: str | None = None) -> ValidationResult:
    errors: list[str] = []
    if not _output_dir_is_allowed(output_dir):
        errors.append("output directory must be outside repository and empty")
    if not _evidence_path_is_allowed(evidence_path):
        errors.append("evidence path must stay under docs/generated without symlink escape")
    source_validation = _validate_sources()
    errors.extend(source_validation.errors)
    if errors:
        return ValidationResult(ok=False, errors=tuple(errors))

    commit = _source_commit(source_commit)
    manifest_files = _copy_sources(output_dir)
    manifest = {
        "schema_version": BUNDLE_SCHEMA_VERSION,
        "source_commit": commit,
        "generated_at_utc": datetime.now(UTC).replace(microsecond=0).isoformat(),
        "role_path_note": ROLE_PATH_NOTE,
        "files": manifest_files,
    }
    _write_json_atomic(output_dir / "manifest.json", manifest)
    _write_text_atomic(evidence_path, render_evidence(manifest))
    return ValidationResult(ok=True, errors=())


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Export the E09 Cloud UI Ansible sync bundle.")
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument(
        "--evidence",
        default=ROOT / "docs/generated/e09-ansible-sync-bundle.md",
        type=Path,
    )
    parser.add_argument("--source-commit", default=None)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    result = export_bundle(
        output_dir=args.output_dir,
        evidence_path=args.evidence,
        source_commit=args.source_commit,
    )
    if not result.ok:
        for error in result.errors:
            print(f"error: {error}", file=sys.stderr)
        return 2
    print(f"exported E09 Ansible sync bundle to {args.output_dir}")
    print(f"wrote evidence to {args.evidence}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 2: Run targeted tests**

Run:

```bash
UV_CACHE_DIR=/tmp/dawn-uv-cache UV_PYTHON_INSTALL_DIR=/tmp/dawn-uv-python UV_PROJECT_ENVIRONMENT=/tmp/dawn-e09-sync-bundle-venv uv run --python 3.11 --project backend --extra dev pytest tests/test_e09_ansible_sync_bundle.py -q
```

Expected: script-related tests pass; docs-related test still fails until Task 3 creates evidence, README section, traceability section and risk `R-070`.

- [ ] **Step 3: Run Ruff**

Run:

```bash
UV_CACHE_DIR=/tmp/dawn-uv-cache UV_PYTHON_INSTALL_DIR=/tmp/dawn-uv-python UV_PROJECT_ENVIRONMENT=/tmp/dawn-e09-sync-bundle-venv uv run --python 3.11 --project backend --extra dev ruff check tests/test_e09_ansible_sync_bundle.py deploy/kolla/scripts/export-ansible-bundle.py
```

Expected: `All checks passed!`

- [ ] **Step 4: Commit exporter**

Run:

```bash
git add deploy/kolla/scripts/export-ansible-bundle.py
git commit -m "deploy: add E09 ansible sync bundle exporter"
```

Expected: commit contains only the exporter script.

## Task 3: Evidence, Docs And Traceability

**Files:**
- Create: `docs/generated/e09-ansible-sync-bundle.md`
- Create: `docs/execplans/E09-ansible-sync-bundle.md`
- Modify: `deploy/kolla/ansible/README.md`
- Modify: `docs/11_DKB_TRACEABILITY.md`
- Modify: `docs/generated/risk-register.md`

- [ ] **Step 1: Generate evidence from the exporter**

Run:

```bash
rm -rf /tmp/dawn-e09-ansible-sync-bundle
deploy/kolla/scripts/export-ansible-bundle.py --output-dir /tmp/dawn-e09-ansible-sync-bundle --evidence docs/generated/e09-ansible-sync-bundle.md
```

Expected:

- exit `0`;
- `/tmp/dawn-e09-ansible-sync-bundle/manifest.json` exists;
- `docs/generated/e09-ansible-sync-bundle.md` exists;
- no remote host is contacted.

- [ ] **Step 2: Add ExecPlan**

Create `docs/execplans/E09-ansible-sync-bundle.md`:

```markdown
# ExecPlan: E09 Ansible Sync Bundle

## Goal

Create a repository-side local-only export bundle for Cloud UI Kolla-Ansible artifacts.

## Scope

This slice creates tests, an exporter, local bundle evidence, documentation, traceability and a risk
row. It does not copy files to a remote host, run live mutating Kolla actions, change DB/MQ/Vault or
claim E09 deployment acceptance.

## Progress

- [x] 2026-06-26: Design approved in `docs/superpowers/specs/2026-06-26-e09-ansible-sync-bundle-design.md`.
- [x] RED contract tests.
- [x] Exporter implementation.
- [x] Evidence and traceability.
- [ ] Verification and review.

## Verification

- `UV_CACHE_DIR=/tmp/dawn-uv-cache UV_PYTHON_INSTALL_DIR=/tmp/dawn-uv-python UV_PROJECT_ENVIRONMENT=/tmp/dawn-e09-sync-bundle-venv uv run --python 3.11 --project backend --extra dev pytest tests/test_e09_ansible_sync_bundle.py tests/test_e09_live_reconfigure_bundle.py tests/test_e09_kolla_ansible_role.py -q`
- `UV_CACHE_DIR=/tmp/dawn-uv-cache UV_PYTHON_INSTALL_DIR=/tmp/dawn-uv-python UV_PROJECT_ENVIRONMENT=/tmp/dawn-e09-sync-bundle-venv uv run --python 3.11 --project backend --extra dev ruff check tests/test_e09_ansible_sync_bundle.py deploy/kolla/scripts/export-ansible-bundle.py`
- `./scripts/secret-scan.sh`
- `git diff --check`

## Rollback

Revert this repository slice and remove any locally generated `/tmp/dawn-e09-ansible-sync-bundle`
directory. No remote host, registry, database, queue, Vault path or credential is changed.
```

- [ ] **Step 3: Update README**

Append this section to `deploy/kolla/ansible/README.md`:

```markdown
## E09 Ansible sync bundle

The E09 Ansible sync bundle is a local-only export for the approved test-stand preparation path. It
packages the `cloud_ui` role, preflight playbook, placeholder example vars and a manifest with file
checksums. It contains no runtime secret value, inventory, SSH material, DB/MQ URL, token, private key
or host-specific credential.

The bundle is not live deployment evidence and does not run live mutating Kolla actions. Remote sync,
DB/MQ auth remediation, live reconfigure and rollback remain `pending_external_evidence`, and the
copied bundle should use `ANSIBLE_ROLES_PATH=roles` or an equivalent Ansible roles path configuration.

Evidence: `docs/generated/e09-ansible-sync-bundle.md`.
```

- [ ] **Step 4: Update DKB traceability**

Add this section to `docs/11_DKB_TRACEABILITY.md` immediately before `## Полная матрица`:

```markdown
## E09 Ansible sync bundle

Обновление требований 2026-06-26: E09 Ansible sync bundle is local-only and prepares a reproducible
operator artifact for a later, separately approved test-host sync. Remote sync, live reconfigure,
DB/MQ auth remediation, 12-container inspection, HAProxy/TLS, SELinux and rollback remain
`pending_external_evidence`.

For ДКБ-55/56, the exporter rejects runtime secret value material and does not include inventory,
DB/MQ URLs, SSH data, tokens, private keys, `.env`, `clouds.yaml` or openrc. Secret delivery and
rotation remain external evidence.

For ДКБ-65/69/70/76/77/80/82, this slice creates a checksum manifest and operator documentation only.
It does not prove live container hardening, registry pull-by-digest, management-zone ACLs, live
deployment, rollback or ДКБ-69 waiver closure.

Evidence paths:

- `tests/test_e09_ansible_sync_bundle.py`
- `deploy/kolla/scripts/export-ansible-bundle.py`
- `docs/generated/e09-ansible-sync-bundle.md`
```

- [ ] **Step 5: Update risk register**

Append this row after `R-069` in `docs/generated/risk-register.md`:

```markdown
| R-070 | E09 Ansible sync bundle mistaken for live deployment or secret remediation | The local-only export bundle proves repository artifact packaging and checksums, but it does not copy the role to the Ansible host, repair DB/MQ auth, run live mutating Kolla actions, inspect containers or test rollback. | Keep remote sync, DB/MQ auth remediation, live reconfigure, 12-container inspection, HAProxy/TLS, SELinux and rollback evidence as `pending_external_evidence` until separately approved test-stand actions produce sanitized proof. | E09 |
```

- [ ] **Step 6: Run targeted tests**

Run:

```bash
UV_CACHE_DIR=/tmp/dawn-uv-cache UV_PYTHON_INSTALL_DIR=/tmp/dawn-uv-python UV_PROJECT_ENVIRONMENT=/tmp/dawn-e09-sync-bundle-venv uv run --python 3.11 --project backend --extra dev pytest tests/test_e09_ansible_sync_bundle.py -q
```

Expected: all tests in the new file pass.

- [ ] **Step 7: Commit docs and evidence**

Run:

```bash
git add docs/generated/e09-ansible-sync-bundle.md docs/execplans/E09-ansible-sync-bundle.md deploy/kolla/ansible/README.md docs/11_DKB_TRACEABILITY.md docs/generated/risk-register.md
git commit -m "docs: add E09 ansible sync bundle evidence"
```

Expected: commit contains only docs/evidence files.

## Task 4: Final Verification And Review

**Files:**
- Verify all changed files.

- [ ] **Step 1: Run targeted pytest**

Run:

```bash
UV_CACHE_DIR=/tmp/dawn-uv-cache UV_PYTHON_INSTALL_DIR=/tmp/dawn-uv-python UV_PROJECT_ENVIRONMENT=/tmp/dawn-e09-sync-bundle-venv uv run --python 3.11 --project backend --extra dev pytest tests/test_e09_ansible_sync_bundle.py tests/test_e09_live_reconfigure_bundle.py tests/test_e09_kolla_ansible_role.py -q
```

Expected: all selected tests pass.

- [ ] **Step 2: Run Ruff**

Run:

```bash
UV_CACHE_DIR=/tmp/dawn-uv-cache UV_PYTHON_INSTALL_DIR=/tmp/dawn-uv-python UV_PROJECT_ENVIRONMENT=/tmp/dawn-e09-sync-bundle-venv uv run --python 3.11 --project backend --extra dev ruff check tests/test_e09_ansible_sync_bundle.py deploy/kolla/scripts/export-ansible-bundle.py
```

Expected: `All checks passed!`

- [ ] **Step 3: Run secret scan**

Run:

```bash
./scripts/secret-scan.sh
```

Expected: exit `0`, no findings.

- [ ] **Step 4: Run diff check**

Run:

```bash
git diff --check
```

Expected: exit `0`.

- [ ] **Step 5: Self-review diff**

Run:

```bash
git diff --stat main...HEAD
git diff main...HEAD -- tests/test_e09_ansible_sync_bundle.py deploy/kolla/scripts/export-ansible-bundle.py docs/generated/e09-ansible-sync-bundle.md docs/execplans/E09-ansible-sync-bundle.md deploy/kolla/ansible/README.md docs/11_DKB_TRACEABILITY.md docs/generated/risk-register.md
```

Confirm:

- no remote host write or live mutating Kolla command execution is added;
- no runtime secret value, inventory, SSH data, token, private key, `.env`, `clouds.yaml` or openrc is committed;
- docs keep remote sync, DB/MQ auth remediation, live reconfigure, 12-container inspection and rollback pending;
- `R-070` is unique.

- [ ] **Step 6: Close ExecPlan**

Update `docs/execplans/E09-ansible-sync-bundle.md` progress:

```markdown
- [x] Verification and review.
```

Run:

```bash
UV_CACHE_DIR=/tmp/dawn-uv-cache UV_PYTHON_INSTALL_DIR=/tmp/dawn-uv-python UV_PROJECT_ENVIRONMENT=/tmp/dawn-e09-sync-bundle-venv uv run --python 3.11 --project backend --extra dev pytest tests/test_e09_ansible_sync_bundle.py -q
git diff --check
```

Expected: targeted test and diff check pass.

- [ ] **Step 7: Commit final ExecPlan close**

Run:

```bash
git add docs/execplans/E09-ansible-sync-bundle.md
git commit -m "docs: close E09 ansible sync bundle execplan"
```

Expected: commit contains only the ExecPlan progress change.
