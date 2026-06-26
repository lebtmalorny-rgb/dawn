#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shlex
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
DEFAULT_EVIDENCE_PATH = ROOT / "docs/generated/e09-ansible-remote-sync.md"

BUNDLE_SCHEMA_VERSION = "e09-ansible-sync-bundle/v1"
APPROVED_REMOTE_HOST = "192.168.10.15"
APPROVED_REMOTE_PATH = "/etc/kolla/cloud-ui-sync-bundle"
ROLE_PATH_NOTE = f"ANSIBLE_ROLES_PATH={APPROVED_REMOTE_PATH}/roles"

TIMESTAMP_RE = re.compile(r"^\d{8}T\d{6}Z$")
SAFE_REMOTE_USER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_-]{0,63}$")
SAFE_EVIDENCE_TEXT_RE = re.compile(r"^[A-Za-z0-9._:/@+-]{1,160}$")
SHA256_RE = re.compile(r"^[a-f0-9]{64}$")

FORBIDDEN_REMOTE_COMMAND_FRAGMENTS = (
    "kolla-ansible",
    "/usr/share/kolla-ansible",
    "reconfigure",
)
FORBIDDEN_BUNDLE_FILENAMES = {
    ".env",
    "clouds.yaml",
    "openrc",
}
REQUIRED_BUNDLE_PATHS = {
    "manifest.json",
    "roles/cloud_ui/defaults/main.yml",
    "roles/cloud_ui/tasks/main.yml",
    "roles/cloud_ui/templates/cloud-ui-backend.env.j2",
    "playbooks/cloud-ui-preflight.yml",
    "examples/cloud-ui-vars.yml.example",
}


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


def _path_is_inside(child: Path, parent: Path) -> bool:
    try:
        child.resolve(strict=False).relative_to(parent.resolve(strict=False))
    except (OSError, ValueError):
        return False
    return True


def _bundle_relative_is_safe(value: str) -> bool:
    if not value or "\x00" in value or "\\" in value:
        return False
    relative = PurePosixPath(value)
    return not relative.is_absolute() and ".." not in relative.parts and "." not in relative.parts


def _bundle_child(bundle_root: Path, relative_value: str) -> Path:
    return bundle_root.joinpath(*PurePosixPath(relative_value).parts)


def _is_forbidden_bundle_filename(relative_value: str) -> bool:
    return any(part.lower() in FORBIDDEN_BUNDLE_FILENAMES for part in PurePosixPath(relative_value).parts)


def _read_manifest(manifest_path: Path) -> tuple[dict[str, Any] | None, tuple[str, ...]]:
    try:
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return None, (f"manifest.json could not be read as JSON: {exc}",)
    if not isinstance(payload, dict):
        return None, ("manifest.json must contain a JSON object",)
    return payload, ()


def _manifest_file_entries(manifest: dict[str, Any]) -> tuple[list[dict[str, Any]], tuple[str, ...]]:
    files = manifest.get("files")
    if not isinstance(files, list):
        return [], ("manifest files must be a list",)
    entries: list[dict[str, Any]] = []
    errors: list[str] = []
    for index, item in enumerate(files):
        if isinstance(item, dict):
            entries.append(item)
        else:
            errors.append(f"manifest file entry {index} must be an object")
    return entries, tuple(errors)


def _actual_bundle_files(bundle_root: Path) -> tuple[set[str], tuple[str, ...]]:
    actual_paths: set[str] = set()
    errors: list[str] = []
    try:
        candidates = sorted(bundle_root.rglob("*"))
    except OSError as exc:
        return actual_paths, (f"bundle directory could not be scanned: {exc}",)

    for candidate in candidates:
        try:
            relative_path = candidate.relative_to(bundle_root).as_posix()
        except ValueError:
            errors.append(f"{candidate}: bundle scan escaped bundle root")
            continue
        if candidate.is_symlink():
            errors.append(f"{relative_path}: symlink bundle file is forbidden")
            continue
        if candidate.is_file():
            actual_paths.add(relative_path)
    return actual_paths, tuple(errors)


def _validate_manifest_file(
    *,
    bundle_root: Path,
    item: dict[str, Any],
    index: int,
    seen_paths: set[str],
) -> tuple[dict[str, Any] | None, tuple[str, ...]]:
    errors: list[str] = []
    relative_value = item.get("path")
    manifest_sha = item.get("sha256")
    manifest_bytes = item.get("bytes")

    if not isinstance(relative_value, str):
        return None, (f"manifest file entry {index} path must be a string",)
    if not _bundle_relative_is_safe(relative_value):
        return None, (f"{relative_value}: unsafe manifest path traversal or bundle escape forbidden",)
    if _is_forbidden_bundle_filename(relative_value):
        errors.append(f"{relative_value}: forbidden credential bundle filename")
    if relative_value in seen_paths:
        errors.append(f"{relative_value}: duplicate manifest path")
    seen_paths.add(relative_value)

    if not isinstance(manifest_sha, str) or not SHA256_RE.fullmatch(manifest_sha):
        errors.append(f"{relative_value}: manifest sha256 must be a lowercase 64-character hex digest")
    if isinstance(manifest_bytes, bool) or not isinstance(manifest_bytes, int) or manifest_bytes < 0:
        errors.append(f"{relative_value}: manifest byte size must be a non-negative integer")

    bundle_file = _bundle_child(bundle_root, relative_value)
    if not _path_is_inside(bundle_file, bundle_root):
        return None, (f"{relative_value}: unsafe manifest path escape forbidden",)
    if bundle_file.is_symlink():
        errors.append(f"{relative_value}: symlink bundle file is forbidden")
    if not bundle_file.is_file():
        errors.append(f"{relative_value}: manifest-listed file is missing")
        return None, tuple(errors)

    try:
        data = bundle_file.read_bytes()
    except OSError as exc:
        errors.append(f"{relative_value}: could not read bundle file: {exc}")
        return None, tuple(errors)

    actual_bytes = len(data)
    actual_sha = hashlib.sha256(data).hexdigest()
    if isinstance(manifest_bytes, int) and not isinstance(manifest_bytes, bool):
        if actual_bytes != manifest_bytes:
            errors.append(
                f"{relative_value}: byte size mismatch, manifest has {manifest_bytes}, "
                f"actual file has {actual_bytes}"
            )
    if isinstance(manifest_sha, str) and actual_sha != manifest_sha:
        errors.append(f"{relative_value}: sha256 mismatch, manifest has {manifest_sha}, actual file has {actual_sha}")

    return (
        {
            "path": relative_value,
            "sha256": actual_sha,
            "bytes": actual_bytes,
        },
        tuple(errors),
    )


def validate_local_bundle(bundle_dir: Path) -> ValidationResult:
    errors: list[str] = []
    bundle_root = bundle_dir.resolve(strict=False)
    if bundle_dir.is_symlink():
        errors.append("bundle directory symlink is forbidden")
    if not bundle_dir.is_dir():
        return ValidationResult(ok=False, errors=tuple(errors + ["bundle directory does not exist"]))

    manifest_path = bundle_dir / "manifest.json"
    if manifest_path.is_symlink():
        errors.append("manifest.json symlink is forbidden")
    if not manifest_path.is_file():
        return ValidationResult(ok=False, errors=tuple(errors + ["manifest.json is missing"]))

    manifest, manifest_errors = _read_manifest(manifest_path)
    errors.extend(manifest_errors)
    if manifest is None:
        return ValidationResult(ok=False, errors=tuple(errors))

    if manifest.get("schema_version") != BUNDLE_SCHEMA_VERSION:
        errors.append(f"manifest schema_version must be {BUNDLE_SCHEMA_VERSION}")

    entries, entry_errors = _manifest_file_entries(manifest)
    errors.extend(entry_errors)
    seen_paths: set[str] = set()
    summary_files: list[dict[str, Any]] = []
    for index, item in enumerate(entries):
        summary_file, file_errors = _validate_manifest_file(
            bundle_root=bundle_root,
            item=item,
            index=index,
            seen_paths=seen_paths,
        )
        errors.extend(file_errors)
        if summary_file is not None:
            summary_files.append(summary_file)

    actual_paths, scan_errors = _actual_bundle_files(bundle_root)
    errors.extend(scan_errors)
    expected_paths = set(seen_paths)
    expected_paths.add("manifest.json")
    for relative_path in sorted(REQUIRED_BUNDLE_PATHS - expected_paths):
        errors.append(f"{relative_path}: required bundle artifact missing")
    for relative_path in sorted(actual_paths - expected_paths):
        if _is_forbidden_bundle_filename(relative_path):
            errors.append(f"{relative_path}: forbidden credential bundle filename")
        errors.append(f"{relative_path}: unmanifested extra bundle file")

    summary = {
        "schema_version": manifest.get("schema_version"),
        "source_commit": manifest.get("source_commit", "unknown"),
        "role_path_note": manifest.get("role_path_note", ""),
        "file_count": len(summary_files),
        "files": sorted(summary_files, key=lambda item: str(item["path"])),
        "paths": sorted(expected_paths),
    }
    return ValidationResult(ok=not errors, errors=tuple(errors), summary=summary if not errors else None)


def _remote_path_text(remote_path: Path | str) -> str:
    if isinstance(remote_path, Path):
        return remote_path.as_posix()
    return str(remote_path)


def validate_sync_request(
    *,
    bundle_dir: Path,
    remote_host: str,
    remote_path: Path | str,
) -> ValidationResult:
    local_result = validate_local_bundle(bundle_dir)
    errors = list(local_result.errors)
    if remote_host != APPROVED_REMOTE_HOST:
        errors.append(f"remote host must match approved host {APPROVED_REMOTE_HOST}")
    if _remote_path_text(remote_path) != APPROVED_REMOTE_PATH:
        errors.append(f"remote path must match approved remote path {APPROVED_REMOTE_PATH}")
    return ValidationResult(ok=not errors, errors=tuple(errors), summary=local_result.summary)


def _timestamp() -> str:
    return datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")


def _quote_remote(value: str) -> str:
    return "'" + value.replace("'", "'\"'\"'") + "'"


def _validate_remote_user(remote_user: str) -> None:
    if not SAFE_REMOTE_USER_RE.fullmatch(remote_user):
        raise ValueError("remote user must be a safe account name")


def _validate_timestamp(value: str) -> None:
    if not TIMESTAMP_RE.fullmatch(value):
        raise ValueError("timestamp must match YYYYMMDDTHHMMSSZ")


def _ensure_remote_commands_are_limited(commands: tuple[str, ...]) -> None:
    joined = "\n".join(commands).lower()
    for fragment in FORBIDDEN_REMOTE_COMMAND_FRAGMENTS:
        if fragment in joined:
            raise ValueError(f"remote command contains forbidden fragment: {fragment}")


def build_sync_request(
    *,
    bundle_dir: Path,
    remote_host: str,
    remote_user: str,
    remote_path: Path | str,
    timestamp: str | None = None,
) -> SyncRequest:
    validation = validate_sync_request(
        bundle_dir=bundle_dir,
        remote_host=remote_host,
        remote_path=remote_path,
    )
    if not validation.ok:
        raise ValueError("; ".join(validation.errors))
    _validate_remote_user(remote_user)

    stamp = _timestamp() if timestamp is None else timestamp
    _validate_timestamp(stamp)
    remote_path_value = _remote_path_text(remote_path)
    remote_root = PurePosixPath(remote_path_value)
    parent = remote_root.parent.as_posix()
    name = remote_root.name
    staging_path = f"{parent}/.{name}.{stamp}.staging"
    backup_path = f"{remote_path_value}.backup-{stamp}"
    target = f"{remote_user}@{remote_host}"
    remote_commands = (
        f"mkdir -p {_quote_remote(parent)}",
        f"rm -rf {_quote_remote(staging_path)}",
        f"mkdir -p {_quote_remote(staging_path)}",
        f"if [ -e {_quote_remote(remote_path_value)} ]; then mv "
        f"{_quote_remote(remote_path_value)} {_quote_remote(backup_path)}; fi",
        f"mv {_quote_remote(staging_path)} {_quote_remote(remote_path_value)}",
    )
    _ensure_remote_commands_are_limited(remote_commands)
    return SyncRequest(
        target=target,
        remote_path=remote_path_value,
        staging_path=staging_path,
        backup_path=backup_path,
        rsync_args=(
            "rsync",
            "-a",
            "--delete",
            str(bundle_dir.resolve()) + "/",
            f"{target}:{staging_path}/",
        ),
        remote_commands=remote_commands,
    )


def _summary_file_map(summary: dict[str, Any], label: str) -> tuple[dict[str, dict[str, Any]], tuple[str, ...]]:
    errors: list[str] = []
    files = summary.get("files")
    if not isinstance(files, list):
        return {}, (f"{label} summary files must be a list",)
    mapped: dict[str, dict[str, Any]] = {}
    for index, item in enumerate(files):
        if not isinstance(item, dict):
            errors.append(f"{label} summary file entry {index} must be an object")
            continue
        path = item.get("path")
        sha = item.get("sha256")
        byte_count = item.get("bytes")
        if not isinstance(path, str) or not _bundle_relative_is_safe(path):
            errors.append(f"{label} summary file entry {index} has unsafe path")
            continue
        if not isinstance(sha, str):
            errors.append(f"{label} summary {path} sha256 must be a string")
            continue
        if isinstance(byte_count, bool) or not isinstance(byte_count, int):
            errors.append(f"{label} summary {path} bytes must be an integer")
            continue
        mapped[path] = {"sha256": sha, "bytes": byte_count}
    return mapped, tuple(errors)


def compare_remote_summary(
    local_summary: dict[str, Any] | None,
    remote_summary: dict[str, Any] | None,
) -> ValidationResult:
    errors: list[str] = []
    if not isinstance(local_summary, dict):
        return ValidationResult(ok=False, errors=("local summary is missing",))
    if not isinstance(remote_summary, dict):
        return ValidationResult(ok=False, errors=("remote summary is missing",))

    local_files, local_errors = _summary_file_map(local_summary, "local")
    remote_files, remote_errors = _summary_file_map(remote_summary, "remote")
    errors.extend(local_errors)
    errors.extend(remote_errors)
    local_paths = set(local_files)
    remote_paths = set(remote_files)
    if local_paths != remote_paths:
        missing = ", ".join(sorted(local_paths - remote_paths)) or "none"
        extra = ", ".join(sorted(remote_paths - local_paths)) or "none"
        errors.append(f"remote file set mismatch: missing={missing}; extra={extra}")

    for relative_path in sorted(local_paths & remote_paths):
        local_file = local_files[relative_path]
        remote_file = remote_files[relative_path]
        if local_file["sha256"] != remote_file["sha256"]:
            errors.append(
                f"{relative_path}: remote sha256 mismatch, local has {local_file['sha256']}, "
                f"remote has {remote_file['sha256']}"
            )
        if local_file["bytes"] != remote_file["bytes"]:
            errors.append(
                f"{relative_path}: remote byte size mismatch, local has {local_file['bytes']}, "
                f"remote has {remote_file['bytes']}"
            )
    return ValidationResult(ok=not errors, errors=tuple(errors), summary=remote_summary if not errors else None)


def _safe_evidence_text(value: object) -> str:
    text = str(value)
    if not SAFE_EVIDENCE_TEXT_RE.fullmatch(text):
        return "redacted"
    if "password" in text.lower():
        return "redacted"
    return text


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
    files: list[dict[str, Any]] = []
    local_file_count = 0
    if isinstance(local_summary, dict):
        local_file_count = int(local_summary.get("file_count", 0))
        summary_files = local_summary.get("files", [])
        if isinstance(summary_files, list):
            files = [item for item in summary_files if isinstance(item, dict)]

    file_rows = [
        f"| `{item['path']}` | {item['bytes']} | `{item['sha256']}` |"
        for item in sorted(files, key=lambda entry: str(entry["path"]))
    ]
    if not file_rows:
        file_rows = ["| none | 0 | none |"]

    remote_status = "yes" if remote_verified else "no"
    return "\n".join(
        [
            "# E09 Ansible remote sync",
            "",
            "- Stage: E09 Ansible remote sync",
            "- Scope: remote-sync-only helper for the approved test host; no live deployment claim",
            f"- Approved host: `{remote_host}`",
            f"- Approved remote path: `{remote_path}`",
            f"- Role path note: `{ROLE_PATH_NOTE}`",
            f"- Backup path: `{backup_path}`",
            f"- Remote sync command status: `{remote_status}`",
            f"- Local manifest file count: {local_file_count}",
            f"- Remote path file count: {remote_file_count}",
            f"- Source commit: `{_safe_evidence_text(source_commit)}`",
            "- runtime secret value: not included in bundle or evidence",
            "",
            "## Bundle contents",
            "",
            "| Path | Bytes | SHA256 |",
            "|---|---:|---|",
            *file_rows,
            "",
            "## Remaining external evidence",
            "",
            "- live reconfigure remains `pending_external_evidence`.",
            "- DB/MQ auth remediation remains `pending_external_evidence`.",
            "- migration remains `pending_external_evidence`.",
            "- 12-container inspection remains `pending_external_evidence`.",
            "- HAProxy/TLS remains `pending_external_evidence`.",
            "- SELinux hardening remains `pending_external_evidence`.",
            "- rollback remains `pending_external_evidence`.",
            "- production deployment is out of scope for this remote-sync-only helper.",
            "",
        ]
    )


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


def execute_sync_request(request: SyncRequest) -> None:
    for command in request.remote_commands[:3]:
        subprocess.run(("ssh", request.target, command), check=True)  # noqa: S603,S607
    subprocess.run(request.rsync_args, check=True)  # noqa: S603
    for command in request.remote_commands[3:]:
        subprocess.run(("ssh", request.target, command), check=True)  # noqa: S603,S607


def pull_remote_bundle_for_verification(request: SyncRequest, verify_dir: Path) -> None:
    subprocess.run(  # noqa: S603
        (
            "rsync",
            "-a",
            f"{request.target}:{request.remote_path}/",
            str(verify_dir) + "/",
        ),
        check=True,
    )


def _summary_path_count(summary: dict[str, Any] | None) -> int:
    if not isinstance(summary, dict):
        return 0
    paths = summary.get("paths")
    if isinstance(paths, list):
        return len(paths)
    files = summary.get("files")
    if isinstance(files, list):
        return len(files)
    return 0


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate and optionally sync the E09 Ansible bundle to the approved test host."
    )
    parser.add_argument("bundle_dir", nargs="?", type=Path)
    parser.add_argument("--bundle-dir", dest="bundle_dir_option", type=Path)
    parser.add_argument("--remote-host", default=APPROVED_REMOTE_HOST)
    parser.add_argument("--remote-user", default="root")
    parser.add_argument("--remote-path", default=Path(APPROVED_REMOTE_PATH), type=Path)
    parser.add_argument("--timestamp", default=None)
    parser.add_argument("--evidence", default=DEFAULT_EVIDENCE_PATH, type=Path)
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Run ssh/rsync and write evidence. Without this flag the command is a dry run.",
    )
    args = parser.parse_args(argv)
    if args.bundle_dir is not None and args.bundle_dir_option is not None:
        parser.error("pass either positional bundle_dir or --bundle-dir, not both")
    args.bundle_dir = args.bundle_dir if args.bundle_dir is not None else args.bundle_dir_option
    delattr(args, "bundle_dir_option")
    if args.bundle_dir is None:
        parser.error("bundle directory is required; pass --bundle-dir or positional bundle_dir")
    return args


def _print_errors(errors: tuple[str, ...]) -> None:
    for error in errors:
        print(f"error: {error}", file=sys.stderr)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    validation = validate_sync_request(
        bundle_dir=args.bundle_dir,
        remote_host=args.remote_host,
        remote_path=args.remote_path,
    )
    if not validation.ok:
        _print_errors(validation.errors)
        return 2

    try:
        request = build_sync_request(
            bundle_dir=args.bundle_dir,
            remote_host=args.remote_host,
            remote_user=args.remote_user,
            remote_path=args.remote_path,
            timestamp=args.timestamp,
        )
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    if not args.execute:
        print("dry-run: remote-sync-only request validated; no SSH or rsync command was executed")
        print(f"target: {request.target}")
        print(f"remote_path: {request.remote_path}")
        print(f"staging_path: {request.staging_path}")
        print(f"backup_path: {request.backup_path}")
        print(f"rsync_args: {shlex.join(request.rsync_args)}")
        for command in request.remote_commands:
            print(f"remote_command: {shlex.join(('ssh', request.target, command))}")
        return 0

    try:
        execute_sync_request(request)
    except (OSError, subprocess.CalledProcessError) as exc:
        print(f"error: remote sync failed: {exc}", file=sys.stderr)
        return 1

    local_summary = validation.summary
    source_commit = "unknown"
    if isinstance(local_summary, dict):
        source_commit = str(local_summary.get("source_commit", "unknown"))
    with tempfile.TemporaryDirectory(prefix="cloud-ui-sync-verify-") as temporary_dir:
        verify_dir = Path(temporary_dir)
        try:
            pull_remote_bundle_for_verification(request, verify_dir)
        except (OSError, subprocess.CalledProcessError) as exc:
            print(f"error: remote verification pullback failed: {exc}", file=sys.stderr)
            return 3
        remote_validation = validate_local_bundle(verify_dir)
        if not remote_validation.ok:
            _print_errors(tuple(f"remote verification: {error}" for error in remote_validation.errors))
            return 3
        comparison = compare_remote_summary(local_summary, remote_validation.summary)
        if not comparison.ok:
            _print_errors(comparison.errors)
            return 3

    evidence = render_evidence(
        local_summary=local_summary,
        remote_host=args.remote_host,
        remote_path=request.remote_path,
        backup_path=request.backup_path,
        remote_verified=comparison.ok,
        remote_file_count=_summary_path_count(remote_validation.summary),
        source_commit=source_commit,
    )
    try:
        _write_text_atomic(args.evidence, evidence)
    except OSError as exc:
        print(f"error: evidence write failed: {exc}", file=sys.stderr)
        return 1
    print(f"synced E09 Ansible bundle to {request.target}:{request.remote_path}")
    print(f"wrote evidence to {args.evidence}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
