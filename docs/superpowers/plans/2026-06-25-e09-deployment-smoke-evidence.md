# E09 Deployment Smoke Evidence Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a fail-closed E09.8 evidence runner and documentation path for controlled live smoke on the approved test stand.

**Architecture:** Add a small Python CLI under `deploy/kolla/scripts/` that validates explicit test-stand inputs, refuses production-looking inventories, rejects tag-only images, redacts secret-like data and writes sanitized Markdown evidence. Repository tests exercise safe and unsafe paths before any live stand command is run.

**Tech Stack:** Python stdlib CLI, pytest, existing root E09 tests, generated Markdown evidence, existing Makefile quality gates.

---

## File Structure

- Create `deploy/kolla/scripts/collect-e09-evidence.py`: fail-closed CLI, input validation, redaction, command-plan rendering and Markdown evidence output.
- Create `tests/test_e09_deployment_smoke_evidence.py`: RED/GREEN tests for digest validation, production rejection, test marker requirement, evidence fields and redaction.
- Create `docs/generated/e09-deployment-smoke-evidence.md`: initial partial evidence document showing repository runner readiness and pending live rows.
- Create `docs/execplans/E09-deployment-smoke-evidence.md`: AGENTS-required live ExecPlan and progress log.
- Modify `docs/11_DKB_TRACEABILITY.md`: E09.8 traceability update without false DKB closure.
- Modify `docs/generated/risk-register.md`: add R-068 for live evidence overclaim risk.

### Task 1: Add ExecPlan And RED Tests

**Files:**
- Create: `docs/execplans/E09-deployment-smoke-evidence.md`
- Create: `tests/test_e09_deployment_smoke_evidence.py`

- [ ] **Step 1: Write the ExecPlan skeleton**

Create `docs/execplans/E09-deployment-smoke-evidence.md` with:

```markdown
# ExecPlan: E09.8 Deployment Smoke Evidence

## Цель и наблюдаемый результат

Оператор получает fail-closed runner для controlled live smoke на утвержденном test stand. До E09.8
репозиторий имел repository-side contracts для image build, role, provisioning, migration, topology,
HAProxy и lifecycle, но не имел единого способа собрать sanitized deployment evidence.

## Контекст и текущее состояние

- Stage: `tasks/E09_KOLLA_DEPLOY.md`, unit E09.8 Deployment smoke/evidence.
- Worktree: `/Users/dmitry/Desktop/dawn/.worktrees/e09-deployment-smoke-evidence`.
- Approved design: `docs/superpowers/specs/2026-06-25-e09-deployment-smoke-evidence-design.md`.
- Baseline: `make test` passed backend `327 passed, 1 skipped` and frontend `35 passed`.
- Live stand exists, but no inventory, credentials, image digests or test-stand command output may be committed.

## Scope

- Add a Python evidence runner with test marker, digest and production-name validation.
- Add RED/GREEN tests for unsafe input rejection and sanitized evidence rendering.
- Add initial generated evidence with live rows marked pending until command output is collected.
- Update DKB traceability and risk register.

## Non-goals

- No production execution.
- No committed inventory, passwords, private keys, `.env`, `clouds.yaml`, `openrc`, cookies or tokens.
- No destructive uninstall.
- No full ДКБ-69 closure without interpreter waiver.

## Требования и ограничения

- Mutating live commands require explicit test marker and rollback window.
- The runner must exit non-zero before mutating if input is incomplete or production-looking.
- Evidence output must stay under `docs/generated/`.
- Secrets must be redacted or reject the run.

## Связь с ДКБ

| Код | Что реализует план | Что остается внешним | Доказательство | Почему не закрыто полностью |
|---|---|---|---|---|
| ДКБ-22.02/24 | Evidence rows for TLS/health smoke. | Corporate PKI/mTLS approval and negative cert tests. | E09.8 evidence doc. | Test stand proof is not production PKI approval. |
| ДКБ-42-44/77/80 | Evidence rows for network/ACL and container inspection. | Network-owner ACL proof. | Evidence doc and command summaries. | Firewall state is external to repo. |
| ДКБ-55/56 | No secrets in Git or evidence. | Full rotation/revoke lifecycle. | Secret scan and redaction tests. | No production SecMan rotation evidence. |
| ДКБ-65 | Container inspection fields for user/caps/mounts/SELinux. | Host SELinux policy owner approval. | Inspection summaries. | Runtime evidence is test-scoped. |
| ДКБ-69/70 | Digest/SBOM/scan links can be recorded. | ДКБ-69 waiver, signature policy. | Evidence doc. | Python backend interpreter remains. |
| ДКБ-82 | Deployment smoke and rollback evidence rows. | Full failed rollback execution if not run. | Evidence doc. | Partial evidence cannot claim acceptance. |

## Milestones

1. RED tests and ExecPlan.
2. Minimal fail-closed runner.
3. Evidence/doc updates.
4. Repository verification.
5. Optional live test-stand run and evidence refresh.
6. Commit, merge and push.

## Progress

- [ ] Исследование фактического состояния.
- [ ] Контракт и тестовый double.
- [ ] Минимальная реализация.
- [ ] Отрицательные сценарии и безопасность.
- [ ] Интеграционные и пользовательские проверки.
- [ ] Документация, evidence и review.

## Неожиданные открытия

No unexpected findings yet.

## Журнал решений

- 2026-06-25: Use a fail-closed Python runner instead of a shell-only script. Alternative: shell script.
  Reason: structured validation/redaction is safer and easier to test. Consequence: live command
  execution remains explicit and bounded.

## Детальный план реализации

Follow `docs/superpowers/plans/2026-06-25-e09-deployment-smoke-evidence.md`.

## Миграции и совместимость

No database, OpenAPI or frontend migrations. Repository rollback is Git revert. Live stand rollback
uses E09.7 failed-update phases before contract migration.

## Проверка

- `backend/.venv/bin/python -m pytest tests/test_e09_deployment_smoke_evidence.py -q`
- `backend/.venv/bin/python -m pytest tests -q`
- `make lint`
- `make typecheck`
- `make security`
- `make test`
- `git diff --check`

## Доказательства

- `tests/test_e09_deployment_smoke_evidence.py`
- `deploy/kolla/scripts/collect-e09-evidence.py`
- `docs/generated/e09-deployment-smoke-evidence.md`
- `docs/generated/risk-register.md`
- `docs/11_DKB_TRACEABILITY.md`

## Откат и восстановление

Revert the E09.8 commits. If a live test run has changed the stand, use the recorded previous image
digests/config commit and E09.7 rollback phases.

## Итог и остаточные риски

Pending implementation.
```

- [ ] **Step 2: Write RED tests**

Create `tests/test_e09_deployment_smoke_evidence.py` with:

```python
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "deploy/kolla/scripts/collect-e09-evidence.py"


def load_module():
    spec = importlib.util.spec_from_file_location("collect_e09_evidence", SCRIPT)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
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


def test_rendered_evidence_contains_required_rows_and_no_secret_values(tmp_path: Path) -> None:
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


def test_generated_evidence_traceability_and_risk_register_are_updated() -> None:
    evidence = (ROOT / "docs/generated/e09-deployment-smoke-evidence.md").read_text(encoding="utf-8")
    traceability = (ROOT / "docs/11_DKB_TRACEABILITY.md").read_text(encoding="utf-8")
    risk_register = (ROOT / "docs/generated/risk-register.md").read_text(encoding="utf-8")

    assert "Stage: E09.8 Deployment smoke/evidence" in evidence
    assert "R-068" in risk_register
    assert "E09.8 Deployment smoke/evidence" in traceability
    assert "production approved" not in evidence.lower()
```

- [ ] **Step 3: Run RED tests**

Run:

```bash
backend/.venv/bin/python -m pytest tests/test_e09_deployment_smoke_evidence.py -q
```

Expected: fails because `deploy/kolla/scripts/collect-e09-evidence.py` and generated evidence do not exist.

- [ ] **Step 4: Commit RED tests and ExecPlan**

```bash
git add docs/execplans/E09-deployment-smoke-evidence.md tests/test_e09_deployment_smoke_evidence.py
git commit -m "test: define E09 deployment smoke evidence contract"
```

### Task 2: Implement The Fail-Closed Evidence Runner

**Files:**
- Create: `deploy/kolla/scripts/collect-e09-evidence.py`
- Test: `tests/test_e09_deployment_smoke_evidence.py`

- [ ] **Step 1: Add executable Python runner**

Create `deploy/kolla/scripts/collect-e09-evidence.py` with:

```python
#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path

DIGEST_RE = re.compile(r"^[^:@\s]+(?:/[^:@\s]+)+@sha256:[a-fA-F0-9]{64}$")
PRODUCTION_RE = re.compile(r"\b(prod|production|prd)\b", re.IGNORECASE)
TEST_MARKERS = ("cloud_ui_test_stand=true", "cloud_ui_test_stand: true")
SECRET_RE = re.compile(
    r"(?i)(password|passwd|token|secret|private[_-]?key|application_credential)\s*[:=]\s*[^,\s]+"
)


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
    return bool(DIGEST_RE.match(value))


def redact(value: str) -> str:
    return SECRET_RE.sub(lambda match: match.group(1) + "=[REDACTED]", value)


def validate_inputs(
    *,
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
    else:
        inventory_text = inventory_path.read_text(encoding="utf-8", errors="replace")

    inventory_display = str(inventory_path)
    if PRODUCTION_RE.search(inventory_display) or PRODUCTION_RE.search(inventory_text):
        errors.append("inventory path or content looks like production")
    if inventory_text and not any(marker in inventory_text for marker in TEST_MARKERS):
        errors.append("inventory is missing explicit cloud_ui_test_stand test marker")
    if not is_digest_ref(backend_image):
        errors.append("backend image must be a sha256 digest reference")
    if not is_digest_ref(frontend_image):
        errors.append("frontend image must be a sha256 digest reference")
    if not rollback_window_open:
        errors.append("rollback window must be explicitly open")

    generated_root = Path("docs/generated").resolve()
    try:
        output_path.resolve().relative_to(generated_root)
    except ValueError:
        errors.append("output path must be under docs/generated")

    return ValidationResult(ok=not errors, errors=tuple(errors))


def render_evidence(
    *,
    inventory_name: str,
    backend_image: str,
    frontend_image: str,
    live_status: str,
    command_summaries: list[CommandSummary],
) -> str:
    lines = [
        "# E09.8 Deployment smoke/evidence",
        "",
        "- Stage: E09.8 Deployment smoke/evidence",
        f"- Live execution status: `{live_status}`",
        f"- Inventory: `{redact(inventory_name)}`",
        f"- Backend image: `{backend_image}`",
        f"- Frontend image: `{frontend_image}`",
        "",
        "## Evidence rows",
        "",
        "| Check | Status | Sanitized summary |",
        "|---|---|---|",
    ]
    for item in command_summaries:
        lines.append(f"| {item.name} | {item.status} | {redact(item.summary)} |")
    lines.extend(
        [
            "",
            "## DKB scope",
            "",
            "- ДКБ-22.02/24: TLS and health rows are test-stand evidence only.",
            "- ДКБ-42-44/77/80: network and ACL proof remains external unless linked here.",
            "- ДКБ-55/56: secrets are not stored in this evidence.",
            "- ДКБ-65: user/caps/mounts/SELinux inspection is recorded when live rows pass.",
            "- ДКБ-69/70: digest evidence is recorded; ДКБ-69 remains open without waiver.",
            "- ДКБ-82: rollback evidence is required before full E09 acceptance.",
            "",
        ]
    )
    return "\n".join(lines)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Collect sanitized E09.8 deployment evidence")
    parser.add_argument("--inventory", required=True, type=Path)
    parser.add_argument("--backend-image", required=True)
    parser.add_argument("--frontend-image", required=True)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--rollback-window-open", action="store_true")
    parser.add_argument("--live-status", default="pending_external_evidence")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
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
            CommandSummary("preflight", "passed", "test stand marker and digest checks passed"),
            CommandSummary("live_reconfigure", "pending", "run controlled test-stand command"),
            CommandSummary("container_count", "pending", "expect 12 permanent containers"),
            CommandSummary("api_ui_smoke", "pending", "expect same-origin API/UI health"),
            CommandSummary("rollback", "pending", "required before full E09 acceptance"),
        ],
    )
    args.output.write_text(evidence, encoding="utf-8")
    print(f"E09.8 evidence written to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 2: Run the E09.8 tests**

Run:

```bash
backend/.venv/bin/python -m pytest tests/test_e09_deployment_smoke_evidence.py -q
```

Expected: remaining failures only for missing generated evidence, traceability and risk updates.

- [ ] **Step 3: Commit runner implementation**

```bash
git add deploy/kolla/scripts/collect-e09-evidence.py
git commit -m "deploy: add E09 evidence collector"
```

### Task 3: Add Evidence, Traceability And Risk Rows

**Files:**
- Create: `docs/generated/e09-deployment-smoke-evidence.md`
- Modify: `docs/11_DKB_TRACEABILITY.md`
- Modify: `docs/generated/risk-register.md`
- Modify: `docs/execplans/E09-deployment-smoke-evidence.md`

- [ ] **Step 1: Add initial generated evidence**

Create `docs/generated/e09-deployment-smoke-evidence.md` with:

```markdown
# E09.8 Deployment smoke/evidence

- Stage: E09.8 Deployment smoke/evidence
- Status: repository runner ready; live test-stand rows are pending until sanitized command output is attached.
- Live execution status: `pending_external_evidence`

## Evidence rows

| Check | Status | Sanitized summary |
|---|---|---|
| preflight | pending | Requires explicit `cloud_ui_test_stand` marker and digest-pinned images. |
| two images | pending | Expected `cloud-ui-backend` and `cloud-ui-frontend` by sha256 digest. |
| container count | pending | Expected three nodes x four permanent containers = 12. |
| migration | pending | Expected one-shot `cloud_ui_db_migrate` before rollout. |
| DB/RabbitMQ | pending | Expected least-privilege access checks without secret output. |
| HAProxy/TLS | pending | Expected same-origin UI/API health over TLS >= 1.2. |
| container hardening | pending | Expected non-root user, dropped caps, controlled mounts, SELinux labels. |
| API/UI smoke | pending | Expected frontend and `/api/v1/health/ready` health. |
| rollback | pending | Required before full E09 acceptance. |

## DKB scope

- ДКБ-22.02/24: TLS and health rows are pending live test evidence.
- ДКБ-42-44/77/80: network/ACL rows remain pending external proof.
- ДКБ-55/56: evidence must not contain secrets; full rotation remains external.
- ДКБ-65: SELinux/caps/mount inspection remains pending live output.
- ДКБ-69/70: image digests can be recorded; ДКБ-69 waiver remains required.
- ДКБ-82: operational lifecycle evidence remains partial until rollback is executed.
```

- [ ] **Step 2: Update traceability**

Insert before `## Полная матрица` in `docs/11_DKB_TRACEABILITY.md`:

```markdown
## Обновление требований 2026-06-25: E09.8 Deployment smoke/evidence

E09.8 adds a fail-closed evidence runner for approved test-stand deployment smoke:

- ДКБ-22.02/24: TLS and health evidence can be recorded from the test stand. Corporate PKI/mTLS
  approval and negative certificate tests remain external.
- ДКБ-42-44/77/80: container count, management network and ACL evidence can be attached only after
  sanitized test-stand output is collected.
- ДКБ-55/56: the runner rejects or redacts secret-like output and stores no credentials in Git.
  Full secret rotation and revoke evidence remain external.
- ДКБ-65: container user/capability/mount/SELinux inspection is represented as live evidence rows.
- ДКБ-69/70: digest-pinned image evidence is required, but ДКБ-69 remains open without the Python
  interpreter waiver and image policy evidence.
- ДКБ-82: deployment smoke evidence improves operational proof; full E09 acceptance still requires
  executed rollback evidence.

Evidence: `tests/test_e09_deployment_smoke_evidence.py`,
`deploy/kolla/scripts/collect-e09-evidence.py`,
`docs/generated/e09-deployment-smoke-evidence.md`,
`docs/generated/risk-register.md` and ExecPlan
`docs/execplans/E09-deployment-smoke-evidence.md`.
```

- [ ] **Step 3: Add risk row**

Append under E09 risks in `docs/generated/risk-register.md`:

```markdown
| R-068 | E09.8 smoke evidence mistaken for production deployment approval | E09.8 collects sanitized test-stand evidence and may include live `kolla-ansible` command summaries, but it is scoped to the approved test inventory only. | Keep production approval, corporate PKI/mTLS, registry signing, DKB-69 waiver, network-owner ACL proof and rollback execution status explicit in generated evidence before any acceptance claim. | E09 |
```

- [ ] **Step 4: Update ExecPlan progress**

Mark RED/GREEN documentation milestones in `docs/execplans/E09-deployment-smoke-evidence.md`.

- [ ] **Step 5: Run tests**

Run:

```bash
backend/.venv/bin/python -m pytest tests/test_e09_deployment_smoke_evidence.py -q
```

Expected: `6 passed`.

- [ ] **Step 6: Commit docs and risk updates**

```bash
git add docs/generated/e09-deployment-smoke-evidence.md docs/11_DKB_TRACEABILITY.md docs/generated/risk-register.md docs/execplans/E09-deployment-smoke-evidence.md tests/test_e09_deployment_smoke_evidence.py
git commit -m "docs: record E09 deployment smoke evidence gates"
```

### Task 4: Repository Verification

**Files:**
- No new files.

- [ ] **Step 1: Run targeted E09 tests**

```bash
backend/.venv/bin/python -m pytest tests/test_e09_deployment_smoke_evidence.py tests/test_e09_reconfigure_rollback.py tests/test_e09_kolla_ansible_role.py tests/test_e09_haproxy_tls_network.py tests/test_e09_process_containers.py tests/test_e09_migration_job.py tests/test_e09_db_rabbitmq_provisioning.py tests/test_e09_kolla_image_build.py -q
```

Expected: all tests pass.

- [ ] **Step 2: Run root tests**

```bash
backend/.venv/bin/python -m pytest tests -q
```

Expected: all root tests pass.

- [ ] **Step 3: Run quality gates**

```bash
make lint
make typecheck
make security
make test
git diff --check
```

Expected: all commands exit 0.

- [ ] **Step 4: Update ExecPlan with command results**

Record exact pass counts and any warnings in `docs/execplans/E09-deployment-smoke-evidence.md`.

- [ ] **Step 5: Commit verification update**

```bash
git add docs/execplans/E09-deployment-smoke-evidence.md
git commit -m "docs: verify E09 deployment smoke evidence"
```

### Task 5: Optional Live Test-Stand Evidence Refresh

**Files:**
- Modify: `docs/generated/e09-deployment-smoke-evidence.md`
- Modify: `docs/execplans/E09-deployment-smoke-evidence.md`

- [ ] **Step 1: Discover live stand inputs outside Git**

Use operator-provided values, not committed files:

```bash
export CLOUD_UI_E09_INVENTORY=/path/to/test/inventory
export CLOUD_UI_E09_BACKEND_IMAGE=registry.example.invalid/cloud-ui-backend@sha256:<64-hex>
export CLOUD_UI_E09_FRONTEND_IMAGE=registry.example.invalid/cloud-ui-frontend@sha256:<64-hex>
```

Expected: variables exist only in the shell/session and are not written to Git.

- [ ] **Step 2: Run preflight evidence generation**

```bash
deploy/kolla/scripts/collect-e09-evidence.py \
  --inventory "$CLOUD_UI_E09_INVENTORY" \
  --backend-image "$CLOUD_UI_E09_BACKEND_IMAGE" \
  --frontend-image "$CLOUD_UI_E09_FRONTEND_IMAGE" \
  --rollback-window-open \
  --output docs/generated/e09-deployment-smoke-evidence.md
```

Expected: writes sanitized evidence or exits 2 before any mutating command.

- [ ] **Step 3: Attach live command summaries**

If the approved stand is reachable, collect sanitized summaries for:

```bash
kolla-ansible -i "$CLOUD_UI_E09_INVENTORY" reconfigure --tags cloud-ui
kolla-ansible -i "$CLOUD_UI_E09_INVENTORY" reconfigure --tags cloud-ui
```

Expected: first run succeeds, second run proves idempotency. Do not paste secrets or full logs into Git.

- [ ] **Step 4: Run final secret and diff checks**

```bash
make security
git diff --check
```

Expected: no secret scan findings and clean diff.

- [ ] **Step 5: Commit live evidence if sanitized**

```bash
git add docs/generated/e09-deployment-smoke-evidence.md docs/execplans/E09-deployment-smoke-evidence.md
git commit -m "docs: attach E09 test-stand smoke evidence"
```

Only do this if evidence is sanitized and contains no credentials, tokens, private keys, cookies or production URLs.

### Task 6: Integrate To Main

**Files:**
- No new files.

- [ ] **Step 1: Check branch status**

```bash
git status --short --branch
git log --oneline --decorate --max-count=6
```

Expected: clean branch with E09.8 commits.

- [ ] **Step 2: Merge to main**

```bash
git -C /Users/dmitry/Desktop/dawn pull --ff-only
git -C /Users/dmitry/Desktop/dawn merge --ff-only e09-deployment-smoke-evidence
```

Expected: fast-forward merge.

- [ ] **Step 3: Re-run verification on main**

```bash
backend/.venv/bin/python -m pytest tests -q
make lint
make typecheck
make security
make test
git diff --check
```

Expected: all pass on `main`.

- [ ] **Step 4: Push**

```bash
git push origin main
```

Expected: `main -> main`.

- [ ] **Step 5: Cleanup**

```bash
git worktree remove /Users/dmitry/Desktop/dawn/.worktrees/e09-deployment-smoke-evidence
git branch -d e09-deployment-smoke-evidence
```

Expected: implementation worktree removed and branch deleted after merge.

## Self-Review

- Spec coverage: the plan covers fail-closed runner, test marker, digest checks, production rejection,
  evidence rendering, DKB/risk updates, repository gates and optional live stand evidence.
- Placeholder scan: no TBD/TODO/fill-in placeholders are used. Live values are explicitly external
  shell variables, not committed content.
- Type consistency: tests and implementation use `ValidationResult`, `CommandSummary`,
  `is_digest_ref`, `validate_inputs` and `render_evidence` consistently.
