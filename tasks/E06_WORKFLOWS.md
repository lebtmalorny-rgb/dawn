# E06 — Каталог операций и Mistral/Watcher/Masakari workflow

## Пользовательский результат

Пользователь выбирает утвержденную операцию для ВМ, host или группы, заполняет валидируемую форму, получает `operation_id` и видит состояние Mistral execution. Повтор request не создает дубликат.

## Входные критерии

- E05 принят.
- Выбран первый безопасный mutating workflow в test project.
- Workflow publication ADR принят.
- Есть Mistral test endpoint/credential или строгий mock.
- Для P2 принята security gate checklist.

## Прочитать

- `docs/07_WORKFLOWS.md`;
- `docs/05_API_AND_INTEGRATIONS.md`;
- `docs/06_AUTH_RBAC_SESSIONS.md`;
- `docs/08_AUDIT_OBSERVABILITY.md`;
- `docs/10_SECURITY_DKB.md`.

## Единицы работы

### E06.1. Operation schema/state machine

Добавить workflow definitions, operations, targets, attempts/events, idempotency и outbox. Реализовать transition rules и tests.

### E06.2. Catalog loader

Версионированные definitions из Git/config/DB по ADR. Проверять checksum, schema, permissions, enabled environment. Browser не задает Mistral name.

### E06.3. Mistral adapter/mock

Start/get/cancel/list by correlation. Typed errors, timeout, no blind POST retry. Mock моделирует lost response и duplicate lookup.

### E06.4. Submit API

Session/CSRF/capability/target/freshness/precondition/schema/idempotency. Создание operation/outbox в одной транзакции и немедленный 202.

### E06.5. Worker dispatch/reconciliation

Worker надежно запускает execution, сохраняет external ID, обновляет timeline и восстанавливается после crash. `unknown` не заменяется на failure без проверки.

### E06.6. First-class Watcher и Masakari vertical slice

Добавить first-class read/status adapters, UI routes and operation links:

- Watcher: goals, strategies, audit templates, audits/continuous audits, action plans, actions, recommendations, telemetry freshness and automatic-apply risk markers;
- Masakari: failover segments, segment hosts, notifications, recovery methods, monitor event timeline, hostmonitor Consul matrix coverage, conflicting Nova/Masakari state and approval gates;
- один утвержденный safe flow: maintenance/recovery preparation, Watcher dry-run/precheck or another test workflow approved by owner.

Точный сценарий из E00/E06 owner decision. Raw action plan execution, Nova evacuate/live migration, portal-side evacuation from Consul/Prometheus and automatic Watcher apply remain disabled unless represented by allowlisted workflow, capability, approval, audit, ADR and rollback/abort policy.

### E06.7. Frontend form/operation page

JSON Schema form, target preview, risk/permission/precondition, confirm, timeline, partial result, cancel when allowed. Polling с backoff.

### E06.8. Failure and idempotency tests

Same key/same body, same key/different body, worker crash before/after external response, Mistral unavailable, forbidden target, stale group snapshot, partial result, cancel/retry.

## Acceptance

- только allowlisted definition;
- arbitrary workflow name/input rejected;
- 202 возвращается после durable operation;
- duplicate request не создает второй execution;
- target set snapshot сохраняется;
- Mistral external ID коррелируется;
- worker restart безопасен;
- UI показывает `unknown`/partial/cancel semantics;
- Watcher/Masakari are visible as first-class modules, not only related links;
- automatic Watcher apply is denied by default and tested;
- Masakari recovery approval/conflict states and Consul hostmonitor matrix status are visible and tested;
- processmonitor is shown as unsupported/diagnostic in Kolla/container context unless lab evidence enables it;
- audit events redacted;
- real test workflow проходит либо mock status явно помечен P0;
- no production action.

## Затронутые ДКБ

- ДКБ-01–07/12/13: authorization and service identities.
- ДКБ-46–52: operation audit/error handling.
- ДКБ-60: group target snapshot.
- ДКБ-77: documented Mistral/Watcher/Masakari APIs.

## Не делать

- arbitrary script executor;
- browser-supplied Mistral YAML;
- long orchestration в Celery;
- shared admin token;
- автоматический retry irreversible POST без lookup.

## Итоговый запрос Codex

> Выполни E06 operations-first: state machine и idempotency до UI. Для lost Mistral response докажи отсутствие duplicate execution. Используй только test workflow и явно различай P0 mock от P2 integration.
