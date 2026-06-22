# Custom task flow и workflow

## Цель

UI должен позволять добавлять новые многошаговые операции без внедрения произвольного кода в браузер и без превращения backend worker в новый orchestration engine.

Mistral является движком длительного workflow. Портал предоставляет каталог, формы, авторизацию, запуск, status projection и аудит.

## Workflow definition

Каждое определение содержит:

- `workflow_key` — стабильный идентификатор функции;
- semantic version;
- human-readable title/description;
- target types;
- JSON Schema input;
- UI schema только для представления;
- Mistral workflow mapping;
- required portal capabilities;
- required OpenStack scope/roles;
- timeout;
- cancel policy;
- retry policy;
- risk level;
- approval mode;
- sanitized audit mapping;
- enabled environments;
- checksum и metadata утверждения.

Клиент выбирает только опубликованное определение. Он не передает имя workflow, arbitrary task graph, shell command или template expression.

## Публикация workflow

Для production предпочтителен GitOps:

1. workflow и portal definition проходят code review;
2. schema и permission review;
3. security review;
4. deploy Mistral definition;
5. register matching checksum/version in portal catalog;
6. smoke test;
7. enable feature flag;
8. сохранить audit evidence.

Административное редактирование workflow прямо в UI не входит в PoC.

## Запуск

1. Backend загружает server-side definition.
2. Проверяет version/enabled state.
3. Валидирует targets и input по JSON Schema.
4. Проверяет capability и scope для каждого target.
5. Выполняет precondition checks: freshness, current state, maintenance window.
6. Создает operation и outbox в транзакции.
7. Возвращает 202 и `operation_id`.
8. Worker запускает Mistral с минимальным input.
9. External execution ID сохраняется один раз.
10. Status reconciler обновляет operation timeline.

## Idempotency

`Idempotency-Key` связан с actor, workflow, scope и hash нормализованного request. Повтор с тем же key и тем же request возвращает существующую operation. Повтор с тем же key и другим request — 409.

При неизвестном результате вызова Mistral worker сначала ищет execution по internal correlation, а не запускает новый.

## Target snapshot

Operation хранит snapshot идентификаторов и критических preconditions. Динамическая группа разворачивается в конкретный target set перед запуском, чтобы последующее изменение группы не меняло уже утвержденную операцию.

## Bulk и частичный результат

Для каждой цели хранится child status. Политика workflow определяет:

- all-or-nothing;
- best-effort;
- stop-on-first-failure;
- quorum/threshold;
- rollback availability.

UI показывает partial failures, а не только общий красный статус.

## Mistral operation center

Раздел операций показывает Mistral как first-class runtime:

- опубликованные workflow definitions and versions;
- текущие executions, task states, progress, correlation ID and external IDs;
- operation history, attempts, child executions and safe retry lookup;
- cancel/abort semantics from the definition and current Mistral state;
- health of Mistral API/engine/executor/event-engine as dependency status.

Browser still cannot submit arbitrary Mistral names, YAML, task graph, Python/Jinja or shell input. Every execution starts from a portal workflow definition.

## Watcher

Watcher workflows are first-class optimization/recommendation flows. Examples:

- создать audit по утвержденному template;
- создать или обновить continuous audit по утвержденному template and scope;
- запустить action plan;
- получить actions/results;
- связать action plan с operation.

Не предоставлять raw strategy parameters без schema и role review.

Перед запуском Watcher action plan backend checks:

- strategy, goal and template are allowlisted and match the portal definition checksum;
- telemetry datasource coverage/freshness is acceptable for the requested scope;
- affected resources are visible and authorized for the actor;
- recommendation confidence/impact/risk are shown in preview;
- conflicting recommendations or stale read model are resolved or explicitly acknowledged;
- automatic apply is disabled unless a production-only policy enables it with approval, max scope, rollback/abort and SIEM evidence.

Rollback/abort is allowed only when the Watcher action and wrapped workflow define it. If rollback is not available, UI must label the operation irreversible or best-effort before confirmation.

## Masakari

Masakari workflows are first-class HA/recovery flows. Examples:

- перевести host в maintenance через утвержденный flow;
- создать/подтвердить notification;
- показать recovery progress;
- связать segment/host/notification с hypervisor.

Опасные действия требуют elevated capability и полного аудита.
Network-health-driven evacuation is modeled through Masakari hostmonitor Consul driver and `matrix.yaml` producing Masakari notification/recovery state. Portal does not start recovery directly from Consul Events or Prometheus metrics.

Preconditions include:

- failover segment and segment host exist and are visible to the actor;
- recovery method is known and supported in the current cloud;
- hostmonitor source is trusted or clearly marked as partial; Consul matrix policy and monitor coverage are visible when `monitoring_driver=consul` is enabled;
- processmonitor is disabled, diagnostic-only or explicitly proven in a Kolla/container lab before it can participate in recovery approval;
- instancemonitor source is trusted or marked partial;
- Nova compute service, hypervisor, instance task state and migration/evacuation state do not conflict;
- operator approval gate is satisfied for recovery workflows that can evacuate, stop, restart or migrate instances;
- duplicate/stale notifications are detected and reconciled before action.

Связь с Nova evacuate/live migration фиксируется в operation timeline. Masakari recommendation or notification never bypasses Nova policy; a Nova 403/409 becomes a safe failed or blocked child status with audit.

## Heat

Heat stack operation использует тот же каталог и operation model. Template source должен поступать из утвержденного repository/artifact store, а не как произвольный template text от browser, если это не отдельная строго ограниченная функция.

## Отмена и retry

- Cancel доступен только если definition и Mistral state допускают.
- Cancel request сам является audit event.
- Retry не меняет исходную operation; создается новая attempt/child execution или новая operation по утвержденной модели.
- Нельзя скрывать необратимый partial effect.
- UI показывает, когда отмена означает только «не запускать следующие шаги».

## Operation state machine

Базовые состояния:

    accepted
    queued
    dispatching
    running
    cancel_requested
    succeeded
    partially_succeeded
    failed
    cancelled
    unknown

`unknown` используется при потере связи и требует reconciliation; он не преобразуется автоматически в failed.

## E06 P0 implementation

Реализованный первый workflow:

- key/version: `maintenance-host-precheck@1.0.0`;
- target: host from trusted inventory read model, or explicit host group expanded to concrete host
  snapshot before operation acceptance;
- input: `{reason: string, dry_run: true}`;
- required capability: `workflow.execute.maintenance-host`;
- approval mode: `none`;
- cancel policy in definition: `best_effort`, but API cancel is fail-closed until live cancel semantics
  are proven.

Backend behavior:

- `GET /api/v1/workflow-definitions` returns allowlisted definitions without Mistral workflow names.
- `POST /api/v1/operations` creates durable operation/outbox/idempotency rows before returning `202`.
- `GET /api/v1/operations` is actor/scope scoped, signed-cursor paginated and stable sorted by
  `updated_at.desc`.
- `GET /api/v1/operations/{operation_id}` returns status, correlation ID, external execution ID and
  timeline events.
- Worker dispatch uses the Mistral adapter boundary and searches by correlation after a lost response
  before attempting another start.

Test evidence is P0 by default: `InMemoryMistralAdapter` proves dispatch, unknown state, lost-response
duplicate prevention and external execution attachment without contacting OpenStack. Optional P2
all-in-one smoke is read-only workflow lookup and is skipped unless `DAWN_MISTRAL_SMOKE=1` and the
explicit test-project configuration are present.

Frontend behavior:

- Operations view is visible through `operation.read`.
- Submit form is enabled only when `workflow.execute.maintenance-host` and in-memory CSRF from login
  are present.
- Detail page shows operation status, timeline, correlation ID and Mistral execution ID when available.
- Polling is used; SSE remains planned.

## Безопасность input

- JSON Schema с `additionalProperties=false` по умолчанию;
- длины, диапазоны и enum ограничены;
- secrets передаются только через server-side reference;
- URL/host/file path input запрещены по умолчанию;
- никакого `eval`;
- template rendering только утвержденным sandboxed механизмом;
- audit хранит redacted summary;
- Mistral input не содержит browser cookie/token.

## UX

- preview: targets, preconditions, estimated impact, required role;
- explicit confirmation для risk level high;
- operation link появляется сразу;
- live update через SSE when available, with polling fallback and adaptive backoff;
- operation timeline shows task correlation, event source, partial result, stale/unknown state and operator approval gates;
- correlation ID виден оператору;
- error message безопасен, подробности доступны в защищенных logs/SIEM.
