# ExecPlan: E09.4 Migration Job

## Цель и наблюдаемый результат

Оператор получает проверяемый repository-side контракт one-shot migration job для Kolla deployment:
`cloud_ui_db_migrate` использует существующий backend image и команду `cloud-ui db-upgrade`, выполняется
до публикации постоянных контейнеров и не входит в набор четырех permanent services per node. До этой
работы backend CLI уже имел `cloud-ui db-upgrade`, но Kolla role помечала migration ordering как
pending external evidence и не имела отдельного job contract.

## Контекст и текущее состояние

- Текущий этап: `tasks/E09_KOLLA_DEPLOY.md`, единица E09.4 Migration job.
- Ветка/worktree: `e09-migration-job` at `/Users/dmitry/Desktop/dawn/.worktrees/e09-migration-job`.
- `deploy/kolla/ansible/roles/cloud_ui/defaults/main.yml` объявляет четыре permanent services:
  frontend, API, worker and events.
- `backend/src/cloud_ui/cli.py` уже содержит `cloud-ui db-upgrade`, который вызывает Alembic upgrade
  to `head`.
- E09.3 provisioned lab MariaDB runtime and migration users plus Vault paths, but application DB
  migration was explicitly not executed.
- Baseline in this worktree: `make test` passed with backend `327 passed, 1 skipped` and frontend
  `35 passed`.

## Scope

- Add a tested Kolla role migration job definition and execution policy.
- Keep migration job outside permanent container definitions.
- Add backend CLI tests proving API startup does not run Alembic migration and `db-upgrade` remains
  explicit.
- Add sanitized generated evidence and DKB traceability.
- Commit one logical E09.4 repository-side slice.

## Non-goals

- No live `cloud-ui db-upgrade` execution on `192.168.10.15` or `192.168.10.14`.
- No mutation of MariaDB schema in this slice.
- No HAProxy/TLS, process container rollout, three-node deploy, SELinux inspection, registry signing
  or rollback execution.
- No production inventory, credentials, token, private key or database dump in the repository.

## Требования и ограничения

- Browser must not access DB/MQ/OpenStack APIs directly.
- API must not run migrations automatically; migration remains an explicit one-shot command.
- Migration job must use the backend image, not a third custom image.
- Migration secret material must remain Vault/SecMan-backed and outside Git.
- Generated evidence must not contain Vault tokens, unseal keys, DB/MQ passwords or production
  credentials.
- E09 order is mandatory: this slice follows E09.3 and does not start E09.5.

## Связь с ДКБ

| Код | Что реализует план | Что остается внешним | Доказательство | Почему не закрыто полностью |
|---|---|---|---|---|
| ДКБ-55/56 | Migration credential is referenced as E09.3 Vault-backed material, not stored in Git. | Production SecMan endpoint/auth, HA, backup, auto-unseal and rotation. | E09.4 evidence and secret-scan. | Repository contract is not production SecMan acceptance. |
| ДКБ-69/70 | Migration uses existing backend image and preserves two-image contract. | Registry digest pull, package provenance, scanner, signing and ДКБ-69 waiver. | Role tests and generated evidence. | No live image pull/signature evidence in this slice. |
| ДКБ-76/77/80 | Deployment interface documents one-shot migration ordering and API no-auto-migration. | Network ACLs, unused-interface blocking and management-zone proof. | Contract tests and traceability update. | Repository role contract is not live network evidence. |
| ДКБ-82 | Rollback window and repository revert path are documented. | Live failed-update rollback and migration rollback on copied data. | Evidence and ExecPlan rollback section. | No live rollback execution in this slice. |

## Milestones

1. Plan/spec written and reviewed for scope.
2. RED contract tests for migration job role and evidence.
3. GREEN role/default/task implementation.
4. RED/GREEN backend CLI safety tests.
5. Evidence, traceability, risk register updated.
6. Verification, self-review, commit and integration handling.

## Progress

- [x] 2026-06-25: Исследование фактического состояния. Evidence: E09 docs read, role/CLI inspected,
  `make test` baseline passed in worktree.
- [ ] Контракт и тестовый double.
- [ ] Минимальная реализация.
- [ ] Отрицательные сценарии и безопасность.
- [ ] Интеграционные и пользовательские проверки.
- [ ] Документация, evidence и review.

## Неожиданные открытия

- 2026-06-25: New worktree lacked untracked dependency directories. `make test` initially failed
  because `backend/.venv/bin/python` did not exist; `make bootstrap` also failed because `python3.11`
  was absent from PATH. Worktree setup succeeded with `uv sync --python 3.11 --project backend --extra
  dev` and `npm ci`.
- 2026-06-25: Frontend install completed under Node `25.9.0` with an engine warning because package
  policy expects `>=24 <25`. Tests still passed; this remains an environment warning.

## Журнал решений

- 2026-06-25: Use repository contract first, not live migration execution. Alternatives: immediate
  live stand migration or docs-only evidence. Reason: E09.4 needs a tested job contract before mutating
  the lab DB schema; docs-only would not add enough observable behavior. Consequence: live migration
  evidence remains pending.
- 2026-06-25: Reuse `cloud-ui db-upgrade` from the backend image. Alternative: add a separate
  migration image or script. Reason: E09 requires exactly two custom runtime images and the backend
  already packages Alembic. Consequence: no third image is introduced.

## Детальный план реализации

1. Add `tests/test_e09_migration_job.py` with YAML contract tests for role defaults, task imports,
   migration job separation from permanent services, execution policy and generated evidence.
2. Run targeted test and confirm RED.
3. Update `deploy/kolla/ansible/roles/cloud_ui/defaults/main.yml` with non-secret migration defaults:
   `cloud_ui_migration_enabled`, `cloud_ui_migration_job`,
   `cloud_ui_migration_execution_policy`.
4. Add `deploy/kolla/ansible/roles/cloud_ui/tasks/migration.yml` to publish migration job definition
   and execution policy when the role is evaluated.
5. Update `deploy/kolla/ansible/roles/cloud_ui/tasks/main.yml` so `migration.yml` is included after
   config rendering and before permanent container definition publishing.
6. Add backend CLI tests proving `cloud-ui api` does not call Alembic `upgrade` and `cloud-ui
   db-upgrade` is the explicit path.
7. Add `docs/generated/e09-migration-job.md`, update `docs/11_DKB_TRACEABILITY.md`, update
   `docs/generated/risk-register.md` and keep this ExecPlan current.
8. Run targeted tests and full gates.

## Миграции и совместимость

This slice does not execute a DB schema migration. It defines the Kolla ordering and command contract
for an expand-compatible `cloud-ui db-upgrade` before API/worker/events rollout. Re-running the
repository role evaluation is idempotent because it publishes definitions and policy facts. Live
execution must use a lock and an approved rollback window before any contract migration. API startup
does not apply migrations automatically, preserving rolling-update control.

## Проверка

Run from `/Users/dmitry/Desktop/dawn/.worktrees/e09-migration-job`:

- `backend/.venv/bin/python -m pytest tests/test_e09_migration_job.py -q`
- `backend/.venv/bin/python -m pytest tests/test_e09_migration_job.py tests/test_e09_kolla_ansible_role.py tests/test_e09_db_rabbitmq_provisioning.py -q`
- `make lint`
- `make typecheck`
- `make security`
- `make test`
- `git diff --check`

Expected final result: all commands exit 0. The first targeted test run must fail before
implementation.

## Доказательства

- `tests/test_e09_migration_job.py`
- `deploy/kolla/ansible/roles/cloud_ui/defaults/main.yml`
- `deploy/kolla/ansible/roles/cloud_ui/tasks/migration.yml`
- `docs/generated/e09-migration-job.md`
- `docs/11_DKB_TRACEABILITY.md`
- `docs/generated/risk-register.md`
- This ExecPlan

## Откат и восстановление

Repository rollback is a Git revert of the E09.4 commit. Because this slice does not execute live
migration, no DB cleanup is required. If a later approved live run uses this contract, rollback must
restore the previous backend/frontend image digests and config commit, avoid contract migrations until
after the rollback window, and validate migration rollback on a copy of data before production use.

## Итог и остаточные риски

Not completed yet. Remaining expected risks: no live migration execution, no failed migration retry
evidence, no copied-data downgrade proof, no three-node rollout and no production SecMan/registry/TLS
owner evidence.
