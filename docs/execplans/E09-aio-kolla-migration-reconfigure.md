# ExecPlan: E09 AIO Kolla CLI migration reconfigure

## Цель и наблюдаемый результат

Оператор может выполнить текущий Cloud UI all-in-one через Kolla-Ansible CLI custom playbook не
только в режиме `reconfigure-no-migration`, но и в обычном `reconfigure` с одноразовой миграцией.
Наблюдаемый результат: `cloud-ui db-upgrade --check` выполняется перед `cloud-ui db-upgrade`,
permanent containers остаются идемпотентными, API ready возвращает HTTP 200, frontend возвращает HTTP
200, `/api/v1/session` через frontend возвращает HTTP 401.

## Контекст и текущее состояние

`deploy/kolla/scripts/run-cloud-ui-aio-kolla.py` уже вызывает `kolla-ansible reconfigure -p ... -t
cloud-ui` для bounded AIO path. Предыдущий live evidence запускал только `reconfigure-no-migration`.
`deploy/kolla/ansible/roles/cloud_ui/tasks/live-aio.yml` запускал one-shot migration без отдельного
precheck task. Runtime DB/MQ vars хранятся вне Git в `/root/dawn-cloud-ui-lab-secrets.yml`.

## Scope

- Добавить migration precheck task перед one-shot upgrade в AIO live role.
- Использовать уже отрендеренный backend env-file для one-shot migration контейнеров.
- Выполнить Kolla CLI preflight, migration-enabled reconfigure, no-migration idempotency и smoke на
  approved AIO stand.
- Обновить evidence, DKB traceability и risk register без секретов.

## Non-goals

- Не заявлять full E09 acceptance.
- Не выполнять three-node rollout.
- Не подключать upstream Kolla `site.yml`.
- Не менять DB schema beyond existing Alembic `head`.
- Не коммитить inventory, runtime vars, cookies, tokens, DB/MQ URLs или backup files.

## Требования и ограничения

Работа выполняется только на test stand. Browser остается за frontend/BFF boundary. Runtime secret
values не попадают в Git или вывод Codex. Контейнеры должны оставаться non-root, read-only,
`cap_drop=["ALL"]`, `no-new-privileges:true`. Миграция выполняется явно через one-shot backend image,
API не запускает миграции автоматически.

## Связь с ДКБ

- ДКБ-55/56: runtime DB/MQ inputs остаются вне Git, migration task берет env из rendered backend
  env-file с `no_log` render task.
- ДКБ-65: после reconfigure подтверждается non-root/read-only/cap-drop/no-new-privileges.
- ДКБ-69/70: используется два digest-pinned image из test registry; ДКБ-69 waiver и corporate
  signing/scanning remain pending.
- ДКБ-82: появляется live AIO Kolla CLI evidence для migration-enabled reconfigure; full rollback,
  three-node и upstream `site.yml` remain pending.

## Milestones

1. Зафиксировать baseline и добавить RED/GREEN test на precheck-before-upgrade.
2. Диагностировать первый live failure без раскрытия секретов.
3. Исправить migration env delivery на rendered env-file.
4. Выполнить Kolla CLI preflight, migration-enabled reconfigure, idempotency, endpoint and hardening
   smoke.
5. Обновить evidence/docs and run repository verification.

## Progress

- [x] 2026-06-28: baseline E09 tests passed, `118 passed`.
- [x] 2026-06-28: RED test failed because live AIO role had only `cloud-ui db-upgrade`.
- [x] 2026-06-28: GREEN test passed after adding `cloud-ui db-upgrade --check` before upgrade.
- [x] 2026-06-28: first live `reconfigure` failed at migration precheck with `changed=0`; permanent
  containers were not changed.
- [x] 2026-06-28: diagnostic one-shot precheck showed schema `0006_audit_delivery (head)` and
  `db migration precheck ok`.
- [x] 2026-06-28: root cause isolated to stale wrapper digest input; registry returned 404 for
  `sha256:7e8a4bae326ca7fb505f8f6cf0583ab76e09729886dfdfc77e35d8bc2e659a30`.
- [x] 2026-06-28: migration tasks changed to use rendered backend env-file; targeted role test passed.
- [x] 2026-06-28: Kolla CLI preflight with current digests passed with `localhost ok=10 changed=0
  failed=0`.
- [x] 2026-06-28: migration-enabled Kolla CLI reconfigure passed with `openstack-aio ok=36 changed=2
  failed=0 skipped=1`.
- [x] 2026-06-28: no-migration idempotency passed with `openstack-aio ok=34 changed=0 failed=0
  skipped=3`.
- [x] 2026-06-28: API ready 200, frontend 200, frontend session 401 and sanitized hardening inspect
  passed.

## Неожиданные открытия

- The earlier digest pair was stale. The backend digest
  `sha256:7e8a4bae326ca7fb505f8f6cf0583ab76e09729886dfdfc77e35d8bc2e659a30` produced a registry
  404 during Docker module pull. The live API container used
  `sha256:7e8a4bae48bbc2b3539b33babe39d290b22ae2d61e21d0f886434af1ac2bc438`.
- `cloud-ui db-upgrade --check` itself was healthy against the lab DB and reported
  `0006_audit_delivery (head)`.
- `community.docker.docker_container` succeeds for the migration precheck when using the rendered
  backend env-file. This also avoids passing secret values through the task argument dict.

## Журнал решений

- 2026-06-28: add explicit migration precheck before upgrade. Alternative was to trust Alembic upgrade
  idempotency only; rejected because E09 lifecycle contract requires precheck.
- 2026-06-28: use rendered backend env-file for one-shot migration containers. Alternative was to keep
  `env: "{{ cloud_ui_backend_environment }}"`; rejected because diagnostics showed rendered env-file
  path works and reduces secret exposure in module arguments.
- 2026-06-28: do not claim full E09 acceptance. The evidence is still bounded to AIO custom playbook.

## Детальный план реализации

- Update `tests/test_e09_aio_kolla_role_live.py` to require two migration tasks, precheck before
  upgrade, `no_log`, hardening and rendered env-file.
- Update `deploy/kolla/ansible/roles/cloud_ui/tasks/live-aio.yml`.
- Sync `deploy/kolla/ansible/` to `/etc/kolla/cloud-ui-sync-bundle/`.
- Run wrapper modes `preflight`, `reconfigure`, `reconfigure-no-migration` with current digests.
- Update `docs/generated/e09-deployment-smoke-evidence.md`,
  `docs/generated/e09-kolla-ansible-role.md`, `docs/generated/current-state.md`,
  `docs/generated/risk-register.md`, `docs/11_DKB_TRACEABILITY.md` and this ExecPlan.

## Миграции и совместимость

The live DB was already at Alembic head `0006_audit_delivery`. The migration-enabled run is
expand/idempotent for current schema and is preceded by `db-upgrade --check`. Repeat convergence uses
`reconfigure-no-migration` and skips both migration one-shot tasks.

## Проверка

- `pytest tests/test_e09_aio_kolla_role_live.py -q` expected pass.
- `pytest tests/test_e09_*.py backend/tests/test_cli.py -q` expected pass.
- `ruff check ...` expected pass.
- `./scripts/secret-scan.sh` expected pass.
- `git diff --check` expected pass.
- Live Kolla CLI evidence: preflight `ok=10 changed=0 failed=0`; migration reconfigure `ok=36
  changed=2 failed=0`; no-migration idempotency `ok=34 changed=0 failed=0`; endpoint/hardening smoke
  pass.

## Доказательства

Evidence is recorded in generated docs and DKB traceability. No runtime vars, inventory copy,
container env backup, cookie, token, DB/MQ URL or private key is committed.

## Откат и восстановление

Repository rollback: revert this branch commit. Runtime rollback: restore previous image digests and
config from the AIO rollback snapshot `/root/cloud-ui-aio-rollback-20260628T122556Z` on the test host
or rerun `reconfigure-no-migration` with the previous known-good digest pair. Snapshot contents stay
off-repo because inspect/env backups can contain secrets.

## Итог и остаточные риски

The AIO Kolla CLI custom-playbook path now has live migration-enabled evidence. Remaining risks:
three-node/twelve-container rollout, upstream `site.yml`, HAProxy/VIP/TLS, SELinux labels, corporate
registry signing/scanning/provenance, ДКБ-69 waiver and failed-update rollback are still pending.
