# ExecPlan: E09 AIO operator baseline

## Цель и наблюдаемый результат

Зафиксировать текущий working all-in-one Cloud UI path as an operator runbook so the team can keep
using the test UI while the three-node rollout is paused.

## Контекст и текущее состояние

`main` already contains the bounded AIO Kolla CLI path, migration-enabled reconfigure evidence,
idempotency evidence and digest availability preflight. Missing piece: a single operator-facing
runbook that says which commands are the supported AIO baseline and where the full E09 boundary stops.

## Scope

- Create `docs/generated/e09-aio-operator-runbook.md`.
- Add a regression test that enforces scope, safe commands, smoke, rollback and no secret material.
- Link the runbook from DKB traceability, risk register and current state.

## Non-goals

- No live reconfigure.
- No three-node rollout.
- No production approval.
- No new deployment secret path.

## Требования и ограничения

No runtime secret values, inventory copies, cookies, tokens, DB/MQ URLs or private keys in repository
docs. The runbook must state that the three-node rollout is paused and AIO is not full E09 acceptance.

## Связь с ДКБ

- ДКБ-70/82: operator runbook references digest availability preflight and AIO evidence.
- ДКБ-55/56: runtime vars remain external and not stored in Git.
- ДКБ-65/69: runbook records container hardening checks and keeps Python interpreter waiver open.

## Progress

- [x] 2026-06-28: RED test failed because runbook and links were absent.
- [x] 2026-06-28: added runbook and links.
- [x] 2026-06-28: verification passed.

## Неожиданные открытия

None. This slice documents the already verified AIO path.

## Журнал решений

- 2026-06-28: keep AIO runbook separate from E11 acceptance runbooks. Reason: this is a test baseline,
  not acceptance documentation.

## Проверка

- `pytest tests/test_e09_aio_operator_runbook.py -q` passed: 2 tests.
- `pytest tests/test_e09_aio_operator_runbook.py tests/test_e09_kolla_ansible_role.py tests/test_e09_deployment_smoke_evidence.py -q` passed: 28 tests.
- `pytest tests/test_e09_*.py backend/tests/test_cli.py -q` passed: 125 tests.
- `ruff check tests/test_e09_aio_operator_runbook.py` passed.
- `./scripts/secret-scan.sh` passed.
- `git diff --check` passed.

## Откат и восстановление

Repository rollback: revert this docs/test commit. Runtime rollback not required because this slice
does not mutate the AIO stand.

## Итог и остаточные риски

The AIO operator baseline is documented and guarded by regression tests. Three-node rollout,
HAProxy/VIP/TLS, SELinux host labels, corporate registry policy, ДКБ-69 waiver and failed-update
rollback acceptance remain outside this slice.
