# E11 — Приемка PoC и эксплуатационная документация

## Пользовательский результат

Независимый инженер по документированной процедуре разворачивает test candidate, входит с тестовой ролью, просматривает inventory, создает группу, запускает разрешенный workflow, проверяет audit и воспроизводит rollback.

## Входные критерии

- E10 принят либо gaps формально согласованы для текущего уровня.
- Release candidate images immutable.
- Нет unresolved critical/high security findings.
- DKB traceability актуальна.

## Прочитать

- `docs/14_DEFINITION_OF_DONE.md`;
- все завершенные ExecPlans;
- test/security/load/deployment summaries;
- `docs/11_DKB_TRACEABILITY.md`.

## Единицы работы

### E11.1. Release manifest

Git commit, image digests, schema version, workflow versions, config revisions, compatibility matrix и known issues.

### E11.2. Installation/upgrade/rollback runbooks

Rocky prerequisites, Kolla build/deploy, migration, smoke, rollback, backup/restore references и troubleshooting.

### E11.3. Operator/user guides

Login/session behavior, inventory, groups, workflows, operation status, audit, partial/stale data, support correlation ID.

### E11.4. Acceptance scenarios

Роли:

- viewer;
- operator;
- security auditor;
- portal admin.

Сценарии positive/negative, DKB evidence и exact expected outcomes.

### E11.5. API/extension guide

Как добавить adapter/resource/workflow safely: contracts, capabilities, audit, tests, registry and DKB update.

### E11.6. Reproducible demo

Scripted seed/mock/test workflow и sanitized demo protocol. Никакого manual hidden step.

### E11.7. Final review

Docs links, secrets scan, command verification on clean environment, independent review findings.

## Acceptance

- clean test deploy by runbook;
- all four roles behave as specified;
- full demo from inventory to audit;
- negative authorization shown;
- rollback reproduced;
- API docs and extension guide complete;
- DKB evidence links valid;
- known external gaps explicit;
- no hidden credential/manual step;
- reviewer signs result.

## Затронутые ДКБ

ДКБ-77 и 82 напрямую; остальные получают consolidated evidence, но external gaps остаются.

## Не делать

- заявлять production readiness без E12;
- включать secret/screenshots with sensitive data;
- замалчивать failed scenario;
- заменять runbook устным знанием.

## Итоговый запрос Codex

> Подготовь E11 как независимую приемку, а не маркетинговое описание. Все команды должны быть воспроизводимы на clean test environment. Негативные сценарии и gaps обязательны.
