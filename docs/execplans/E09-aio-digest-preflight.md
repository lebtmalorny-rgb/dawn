# ExecPlan: E09 AIO digest availability preflight

## Цель и наблюдаемый результат

Оператор получает fail-fast проверку digest refs до запуска `kolla-ansible reconfigure -p ... -t
cloud-ui`. Если backend или frontend digest отсутствует в test registry, wrapper завершится до
mutating playbook и напечатает безопасную ошибку без runtime secrets.

## Контекст и текущее состояние

`deploy/kolla/scripts/run-cloud-ui-aio-kolla.py` уже валидирует формат digest, test inventory marker,
rollback window и production-looking inputs. Live AIO evidence 2026-06-28 показал реальный failure
mode: stale digest прошел format validation, но Docker module later получил registry 404 during
migration precheck. Это надо ловить в wrapper preflight.

## Scope

- Добавить registry manifest availability check для `cloud-ui-backend` и `cloud-ui-frontend`.
- Проверять digest availability для всех wrapper modes до запуска Kolla-Ansible.
- Сохранить `--dry-run` как локальный command preview без сетевой проверки.
- Покрыть success, missing digest, unsupported registry scheme and no-secret-output tests.
- Обновить docs/evidence/risk traceability.

## Non-goals

- Не добавлять registry authentication.
- Не выполнять Docker pull из wrapper.
- Не менять Ansible role runtime behavior.
- Не заявлять full E09 acceptance или corporate registry compliance.

## Требования и ограничения

Проверка не читает runtime vars and DB/MQ secrets. Ошибка не должна печатать credential-looking data.
Поддерживается текущий lab registry format `host[:port]/namespace`. HTTPS можно указать явно через
`https://host/...`; default for current lab stays HTTP.

## Связь с ДКБ

- ДКБ-69/70: narrows digest-pull evidence gap for AIO lab by checking registry manifest existence.
  Corporate signing/scanning/provenance remain external.
- ДКБ-82: prevents stale digest from reaching mutating AIO reconfigure. Three-node, upstream
  `site.yml` and failed-update rollback remain pending.

## Milestones

1. Baseline wrapper tests.
2. RED tests for manifest URL construction and stale digest failure before subprocess.
3. Minimal wrapper implementation with standard-library HTTP.
4. Docs/evidence updates.
5. Full targeted and E09 verification.

## Progress

- [x] 2026-06-28: pushed previous `main` to `origin/main` at `e02cc4f`.
- [x] 2026-06-28: created isolated worktree `e09-aio-digest-preflight`.
- [x] 2026-06-28: baseline wrapper/live-role tests passed: `17 passed`.
- [x] 2026-06-28: RED tests failed on missing manifest helpers, missing credential rejection and
  missing pre-subprocess availability check.
- [x] 2026-06-28: implementation added registry manifest URL construction, credential rejection and
  digest availability checks before non-dry-run Kolla execution.
- [x] 2026-06-28: live stale digest check returned wrapper exit code `2` before Kolla-Ansible
  started; current digest preflight still passed with `localhost ok=10 changed=0 failed=0`.
- [x] 2026-06-28: docs/evidence updated.
- [ ] Verification and commit.

## Неожиданные открытия

- The stale backend and frontend digests from the earlier failed run are both absent from the current
  test registry manifest path, and the wrapper now catches both before invoking Kolla-Ansible.

## Журнал решений

- 2026-06-28: use Docker Registry HTTP manifest check instead of Docker pull. This is lighter, avoids
  mutating target image cache, and directly catches the stale digest failure seen in the lab.
- 2026-06-28: keep `--dry-run` network-free so operators can preview generated Kolla command without
  requiring registry reachability.

## Детальный план реализации

- Modify `tests/test_e09_aio_kolla_cli_path.py` with tests for:
  - backend/frontend manifest URLs;
  - successful HEAD/GET manifest checks;
  - stale digest failure returning exit code `2` before `subprocess.run`;
  - no DB/MQ URL or runtime secret value in digest error output.
- Modify `deploy/kolla/scripts/run-cloud-ui-aio-kolla.py`:
  - add `ImageRef`, `DigestAvailability`, and manifest-check helpers;
  - parse registry into scheme/netloc/repository prefix;
  - use `urllib.request` with short timeout and Docker manifest Accept header;
  - call availability check in `main()` after static validation and before `build_invocation`/subprocess,
    except for `--dry-run`.
- Update `deploy/kolla/ansible/README.md`, `docs/generated/e09-deployment-smoke-evidence.md`,
  `docs/generated/risk-register.md` and `docs/11_DKB_TRACEABILITY.md`.

## Миграции и совместимость

No DB migration. CLI behavior changes only by failing earlier when registry manifest is unavailable.
Existing successful inputs continue to generate the same Kolla-Ansible command.

## Проверка

- `pytest tests/test_e09_aio_kolla_cli_path.py -q`
- `pytest tests/test_e09_*.py backend/tests/test_cli.py -q`
- `ruff check deploy/kolla/scripts/run-cloud-ui-aio-kolla.py tests/test_e09_aio_kolla_cli_path.py`
- `./scripts/secret-scan.sh`
- `git diff --check`

## Доказательства

Evidence updates stay sanitized and do not include runtime secret files, inventory copies, tokens,
cookies, DB/MQ URLs or registry credentials.

## Откат и восстановление

Repository rollback: revert this commit. Runtime rollback is not required because this slice changes
the local wrapper/docs/tests only and does not mutate the AIO stand.

## Итог и остаточные риски

Pending until implementation and verification complete.
