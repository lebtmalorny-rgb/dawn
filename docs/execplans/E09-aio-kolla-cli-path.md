# ExecPlan: E09 AIO Kolla CLI Path

## Цель и наблюдаемый результат

Оператор получает воспроизводимый all-in-one путь запуска Cloud UI через `kolla-ansible
reconfigure -p <custom-playbook>`, а не прямой `ansible-playbook`. После запуска AIO UI должен
оставаться доступным: frontend HTTP 200, API readiness HTTP 200, frontend `/api/v1/session` HTTP
401, контейнеры non-root/read-only/cap-drop/no-new-privileges.

## Контекст и текущее состояние

- `main` на commit `4bb4011` уже содержит default-off AIO live role mode:
  `deploy/kolla/ansible/playbooks/cloud-ui-aio-reconfigure.yml` и
  `deploy/kolla/ansible/roles/cloud_ui/tasks/live-aio.yml`.
- Live evidence 2026-06-28 подтверждает direct role playbook path:
  preflight `ok=10 changed=0 failed=0`, AIO role reconfigure `ok=35 changed=6 failed=0 skipped=1`,
  repeat with `cloud_ui_aio_run_migration=false` `ok=34 changed=0 failed=0 skipped=2`.
- Read-only host discovery showed Kolla-Ansible `20.4.1.dev5` at `/root/venvs/kolla-epoxy/bin/kolla-ansible`.
  CLI help supports `reconfigure -p PLAYBOOKS`.
- Upstream Kolla `site.yml` in the venv has a fixed service list, so this slice will not mutate that
  vendor file.

## Scope

- Add a repository wrapper for safe AIO Kolla CLI invocation.
- Add tags to the custom AIO playbook/role so `-t cloud-ui` can filter the run.
- Add non-secret vars example for the AIO Kolla CLI path.
- Sync and execute the wrapper path on the approved AIO test stand.
- Update evidence, traceability and risk register.

## Non-goals

- No upstream `site.yml` patch.
- No HAProxy/VIP/TLS route enablement.
- No three-node/twelve-container rollout.
- No production inventory or credential use.
- No committed DB/MQ runtime URL, token, private key, `clouds.yaml`, openrc or `.env`.
- No full E09 acceptance claim.

## Требования и ограничения

- Browser remains behind frontend/BFF only.
- Runtime secrets stay outside Git and are supplied through external vars/secret mechanism.
- Mutating live run requires test marker, rollback window and digest-pinned images.
- Kolla CLI path must be idempotent and safe to repeat with migration disabled.
- ДКБ-69 remains open because backend runtime contains Python.

## Связь с ДКБ

| Код | Что реализует план | Что остается внешним | Доказательство | Почему не полное закрытие |
|---|---|---|---|---|
| ДКБ-55/56 | Wrapper does not store or print runtime secrets; vars example is placeholder-only. | SecMan/Kolla full rotation, revoke and owner approval. | Tests, secret scan, evidence docs. | Runtime secret lifecycle is external. |
| ДКБ-65 | AIO Kolla CLI path preserves non-root/read-only/cap-drop evidence. | SELinux labels and host denial proof. | Sanitized inspect. | AIO Docker inspect is not host policy evidence. |
| ДКБ-69/70 | Digest image inputs required; no `latest`. | Formal Python waiver, corporate scan/signing/provenance. | Contract tests and live digest evidence. | Registry policy remains external. |
| ДКБ-76/77/80 | Kolla CLI operator path for AIO direct-port deployment. | HAProxy/VIP/TLS, management VLAN and ACL proof. | Kolla CLI recap and endpoint smoke. | Direct AIO ports are not network acceptance. |
| ДКБ-82 | Reconfigure and idempotency through Kolla CLI custom playbook. | Upstream `site.yml`, rolling update and failed rollback. | Live recap and evidence doc. | Custom playbook path is partial AIO acceptance only. |

## Milestones

1. Repository contract and tests for Kolla CLI wrapper/tags.
2. Minimal wrapper and non-secret vars example.
3. Local verification and bundle evidence refresh.
4. Remote sync and live AIO `kolla-ansible reconfigure -p` run.
5. Evidence, traceability, risk register and final review.

## Progress

- [x] 2026-06-28: Исследование фактического состояния. Evidence: E09 task/docs read, current role
  inspected, Kolla host CLI help confirms `reconfigure -p`, baseline E09 pytest `108 passed`.
- [ ] Контракт и тестовый double.
- [ ] Минимальная реализация.
- [ ] Отрицательные сценарии и безопасность.
- [ ] Интеграционные и пользовательские проверки.
- [ ] Документация, evidence и review.

## Неожиданные открытия

- Kolla-Ansible custom playbooks are supported by CLI option `-p PLAYBOOKS`; this allows an AIO path
  without mutating venv-owned upstream `site.yml`.

## Журнал решений

- 2026-06-28: Use `kolla-ansible reconfigure -p` wrapper instead of patching upstream `site.yml`.
  Alternatives: direct `ansible-playbook` remains too far from Kolla CLI; patching `site.yml` is
  brittle and should wait for a full service integration design.

## Детальный план реализации

1. Add tests in `tests/test_e09_aio_kolla_cli_path.py` requiring:
   - wrapper script exists;
   - safe commands contain `kolla-ansible reconfigure -p ... -t cloud-ui`;
   - unsafe verbs and production-looking inventories are rejected;
   - no runtime secret values or `latest` image refs are accepted;
   - AIO playbook/role tasks carry `cloud-ui` tags.
2. Add `deploy/kolla/scripts/run-cloud-ui-aio-kolla.py` with an allowlisted command builder and CLI.
3. Add `deploy/kolla/ansible/examples/cloud-ui-aio-kolla-vars.yml.example` with only non-secret
   placeholders and comments for external secret vars.
4. Tag `cloud-ui-aio-reconfigure.yml` and `live-aio.yml` for `cloud-ui`.
5. Update `export-ansible-bundle.py` allowlist and generated evidence to include the new example.
6. Sync the updated bundle to `/etc/kolla/cloud-ui-sync-bundle` and run live Kolla CLI path.
7. Update generated evidence and traceability.

## Миграции и совместимость

No database schema migration is introduced. The existing one-shot `cloud-ui db-upgrade` command
remains controlled by `cloud_ui_aio_run_migration`. Repeat reconfigure should use
`reconfigure-no-migration`.

Rollback is a Git revert plus re-syncing the previous bundle. On the test host, use the existing
rollback snapshot if container state must be restored.

## Проверка

Local:

- `UV_CACHE_DIR=/tmp/dawn-uv-cache UV_PYTHON_INSTALL_DIR=/tmp/dawn-uv-python UV_PROJECT_ENVIRONMENT=/tmp/dawn-backend-venv uv run --python 3.11 --project backend --extra dev pytest tests/test_e09_*.py backend/tests/test_cli.py -q`
- `./scripts/secret-scan.sh`
- `git diff --check`
- targeted `ruff check` for changed Python files.

Live AIO:

- sync `deploy/kolla/ansible` and wrapper to the Ansible host;
- create rollback snapshot;
- run wrapper `preflight`;
- run wrapper `reconfigure-no-migration` through `kolla-ansible reconfigure -p`;
- check API ready 200, frontend 200, frontend session 401 and sanitized inspect.

## Доказательства

- `docs/generated/e09-deployment-smoke-evidence.md`
- `docs/generated/e09-kolla-ansible-role.md`
- `docs/generated/e09-ansible-sync-bundle.md`
- `docs/generated/current-state.md`
- `docs/generated/risk-register.md`
- `docs/11_DKB_TRACEABILITY.md`

## Откат и восстановление

Repository rollback: revert this slice commit. Remote rollback: re-sync the previous
`/etc/kolla/cloud-ui-sync-bundle` content or use the existing all-in-one rollback snapshot. Do not
copy snapshot env/inspect contents into Git.

## Итог и остаточные риски

Pending until implementation and live evidence are complete.
