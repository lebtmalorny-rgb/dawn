# E09 Ansible Remote Sync Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Copy the Cloud UI Ansible bundle to the approved test Ansible host and record sanitized evidence without running live Kolla deployment actions.

**Architecture:** Add a small stdlib Python sync helper that validates a local exported bundle, enforces the approved host/path, builds safe `ssh`/`rsync` commands without shell interpolation for local arguments, and renders sanitized evidence. Repository tests drive the contract; a separate operational task performs the approved remote copy to `192.168.10.15:/etc/kolla/cloud-ui-sync-bundle`.

**Tech Stack:** Python standard library, pytest, existing E09 bundle exporter, OpenSSH/rsync on the operator machine, Markdown evidence.

---

## Files

- Create: `tests/test_e09_ansible_remote_sync.py`
- Create: `deploy/kolla/scripts/sync-ansible-remote-bundle.py`
- Create: `docs/generated/e09-ansible-remote-sync.md`
- Create: `docs/execplans/E09-ansible-remote-sync.md`
- Modify: `docs/11_DKB_TRACEABILITY.md`
- Modify: `docs/generated/risk-register.md`

## ExecPlan Requirement

Create `docs/execplans/E09-ansible-remote-sync.md` during the docs/evidence task. It must follow
`PLANS.md`, track remote copy progress, and keep final verification unchecked until the final task.

## Task 1: RED Contract Tests

**Files:**
- Create: `tests/test_e09_ansible_remote_sync.py`

- [ ] **Step 1: Create the failing test file**

Create `tests/test_e09_ansible_remote_sync.py`:

```python
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
    assert request.rsync_args[:2] == ("rsync", "-a")
    assert str(bundle_dir) + "/" in request.rsync_args
    assert "kolla-ansible" not in " ".join(request.remote_commands)
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
UV_CACHE_DIR=/tmp/dawn-uv-cache UV_PYTHON_INSTALL_DIR=/tmp/dawn-uv-python UV_PROJECT_ENVIRONMENT=/tmp/dawn-e09-remote-sync-venv uv run --python 3.11 --project backend --extra dev pytest tests/test_e09_ansible_remote_sync.py -q
```

Expected: fails because `deploy/kolla/scripts/sync-ansible-remote-bundle.py` and committed evidence
do not exist.

- [ ] **Step 3: Commit RED tests**

Run:

```bash
git add tests/test_e09_ansible_remote_sync.py
git commit -m "test: add E09 ansible remote sync contract"
```

Expected: commit contains only the new test file.

## Task 2: Remote Sync Helper

**Files:**
- Create: `deploy/kolla/scripts/sync-ansible-remote-bundle.py`

> Controller amendment after Task 1 reviews: use the committed
> `tests/test_e09_ansible_remote_sync.py` as the executable contract. The helper must reject
> unmanifested benign extra files, forbidden credential filenames such as `clouds.yaml`, manifest byte
> mismatches and manifest path traversal. `build_sync_request(...)` must produce the exact staging
> `rsync` args and exact backup-before-replace command sequence asserted by the test. Evidence text
> must keep live reconfigure, DB/MQ auth remediation, migration, 12-container inspection,
> HAProxy/TLS, SELinux hardening and rollback as same-line `remains pending_external_evidence`
> statements, and production deployment must remain out of scope.

- [ ] **Step 1: Implement helper**

Create `deploy/kolla/scripts/sync-ansible-remote-bundle.py`:

```python
#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

APPROVED_REMOTE_HOST = "192.168.10.15"
APPROVED_REMOTE_PATH = Path("/etc/kolla/cloud-ui-sync-bundle")
ROLE_PATH_NOTE = "ANSIBLE_ROLES_PATH=/etc/kolla/cloud-ui-sync-bundle/roles"
REQUIRED_PATHS = {
    "roles/cloud_ui/defaults/main.yml",
    "roles/cloud_ui/tasks/main.yml",
    "roles/cloud_ui/templates/cloud-ui-backend.env.j2",
    "playbooks/cloud-ui-preflight.yml",
    "examples/cloud-ui-vars.yml.example",
}
SAFE_TIMESTAMP_RE = re.compile(r"^[0-9]{8}T[0-9]{6}Z$")
MUTATING_KOLLA_RE = re.compile(r"\\bkolla-ansible\\b.*\\b(deploy|reconfigure|upgrade|destroy|pull|prechecks|check)\\b")


@dataclass(frozen=True)
class ValidationResult:
    ok: bool
    errors: tuple[str, ...]
    summary: dict[str, Any] | None = None


@dataclass(frozen=True)
class SyncRequest:
    target: str
    remote_path: str
    staging_path: str
    backup_path: str
    rsync_args: tuple[str, ...]
    remote_commands: tuple[str, ...]


def _load_manifest(bundle_dir: Path) -> tuple[dict[str, Any] | None, tuple[str, ...]]:
    manifest_path = bundle_dir / "manifest.json"
    if not manifest_path.is_file():
        return None, ("manifest.json is missing",)
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return None, (f"manifest.json is invalid JSON: {exc}",)
    if manifest.get("schema_version") != "e09-ansible-sync-bundle/v1":
        return None, ("manifest schema_version must be e09-ansible-sync-bundle/v1",)
    files = manifest.get("files")
    if not isinstance(files, list):
        return None, ("manifest files must be a list",)
    return manifest, ()


def validate_local_bundle(bundle_dir: Path) -> ValidationResult:
    errors: list[str] = []
    if not bundle_dir.exists() or not bundle_dir.is_dir() or bundle_dir.is_symlink():
        return ValidationResult(ok=False, errors=("bundle_dir must be an existing directory",))
    manifest, manifest_errors = _load_manifest(bundle_dir)
    errors.extend(manifest_errors)
    if manifest is None:
        return ValidationResult(ok=False, errors=tuple(errors))

    files: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in manifest["files"]:
        if not isinstance(item, dict):
            errors.append("manifest file entry must be an object")
            continue
        path_value = item.get("path")
        expected_sha = item.get("sha256")
        expected_bytes = item.get("bytes")
        if not isinstance(path_value, str) or path_value.startswith("/") or ".." in Path(path_value).parts:
            errors.append(f"{path_value}: unsafe manifest path")
            continue
        file_path = bundle_dir / path_value
        if not file_path.is_file() or file_path.is_symlink():
            errors.append(f"{path_value}: bundle file missing or symlink")
            continue
        data = file_path.read_bytes()
        actual_sha = hashlib.sha256(data).hexdigest()
        actual_bytes = len(data)
        if expected_sha != actual_sha:
            errors.append(f"{path_value}: sha256 mismatch")
        if expected_bytes != actual_bytes:
            errors.append(f"{path_value}: byte count mismatch")
        files.append({"path": path_value, "sha256": actual_sha, "bytes": actual_bytes})
        seen.add(path_value)

    missing = sorted(REQUIRED_PATHS - seen)
    for path in missing:
        errors.append(f"{path}: required bundle artifact missing")

    summary = {
        "schema_version": manifest.get("schema_version"),
        "source_commit": manifest.get("source_commit", "unknown"),
        "file_count": len(files),
        "paths": sorted(seen),
        "files": sorted(files, key=lambda value: value["path"]),
    }
    return ValidationResult(ok=not errors, errors=tuple(errors), summary=summary)


def validate_sync_request(bundle_dir: Path, remote_host: str, remote_path: Path) -> ValidationResult:
    errors: list[str] = []
    if remote_host != APPROVED_REMOTE_HOST:
        errors.append(f"remote host must be approved host {APPROVED_REMOTE_HOST}")
    if remote_path != APPROVED_REMOTE_PATH:
        errors.append(f"remote path must be approved remote path {APPROVED_REMOTE_PATH}")
    bundle_result = validate_local_bundle(bundle_dir)
    errors.extend(bundle_result.errors)
    return ValidationResult(ok=not errors, errors=tuple(errors), summary=bundle_result.summary)


def _remote_shell_quote(value: str) -> str:
    return "'" + value.replace("'", "'\"'\"'") + "'"


def _timestamp(value: str | None) -> str:
    if value is None:
        return datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    if not SAFE_TIMESTAMP_RE.fullmatch(value):
        raise ValueError("timestamp must match YYYYMMDDTHHMMSSZ")
    return value


def build_sync_request(
    bundle_dir: Path,
    remote_host: str,
    remote_user: str,
    remote_path: Path,
    timestamp: str | None = None,
) -> SyncRequest:
    stamp = _timestamp(timestamp)
    target = f"{remote_user}@{remote_host}"
    staging_path = f"/etc/kolla/.cloud-ui-sync-bundle.{stamp}.staging"
    backup_path = f"{APPROVED_REMOTE_PATH}.backup-{stamp}"
    bundle_source = str(bundle_dir.resolve()) + "/"
    remote_staging = f"{target}:{staging_path}/"
    remote_commands = (
        f"mkdir -p {_remote_shell_quote('/etc/kolla')}",
        f"rm -rf {_remote_shell_quote(staging_path)}",
        f"mkdir -p {_remote_shell_quote(staging_path)}",
        (
            f"if [ -e {_remote_shell_quote(str(APPROVED_REMOTE_PATH))} ]; then "
            f"mv {_remote_shell_quote(str(APPROVED_REMOTE_PATH))} {_remote_shell_quote(backup_path)}; fi"
        ),
        f"mv {_remote_shell_quote(staging_path)} {_remote_shell_quote(str(APPROVED_REMOTE_PATH))}",
    )
    for command in remote_commands:
        if MUTATING_KOLLA_RE.search(command):
            raise ValueError("remote command unexpectedly contains mutating kolla-ansible action")
    return SyncRequest(
        target=target,
        remote_path=str(remote_path),
        staging_path=staging_path,
        backup_path=backup_path,
        rsync_args=("rsync", "-a", "--delete", bundle_source, remote_staging),
        remote_commands=remote_commands,
    )


def compare_remote_summary(
    local_summary: dict[str, Any] | None,
    remote_summary: dict[str, Any] | None,
) -> ValidationResult:
    if local_summary is None or remote_summary is None:
        return ValidationResult(ok=False, errors=("local and remote summaries are required",))
    errors: list[str] = []
    local_files = {item["path"]: item for item in local_summary.get("files", [])}
    remote_files = {item["path"]: item for item in remote_summary.get("files", [])}
    if set(local_files) != set(remote_files):
        errors.append("remote file set does not match local bundle manifest")
    for path, local_item in local_files.items():
        remote_item = remote_files.get(path)
        if remote_item is None:
            continue
        if local_item["sha256"] != remote_item["sha256"]:
            errors.append(f"{path}: remote sha256 mismatch")
        if local_item["bytes"] != remote_item["bytes"]:
            errors.append(f"{path}: remote byte count mismatch")
    summary = {
        "file_count": len(remote_files),
        "paths": sorted(remote_files),
        "files": [remote_files[path] for path in sorted(remote_files)],
    }
    return ValidationResult(ok=not errors, errors=tuple(errors), summary=summary)


def render_evidence(
    *,
    local_summary: dict[str, Any] | None,
    remote_host: str,
    remote_path: str,
    backup_path: str,
    remote_verified: bool,
    remote_file_count: int,
    source_commit: str,
) -> str:
    file_count = local_summary.get("file_count") if local_summary else "unknown"
    schema = local_summary.get("schema_version") if local_summary else "unknown"
    return "\\n".join(
        [
            "# E09 Ansible remote sync",
            "",
            "- Stage: E09 Ansible remote sync",
            "- Scope: remote-sync-only test-stand evidence",
            f"- Host: `{remote_host}`",
            f"- Remote path: `{remote_path}`",
            f"- Backup path: `{backup_path}`",
            f"- Local bundle schema: `{schema}`",
            f"- Local bundle file count: `{file_count}`",
            f"- Remote verified: `{str(remote_verified).lower()}`",
            f"- Remote file count: `{remote_file_count}`",
            f"- Source commit: `{source_commit}`",
            "- runtime secret value: absent; placeholder example vars only",
            "",
            "## Role resolution",
            "",
            f"Use `{ROLE_PATH_NOTE}` for a later separately approved preflight or Kolla action.",
            "",
            "## Non-goals",
            "",
            "- no live reconfigure;",
            "- no DB/MQ auth remediation;",
            "- no one-shot migration execution;",
            "- no 12-container inspection;",
            "- no HAProxy/TLS, SELinux or rollback execution evidence.",
            "",
            "## Remaining blockers",
            "",
            "- live reconfigure remains `pending_external_evidence`;",
            "- DB/MQ auth remediation remains `pending_external_evidence`;",
            "- migration, twelve containers, HAProxy/TLS, SELinux and rollback remain `pending_external_evidence`.",
            "",
        ]
    )


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Sync the E09 Cloud UI Ansible bundle to the approved test host.")
    parser.add_argument("--bundle-dir", required=True, type=Path)
    parser.add_argument("--remote-host", default=APPROVED_REMOTE_HOST)
    parser.add_argument("--remote-user", default="root")
    parser.add_argument("--remote-path", default=APPROVED_REMOTE_PATH, type=Path)
    parser.add_argument("--evidence", default=Path("docs/generated/e09-ansible-remote-sync.md"), type=Path)
    parser.add_argument("--execute", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    validation = validate_sync_request(args.bundle_dir, args.remote_host, args.remote_path)
    if not validation.ok:
        for error in validation.errors:
            print(f"error: {error}", file=sys.stderr)
        return 2
    request = build_sync_request(args.bundle_dir, args.remote_host, args.remote_user, args.remote_path)
    if not args.execute:
        print("dry-run remote sync request is valid")
        print(" ".join(request.rsync_args))
        return 0
    for command in request.remote_commands[:3]:
        subprocess.run(("ssh", request.target, command), check=True)  # noqa: S603
    subprocess.run(request.rsync_args, check=True)  # noqa: S603
    for command in request.remote_commands[3:]:
        subprocess.run(("ssh", request.target, command), check=True)  # noqa: S603
    with tempfile.TemporaryDirectory(prefix="e09-ansible-remote-verify-") as verify_root:
        verify_dir = Path(verify_root) / "bundle"
        verify_dir.mkdir()
        subprocess.run(
            ("rsync", "-a", f"{request.target}:{request.remote_path}/", str(verify_dir) + "/"),
            check=True,
        )  # noqa: S603
        remote_validation = validate_local_bundle(verify_dir)
    comparison = compare_remote_summary(validation.summary, remote_validation.summary)
    if not remote_validation.ok or not comparison.ok:
        for error in (*remote_validation.errors, *comparison.errors):
            print(f"error: {error}", file=sys.stderr)
        return 3
    evidence = render_evidence(
        local_summary=validation.summary,
        remote_host=args.remote_host,
        remote_path=str(args.remote_path),
        backup_path=request.backup_path,
        remote_verified=comparison.ok,
        remote_file_count=int(comparison.summary["file_count"]) + 1 if comparison.summary else 0,
        source_commit=str(validation.summary.get("source_commit", "unknown")) if validation.summary else "unknown",
    )
    args.evidence.parent.mkdir(parents=True, exist_ok=True)
    args.evidence.write_text(evidence, encoding="utf-8")
    print(f"synced E09 Ansible bundle to {request.target}:{request.remote_path}")
    print(f"wrote evidence to {args.evidence}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

Set executable mode:

```bash
chmod +x deploy/kolla/scripts/sync-ansible-remote-bundle.py
```

- [ ] **Step 2: Run targeted tests**

Run:

```bash
UV_CACHE_DIR=/tmp/dawn-uv-cache UV_PYTHON_INSTALL_DIR=/tmp/dawn-uv-python UV_PROJECT_ENVIRONMENT=/tmp/dawn-e09-remote-sync-venv uv run --python 3.11 --project backend --extra dev pytest tests/test_e09_ansible_remote_sync.py -q
```

Expected: helper-related tests pass; committed docs test still fails until Task 3 creates evidence and
risk/traceability rows.

- [ ] **Step 3: Run Ruff**

Run:

```bash
UV_CACHE_DIR=/tmp/dawn-uv-cache UV_PYTHON_INSTALL_DIR=/tmp/dawn-uv-python UV_PROJECT_ENVIRONMENT=/tmp/dawn-e09-remote-sync-venv uv run --python 3.11 --project backend --extra dev ruff check tests/test_e09_ansible_remote_sync.py deploy/kolla/scripts/sync-ansible-remote-bundle.py
```

Expected: `All checks passed!`

- [ ] **Step 4: Commit helper**

Run:

```bash
git add deploy/kolla/scripts/sync-ansible-remote-bundle.py
git commit -m "deploy: add E09 ansible remote sync helper"
```

Expected: commit contains only the helper script.

## Task 3: Repository Docs And Evidence Contract

**Files:**
- Create: `docs/generated/e09-ansible-remote-sync.md`
- Create: `docs/execplans/E09-ansible-remote-sync.md`
- Modify: `docs/11_DKB_TRACEABILITY.md`
- Modify: `docs/generated/risk-register.md`

- [ ] **Step 1: Create initial evidence with dry-run state**

Generate a local bundle and render evidence without remote execution:

```bash
rm -rf /tmp/dawn-e09-ansible-remote-sync-bundle
deploy/kolla/scripts/export-ansible-bundle.py --output-dir /tmp/dawn-e09-ansible-remote-sync-bundle --evidence /tmp/dawn-e09-ansible-remote-sync-local.md
deploy/kolla/scripts/sync-ansible-remote-bundle.py --bundle-dir /tmp/dawn-e09-ansible-remote-sync-bundle --remote-host 192.168.10.15 --remote-path /etc/kolla/cloud-ui-sync-bundle
```

Expected: dry-run exits 0 and prints the rsync command shape without contacting the remote host.

Create `docs/generated/e09-ansible-remote-sync.md` from `render_evidence(...)` with
`remote_verified=false`, `remote_file_count=0`, backup path `not-created-yet`, and source commit from
the local bundle manifest. This file will be refreshed by Task 4 after the approved remote copy.

- [ ] **Step 2: Create ExecPlan**

Create `docs/execplans/E09-ansible-remote-sync.md`:

```markdown
# ExecPlan: E09 Ansible Remote Sync

## Цель и наблюдаемый результат

Copy the Cloud UI Ansible sync bundle to `192.168.10.15:/etc/kolla/cloud-ui-sync-bundle` and prove
that the remote host has the role, preflight playbook, example vars and manifest checksums. Before
this slice, E09 deployment smoke evidence recorded that the remote Cloud UI role/config was not found.

## Контекст и текущее состояние

The repository already contains `deploy/kolla/scripts/export-ansible-bundle.py` and
`docs/generated/e09-ansible-sync-bundle.md`. The approved test Ansible host is `192.168.10.15`.
The live deployment evidence in `docs/generated/e09-deployment-smoke-evidence.md` remains blocked by
missing remote role/config, DB/MQ auth failures, incomplete container topology and missing rollback.

## Scope

- Validate and copy the bundle to `/etc/kolla/cloud-ui-sync-bundle`.
- Record sanitized remote-sync evidence.
- Update DKB traceability and risk register.

## Non-goals

- No `kolla-ansible deploy`, `reconfigure`, `upgrade`, `destroy`, `pull`, `prechecks` or `check`.
- No DB/MQ/Vault/Keystone/OpenStack/container/HAProxy mutation.
- No runtime secret value copying.
- No full E09 acceptance claim.

## Требования и ограничения

Use only the approved test host `192.168.10.15` and approved target
`/etc/kolla/cloud-ui-sync-bundle`. Keep secrets out of Git and evidence. Rollback is path-scoped to
the previous bundle backup.

## Связь с ДКБ

- ДКБ-55/56: proves no runtime secret value is copied by this bundle; secret delivery and rotation
  remain external.
- ДКБ-65/69/70/76/77/80/82: creates operator deployment documentation and checksum evidence only.
  Live hardening, registry/signing, management ACL, live deployment and rollback remain pending.

## Milestones

1. RED tests and local helper.
2. Dry-run evidence and docs.
3. Approved remote copy and checksum verification.
4. Final verification and review.

## Progress

- [x] 2026-06-26: Design approved in `docs/superpowers/specs/2026-06-26-e09-ansible-remote-sync-design.md`.
- [x] Contract tests.
- [x] Remote sync helper.
- [x] Repository docs and dry-run evidence.
- [ ] Approved remote copy and sanitized evidence.
- [ ] Final verification and review.

## Неожиданные открытия

- None yet.

## Журнал решений

- 2026-06-26: Use `/etc/kolla/cloud-ui-sync-bundle` instead of installing into a Kolla role path.
  This keeps the slice remote-sync-only and avoids accidental live role activation.

## Детальный план реализации

Implementation details are in `docs/superpowers/plans/2026-06-26-e09-ansible-remote-sync.md`.

## Миграции и совместимость

No database or API migration. Remote replacement is a directory swap with a timestamped backup.

## Проверка

- `UV_CACHE_DIR=/tmp/dawn-uv-cache UV_PYTHON_INSTALL_DIR=/tmp/dawn-uv-python UV_PROJECT_ENVIRONMENT=/tmp/dawn-e09-remote-sync-venv uv run --python 3.11 --project backend --extra dev pytest tests/test_e09_ansible_remote_sync.py tests/test_e09_ansible_sync_bundle.py -q`
- `UV_CACHE_DIR=/tmp/dawn-uv-cache UV_PYTHON_INSTALL_DIR=/tmp/dawn-uv-python UV_PROJECT_ENVIRONMENT=/tmp/dawn-e09-remote-sync-venv uv run --python 3.11 --project backend --extra dev ruff check tests/test_e09_ansible_remote_sync.py deploy/kolla/scripts/sync-ansible-remote-bundle.py`
- `./scripts/secret-scan.sh`
- `git diff --check`

## Доказательства

- `docs/generated/e09-ansible-remote-sync.md`
- `docs/generated/risk-register.md`
- `docs/11_DKB_TRACEABILITY.md`

## Откат и восстановление

Restore the backup path recorded in `docs/generated/e09-ansible-remote-sync.md` to
`/etc/kolla/cloud-ui-sync-bundle`, or remove `/etc/kolla/cloud-ui-sync-bundle` if the evidence says no
previous bundle existed. Do not modify other Kolla paths.

## Итог и остаточные риски

Pending until implementation completes.
```

- [ ] **Step 3: Update DKB traceability**

Insert this section immediately before `## Полная матрица` in `docs/11_DKB_TRACEABILITY.md`:

```markdown
## E09 Ansible remote sync

Обновление требований 2026-06-26: E09 Ansible remote sync is remote-sync-only evidence for the
approved test Ansible host `192.168.10.15`. The bundle target is
`/etc/kolla/cloud-ui-sync-bundle`; role resolution for later approved actions is
`ANSIBLE_ROLES_PATH=/etc/kolla/cloud-ui-sync-bundle/roles`.

For ДКБ-55/56, this slice copies no runtime secret value and includes only placeholder example vars.
Secret delivery, rotation and DB/MQ auth remediation remain `pending_external_evidence`.

For ДКБ-65/69/70/76/77/80/82, this slice proves copied operator artifacts and checksums only. It does
not prove live reconfigure, migration, twelve containers, HAProxy/TLS, SELinux, rollback, registry
signing or ДКБ-69 waiver closure.

Evidence paths:

- `tests/test_e09_ansible_remote_sync.py`
- `deploy/kolla/scripts/sync-ansible-remote-bundle.py`
- `docs/generated/e09-ansible-remote-sync.md`
```

- [ ] **Step 4: Update risk register**

Append after `R-070`:

```markdown
| R-071 | E09 Ansible remote sync mistaken for live deployment evidence | The remote-sync-only bundle on `192.168.10.15:/etc/kolla/cloud-ui-sync-bundle` proves artifact delivery and checksum verification, but it does not run Kolla, repair DB/MQ auth, execute migration, inspect containers, validate HAProxy/TLS, prove SELinux or test rollback. | Keep live reconfigure, DB/MQ auth remediation, migration, twelve-container inspection, HAProxy/TLS, SELinux, registry/signing and rollback rows as `pending_external_evidence` until separately approved test-stand actions produce sanitized proof. | E09 |
```

- [ ] **Step 5: Run docs tests**

Run:

```bash
UV_CACHE_DIR=/tmp/dawn-uv-cache UV_PYTHON_INSTALL_DIR=/tmp/dawn-uv-python UV_PROJECT_ENVIRONMENT=/tmp/dawn-e09-remote-sync-venv uv run --python 3.11 --project backend --extra dev pytest tests/test_e09_ansible_remote_sync.py -q
```

Expected: all tests in the remote-sync file pass with dry-run evidence.

- [ ] **Step 6: Commit docs**

Run:

```bash
git add docs/generated/e09-ansible-remote-sync.md docs/execplans/E09-ansible-remote-sync.md docs/11_DKB_TRACEABILITY.md docs/generated/risk-register.md
git commit -m "docs: add E09 ansible remote sync evidence contract"
```

Expected: commit contains only docs/evidence files.

## Task 4: Approved Remote Copy And Evidence Refresh

**Files:**
- Modify: `docs/generated/e09-ansible-remote-sync.md`
- Modify: `docs/execplans/E09-ansible-remote-sync.md`

- [ ] **Step 1: Export local bundle**

Run:

```bash
rm -rf /tmp/dawn-e09-ansible-remote-sync-bundle
deploy/kolla/scripts/export-ansible-bundle.py --output-dir /tmp/dawn-e09-ansible-remote-sync-bundle --evidence /tmp/dawn-e09-ansible-remote-sync-local.md
```

Expected: exit 0 and `/tmp/dawn-e09-ansible-remote-sync-bundle/manifest.json` exists.

- [ ] **Step 2: Execute remote sync**

Run only after confirming the active user approval still applies:

```bash
deploy/kolla/scripts/sync-ansible-remote-bundle.py --bundle-dir /tmp/dawn-e09-ansible-remote-sync-bundle --remote-host 192.168.10.15 --remote-user root --remote-path /etc/kolla/cloud-ui-sync-bundle --evidence docs/generated/e09-ansible-remote-sync.md --execute
```

Expected: exit 0, remote path exists, evidence file refreshed. If SSH authentication fails, stop and
record the blocker without retrying with secrets in the command line or repository.

- [ ] **Step 3: Verify remote path read-only**

Run:

```bash
ssh root@192.168.10.15 'test -f /etc/kolla/cloud-ui-sync-bundle/manifest.json && test -d /etc/kolla/cloud-ui-sync-bundle/roles/cloud_ui && test -f /etc/kolla/cloud-ui-sync-bundle/playbooks/cloud-ui-preflight.yml && printf remote_bundle_present'
```

Expected: prints `remote_bundle_present`. Do not run Kolla commands.

- [ ] **Step 4: Update ExecPlan progress**

In `docs/execplans/E09-ansible-remote-sync.md`, mark approved remote copy complete and record the
sanitized command result. Keep final verification unchecked until Task 5.

- [ ] **Step 5: Run targeted tests**

Run:

```bash
UV_CACHE_DIR=/tmp/dawn-uv-cache UV_PYTHON_INSTALL_DIR=/tmp/dawn-uv-python UV_PROJECT_ENVIRONMENT=/tmp/dawn-e09-remote-sync-venv uv run --python 3.11 --project backend --extra dev pytest tests/test_e09_ansible_remote_sync.py tests/test_e09_ansible_sync_bundle.py -q
```

Expected: all selected tests pass.

- [ ] **Step 6: Commit refreshed evidence**

Run:

```bash
git add docs/generated/e09-ansible-remote-sync.md docs/execplans/E09-ansible-remote-sync.md
git commit -m "docs: record E09 ansible remote sync evidence"
```

Expected: commit contains only refreshed evidence and ExecPlan progress.

## Task 5: Final Verification And Review

**Files:**
- Modify: `docs/execplans/E09-ansible-remote-sync.md`

- [ ] **Step 1: Run final pytest**

Run:

```bash
UV_CACHE_DIR=/tmp/dawn-uv-cache UV_PYTHON_INSTALL_DIR=/tmp/dawn-uv-python UV_PROJECT_ENVIRONMENT=/tmp/dawn-e09-remote-sync-venv uv run --python 3.11 --project backend --extra dev pytest tests/test_e09_ansible_remote_sync.py tests/test_e09_ansible_sync_bundle.py tests/test_e09_deployment_smoke_evidence.py -q
```

Expected: all selected tests pass.

- [ ] **Step 2: Run Ruff**

Run:

```bash
UV_CACHE_DIR=/tmp/dawn-uv-cache UV_PYTHON_INSTALL_DIR=/tmp/dawn-uv-python UV_PROJECT_ENVIRONMENT=/tmp/dawn-e09-remote-sync-venv uv run --python 3.11 --project backend --extra dev ruff check tests/test_e09_ansible_remote_sync.py deploy/kolla/scripts/sync-ansible-remote-bundle.py
```

Expected: `All checks passed!`

- [ ] **Step 3: Run security scan and diff check**

Run:

```bash
./scripts/secret-scan.sh
git diff --check
```

Expected: both exit 0.

- [ ] **Step 4: Final reviewer**

Dispatch a final reviewer over `main...HEAD`. Required review focus:

- no live Kolla action was run or encoded;
- remote write is scoped to `/etc/kolla/cloud-ui-sync-bundle`;
- no secrets or credential files were committed;
- evidence does not overclaim E09 acceptance;
- rollback instructions are path-scoped.

- [ ] **Step 5: Close ExecPlan**

Mark `Final verification and review` complete in `docs/execplans/E09-ansible-remote-sync.md`.

- [ ] **Step 6: Commit close-out**

Run:

```bash
git add docs/execplans/E09-ansible-remote-sync.md
git commit -m "docs: close E09 ansible remote sync execplan"
```

Expected: commit contains only the ExecPlan checkbox/status update.

## Rollback

Repository rollback:

```bash
git revert --no-commit 6c085d4..HEAD
git commit -m "revert: E09 ansible remote sync"
```

Remote rollback, only if the remote sync executed:

```bash
ssh root@192.168.10.15 'if ls -d /etc/kolla/cloud-ui-sync-bundle.backup-* >/dev/null 2>&1; then latest=$(ls -dt /etc/kolla/cloud-ui-sync-bundle.backup-* | head -n 1); rm -rf /etc/kolla/cloud-ui-sync-bundle; mv "$latest" /etc/kolla/cloud-ui-sync-bundle; else rm -rf /etc/kolla/cloud-ui-sync-bundle; fi'
```

Do not run this rollback command automatically. Ask for explicit approval if rollback is needed.
