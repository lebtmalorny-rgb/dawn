# ExecPlan: E09.8 Deployment Smoke Evidence

## Цель и наблюдаемый результат

Оператор получает fail-closed runner для controlled live smoke на утвержденном test stand. До E09.8
репозиторий имел repository-side contracts для image build, role, provisioning, migration, topology,
HAProxy и lifecycle, но не имел единого способа собрать sanitized deployment evidence для container
count, image digests, hardening inspection, DB/RabbitMQ access, HAProxy/TLS health and API/UI smoke.

## Контекст и текущее состояние

- Stage: `tasks/E09_KOLLA_DEPLOY.md`, unit E09.8 Deployment smoke/evidence.
- Worktree: `/Users/dmitry/Desktop/dawn/.worktrees/e09-deployment-smoke-evidence`.
- Approved design: `docs/superpowers/specs/2026-06-25-e09-deployment-smoke-evidence-design.md`.
- Baseline setup in this worktree:
  - `uv sync --python 3.11 --project backend --extra dev` required network escalation after sandbox
    DNS blocked PyPI;
  - `npm --prefix frontend ci` completed with existing Node engine warning (`v25.9.0` vs `>=24 <25`);
  - `make test` passed backend `327 passed, 1 skipped` and frontend `35 passed`.
- Existing E09 evidence before this plan remains mostly repository-side. E09.7 explicitly left live
  reconfigure, idempotency, rolling update, failed rollback, image digest pull, smoke and inspection
  pending for E09.8/test-stand execution.
- The user confirmed that a test stand exists. No inventory, credentials, image digests or stand logs
  may be committed.

## Scope

- Add a Python evidence runner with explicit inventory path, output path, digest images and rollback
  window inputs.
- Reject production-looking inventory names/content, missing test marker, tag-only image references,
  output outside `docs/generated/` and closed rollback window.
- Render sanitized Markdown evidence with required E09.8 acceptance rows.
- Add tests for safe/unsafe runner behavior and evidence redaction.
- Add initial generated evidence, DKB traceability and risk register rows.
- Optionally run approved live test-stand smoke after repository checks and attach only sanitized
  command summaries.

## Non-goals

- No production execution.
- No committed inventory, passwords, private keys, `.env`, `clouds.yaml`, `openrc`, cookies or tokens.
- No destructive uninstall or database/RabbitMQ/Vault cleanup.
- No direct OpenStack calls from frontend.
- No full ДКБ-69 closure without interpreter waiver and scanner/signature policy.
- No rollback acceptance claim unless failed-update rollback is actually executed and sanitized
  evidence is attached.

## Требования и ограничения

- E09 remains test-inventory only.
- Mutating live commands require explicit test marker and rollback window.
- The runner must exit non-zero before mutating if input is incomplete or production-looking.
- Evidence output must stay under `docs/generated/`.
- Secrets must be redacted or the run must fail.
- The two-image contract must remain: `cloud-ui-frontend` and `cloud-ui-backend`; backend image is
  reused for API, worker, events, migration and smoke.
- Repository verification must pass before any push or completion claim.

## Связь с ДКБ

| Код | Что реализует план | Что остается внешним | Доказательство | Почему нельзя заявлять полное закрытие |
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
3. Evidence, DKB traceability and risk register updates.
4. Repository verification.
5. Optional live test-stand run and evidence refresh.
6. Commit, merge and push.

## Progress

- [x] 2026-06-25: Исследование фактического состояния. Evidence: E09 task, listed docs, E08 security
  review, `deploy/AGENTS.md`, existing E09 tests/scripts and approved design were read; worktree
  baseline `make test` passed.
- [x] 2026-06-25: Контракт и тестовый double. Evidence:
  `backend/.venv/bin/python -m pytest tests/test_e09_deployment_smoke_evidence.py -q` exited
  `1` with `6 failed`; failures are the expected RED state because
  `deploy/kolla/scripts/collect-e09-evidence.py` and
  `docs/generated/e09-deployment-smoke-evidence.md` do not exist yet.
- [ ] Минимальная реализация.
- [ ] Отрицательные сценарии и безопасность.
- [ ] Интеграционные и пользовательские проверки.
- [ ] Документация, evidence и review.

## Неожиданные открытия

- 2026-06-25: The new worktree again needed `uv --python 3.11` because local system Python is outside
  backend bounds. First sandboxed `uv sync` failed on PyPI DNS; escalated sync succeeded.
- 2026-06-25: `npm --prefix frontend ci` still completes with the known Node engine warning for
  local `v25.9.0`; this is unrelated to E09.8.

## Журнал решений

- 2026-06-25: Use a fail-closed Python runner instead of a shell-only script. Alternative: shell
  script. Reason: structured validation/redaction is safer and easier to test. Consequence: live
  command execution remains explicit and bounded.
- 2026-06-25: Keep live stand values outside Git and represent them only as sanitized summaries.
  Alternative: commit sample inventory or exact command logs. Reason: AGENTS forbids real inventory,
  credentials and production URLs in Git. Consequence: exact stand details must be reproduced from
  operator shell/history or external evidence store, not repository secrets.

## Детальный план реализации

The exact step-by-step implementation plan is
`docs/superpowers/plans/2026-06-25-e09-deployment-smoke-evidence.md`.

Repository paths to create or modify:

- `tests/test_e09_deployment_smoke_evidence.py`;
- `deploy/kolla/scripts/collect-e09-evidence.py`;
- `docs/generated/e09-deployment-smoke-evidence.md`;
- `docs/11_DKB_TRACEABILITY.md`;
- `docs/generated/risk-register.md`;
- this ExecPlan.

## Миграции и совместимость

No database, OpenAPI, backend runtime command or frontend behavior changes are planned. The runner is
additive and can be reverted by Git. Live stand rollback, if a mutating test run is executed, follows
E09.7 failed-update phases before contract migration: stop rollout, restore previous config commit,
restore previous image digests, rerun test reconfigure, smoke previous version and preserve
operations/audit/read model/queued messages.

## Проверка

Run from `/Users/dmitry/Desktop/dawn/.worktrees/e09-deployment-smoke-evidence`:

- `backend/.venv/bin/python -m pytest tests/test_e09_deployment_smoke_evidence.py -q`
- `backend/.venv/bin/python -m pytest tests -q`
- `make lint`
- `make typecheck`
- `make security`
- `make test`
- `git diff --check`

Optional live test-stand checks must be recorded as sanitized command summaries only after repository
checks pass and test inventory marker/digests/rollback window are present.

## Доказательства

- `tests/test_e09_deployment_smoke_evidence.py`
- `deploy/kolla/scripts/collect-e09-evidence.py`
- `docs/generated/e09-deployment-smoke-evidence.md`
- `docs/generated/risk-register.md`
- `docs/11_DKB_TRACEABILITY.md`
- Live stand command summaries if executed and sanitized.

## Откат и восстановление

Repository rollback is `git revert` of the E09.8 commits. This runner itself does not mutate remote
hosts unless explicitly used with approved live commands. If a live test reconfigure changes the
stand, rollback must use recorded previous image digests/config commit and the E09.7 rollback phases.

## Итог и остаточные риски

Pending implementation.
