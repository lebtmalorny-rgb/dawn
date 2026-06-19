# E07 — Прикладной аудит и централизованная доставка

## Пользовательский результат

Security auditor видит защищенный журнал действий портала с обязательными полями, безопасными ошибками и correlation ID. События надежно доставляются в test SIEM/syslog adapter; сбой доставки видим и восстанавливается без потери.

## Входные критерии

- E06 принят.
- Audit sink ADR принят либо есть test sink.
- Утверждены retention и field classification.
- Определена роль `security_auditor`.

## Прочитать

- `docs/08_AUDIT_OBSERVABILITY.md`;
- `docs/10_SECURITY_DKB.md`;
- `docs/11_DKB_TRACEABILITY.md`;
- `docs/13_TEST_STRATEGY.md`.

## Единицы работы

### E07.1. Audit schema и taxonomy

Версионированная schema, action/event dictionary и mapping ДКБ-49.01–49.08. Поля allowlisted.

### E07.2. Transactional audit/outbox

Business mutation и audit/outbox создаются атомарно. Delivery state, retry, dead-letter и replay idempotency.

### E07.3. Redaction

Central sanitizer для logs/audit/errors. Canary tests для password/token/cookie/private key/workflow secret. Запрет raw bodies по умолчанию.

### E07.4. SIEM/test sink adapter

Защищенный contract, auth/TLS placeholders, batch/retry/ack. Test sink позволяет доказать success/failure/recovery. Production credential отсутствует.

### E07.5. Heartbeat и disable detection

Heartbeat event/metric, queue age/delivery failure alerts. Документировать внешний FIM/auditd для ДКБ-48.

### E07.6. Audit search UI/API

`audit.read` и `audit.export` раздельно. Server-side filters/page, field scope, access itself audited. No direct broker/index access.

### E07.7. OpenStack/full audit mapping

Создать `docs/generated/audit-source-map.md`: CADF, Keystone/Nova/etc notifications, host/container/libvirt/OVS/IdP/storage/monitoring. Пометить реализованные и внешние источники.

### E07.8. Security tests

Unauthorized audit access, export denial, redaction, delivery outage, duplicate/replay, full internal error correlation, no PII overcollection.

## Acceptance

- mandatory fields present to second precision/UTC;
- success/failure/unknown represented;
- canary secrets absent from all sinks/client;
- internal error linked by correlation ID;
- delivery outage leaves durable backlog and alert;
- heartbeat works;
- audit read/export scoped;
- audit access audited;
- source map shows why DKB-50 is not fully closed by portal;
- DKB traceability/evidence updated.

## Затронутые ДКБ

ДКБ-46–53 полностью анализируются. Портал может закрыть свою часть ДКБ-49/51/53; ДКБ-48/50 и часть 52 требуют внешних controls.

## Не делать

- объявлять MariaDB portal audit неизменяемым SIEM;
- хранить raw stack traces в browser-facing audit;
- давать direct SQL/index access;
- логировать каждый inventory read с лишними персональными данными;
- silently drop events.

## Итоговый запрос Codex

> Выполни E07 evidence-first. Создай schema и redaction tests до sink/UI. Явно раздели portal audit и полный инфраструктурный audit. Сбой sink должен быть наблюдаемым и не терять событие.
