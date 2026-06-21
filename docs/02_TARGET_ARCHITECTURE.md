# Целевая архитектура

## Логическая схема

```mermaid
flowchart LR
    U[Браузер оператора] -->|HTTPS, same origin| LB[HAProxy / VIP]
    LB --> FE[Frontend replicas]
    LB --> API[Backend API replicas]

    API --> IDP[Корпоративный IdP]
    API --> KS[Keystone]
    API --> DB[(MariaDB cloud_ui)]
    API --> MQ[(RabbitMQ /cloud-ui)]
    API --> OSAPI[OpenStack service APIs]
    API --> WATCHER[Watcher]
    API --> MASAKARI[Masakari]
    API --> TELEMETRY[Telemetry: Ceilometer/Gnocchi/Prometheus/Aetos]
    API --> SIEM[SIEM adapter]
    API --> VAULT[Vault (SecMan) adapter]
    CONSUL[Consul health checks] --> MASAKARI_MON[Masakari hostmonitor]
    MASAKARI_MON --> MASAKARI

    WORKER[Background worker replicas] --> DB
    WORKER --> MQ
    WORKER --> OSAPI
    WORKER --> MISTRAL[Mistral]
    WORKER --> WATCHER
    WORKER --> MASAKARI
    WORKER --> TELEMETRY
    MISTRAL --> WATCHER
    MISTRAL --> MASAKARI
    MISTRAL --> HEAT[Heat, опционально]

    EVENTS[Event consumer replicas] --> MQ
    EVENTS --> DB
    EVENTS --> OSAPI

    RECON[Reconciliation jobs] --> OSAPI
    RECON --> DB
```

## Ключевая идея

Backend является BFF: он объединяет неоднородные API OpenStack, нормализует ошибки и поля, применяет прикладную авторизацию и не отдает OpenStack credential в браузер.

Для крупного inventory backend не строит каждую страницу синхронным fan-out по всем сервисам. Он читает индексированную read model из собственной MariaDB. Read model обновляется:

1. первичной полной синхронизацией;
2. периодическим инкрементальным reconciliation;
3. событиями OpenStack, если они доступны и надежно изолированы;
4. точечным refresh после пользовательской операции.

Mistral, Watcher и Masakari являются first-class product modules. Mistral остается источником истины длительного execution, но Watcher и Masakari имеют собственные read/status adapters, read model projections, capability checks, audit mappings and UI routes. Workflow через Mistral используется для утвержденных действий, а не как замена доменной модели Watcher/Masakari.

Для network-health-driven evacuation целевой путь — штатный Masakari hostmonitor с Consul driver and `matrix.yaml`. Портал не строит собственный recovery controller поверх Consul Events или Prometheus metrics: он отображает Masakari notification/recovery workflow, correlates Nova/telemetry state and records audit.

## Runtime-компоненты

### Frontend

Статический SPA. Отвечает за shell, маршрутизацию, таблицы, формы и визуализацию operation status. Получает capabilities от backend. Не содержит секретов и не знает Keystone token.

### API

Обслуживает browser requests, аутентификацию, server-side session, authorization, list/detail endpoints, operation submission и audit queries. Реплики stateless относительно локального диска.

### Worker

Выполняет короткие фоновые задачи портала: reconciliation chunks, enrichment, refresh, отправку событий, cleanup и retry. Длительную бизнес-оркестрацию передает Mistral.

### Event consumer

Получает только специально опубликованные notifications или сообщения собственного exchange. Нормализует события, выполняет idempotent upsert read model и сохраняет cursor/offset.

### Real-time gateway

Browser получает события только от backend API/BFF. Базовый транспорт для server-to-browser updates — SSE endpoint с authenticated session, scope/capability filtering, heartbeat and resume cursor. WebSocket допускается только после ADR, если появится bidirectional UX, который нельзя безопасно и проще реализовать через SSE + HTTP commands. Для клиентов или proxy без stream support используется polling fallback.

Real-time gateway не читает raw OpenStack RPC queues и не раздает raw notifications. Он публикует агрегированные portal events из read model, operation timeline, health projections and audit tail with field-level restrictions.

### Migration job

Одноразовый процесс, выполняющий Alembic upgrade. Не масштабируется и не запускается одновременно несколькими экземплярами без DB lock.

## Интеграционный слой

Каждый сервис реализуется адаптером с единым набором правил:

- typed input/output;
- API microversion;
- timeout;
- bounded concurrency;
- retry только для безопасных временных ошибок;
- mapping внешней ошибки в доменный error;
- metrics;
- correlation ID;
- contract tests;
- mock implementation.

Рекомендуемые модули:

    backend/src/cloud_ui/integrations/keystone/
    backend/src/cloud_ui/integrations/nova/
    backend/src/cloud_ui/integrations/placement/
    backend/src/cloud_ui/integrations/mistral/
    backend/src/cloud_ui/integrations/watcher/
    backend/src/cloud_ui/integrations/masakari/
    backend/src/cloud_ui/integrations/telemetry/
    backend/src/cloud_ui/integrations/heat/
    backend/src/cloud_ui/integrations/siem/
    backend/src/cloud_ui/integrations/vault/

## Поток чтения inventory

```mermaid
sequenceDiagram
    participant B as Browser
    participant A as API
    participant D as Read model
    participant O as OpenStack API
    participant W as Worker

    B->>A: GET /api/v1/instances?cursor=...&filter=...
    A->>A: authenticate + authorize
    A->>D: indexed query
    D-->>A: page + freshness
    A-->>B: data + next_cursor + warnings

    W->>O: periodic reconciliation
    O-->>W: changed resources
    W->>D: idempotent upsert
```

## Поток mutating workflow

```mermaid
sequenceDiagram
    participant B as Browser
    participant A as API
    participant D as MariaDB
    participant W as Worker
    participant M as Mistral
    participant S as SIEM

    B->>A: POST action + Idempotency-Key
    A->>A: session, CSRF, capability, target policy
    A->>D: create operation + outbox in one transaction
    A-->>B: 202 operation_id
    W->>D: claim outbox/job
    W->>M: start allowlisted workflow
    M-->>W: execution_id
    W->>D: update operation
    W->>S: audit event
    B->>A: GET operation status
    A->>D: read status
    A-->>B: progress/outcome
```

## Данные и согласованность

- Источник истины ресурсов — OpenStack.
- Источник истины прикладных групп, ролей и каталога workflow — MariaDB портала.
- Источник истины выполнения длительной операции — Mistral; портал хранит проекцию и correlation.
- Источник истины Watcher entities — Watcher API; портал хранит projection goals/strategies/audits/action plans/actions/recommendations and execution correlations.
- Источник истины Masakari entities — Masakari API, Masakari notifications/recovery workflow and Nova state; Consul health checks and matrix policy are handled by Masakari hostmonitor, not by a portal-side recovery controller.
- Источник истины telemetry metrics — утвержденный datasource per metric family; first Prometheus path is exporter-backed telemetry, and портал хранит агрегированные series/cache only with freshness metadata.
- Источник истины долговременного централизованного аудита — SIEM.
- Read model допускает eventual consistency, но всегда показывает freshness.
- Изменение группы и создание операции используют транзакцию.
- Надежная публикация после транзакции реализуется transactional outbox.

## Отказоустойчивость

- Потеря API-реплики не теряет сессию или операцию.
- Повторная обработка сообщения безопасна.
- Недоступность OpenStack API не блокирует чтение последней read model, но возвращает warning о stale data.
- Недоступность Mistral не создает дублирующий execution при retry.
- Недоступность Watcher/Masakari/telemetry не блокирует базовый inventory, но соответствующие modules показывают dependency warning and partial freshness.
- Недоступность SIEM не приводит к silent loss: событие остается в outbox/dead-letter и формируется alert.
- Reconciliation обнаруживает расхождения между OpenStack и read model.
- Real-time stream degradation switches clients to adaptive polling without increasing OpenStack API pressure.

## Что запрещено

- fan-out по всем ВМ при каждом открытии таблицы;
- direct DB query к OpenStack;
- shared admin token;
- хранение токена в frontend;
- выполнение произвольного workflow по строковому имени от клиента;
- использование RabbitMQ RPC queues OpenStack;
- прямая browser-подписка на OpenStack notifications или telemetry endpoints;
- автоматическое применение Watcher recommendations без отдельного утвержденного workflow, capability, audit and rollback/abort policy;
- самостоятельная эвакуация из портала по Consul Events, Prometheus alerts or exporter metrics without Masakari workflow/notification, ADR and failover evidence;
- хранение бизнес-состояния в etcd;
- локальная очередь в памяти API;
- автоматическая миграция при старте каждой API-реплики.
