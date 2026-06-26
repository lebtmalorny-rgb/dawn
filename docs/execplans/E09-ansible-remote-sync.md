# ExecPlan: E09 Ansible remote sync

## Цель и наблюдаемый результат

Оператор получает repository-side доказательство для E09 Ansible remote sync: локально собранный bundle
можно проверить helper-ом для approved test Ansible host `192.168.10.15` и пути
`/etc/kolla/cloud-ui-sync-bundle` без запуска удаленных команд. Наблюдаемый результат текущей задачи:
committed evidence file `docs/generated/e09-ansible-remote-sync.md`, обновленная трассировка ДКБ и risk
register, а также dry-run helper output с exit 0. До этой задачи pytest-контракт падал, потому что
committed evidence отсутствовал.

## Контекст и текущее состояние

Рабочая ветка: `e09-ansible-remote-sync`. Фактический контракт находится в
`tests/test_e09_ansible_remote_sync.py`: helper должен валидировать локальный bundle, отвергать
tampered/extra/credential-like files, строить только ограниченную форму remote commands и проверять
committed docs на отсутствие overclaim. Экспортер `deploy/kolla/scripts/export-ansible-bundle.py`
разрешает evidence path только под `docs/generated`. Remote sync helper
`deploy/kolla/scripts/sync-ansible-remote-bundle.py` имеет approved host `192.168.10.15`, approved path
`/etc/kolla/cloud-ui-sync-bundle` и role path note
`ANSIBLE_ROLES_PATH=/etc/kolla/cloud-ui-sync-bundle/roles`.

## Scope

- Сформировать локальный bundle в `/tmp/dawn-e09-ansible-remote-sync-bundle`.
- Выполнить только dry-run remote sync helper без `--execute`.
- Создать `docs/generated/e09-ansible-remote-sync.md`.
- Создать этот ExecPlan в `docs/execplans/E09-ansible-remote-sync.md`.
- Обновить `docs/11_DKB_TRACEABILITY.md` и `docs/generated/risk-register.md`.
- Проверить pytest contract, ruff для test/helper, secret scan и whitespace diff.

## Non-goals

- Не контактировать с `192.168.10.15`.
- Не запускать SSH, rsync transfer или remote verification pullback.
- Не запускать Kolla command, migration, deployment smoke или rollback.
- Не ремонтировать DB/MQ auth.
- Не доказывать 12 running containers, HAProxy/TLS, SELinux hardening, registry signing or production
  acceptance.
- Не добавлять secrets, inventory, openrc, `.env`, private keys, dumps or production credential URLs.

## Требования и ограничения

- Браузерные и backend архитектурные инварианты не меняются.
- Secret material не попадает в Git, logs или evidence.
- Действия ограничены local docs/evidence, без remote mutation.
- Current slice остается `remote-sync-only`; все live rows остаются `pending_external_evidence`.
- В финальном commit должны попасть только четыре Task 3 файла.

## Связь с ДКБ

- ДКБ-55/56: план доказывает, что remote-sync evidence не содержит runtime secret value. Secret
  delivery, rotation and DB/MQ auth remediation остаются во внешнем контуре с
  `pending_external_evidence`.
- ДКБ-65: план не доказывает SELinux/AppArmor enforcing состояние; copied artifacts/checksums only.
- ДКБ-69: план не закрывает Python interpreter waiver и не доказывает hardened live image baseline.
- ДКБ-70: план не доказывает corporate registry signing/provenance or pull-by-digest.
- ДКБ-76/77/80: план документирует operator artifact delivery boundary, но не доказывает live
  container, interface blocking or management-zone ACL.
- ДКБ-82: план добавляет эксплуатационную документацию и rollback note для local docs-only undo, но не
  live rollback execution.

## Milestones

1. Contract read and RED check: run `tests/test_e09_ansible_remote_sync.py` and observe committed docs
   failure.
2. Bundle/export dry-run: create `/tmp/dawn-e09-ansible-remote-sync-bundle` with temporary generated
   evidence and run sync helper without `--execute`.
3. Docs/evidence: create evidence, ExecPlan, DKB traceability section and R-071 row.
4. Verification and cleanup: run required commands, remove temporary generated side effects and review
   final diff.
5. Commit Task 3 docs only.

## Progress

- [x] 2026-06-26: Contract tests reviewed; initial pytest run failed only on missing committed evidence.
- [x] 2026-06-26: Helper and exporter behavior reviewed; dry-run helper command is scoped to approved
  host/path and does not execute remote commands without `--execute`.
- [x] 2026-06-26: Docs/evidence content drafted for remote-sync-only scope.
- [x] 2026-06-26: Approved remote copy to
  `192.168.10.15:/etc/kolla/cloud-ui-sync-bundle` completed with helper `--execute`; pull-back
  checksum verification passed and read-only marker returned `remote_bundle_present`.
- [ ] Final external review and live deployment evidence acceptance remain pending.

## Неожиданные открытия

- Initial pytest already covered 11 helper/security scenarios and failed only because
  `docs/generated/e09-ansible-remote-sync.md` was absent. Evidence: first local pytest run.
- The exporter enforces generated evidence under `docs/generated`, so temporary local export evidence must
  use `docs/generated/e09-ansible-remote-sync-local.md` and be removed before commit.
- The approved remote sync created/refreshed `/etc/kolla/cloud-ui-sync-bundle` on `192.168.10.15` and
  recorded backup path `/etc/kolla/cloud-ui-sync-bundle.backup-20260626T132956Z`. This is still
  artifact delivery evidence only; no Kolla command was run.

## Журнал решений

- 2026-06-26: Keep final evidence as remote-sync-only and set `remote_verified=false`,
  `remote_file_count=0`, `backup_path=not-created-yet`. Alternative rejected: using dry-run command
  timestamp backup path as if a remote backup existed. Reason: no remote copy occurred.
- 2026-06-26: Add a separate R-071 risk instead of broadening R-070. Reason: R-070 covers local-only
  export; R-071 covers the new risk that remote-sync-only delivery may be mistaken for live deployment
  evidence.
- 2026-06-26: Run the approved copy through `sync-ansible-remote-bundle.py --execute` rather than ad
  hoc `rsync`. Reason: the helper performs staging, path-scoped backup, remote pull-back validation and
  manifest checksum comparison before writing evidence.

## Детальный план реализации

- Create `/tmp/dawn-e09-ansible-remote-sync-bundle` with
  `deploy/kolla/scripts/export-ansible-bundle.py --output-dir /tmp/dawn-e09-ansible-remote-sync-bundle --evidence docs/generated/e09-ansible-remote-sync-local.md`.
- Run `deploy/kolla/scripts/sync-ansible-remote-bundle.py --bundle-dir /tmp/dawn-e09-ansible-remote-sync-bundle --remote-host 192.168.10.15 --remote-path /etc/kolla/cloud-ui-sync-bundle` without `--execute`.
- Create `docs/generated/e09-ansible-remote-sync.md` from the local manifest and helper contract.
- Insert `## E09 Ansible remote sync` immediately before `## Полная матрица` in
  `docs/11_DKB_TRACEABILITY.md`.
- Append R-071 after R-070 in `docs/generated/risk-register.md`.
- Remove temporary `docs/generated/e09-ansible-remote-sync-local.md` before commit.

## Миграции и совместимость

No database, OpenAPI, container image or runtime migration is introduced. The change is docs/evidence
only and is compatible with rolling update because it changes no deployed code. Rollback is Git revert
of the four documentation files. Re-running the local bundle export is safe after removing the `/tmp`
bundle directory because the exporter requires an empty output directory.

## Проверка

Run from `/Users/dmitry/Desktop/dawn/.worktrees/e09-ansible-remote-sync`:

- `UV_CACHE_DIR=/tmp/dawn-uv-cache UV_PYTHON_INSTALL_DIR=/tmp/dawn-uv-python UV_PROJECT_ENVIRONMENT=/tmp/dawn-e09-remote-sync-venv uv run --python 3.11 --project backend --extra dev pytest tests/test_e09_ansible_remote_sync.py -q`
- `UV_CACHE_DIR=/tmp/dawn-uv-cache UV_PYTHON_INSTALL_DIR=/tmp/dawn-uv-python UV_PROJECT_ENVIRONMENT=/tmp/dawn-e09-remote-sync-venv uv run --python 3.11 --project backend --extra dev ruff check tests/test_e09_ansible_remote_sync.py deploy/kolla/scripts/sync-ansible-remote-bundle.py`
- `./scripts/secret-scan.sh`
- `git diff --check`

Expected result: all commands exit 0. No `kolla` live command is required or allowed for this plan.

## Доказательства

- `docs/generated/e09-ansible-remote-sync.md`
- `docs/11_DKB_TRACEABILITY.md`
- `docs/generated/risk-register.md`
- `tests/test_e09_ansible_remote_sync.py`
- `deploy/kolla/scripts/sync-ansible-remote-bundle.py`
- Dry-run helper output showing command shape only and no `--execute`.

## Откат и восстановление

Safe rollback is `git revert <commit>` for the documentation commit. If only local generated side
effects need cleanup, remove `/tmp/dawn-e09-ansible-remote-sync-bundle` and
`docs/generated/e09-ansible-remote-sync-local.md`. No remote state exists from this task.

## Итог и остаточные риски

Task 3 creates local docs/evidence for an approved remote-sync request shape only. It does not prove
remote copy, DB/MQ auth remediation, migration, live reconfigure, 12-container inspection, HAProxy/TLS,
SELinux hardening, registry signing, DKB-69 waiver closure, rollback or production deployment.
