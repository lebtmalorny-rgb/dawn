# ExecPlan: E09.7 Reconfigure Upgrade Rollback

## Цель и наблюдаемый результат

Оператор получает проверяемый repository-side lifecycle contract для Cloud UI Kolla deployment:
clean deploy/reconfigure, idempotent reconfigure, rolling upgrade, failed update rollback and
disable/uninstall path описаны как упорядоченные фазы с prechecks, gates, rollback decision table and
evidence requirements. До этой работы роль описывала images, services, migration job, process topology
and HAProxy route, но не фиксировала безопасный порядок reconfigure/upgrade/rollback.

## Контекст и текущее состояние

- Текущий этап: `tasks/E09_KOLLA_DEPLOY.md`, единица E09.7 Reconfigure/upgrade/rollback.
- Ветка/worktree: `e09-reconfigure-rollback` at
  `/Users/dmitry/Desktop/dawn/.worktrees/e09-reconfigure-rollback`.
- `deploy/AGENTS.md` requires deployment commands to be documented/dry-run by default; real execution
  only in explicitly provided test environment.
- `deploy/kolla/ansible/roles/cloud_ui/defaults/main.yml` already contains:
  - two images: `cloud-ui-frontend` and `cloud-ui-backend`;
  - four permanent services per node;
  - one-shot `cloud_ui_db_migrate` job and migration execution policy;
  - synthetic 3-node / 12-container process topology;
  - same-origin HAProxy route contract.
- `deploy/kolla/ansible/roles/cloud_ui/tasks/main.yml` includes validation, config, migration and
  container-definition tasks. No lifecycle task currently exists.
- Baseline in this worktree:
  - `uv sync --python 3.11 --project backend --extra dev` was required because host `python3.11` is
    not directly available and system `python3` is `3.14.0`;
  - `npm --prefix frontend ci` completed with the existing Node engine warning (`v25.9.0` vs
    `>=24 <25`);
  - `make test` passed backend `327 passed, 1 skipped` and frontend `35 passed`.

## Scope

- Add non-secret role defaults for E09.7 lifecycle policy:
  clean deploy, reconfigure, rolling upgrade, failed update rollback and disable/uninstall.
- Add a role task that publishes lifecycle facts for later Kolla execution/dry-run tooling without
  invoking live `kolla-ansible`.
- Add validation rules for phase ordering and required gates.
- Add tests proving:
  - migration runs before incompatible backend rollout;
  - images are pulled by digest before rollout;
  - backend rolls before frontend;
  - HAProxy/smoke gates happen after service rollout;
  - rollback stops before contract migration and preserves queued operations;
  - disable/uninstall path is explicit and non-destructive by default;
  - no production inventory, secrets or live deployment commands are introduced.
- Add generated E09.7 evidence and update DKB traceability and risk register.

## Non-goals

- No live `kolla-ansible deploy`, `reconfigure`, `upgrade`, `destroy`, `stop`, `pull` or `rollback`
  execution.
- No test inventory, production inventory, hostnames, passwords, private keys, openrc, clouds.yaml,
  `.env` or registry credentials in Git.
- No registry push/pull by digest proof, scanner/signing proof or live container inspection.
- No DB schema mutation, live migration execution or copied-data rollback test.
- No HAProxy URL smoke, TLS scan, SELinux/caps/mount inspection or E09.8 evidence.
- No frontend/UI behavior change.

## Требования и ограничения

- E09 remains test-inventory only. Production actions are forbidden.
- Migration stays one-shot and explicit; API startup must not run migrations automatically.
- Rolling update must stay compatible with schema/API rollback window.
- Backend image remains shared by API, worker, events, migration and smoke.
- Rollback must not delete queued operations, audit events or read model data.
- Destructive uninstall is not allowed by default; disable path must preserve data and require
  explicit cleanup approval.
- Repository contract must not claim live deploy/reconfigure/rollback acceptance.

## Связь с ДКБ

| Код | Что реализует план | Что остается внешним | Доказательство | Почему не закрыто полностью |
|---|---|---|---|---|
| ДКБ-55/56 | Lifecycle ordering references existing Vault/SecMan secret path and no Git secrets. | Full Kolla/OpenStack/MariaDB/RabbitMQ/SIEM/PKI secret rotation. | Tests and E09.7 evidence show no secret material. | No live rotation/revoke evidence. |
| ДКБ-69/70 | Lifecycle requires digest-pinned image pull before rollout and preserves two-image contract. | Registry digest pull, scanner, signing, SBOM tied to deployed digests and ДКБ-69 waiver. | Lifecycle tests and evidence. | No live registry or scanner output. |
| ДКБ-76/77/80 | Adds deployment lifecycle interface, disable path and rollback gates. | Firewall/ACL, management-zone scan and disabled unused interface proof. | Generated E09.7 evidence, network/risk references. | Repository lifecycle contract is not live network enforcement. |
| ДКБ-82 | Documents operational lifecycle and rollback path. | Executed rolling update, failed update rollback and uninstall/disable run in test. | ExecPlan and evidence doc. | No live rollback execution in this slice. |

## Milestones

1. Plan/spec written and committed.
2. RED lifecycle contract tests.
3. GREEN role defaults/task/validation lifecycle contract.
4. Evidence, DKB traceability and risk register updates.
5. Verification, self-review, commit and integration to `main`.

## Progress

- [x] 2026-06-25: Исследование фактического состояния. Evidence: E09 task and listed docs were read;
  `deploy/AGENTS.md`, role tasks/defaults and existing E09 tests inspected; baseline `make test`
  passed after Python 3.11 setup.
- [ ] Контракт и тестовый double.
- [ ] Минимальная реализация.
- [ ] Отрицательные сценарии и безопасность.
- [ ] Интеграционные и пользовательские проверки.
- [ ] Документация, evidence и review.

## Неожиданные открытия

- 2026-06-25: New worktree setup again requires `uv --python 3.11` because `python3.11` is not on PATH
  and system `python3` is outside backend version bounds.
- 2026-06-25: `npm --prefix frontend ci` still succeeds with Node engine warning for local
  `v25.9.0`; this is unrelated to E09.7.

## Журнал решений

- 2026-06-25: Implement repository lifecycle contract first, not live Kolla reconfigure. Alternatives:
  immediate live lab run or jumping to E09.8 smoke. Reason: live execution needs registry digests,
  test inventory overrides and rollback window proof; repository contract gives safe ordering and
  testable gates without false claims. Consequence: live deploy/rollback evidence remains pending.
- 2026-06-25: Model disable/uninstall as data-preserving by default. Alternatives: include destructive
  cleanup in role defaults. Reason: deleting DB/RabbitMQ/Vault paths requires explicit approval and
  external backup/retention policy. Consequence: cleanup remains a separate approved runbook step.

## Детальный план реализации

1. Add `tests/test_e09_reconfigure_rollback.py` requiring lifecycle defaults, phase ordering,
   dry-run task facts, validation assertions, generated evidence, DKB traceability and risk row.
2. Run the new test and confirm RED.
3. Update `deploy/kolla/ansible/roles/cloud_ui/defaults/main.yml` with:
   - `cloud_ui_lifecycle_contract_version`;
   - `cloud_ui_lifecycle_dry_run_only`;
   - `cloud_ui_deploy_reconfigure_phases`;
   - `cloud_ui_rolling_upgrade_phases`;
   - `cloud_ui_failed_update_rollback_phases`;
   - `cloud_ui_disable_uninstall_policy`;
   - `cloud_ui_rollback_decision_table`.
4. Add `deploy/kolla/ansible/roles/cloud_ui/tasks/lifecycle.yml` to publish lifecycle facts for
   later Kolla execution tooling.
5. Include `lifecycle.yml` from `tasks/main.yml` after validation and before live container data.
6. Update `tasks/validate.yml` with phase/gate assertions.
7. Update adjacent E09 role tests if they list expected role files/imports.
8. Add `docs/generated/e09-reconfigure-rollback.md`, update `docs/11_DKB_TRACEABILITY.md`,
   `docs/generated/risk-register.md` and this ExecPlan.
9. Run targeted and full verification.

## Миграции и совместимость

No database schema, OpenAPI, backend runtime command or frontend behavior changes are planned. The
lifecycle contract explicitly keeps migration before incompatible rollout and before any contract
migration. Rollback is allowed only inside compatibility window and before contract migration. The
repository change itself is rollback-safe by Git revert.

## Проверка

Run from `/Users/dmitry/Desktop/dawn/.worktrees/e09-reconfigure-rollback`:

- `backend/.venv/bin/python -m pytest tests/test_e09_reconfigure_rollback.py -q`
- `backend/.venv/bin/python -m pytest tests/test_e09_reconfigure_rollback.py tests/test_e09_kolla_ansible_role.py tests/test_e09_haproxy_tls_network.py tests/test_e09_process_containers.py tests/test_e09_migration_job.py -q`
- `backend/.venv/bin/python -m pytest tests -q`
- `make lint`
- `make typecheck`
- `make security`
- `make test`
- `git diff --check`

Expected final result: all commands exit 0. The first E09.7 test run must fail before implementation.

## Доказательства

- `tests/test_e09_reconfigure_rollback.py`
- `deploy/kolla/ansible/roles/cloud_ui/defaults/main.yml`
- `deploy/kolla/ansible/roles/cloud_ui/tasks/main.yml`
- `deploy/kolla/ansible/roles/cloud_ui/tasks/lifecycle.yml`
- `deploy/kolla/ansible/roles/cloud_ui/tasks/validate.yml`
- `docs/generated/e09-reconfigure-rollback.md`
- `docs/generated/risk-register.md`
- `docs/11_DKB_TRACEABILITY.md`
- This ExecPlan

## Откат и восстановление

Repository rollback is `git revert` of the E09.7 commits. This slice does not mutate remote hosts,
Vault, MariaDB, RabbitMQ, registry, Kolla inventory or HAProxy. If a later approved test run uses this
contract, rollback must use the recorded failed-update phases before contract migration and must not
delete queued operations or audit/read-model state.

## Итог и остаточные риски

Pending implementation.
