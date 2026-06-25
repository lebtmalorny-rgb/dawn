# ExecPlan: E09.5 Process Containers

## Цель и наблюдаемый результат

Оператор получает проверяемый repository-side контракт permanent process topology для Kolla
deployment: три control/UI nodes × четыре процесса (`frontend`, `api`, `worker`, `events`) дают
12 permanent containers, а `cloud_ui_db_migrate` остается one-shot job вне постоянного набора. До этой
работы роль объявляла четыре service definitions, но не фиксировала three-node topology matrix и
summary counts.

## Контекст и текущее состояние

- Текущий этап: `tasks/E09_KOLLA_DEPLOY.md`, единица E09.5 Process containers.
- Ветка/worktree: `e09-process-containers` at
  `/Users/dmitry/Desktop/dawn/.worktrees/e09-process-containers`.
- `deploy/kolla/ansible/roles/cloud_ui/defaults/main.yml` defines four permanent services and one
  separate migration job.
- `deploy/kolla/ansible/roles/cloud_ui/tasks/containers.yml` currently publishes only
  `cloud_ui_container_definitions`.
- Baseline in this worktree: `make test` passed backend `327 passed, 1 skipped` and frontend
  `35 passed`; `backend/.venv/bin/python -m pytest tests -q` passed `28 passed`.

## Scope

- Add synthetic three-node process topology defaults and facts.
- Preserve exactly two custom images and the four-per-node permanent process set.
- Keep migration job outside permanent containers.
- Add tests, generated evidence, DKB traceability and risk register updates.
- No live Kolla deployment or HAProxy/TLS work.

## Non-goals

- No live container start, Kolla deploy/reconfigure or host inspection.
- No HAProxy/TLS/network routing.
- No image digest pull, registry push, scanner, signature or SBOM update.
- No SELinux label inspection or filesystem/capability evidence.
- No production inventory, credentials, token, private key, `.env` or real cloud config.

## Требования и ограничения

- Exactly two custom images remain: `cloud-ui-frontend` and `cloud-ui-backend`.
- API, worker and events use one backend image with different commands/config roles.
- Permanent topology must be 3 nodes × 4 services = 12 containers.
- Migration job is one-shot and must not be counted as permanent.
- Repository evidence must not claim live deployment, production approval or Kolla HA readiness.

## Связь с ДКБ

| Код | Что реализует план | Что остается внешним | Доказательство | Почему не закрыто полностью |
|---|---|---|---|---|
| ДКБ-69/70 | Preserves two-image contract and process-to-image mapping. | Registry digest, scanner, signing, package provenance and ДКБ-69 waiver. | Topology tests and E09.5 evidence. | No live image pull or scanner/signature proof. |
| ДКБ-76/77/80 | Documents deployment process interfaces and expected 12-container topology. | Network ACLs, management zones, unused interface blocking, HAProxy/TLS and live inspection. | Generated process-container evidence and traceability. | Synthetic topology is not live network/container evidence. |
| ДКБ-82 | Records repository rollback and keeps migration separate from permanent rollout. | Live reconfigure, rolling update and failed-update rollback. | ExecPlan and risk register. | No live rollback execution in this slice. |

## Milestones

1. Plan/spec written and committed.
2. RED process topology tests.
3. GREEN role topology defaults/facts.
4. Validation and adjacent contract updates.
5. Evidence/traceability/risk updates.
6. Verification, self-review, commit and integration handling.

## Progress

- [x] 2026-06-25: Исследование фактического состояния. Evidence: E09 docs and E08 security review
  read; role defaults/tasks/tests inspected; baseline `make test` and root `tests` passed.
- [x] 2026-06-25: Контракт и тестовый double. Evidence:
  `backend/.venv/bin/python -m pytest tests/test_e09_process_containers.py -q` failed with missing
  topology defaults, missing topology facts, missing generated evidence and missing traceability/risk
  references.
- [x] 2026-06-25: Минимальная реализация. Evidence:
  `backend/.venv/bin/python -m pytest tests/test_e09_process_containers.py -q` passed `8 passed`.
- [x] 2026-06-25: Отрицательные сценарии и безопасность. Evidence: tests verify migration job is not
  part of permanent topology, topology contains no secret keywords, and evidence does not claim
  production approval or live 12-container proof.
- [x] 2026-06-25: Интеграционные и пользовательские проверки. Evidence:
  `backend/.venv/bin/python -m pytest tests/test_e09_process_containers.py tests/test_e09_kolla_ansible_role.py tests/test_e09_migration_job.py -q`
  passed `24 passed`.
- [x] 2026-06-25: Документация, evidence и review. Evidence: generated E09.5 evidence,
  traceability, risk register and adjacent E09.2/E09.4 evidence were updated; `backend/.venv/bin/python
  -m pytest tests -q`, `make lint`, `make typecheck`, `make security`, `make test` and
  `git diff --check` passed.

## Неожиданные открытия

- 2026-06-25: New worktree lacked untracked dependency directories. `make test` initially failed with
  missing `backend/.venv/bin/python`; setup succeeded with `uv sync --python 3.11 --project backend
  --extra dev` and `npm ci`.
- 2026-06-25: `npm ci` completed with the existing Node engine warning: project expects `>=24 <25`,
  current runtime is `v25.9.0`.

## Журнал решений

- 2026-06-25: Use repository/synthetic topology proof first, not live deploy. Alternatives:
  single-node dry run or immediate live rollout. Reason: E09.5 must prove process topology before
  E09.6/E09.7 HAProxy/reconfigure/rollback. Consequence: live container evidence remains pending.
- 2026-06-25: Keep topology node names synthetic (`control-ui-01..03`) instead of real inventory host
  names. Alternatives: copy lab/production inventory hostnames. Reason: avoid committing inventory
  assumptions or production identifiers while still proving cardinality. Consequence: live mapping is
  pending E09.7/E09.8 evidence.

## Детальный план реализации

1. Add `tests/test_e09_process_containers.py` requiring process topology defaults, 12 entries,
   process/image/command mapping, migration exclusion, task fact publishing and evidence.
2. Run the new test and confirm RED.
3. Update `deploy/kolla/ansible/roles/cloud_ui/defaults/main.yml` with:
   `cloud_ui_control_ui_nodes`, `cloud_ui_expected_control_ui_node_count`,
   `cloud_ui_expected_permanent_containers_total`, `cloud_ui_process_topology`.
4. Update `deploy/kolla/ansible/roles/cloud_ui/tasks/containers.yml` to publish topology and summary
   facts.
5. Update `deploy/kolla/ansible/roles/cloud_ui/tasks/validate.yml` with count assertions.
6. Update existing E09 role tests if old E09.2 assumptions need to recognize E09.5 topology.
7. Add `docs/generated/e09-process-containers.md`, update `docs/11_DKB_TRACEABILITY.md`,
   `docs/generated/risk-register.md` and this ExecPlan.
8. Run targeted and full verification.

## Миграции и совместимость

No database schema, OpenAPI, runtime command or frontend behavior changes are planned. Rolling update
compatibility is unaffected. The topology contract preserves API/worker/events commands and keeps
`cloud_ui_db_migrate` separate. Rollback is a Git revert of the E09.5 commits.

## Проверка

Run from `/Users/dmitry/Desktop/dawn/.worktrees/e09-process-containers`:

- `backend/.venv/bin/python -m pytest tests/test_e09_process_containers.py -q`
- `backend/.venv/bin/python -m pytest tests/test_e09_process_containers.py tests/test_e09_kolla_ansible_role.py tests/test_e09_migration_job.py -q`
- `backend/.venv/bin/python -m pytest tests -q`
- `make lint`
- `make typecheck`
- `make security`
- `make test`
- `git diff --check`

Expected final result: all commands exit 0. The first targeted E09.5 test must fail before
implementation.

## Доказательства

- `tests/test_e09_process_containers.py`
- `deploy/kolla/ansible/roles/cloud_ui/defaults/main.yml`
- `deploy/kolla/ansible/roles/cloud_ui/tasks/containers.yml`
- `deploy/kolla/ansible/roles/cloud_ui/tasks/validate.yml`
- `docs/generated/e09-process-containers.md`
- `docs/11_DKB_TRACEABILITY.md`
- `docs/generated/risk-register.md`
- This ExecPlan

## Откат и восстановление

Repository rollback is `git revert` of the E09.5 commits. This slice does not mutate remote hosts,
database schema, RabbitMQ, Vault, registry or Kolla inventory, so no live cleanup is required.

## Итог и остаточные риски

Implemented E09.5 as a tested repository-side process topology contract. The role defines three
synthetic control/UI nodes, twelve permanent topology entries, topology summary facts and validation
for the 3x4=12 contract while keeping `cloud_ui_db_migrate` outside the permanent set.

Residual risks: no live 12-container inspection, no registry digest pull, no SELinux/caps/mount
proof, no HAProxy/TLS URL, no rolling update or rollback execution and no production
SecMan/registry/network owner evidence.
