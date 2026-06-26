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
  `1` with `14 failed`; failures are the expected RED state because
  `deploy/kolla/scripts/collect-e09-evidence.py` and
  `docs/generated/e09-deployment-smoke-evidence.md` do not exist yet.
- [x] 2026-06-25: Минимальная реализация runner. Evidence: current branch HEAD
  `29ec0f8 deploy: redact JSON evidence string values` contains
  `deploy/kolla/scripts/collect-e09-evidence.py`; targeted pytest after Task 2 reached
  `16 passed, 1 failed`, with the single known failure being missing generated evidence/docs.
- [x] 2026-06-25: Отрицательные сценарии и безопасность. Evidence: current branch tests cover
  production-looking inventory rejection, missing test marker, non-digest images, output path escape,
  wrong image names, closed rollback window and redaction; after Task 2 the targeted result was
  `16 passed, 1 failed` because generated evidence/docs were still absent.
- [x] 2026-06-25: Интеграционные и пользовательские проверки на стороне репозитория. Evidence:
  `backend/.venv/bin/python -m pytest tests/test_e09_deployment_smoke_evidence.py tests/test_e09_reconfigure_rollback.py tests/test_e09_kolla_ansible_role.py tests/test_e09_haproxy_tls_network.py tests/test_e09_process_containers.py tests/test_e09_migration_job.py tests/test_e09_db_rabbitmq_provisioning.py tests/test_e09_kolla_image_build.py -q`
  exited `0` with `68 passed in 0.28s`; `backend/.venv/bin/python -m pytest tests -q` exited
  `0` with `68 passed in 0.28s`.
- [x] 2026-06-25: Документация и evidence для Task 3. Evidence:
  `backend/.venv/bin/python -m pytest tests/test_e09_deployment_smoke_evidence.py -q` exited `0`
  with `17 passed`; generated evidence, DKB traceability and R-068 risk row are present.
- [x] 2026-06-25: Документация, evidence и review для repository verification. Evidence:
  `make lint` exited `0` after ruff reported `All checks passed!`, frontend eslint completed, and
  `./scripts/secret-scan.sh` completed; `make typecheck` exited `0` with mypy `Success: no issues
  found in 83 source files` and frontend `tsc -b`; `make security` exited `0` via
  `./scripts/secret-scan.sh`; `make test` exited `0` with backend `327 passed, 1 skipped in 3.28s`
  and frontend vitest `35 passed (35)`; `git diff --check` exited `0` before the ExecPlan update.
- [ ] Optional live test-stand execution and sanitized evidence refresh remain pending. Read-only
  discovery against the provided test address on 2026-06-25 did not produce attachable live evidence:
  OpenSSH reported a host-key mismatch, `podman` was present but Cloud UI/Kolla containers/images were
  not found by name, `kolla-ansible`/`kolla-build` were not on PATH, and no approved inventory path or
  backend/frontend image digests were available.
  - 2026-06-26 continuation from branch `e09-live-evidence-continuation`: read-only host-key scan
    matched local known_hosts ED25519 keys for `192.168.10.15` and `192.168.10.14`. Read-only SSH to
    `192.168.10.15` confirmed host `ansible.example.local`, `/etc/kolla/all-in-one` present,
    `kolla-ansible 20.4.1.dev5` present and `/usr/bin/podman` present. The inventory is still missing
    the required `cloud_ui_test_stand` marker, so no mutating live command was run.
  - 2026-06-26: read-only Podman image discovery on `192.168.10.15` found digest refs for
    `cloud-ui-backend` and `cloud-ui-frontend` in the local registry. SSH to `192.168.10.14` failed
    with public-key authentication denied, so no live container count, hardening inspection,
    HAProxy/TLS smoke, API/UI smoke or rollback evidence was collected.
  - 2026-06-26 after user approval: added `cloud_ui_test_stand=true` to `/etc/kolla/all-in-one` on
    `192.168.10.15` and created a test-host backup before editing. Copied the test inventory to
    `/private/tmp` only for runner validation; it was not committed.
  - 2026-06-26: E09.8 preflight runner passed with the approved marker, backend/frontend digest refs
    and open rollback window.
  - 2026-06-26: read-only live inspection through the Ansible host found four healthy Cloud UI
    containers on the all-in-one host, not twelve containers on three nodes. Docker inspect showed
    `user=cloudui`, but `readonly=false`, `capdrop=null` and `securityopt=null`.
  - 2026-06-26: frontend port smoke returned HTTP 200; backend readiness returned HTTP 503. No
    `cloud_ui_db_migrate` or `cloud-ui db-upgrade` container was found. Remote Cloud UI custom
    role/config was not found on the Ansible host, so `kolla-ansible reconfigure --tags cloud-ui`
    was not run as acceptance evidence.

## Неожиданные открытия

- 2026-06-25: The new worktree again needed `uv --python 3.11` because local system Python is outside
  backend bounds. First sandboxed `uv sync` failed on PyPI DNS; escalated sync succeeded.
- 2026-06-25: `npm --prefix frontend ci` still completes with the known Node engine warning for
  local `v25.9.0`; this is unrelated to E09.8.
- 2026-06-25: First Task 4 `make lint` attempt failed inside `./scripts/secret-scan.sh` because
  static E09 redaction canary literals in `tests/test_e09_deployment_smoke_evidence.py` matched the
  repository secret patterns. Commit `5574b2f test: avoid static E09 redaction canaries` fixed the
  fixture by building the same canary values from runtime fragments without weakening the scanner;
  the retry `make lint` and `make security` both completed with exit `0`.
- 2026-06-25: Optional live test-stand discovery was kept read-only. OpenSSH reported that the known
  ED25519 host key for the provided test address changed, so no mutating `kolla-ansible` command was
  run. Additional read-only probes found `/usr/bin/podman`, but no Cloud UI/Kolla containers/images by
  name, no `kolla-ansible`/`kolla-build` on PATH and no approved inventory/digest inputs to feed into
  the evidence runner.
- 2026-06-26: The host-key blocker did not reproduce for ED25519 keys: `ssh-keyscan` output for
  `192.168.10.15` and `192.168.10.14` matched local known_hosts. The next blocker is the missing
  `cloud_ui_test_stand` marker in `/etc/kolla/all-in-one`.
- 2026-06-26: Two Cloud UI image digest refs exist on the Ansible host local registry, but this is
  only partial lab evidence. Registry signing, provenance, deployed pull-by-digest proof and
  container inspection remain pending.
- 2026-06-26: SSH authentication to `192.168.10.14` failed with the current key, preventing live
  container count, hardening inspection and API/UI smoke collection from that host.
- 2026-06-26: The production-inventory guard had a false positive on the standard Kolla group name
  `designate-producer`. Regression coverage was added and the guard was narrowed to keep rejecting
  `production`, `prd*` and `prod*` environment markers while allowing Kolla `producer` groups.
- 2026-06-26: The test stand has Cloud UI containers already running on the all-in-one host, but the
  repository custom role/config was not found on the Ansible host. This means current live evidence
  can describe observed state, but cannot prove the E09 Kolla role deploy/reconfigure path.
- 2026-06-26: Container hardening evidence fails the E09 target on the observed all-in-one containers:
  read-only root filesystem is disabled and capability/security options are unset.
- 2026-06-26: API readiness returned HTTP 503 while frontend returned HTTP 200; the UI smoke is only
  partial until backend readiness is healthy.
- 2026-06-25: Final whole-branch review found an important redaction gap: non-JSON
  `Authorization:` headers were redacted only for Bearer values. Commit
  `8cac2a4 deploy: redact all E09 authorization headers` now redacts any `Authorization:` or
  `Proxy-Authorization:` header value and adds Basic/Token/custom scheme regression tests.

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

- `backend/.venv/bin/python -m pytest tests/test_e09_deployment_smoke_evidence.py tests/test_e09_reconfigure_rollback.py tests/test_e09_kolla_ansible_role.py tests/test_e09_haproxy_tls_network.py tests/test_e09_process_containers.py tests/test_e09_migration_job.py tests/test_e09_db_rabbitmq_provisioning.py tests/test_e09_kolla_image_build.py -q`
  - 2026-06-25 retry result: exit `0`, `68 passed in 0.28s`.
- `backend/.venv/bin/python -m pytest tests -q`
  - 2026-06-25 retry result: exit `0`, `68 passed in 0.28s`.
- `make lint`
  - 2026-06-25 retry result: exit `0`; ruff `All checks passed!`, frontend eslint completed,
    `./scripts/secret-scan.sh` completed.
- `make typecheck`
  - 2026-06-25 retry result: exit `0`; mypy `Success: no issues found in 83 source files`,
    frontend `tsc -b` completed.
- `make security`
  - 2026-06-25 retry result: exit `0`; `./scripts/secret-scan.sh` completed.
- `make test`
  - 2026-06-25 retry result: exit `0`; backend `327 passed, 1 skipped in 3.28s`, frontend vitest
    `35 passed (35)`.
- `git diff --check`
  - 2026-06-25 pre-ExecPlan-update result: exit `0`.
  - 2026-06-25 post-ExecPlan-update result: exit `0`.
- `backend/.venv/bin/python -m pytest tests/test_e09_deployment_smoke_evidence.py tests/test_e09_reconfigure_rollback.py tests/test_e09_kolla_ansible_role.py tests/test_e09_haproxy_tls_network.py tests/test_e09_process_containers.py tests/test_e09_migration_job.py tests/test_e09_db_rabbitmq_provisioning.py tests/test_e09_kolla_image_build.py -q`
  - 2026-06-25 post-review auth-header fix result: exit `0`, `68 passed in 0.31s`.
- `make lint`
  - 2026-06-25 post-review auth-header fix result: exit `0`; ruff `All checks passed!`,
    frontend eslint completed, `./scripts/secret-scan.sh` completed.
- `git diff --check`
  - 2026-06-25 post-review auth-header fix result: exit `0`.

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

Repository-side E09.8 status is implemented and verified: the fail-closed evidence runner,
repository evidence, DKB traceability row and R-068 risk entry exist, and the retry verification gates
above passed after the static canary fixture fix in `5574b2f`. Final whole-branch review found an
authorization-header scheme redaction gap, fixed by `8cac2a4`.

Full E09 acceptance is still not claimed. The optional live test-stand smoke, real container/HAProxy/
DB/RabbitMQ inspection summaries, image digest pull proof and failed-update rollback evidence remain
pending external sanitized evidence. The provided test address also needs host-key confirmation and
operator-provided inventory/image digest inputs before any live command can be used as evidence.
ДКБ-69 remains limited by the Python backend interpreter waiver question, and production deployment
approval/PKI/network-owner proof remain outside this repository verification.
