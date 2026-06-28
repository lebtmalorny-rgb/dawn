#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

try:
    import yaml
except ModuleNotFoundError:  # pragma: no cover - PyYAML is present with Ansible.
    yaml = None  # type: ignore[assignment]

ROOT = Path(__file__).resolve().parents[3]
GENERATED_DOCS = (ROOT / "docs/generated").resolve()

BUNDLE_SCHEMA_VERSION = "e09-ansible-sync-bundle/v1"
BUNDLE_SOURCES = (
    ("deploy/kolla/ansible/roles/cloud_ui", "roles/cloud_ui"),
    ("deploy/kolla/ansible/playbooks/cloud-ui-preflight.yml", "playbooks/cloud-ui-preflight.yml"),
    (
        "deploy/kolla/ansible/playbooks/cloud-ui-aio-reconfigure.yml",
        "playbooks/cloud-ui-aio-reconfigure.yml",
    ),
    ("deploy/kolla/ansible/examples/cloud-ui-vars.yml.example", "examples/cloud-ui-vars.yml.example"),
    (
        "deploy/kolla/ansible/examples/cloud-ui-aio-kolla-vars.yml.example",
        "examples/cloud-ui-aio-kolla-vars.yml.example",
    ),
)
ROLE_PATH_NOTE = "Set ANSIBLE_ROLES_PATH=roles or configure an equivalent Ansible roles path."

SAFE_SOURCE_COMMIT_RE = re.compile(r"^[A-Za-z0-9._/-]{1,128}$")
CREDENTIAL_URL_RE = re.compile(r"(?i)\b[a-z][a-z0-9+.-]*://[^/\s:@]+:[^@\s/]+@")
PEM_PRIVATE_KEY_RE = re.compile(
    r"(?is)-----BEGIN [A-Z ]*PRIVATE KEY-----.*?-----END [A-Z ]*PRIVATE KEY-----"
)
SECRET_ASSIGNMENT_RE = re.compile(
    r"(?i)\b(?:[A-Za-z0-9_-]+_)?(?:password|passwd|token|private[_-]?key|"
    r"application_credential(?:_secret)?)(?:_[A-Za-z0-9_-]+)?\s*[:=]\s*"
    r"(?:\"[^\"]+\"|'[^']+'|[^\n#]+)"
)
FORBIDDEN_CREDENTIAL_FILE_RE = re.compile(
    r"(?i)(?:clouds\.yaml|\bopenrc\b|(?<![A-Za-z0-9_-])\.env(?![A-Za-z0-9_.-]))"
)
MUTATING_KOLLA_RE = re.compile(
    r"(?is)\bkolla-ansible\b(?:(?!\n).)*\b(?:deploy|reconfigure|destroy|upgrade)\b"
)
TASK_SHELL_OR_COMMAND_RE = re.compile(
    r"(?im)^\s*(?:-\s*)?ansible\.builtin\.(?:shell|command)\s*:|"
    r"^\s*-\s*(?:shell|command)\s*:"
)
SHELL_OR_COMMAND_ACTIONS = {
    "ansible.builtin.command",
    "ansible.builtin.shell",
    "command",
    "shell",
}
PLAY_TASK_SECTIONS = ("tasks", "pre_tasks", "post_tasks", "handlers")
TASK_BLOCK_SECTIONS = ("block", "rescue", "always")


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
        try:
            path.resolve(strict=True).relative_to(GENERATED_DOCS)
        except (OSError, ValueError):
            return False
        return path.is_file()
    if path.parent.exists():
        try:
            path.parent.resolve(strict=True).relative_to(GENERATED_DOCS)
        except (OSError, ValueError):
            return False
    return True


def _output_dir_is_allowed(path: Path) -> bool:
    if path.is_symlink():
        return False
    if _path_is_inside(path, ROOT):
        return False
    try:
        resolved_parent = path.parent.resolve(strict=True)
    except OSError:
        return False
    if not resolved_parent.is_dir() or _path_is_inside(resolved_parent, ROOT):
        return False
    if path.exists() and not path.is_dir():
        return False
    return not (path.exists() and any(path.iterdir()))


def _bundle_relative_is_safe(path: Path) -> bool:
    return not path.is_absolute() and ".." not in path.parts


def _source_files() -> tuple[tuple[Path, Path], ...]:
    files: list[tuple[Path, Path]] = []
    for source_relative, bundle_relative in BUNDLE_SOURCES:
        source = ROOT / source_relative
        target = Path(bundle_relative)
        if source.is_file() or source.is_symlink():
            files.append((source, target))
            continue
        for item in sorted(source.rglob("*")):
            if item.is_file() or item.is_symlink():
                files.append((item, target / item.relative_to(source)))
    return tuple(files)


def _is_task_or_playbook_source(relative_path: Path) -> bool:
    parts = relative_path.parts
    if "playbooks" in parts:
        return True
    return "roles" in parts and "tasks" in parts


def _iter_task_dicts(value: Any) -> list[dict[str, Any]]:
    tasks: list[dict[str, Any]] = []
    if isinstance(value, list):
        for item in value:
            if isinstance(item, dict):
                tasks.extend(_iter_task_dicts(item))
        return tasks
    if not isinstance(value, dict):
        return tasks

    is_play = any(section in value for section in PLAY_TASK_SECTIONS) or "hosts" in value
    if is_play:
        for section in PLAY_TASK_SECTIONS:
            section_value = value.get(section)
            if isinstance(section_value, list):
                tasks.extend(_iter_task_dicts(section_value))
        return tasks

    tasks.append(value)
    for section in TASK_BLOCK_SECTIONS:
        section_value = value.get(section)
        if isinstance(section_value, list):
            tasks.extend(_iter_task_dicts(section_value))
    return tasks


def _has_shell_or_command_action(text: str) -> bool:
    if yaml is None:
        return TASK_SHELL_OR_COMMAND_RE.search(text) is not None
    try:
        documents = list(yaml.safe_load_all(text))
    except yaml.YAMLError:
        return TASK_SHELL_OR_COMMAND_RE.search(text) is not None

    for document in documents:
        for task in _iter_task_dicts(document):
            if any(str(key) in SHELL_OR_COMMAND_ACTIONS for key in task):
                return True
    return False


def _scan_text(relative_path: Path, text: str) -> tuple[str, ...]:
    errors: list[str] = []
    if (
        CREDENTIAL_URL_RE.search(text)
        or PEM_PRIVATE_KEY_RE.search(text)
        or SECRET_ASSIGNMENT_RE.search(text)
    ):
        errors.append(f"{relative_path}: secret-like value found")
    if FORBIDDEN_CREDENTIAL_FILE_RE.search(text):
        errors.append(f"{relative_path}: forbidden credential file reference found")
    if MUTATING_KOLLA_RE.search(text):
        errors.append(f"{relative_path}: live mutating Kolla command pattern found")
    elif _is_task_or_playbook_source(relative_path) and _has_shell_or_command_action(text):
        errors.append(f"{relative_path}: live mutating shell/command module pattern found")
    return tuple(errors)


def _validate_sources() -> ValidationResult:
    errors: list[str] = []
    for source_relative, bundle_relative in BUNDLE_SOURCES:
        source = ROOT / source_relative
        target = Path(bundle_relative)
        if source.is_symlink():
            errors.append(f"{source_relative}: symlink source is not allowed")
        elif not source.exists():
            errors.append(f"missing source path: {source_relative}")
        elif not _path_is_inside(source, ROOT):
            errors.append(f"{source_relative}: source path escapes repository")
        if not _bundle_relative_is_safe(target):
            errors.append(f"{bundle_relative}: bundle-relative path escapes output")

    for source, bundle_relative in _source_files():
        relative_source = source.relative_to(ROOT) if _path_is_inside(source, ROOT) else source
        if source.is_symlink():
            errors.append(f"{relative_source}: symlink source is not allowed")
            continue
        if not _path_is_inside(source, ROOT):
            errors.append(f"{source}: source path escapes repository")
            continue
        if "__pycache__" in source.parts or source.suffix == ".pyc":
            errors.append(f"{relative_source}: generated Python cache is not allowed")
            continue
        if not _bundle_relative_is_safe(bundle_relative):
            errors.append(f"{bundle_relative}: bundle-relative path escapes output")
            continue
        text = source.read_text(encoding="utf-8", errors="replace")
        errors.extend(_scan_text(relative_source, text))
    return ValidationResult(ok=not errors, errors=tuple(errors))


def _copy_sources(output_dir: Path) -> list[dict[str, object]]:
    manifest_files: list[dict[str, object]] = []
    output_dir.mkdir(parents=True, exist_ok=True)
    resolved_output = output_dir.resolve(strict=True)

    for source, bundle_relative in _source_files():
        if source.is_symlink() or not _bundle_relative_is_safe(bundle_relative):
            raise ValueError(f"unsafe source or bundle path: {bundle_relative}")
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
    return sorted(manifest_files, key=lambda item: str(item["path"]))


def _source_commit(explicit: str | None) -> str:
    if explicit is not None:
        return explicit
    try:
        completed = subprocess.run(  # noqa: S603,S607
            ["git", "rev-parse", "--short=12", "HEAD"],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return "unknown"
    return completed.stdout.strip() or "unknown"


def _validate_source_commit(value: str) -> tuple[str, ...]:
    if (
        not SAFE_SOURCE_COMMIT_RE.fullmatch(value)
        or value.startswith("/")
        or ".." in value
        or CREDENTIAL_URL_RE.search(value)
        or PEM_PRIVATE_KEY_RE.search(value)
        or SECRET_ASSIGNMENT_RE.search(value)
    ):
        return ("source_commit must be a safe token matching [A-Za-z0-9._/-]{1,128}",)
    return ()


def _write_json_atomic(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            "w",
            encoding="utf-8",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as temporary:
            json.dump(payload, temporary, indent=2, sort_keys=True)
            temporary.write("\n")
            temporary_path = Path(temporary.name)
        temporary_path.replace(path)
    except OSError:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)
        raise


def _write_text_atomic(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path: Path | None = None
    try:
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
    except OSError:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)
        raise


def _stage_text(path: Path, text: str) -> Path:
    temporary_path: Path | None = None
    try:
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
        return temporary_path
    except OSError:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)
        raise


def _create_staging_dir(output_dir: Path) -> Path:
    if not output_dir.parent.exists() or not output_dir.parent.is_dir():
        raise OSError(f"output parent does not exist or is not a directory: {output_dir.parent}")
    return Path(
        tempfile.mkdtemp(
            dir=output_dir.parent,
            prefix=f".{output_dir.name}.",
            suffix=".staging",
        )
    )


def _install_staged_output(staging_dir: Path, output_dir: Path) -> None:
    if not _output_dir_is_allowed(output_dir):
        raise OSError("output directory became unavailable or non-empty before export commit")
    staging_dir.replace(output_dir)


def _manifest_files(manifest: dict[str, object]) -> list[dict[str, Any]]:
    files = manifest.get("files")
    if not isinstance(files, list):
        return []
    return [item for item in files if isinstance(item, dict)]


def render_evidence(manifest: dict[str, object]) -> str:
    files = _manifest_files(manifest)
    file_rows = [
        f"| `{item['path']}` | {item['bytes']} | `{item['sha256']}` |"
        for item in files
    ]
    return "\n".join(
        [
            "# E09 Ansible sync bundle",
            "",
            "- Stage: E09 Ansible sync bundle",
            "- Scope: local-only export; remote sync remains separately approved",
            "- Live execution status: `pending_external_evidence`",
            f"- Source commit: `{manifest['source_commit']}`",
            f"- Bundle schema: `{manifest['schema_version']}`",
            "- runtime secret value: absent; DB/MQ URLs remain external runtime secret inputs",
            "",
            "## Bundle contents",
            "",
            "| Path | Bytes | SHA256 |",
            "|---|---:|---|",
            *file_rows,
            "",
            "## Operator note",
            "",
            ROLE_PATH_NOTE,
            "",
            "This local-only export does not itself copy the bundle to a host, run live mutating",
            "Kolla actions, remediate DB/MQ auth, inspect containers, validate HAProxy/TLS or",
            "execute rollback. Separate 2026-06-28 AIO role evidence is recorded in",
            "`docs/generated/e09-deployment-smoke-evidence.md`.",
            "",
            "## Remaining blockers",
            "",
            "- remote sync remains separately approved for each target stand;",
            "- DB/MQ auth remediation remains `pending_external_evidence` for new stands;",
            "- upstream Kolla `site.yml`/tag integration, 12-container inspection, HAProxy/TLS,",
            "  SELinux and failed-update rollback remain pending.",
            "",
        ]
    )


def export_bundle(
    output_dir: Path,
    evidence_path: Path,
    source_commit: str | None = None,
) -> ValidationResult:
    errors: list[str] = []
    commit = _source_commit(source_commit)
    errors.extend(_validate_source_commit(commit))
    if not _output_dir_is_allowed(output_dir):
        errors.append("output directory must be outside repository, not a symlink, and empty")
    if not _evidence_path_is_allowed(evidence_path):
        errors.append("evidence path must stay under docs/generated without symlink escape")

    source_validation = _validate_sources()
    errors.extend(source_validation.errors)
    if errors:
        return ValidationResult(ok=False, errors=tuple(errors))

    staging_dir: Path | None = None
    evidence_temporary_path: Path | None = None
    final_output_installed = False
    try:
        staging_dir = _create_staging_dir(output_dir)
        manifest_files = _copy_sources(staging_dir)
        manifest: dict[str, object] = {
            "schema_version": BUNDLE_SCHEMA_VERSION,
            "source_commit": commit,
            "generated_at_utc": datetime.now(UTC).replace(microsecond=0).isoformat(),
            "role_path_note": ROLE_PATH_NOTE,
            "files": manifest_files,
        }
        _write_json_atomic(staging_dir / "manifest.json", manifest)
        evidence_temporary_path = _stage_text(evidence_path, render_evidence(manifest))
        _install_staged_output(staging_dir, output_dir)
        staging_dir = None
        final_output_installed = True
        evidence_temporary_path.replace(evidence_path)
        evidence_temporary_path = None
    except (OSError, ValueError) as exc:
        if final_output_installed:
            shutil.rmtree(output_dir, ignore_errors=True)
        return ValidationResult(ok=False, errors=(f"failed to export bundle: {exc}",))
    finally:
        if staging_dir is not None:
            shutil.rmtree(staging_dir, ignore_errors=True)
        if evidence_temporary_path is not None:
            evidence_temporary_path.unlink(missing_ok=True)

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
