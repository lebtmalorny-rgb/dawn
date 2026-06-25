#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
GENERATED_DOCS = (ROOT / "docs/generated").resolve()

DIGEST_RE = re.compile(
    r"^[A-Za-z0-9._-]+(?::[0-9]+)?(?:/[A-Za-z0-9._-]+)+@sha256:[a-fA-F0-9]{64}$"
)
PRODUCTION_RE = re.compile(
    r"(?i)(?:^|[^a-z0-9])(?:production|prd[a-z0-9]*|prod(?!uct)[a-z0-9]*)"
    r"(?:$|[^a-z0-9])"
)
TEST_MARKER_RE = re.compile(
    r"(?m)^\s*cloud_ui_test_stand\s*(?:=|:)\s*true\s*$",
    re.IGNORECASE,
)
JSON_SECRET_RE = re.compile(
    r"(?i)([\"']?[A-Za-z0-9_-]*(?:password|passwd|token|secret|private[_-]?key|"
    r"application_credential(?:_secret)?)[A-Za-z0-9_-]*[\"']?\s*:\s*)([\"'])(.*?)(\2)"
)
ASSIGNMENT_SECRET_RE = re.compile(
    r"(?i)\b([A-Za-z0-9_-]*(?:password|passwd|token|secret|private[_-]?key|"
    r"application_credential(?:_secret)?)[A-Za-z0-9_-]*)(\s*[:=]\s*)"
    r"(?:\"[^\"]*\"|'[^']*'|[^\n|`]+)"
)
AUTHORIZATION_BEARER_RE = re.compile(
    r"(?i)\b(authorization\s*:\s*bearer\s+)[^\s,|`]+"
)
SENSITIVE_KEY_RE = re.compile(
    r"(?i)(password|passwd|token|secret|private[_-]?key|application_credential)"
)
CREDENTIAL_URL_RE = re.compile(
    r"(?i)\b([a-z][a-z0-9+.-]*://[^/\s:@]+:)([^@\s/]+)(@)"
)
PEM_PRIVATE_KEY_RE = re.compile(
    r"(?is)-----BEGIN [A-Z ]*PRIVATE KEY-----.*?-----END [A-Z ]*PRIVATE KEY-----"
)
COOKIE_RE = re.compile(r"(?i)\b((?:set-)?cookie\s*:\s*)[^\n|`]+")


@dataclass(frozen=True)
class ValidationResult:
    ok: bool
    errors: tuple[str, ...]


@dataclass(frozen=True)
class CommandSummary:
    name: str
    status: str
    summary: str


def is_digest_ref(value: str) -> bool:
    return bool(DIGEST_RE.fullmatch(value))


def _image_name(value: str) -> str:
    image_ref = value.split("@", maxsplit=1)[0]
    return image_ref.rsplit("/", maxsplit=1)[-1]


def _output_path_is_allowed(output_path: Path) -> bool:
    try:
        resolved_output = output_path.resolve(strict=False)
        resolved_output.relative_to(GENERATED_DOCS)
    except (OSError, ValueError):
        return False

    if output_path.exists():
        try:
            output_path.resolve(strict=True).relative_to(GENERATED_DOCS)
        except (OSError, ValueError):
            return False

    return True


def redact(value: str) -> str:
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        parsed = None
    else:
        return json.dumps(_redact_json(parsed), ensure_ascii=False, sort_keys=True)

    value = AUTHORIZATION_BEARER_RE.sub(
        lambda match: f"{match.group(1)}[REDACTED]",
        value,
    )
    value = PEM_PRIVATE_KEY_RE.sub("[REDACTED]", value)
    value = CREDENTIAL_URL_RE.sub(
        lambda match: f"{match.group(1)}[REDACTED]{match.group(3)}",
        value,
    )
    value = COOKIE_RE.sub(
        lambda match: f"{match.group(1)}[REDACTED]",
        value,
    )
    value = JSON_SECRET_RE.sub(
        lambda match: f"{match.group(1)}{match.group(2)}[REDACTED]{match.group(2)}",
        value,
    )
    return ASSIGNMENT_SECRET_RE.sub(
        lambda match: f"{match.group(1)}{match.group(2)}[REDACTED]",
        value,
    )


def _redact_json(value):
    if isinstance(value, dict):
        return {
            key: "[REDACTED]" if SENSITIVE_KEY_RE.search(str(key)) else _redact_json(item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [_redact_json(item) for item in value]
    return value


def _table_cell(value: str) -> str:
    return redact(value).replace("\\", "\\\\").replace("|", "\\|").replace("\n", " ")


def _inline_code(value: str) -> str:
    return redact(value).replace("\\", "\\\\").replace("`", "\\`").replace("\n", " ")


def _write_evidence(output_path: Path, evidence: str) -> ValidationResult:
    if output_path.is_symlink() or not _output_path_is_allowed(output_path):
        return ValidationResult(
            ok=False,
            errors=("output path must be under docs/generated without symlink escape",),
        )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        output_path.parent.resolve(strict=True).relative_to(GENERATED_DOCS)
    except (OSError, ValueError):
        return ValidationResult(
            ok=False,
            errors=("output path parent must be under docs/generated",),
        )

    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            "w",
            encoding="utf-8",
            dir=output_path.parent,
            prefix=f".{output_path.name}.",
            suffix=".tmp",
            delete=False,
        ) as temporary_file:
            temporary_file.write(evidence)
            temporary_path = Path(temporary_file.name)

        temporary_path.replace(output_path)
    except OSError as exc:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)
        return ValidationResult(ok=False, errors=(f"failed to write evidence: {exc}",))

    return ValidationResult(ok=True, errors=())


def validate_inputs(
    inventory_path: Path,
    output_path: Path,
    backend_image: str,
    frontend_image: str,
    rollback_window_open: bool,
) -> ValidationResult:
    errors: list[str] = []
    inventory_text = ""

    if not inventory_path.exists():
        errors.append("inventory path does not exist")
    elif not inventory_path.is_file():
        errors.append("inventory path must be a file")
    else:
        inventory_text = inventory_path.read_text(encoding="utf-8", errors="replace")

    inventory_probe = f"{inventory_path}\n{inventory_text}"
    if PRODUCTION_RE.search(inventory_probe):
        errors.append("inventory path or content looks like production")

    if not TEST_MARKER_RE.search(inventory_text):
        errors.append("inventory is missing explicit cloud_ui_test_stand test marker")

    if not is_digest_ref(backend_image) or _image_name(backend_image) != "cloud-ui-backend":
        errors.append("backend image must be cloud-ui-backend by sha256 digest")
    elif PRODUCTION_RE.search(backend_image):
        errors.append("backend image registry looks like production")

    if not is_digest_ref(frontend_image) or _image_name(frontend_image) != "cloud-ui-frontend":
        errors.append("frontend image must be cloud-ui-frontend by sha256 digest")
    elif PRODUCTION_RE.search(frontend_image):
        errors.append("frontend image registry looks like production")

    if not rollback_window_open:
        errors.append("rollback window must be explicitly open")

    if not _output_path_is_allowed(output_path):
        errors.append("output path must be under docs/generated without traversal or symlink escape")

    return ValidationResult(ok=not errors, errors=tuple(errors))


def render_evidence(
    inventory_name: str,
    backend_image: str,
    frontend_image: str,
    live_status: str,
    command_summaries: list[CommandSummary],
) -> str:
    rows = [
        CommandSummary("scope", "partial", "test-stand evidence only; production approval absent"),
        CommandSummary("two_images", "pending", "backend and frontend images are digest-pinned"),
        CommandSummary("migration", "pending", "one-shot migration evidence required"),
        CommandSummary("DB/RabbitMQ", "pending", "least-privilege access evidence required"),
        CommandSummary("HAProxy/TLS", "pending", "same-origin TLS smoke evidence required"),
        CommandSummary(
            "container hardening",
            "pending",
            "user/caps/mounts/SELinux inspection evidence required",
        ),
        CommandSummary("API/UI smoke", "pending", "API/UI smoke evidence required"),
        CommandSummary("rollback", "pending", "rollback pending before full E09 acceptance"),
        *command_summaries,
    ]

    lines = [
        "# E09.8 Deployment smoke/evidence",
        "",
        "- Stage: E09.8 Deployment smoke/evidence",
        f"- Live execution status: `{_inline_code(live_status)}`",
        "- Scope: `partial` `test-stand`",
        f"- Inventory: `{_inline_code(inventory_name)}`",
        f"- Backend image: `{backend_image}`",
        f"- Frontend image: `{frontend_image}`",
        "",
        "## Evidence rows",
        "",
        "| Check | Status | Sanitized summary |",
        "|---|---|---|",
    ]

    for item in rows:
        lines.append(
            f"| {_table_cell(item.name)} | {_table_cell(item.status)} | "
            f"{_table_cell(item.summary)} |"
        )

    lines.extend(
        [
            "",
            "## DKB scope",
            "",
            "- ДКБ-22.02/24: TLS and health rows are test-stand evidence only.",
            "- ДКБ-42-44/77/80: network, ACL and container evidence remain external until linked.",
            "- ДКБ-55/56: secret-like output is redacted from this evidence.",
            "- ДКБ-65: user/caps/mounts/SELinux inspection is represented as a pending row.",
            "- ДКБ-69/70: image digest evidence is recorded; ДКБ-69 still needs a waiver.",
            "- ДКБ-82: rollback pending status prevents full deployment acceptance.",
            "",
        ]
    )
    return "\n".join(lines)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Collect sanitized E09.8 deployment evidence")
    parser.add_argument("--inventory", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--backend-image", required=True)
    parser.add_argument("--frontend-image", required=True)
    parser.add_argument("--rollback-window-open", action="store_true")
    parser.add_argument("--live-status", default="pending_external_evidence")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None, command_executor=None) -> int:
    # Reserved for a future explicit live mode; current behavior never runs commands.
    args = parse_args(list(argv if argv is not None else sys.argv[1:]))
    result = validate_inputs(
        inventory_path=args.inventory,
        output_path=args.output,
        backend_image=args.backend_image,
        frontend_image=args.frontend_image,
        rollback_window_open=args.rollback_window_open,
    )
    if not result.ok:
        for error in result.errors:
            print(f"E09.8 preflight failed: {error}", file=sys.stderr)
        return 2

    evidence = render_evidence(
        inventory_name=args.inventory.name,
        backend_image=args.backend_image,
        frontend_image=args.frontend_image,
        live_status=args.live_status,
        command_summaries=[
            CommandSummary("preflight", "passed", "test marker and digest checks passed"),
            CommandSummary(
                "live commands",
                "not_run",
                "runner does not run live commands by default",
            ),
        ],
    )
    write_result = _write_evidence(args.output, evidence)
    if not write_result.ok:
        for error in write_result.errors:
            print(f"E09.8 write failed: {error}", file=sys.stderr)
        return 2

    print(f"E09.8 evidence written to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
