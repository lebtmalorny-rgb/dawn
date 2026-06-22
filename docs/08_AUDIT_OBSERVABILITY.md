# Аудит и наблюдаемость

## Граница аудита

Портал обязан полно и надежно фиксировать собственные действия. Полный аудит OpenStack, ОС, гипервизоров, СХД и гостевых ОС требует внешнего контура. Нельзя считать ДКБ-50 закрытым только за счет таблицы `audit_events` портала.

## Минимальная схема audit event

Каждое событие содержит:

- `event_id`;
- `event_version`;
- UTC timestamp с точностью не хуже секунды;
- actor type/id/display reference;
- authentication method и session reference;
- action code;
- event name/type;
- outcome: success/failure/unknown;
- target type/id/name reference;
- cloud/region/project/scope;
- source IP и trusted proxy chain в утвержденном объеме;
- request ID;
- correlation ID;
- operation/external execution ID;
- service/component;
- safe error code;
- redacted metadata;
- delivery state.

Это покрывает основу ДКБ-49.01–49.08 для действий портала.

## События портала

Обязательные типы:

- login success/failure;
- logout, timeout, revoke;
- capability/policy denial;
- session limit event;
- role/permission/binding change;
- group create/update/delete/member change;
- workflow definition publication/enable/disable;
- operation accepted/dispatched/completed/failed/cancelled;
- Watcher audit/template/action-plan/recommendation view and approved execution/abort/rollback request;
- Masakari segment/host/notification view, recovery approval decision and evacuation/recovery workflow request;
- real-time stream subscription, denied channel and forced disconnect when protected/audit channels are accessed;
- access to audit search/export;
- configuration change;
- secret integration failure без secret value;
- SIEM delivery failure/recovery;
- reconciliation anomaly;
- admin refresh и bulk action.

Чтение обычной inventory page логируется агрегированно по утвержденной политике, чтобы не создать чрезмерный шум и не собрать лишние персональные данные. Просмотр защищенного audit/role/secret metadata логируется всегда.

E02 реализует только базовый in-process audit для `session.login` success/failure, `session.logout`, `session.revoke`, `session.timeout`, `session.limit_reached`, `session.required`, `csrf.denied`, `origin.denied`, `authorization.denied` и `openstack.denied`. Durable outbox, delivery state, SIEM/syslog отправка, heartbeat и полный аудит OpenStack/host/storage остаются задачами E07/P3.

E06 добавляет portal-side operation evidence: `operation.accepted` audit event, authorization denial
events for workflow execution, safe idempotency hash metadata, operation timeline events and worker
attempt records. Raw `Idempotency-Key`, browser cookies, Mistral tokens and full unredacted workflow
input are not stored in audit metadata. This was local portal evidence before E07; durable portal
outbox/delivery and heartbeat are added below, while external OpenStack/Mistral audit collection
remains outside the portal boundary.

E07 реализует нормализованную схему событий портала, рекурсивную redaction, durable `audit_events` +
`audit_outbox`, delivery attempts, heartbeat state, bounded `cloud-ui events --once`, local test sink,
Fluentd HTTP payload contract, audit search/detail/export API and frontend view. Доказательные
артефакты: `docs/generated/audit-event-schema.json`,
`docs/generated/audit-action-dictionary.md`, `docs/generated/audit-sample-events.md`,
`docs/generated/audit-source-map.md` и `docs/generated/e07-fluentd-opensearch-lab.md`.
Production SIEM endpoint, mTLS/auth, retention, OpenStack service audit and host/storage/IdP audit
остаются внешним контуром; таблица портала не считается неизменяемым SIEM.

## Redaction

Запрещено логировать:

- password;
- token;
- cookie;
- authorization header;
- private key/certificate private material;
- application credential secret;
- Vault response;
- полный workflow input, если он может содержать бизнес-данные;
- guest data;
- полный request/response body без allowlist.

Redaction выполняется до сериализации события. Тесты используют canary secrets и проверяют все sinks.

## Баланс ДКБ-51 и ДКБ-52

Клиент и audit event получают безопасный error code/message. Полный системный stack trace сохраняется в защищенном service log, очищенном от секретов, с тем же correlation ID. SIEM связывает audit event и service log. Нельзя помещать raw stack trace в доступный пользователю audit payload.

## Доставка

Паттерн:

1. audit/outbox row создается в транзакции с бизнес-изменением;
2. delivery worker отправляет событие в SIEM/syslog/broker через защищенный канал;
3. подтверждение сохраняется;
4. retry ограничен и использует dead-letter;
5. длительное отсутствие подтверждения формирует alert;
6. heartbeat доказывает работоспособность пути;
7. отключение consumer/config отслеживается внешним monitoring/FIM/auditd.

В E07 шаги 1, 3, 4, 6 доказаны для portal audit через локальный sink/contract tests. Шаг 2 доказан
как Fluentd HTTP-compatible payload contract без live отправки; защищенный production канал и
авторизация sink являются задачей SIEM/PKI владельцев. Шаг 7 не закрывается кодом портала и требует
FIM/auditd/IaC/missing-flow alerting.

## Источники полного аудита

Внешняя архитектура должна объединять:

- keystonemiddleware CADF/audit;
- Keystone notifications;
- Nova/Neutron/Glance/Cinder notifications;
- Mistral/Watcher/Masakari события;
- telemetry datasource events and freshness gaps from Ceilometer/Gnocchi/Prometheus/Aetos where enabled;
- HAProxy/API access logs;
- Kolla/container runtime events;
- systemd, sudo, PAM и auditd;
- libvirt/QEMU/OVS/OVN logs;
- monitoring unavailable events;
- SIEM heartbeat;
- storage/backup audit;
- IdP/IAM audit;
- portal audit.

## Доступ

`audit.read` и `audit.export` разделяются. Backend всегда применяет scope и field-level restrictions. Direct access к log files, RabbitMQ, DB table или SIEM index не считается прикладным доступом и должен быть запрещен/ограничен внешними controls.

Просмотр и экспорт аудита сами журналируются.

## Observability

### Logs

Структурированный JSON:

- timestamp;
- level;
- service/process;
- request/correlation/job IDs;
- actor reference при допустимости;
- operation ID;
- event code;
- safe message;
- exception class и sanitized detail.

### Metrics

Минимум:

- request count/latency/outcome;
- DB pool usage;
- OpenStack adapter latency/errors;
- worker queue depth/age;
- event lag;
- reconciliation lag and drift;
- operation states/duration;
- SIEM delivery lag/failures;
- active/revoked sessions;
- auth failures and policy denials;
- stale inventory count.

### Traces

Trace context передается между API, outbox, worker и внешними adapter calls, но не включает secrets. Для систем без trace propagation сохраняется correlation ID.

### Health

- liveness: процесс способен отвечать;
- readiness: DB и критическая конфигурация доступны;
- dependency status: отдельный защищенный endpoint/metrics, чтобы temporary OpenStack outage не перезапускал все API containers.

## Доказательства

E07 создает:

- JSON Schema audit event;
- mapping DKB fields;
- sample events для success/failure;
- automated redaction tests;
- delivery integration test;
- replay/idempotency test;
- access-control tests;
- heartbeat/alert test;
- document describing external sources not covered by portal.

Фактические E07 артефакты:

- `docs/generated/audit-event-schema.json`;
- `docs/generated/audit-action-dictionary.md`;
- `docs/generated/audit-sample-events.md`;
- `docs/generated/audit-source-map.md`;
- `docs/generated/e07-fluentd-opensearch-lab.md`;
- backend tests under `backend/tests/audit/`;
- frontend audit capability tests in `frontend/src/App.test.tsx`.
