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

## Watcher

Примеры allowlisted функций:

- создать audit по утвержденному template;
- запустить action plan;
- получить actions/results;
- связать action plan с operation.

Не предоставлять raw strategy parameters без schema и role review.

## Masakari

Примеры:

- перевести host в maintenance через утвержденный flow;
- создать/подтвердить notification;
- показать recovery progress;
- связать segment/host/notification с hypervisor.

Опасные действия требуют elevated capability и полного аудита.

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
- live update через polling; SSE добавляется после доказанной необходимости;
- correlation ID виден оператору;
- error message безопасен, подробности доступны в защищенных logs/SIEM.
