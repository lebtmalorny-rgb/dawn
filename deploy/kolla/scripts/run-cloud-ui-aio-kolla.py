#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import re
import shlex
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

ALLOWED_MODES = frozenset({"preflight", "reconfigure", "reconfigure-no-migration"})
PRODUCTION_RE = re.compile(
    r"(?i)(?:^|[^a-z0-9])(?:production|prd[a-z0-9]*|prod(?!uct|ucer)[a-z0-9]*)"
    r"(?:$|[^a-z0-9])"
)
TEST_MARKER_RE = re.compile(
    r"(?m)^\s*cloud_ui_test_stand\s*(?:=|:)\s*true\s*$",
    re.IGNORECASE,
)
DIGEST_RE = re.compile(r"^sha256:[a-f0-9]{64}$")


@dataclass(frozen=True)
class ValidationResult:
    ok: bool
    errors: tuple[str, ...]


@dataclass(frozen=True)
class InvocationConfig:
    mode: str
    inventory: Path
    bundle_dir: Path
    runtime_vars: Path
    registry: str
    backend_digest: str
    frontend_digest: str
    kolla_ansible: Path
    rollback_window_open: bool


@dataclass(frozen=True)
class InvocationPlan:
    argv: list[str]
    env: dict[str, str]
    redacted_command: str


def _path_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def validate_config(config: InvocationConfig) -> ValidationResult:
    errors: list[str] = []
    inventory_text = _path_text(config.inventory)

    if config.mode not in ALLOWED_MODES:
        errors.append("mode must be one of preflight, reconfigure or reconfigure-no-migration")
    if not config.inventory.is_file():
        errors.append("inventory path must be an existing file")
    if PRODUCTION_RE.search(f"{config.inventory}\n{inventory_text}"):
        errors.append("inventory path or content looks like production")
    if not TEST_MARKER_RE.search(inventory_text):
        errors.append("inventory is missing cloud_ui_test_stand=true")
    if not config.bundle_dir.is_dir():
        errors.append("bundle directory must exist")
    if not (config.bundle_dir / "roles").is_dir():
        errors.append("bundle roles directory must exist")
    if not (config.bundle_dir / "playbooks/cloud-ui-aio-reconfigure.yml").is_file():
        errors.append("AIO reconfigure playbook is missing from bundle")
    if not (config.bundle_dir / "playbooks/cloud-ui-preflight.yml").is_file():
        errors.append("preflight playbook is missing from bundle")
    if not config.runtime_vars.is_file():
        errors.append("runtime vars path must be an existing file")
    if PRODUCTION_RE.search(config.registry):
        errors.append("registry looks like production")
    if not DIGEST_RE.fullmatch(config.backend_digest):
        errors.append("backend digest must be sha256:<64 lowercase hex chars>")
    if not DIGEST_RE.fullmatch(config.frontend_digest):
        errors.append("frontend digest must be sha256:<64 lowercase hex chars>")
    if not config.rollback_window_open:
        errors.append("rollback window must be explicitly open")

    return ValidationResult(ok=not errors, errors=tuple(errors))


def _playbook_for_mode(config: InvocationConfig) -> Path:
    if config.mode == "preflight":
        return config.bundle_dir / "playbooks/cloud-ui-preflight.yml"
    return config.bundle_dir / "playbooks/cloud-ui-aio-reconfigure.yml"


def build_invocation(config: InvocationConfig) -> InvocationPlan:
    validation = validate_config(config)
    if not validation.ok:
        raise ValueError("; ".join(validation.errors))

    argv = [
        str(config.kolla_ansible),
        "reconfigure",
        "-i",
        str(config.inventory),
        "-p",
        str(_playbook_for_mode(config)),
        "-t",
        "cloud-ui",
        "-e",
        f"@{config.runtime_vars}",
        "-e",
        "cloud_ui_test_stand=true",
        "-e",
        "cloud_ui_rollback_window_open=true",
        "-e",
        f"cloud_ui_registry={config.registry}",
        "-e",
        f"cloud_ui_backend_image_digest={config.backend_digest}",
        "-e",
        f"cloud_ui_frontend_image_digest={config.frontend_digest}",
    ]
    if config.mode == "reconfigure-no-migration":
        argv.extend(["-e", "cloud_ui_aio_run_migration=false"])

    kolla_bin_dir = str(config.kolla_ansible.parent)
    current_path = os.environ.get("PATH", "")
    path = kolla_bin_dir if not current_path else f"{kolla_bin_dir}:{current_path}"

    return InvocationPlan(
        argv=argv,
        env={
            "ANSIBLE_ROLES_PATH": str(config.bundle_dir / "roles"),
            "PATH": path,
        },
        redacted_command=shlex.join(argv),
    )


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run Cloud UI all-in-one through kolla-ansible custom playbooks."
    )
    parser.add_argument("mode", choices=sorted(ALLOWED_MODES))
    parser.add_argument("--inventory", required=True, type=Path)
    parser.add_argument("--bundle-dir", required=True, type=Path)
    parser.add_argument("--runtime-vars", required=True, type=Path)
    parser.add_argument("--registry", required=True)
    parser.add_argument("--backend-digest", required=True)
    parser.add_argument("--frontend-digest", required=True)
    parser.add_argument("--kolla-ansible", default=Path("kolla-ansible"), type=Path)
    parser.add_argument("--rollback-window-open", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args(argv)


def config_from_args(args: argparse.Namespace) -> InvocationConfig:
    return InvocationConfig(
        mode=args.mode,
        inventory=args.inventory,
        bundle_dir=args.bundle_dir,
        runtime_vars=args.runtime_vars,
        registry=args.registry,
        backend_digest=args.backend_digest,
        frontend_digest=args.frontend_digest,
        kolla_ansible=args.kolla_ansible,
        rollback_window_open=args.rollback_window_open,
    )


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    config = config_from_args(args)
    validation = validate_config(config)
    if not validation.ok:
        for error in validation.errors:
            print(f"error: {error}", file=sys.stderr)
        return 2

    plan = build_invocation(config)
    print(plan.redacted_command)
    if args.dry_run:
        return 0

    env = os.environ.copy()
    env.update(plan.env)
    completed = subprocess.run(plan.argv, env=env, check=False)  # noqa: S603
    return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main())
