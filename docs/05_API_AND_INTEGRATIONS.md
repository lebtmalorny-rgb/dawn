# API и интеграционные контракты

## Общие правила API

- Prefix: `/api/v1`.
- JSON, UTF-8, UTC timestamps.
- OpenAPI — обязательный контракт.
- Auth через server-side session cookie.
- Mutating requests требуют CSRF. `Idempotency-Key` обязателен для retry-safe operation/member
  contracts where specified; P0 metadata CRUD без `operation_id` фиксируется как ограничение и не
  должен копироваться в destructive workflow APIs.
- Каждый ответ содержит или принимает correlation/request ID.
- Ошибки имеют единый объект с `code`, `title`, безопасным `detail`, `request_id`, optional field errors.
- Не возвращать stack trace, token, credential или raw request body.
- List endpoints имеют `limit`, `cursor`, typed filters, sort и `warnings`.
- Page size максимум 200.
- Partial response явно обозначается `partial=true`, `warnings` и freshness по источникам.

## Базовые endpoints

### Health

    GET /api/v1/health/live
    GET /api/v1/health/ready

Readiness проверяет критические зависимости с коротким timeout, но не выполняет дорогой полный fan-out.

### Session

    GET    /api/v1/session
    POST   /api/v1/session/login
    POST   /api/v1/session/logout
    GET    /api/v1/session/active
    DELETE /api/v1/session/active/{session_id}

Конкретный login flow зависит от federation/IdP и фиксируется ADR.

### Capabilities

    GET /api/v1/capabilities

Возвращает эффективные прикладные permissions для текущего subject и scope. Не раскрывает внутренние policy expressions.

### Instances

    GET /api/v1/instances
    GET /api/v1/instances/{cloud_id}/{region_id}/{instance_id}
    POST /api/v1/instances/{...}/refresh

Refresh является rate-limited operation и не превращает list endpoint в fan-out.
List поддерживает optional `group_id`; backend сначала проверяет `instance.read`, затем `group.read`
и owner/scope доступ к группе, после чего применяет server-side filter в read model.

### Hypervisors

    GET /api/v1/hypervisors
    GET /api/v1/hypervisors/{cloud_id}/{region_id}/{hypervisor_id}

List поддерживает optional `group_id` с тем же route-level group access check. Host group доступ не
выводится из project ownership и требует утвержденной admin/system-like политики при изменениях.

### Service health

    GET /api/v1/compute-services
    GET /api/v1/network-agents
    GET /api/v1/volume-services
    GET /api/v1/image-tasks
    GET /api/v1/orchestration-stacks

Каждый list endpoint server-side paginated/filtered/sorted and returns freshness. Modules for load balancers, DNS, secrets metadata and bare metal nodes are disabled until corresponding OpenStack service integration is explicitly included.

### Topology and visualization data

    GET /api/v1/topology
    GET /api/v1/topology/nodes/{node_type}/{node_id}
    GET /api/v1/capacity/summary
    GET /api/v1/capacity/timeseries
    GET /api/v1/search

Topology returns bounded graph pages or expansions, not an unbounded full cloud graph. Capacity endpoints return aggregated, downsampled series with source/freshness metadata. Global search is capability-aware and can return redacted/partial counts.

### Resource groups

    GET    /api/v1/groups
    POST   /api/v1/groups
    GET    /api/v1/groups/{group_id}
    PATCH  /api/v1/groups/{group_id}
    DELETE /api/v1/groups/{group_id}
    GET    /api/v1/groups/{group_id}/members
    POST   /api/v1/groups/{group_id}/members
    DELETE /api/v1/groups/{group_id}/members/{resource_type}/{cloud_id}/{region_id}/{resource_id}
    POST   /api/v1/groups/rules/validate
    POST   /api/v1/groups/{group_id}/preview

List/detail/preview требуют `group.read`; create/update/delete/member mutations требуют
`group.manage`, trusted Origin и CSRF. Member add/remove дополнительно требуют `Idempotency-Key`,
сохраняют key binding без raw key и возвращают `operation_id`. Preview dynamic rule возвращает
ограниченную страницу, `count_estimate`, `explain` и warnings, но не принимает SQL/Jinja/Python/regex.
VM preview дополнительно требует `instance.read`, host preview — `hypervisor.read`, чтобы `group.read`
не раскрывал inventory DTO без соответствующего права.

### Workflow catalog

    GET /api/v1/workflow-definitions

E06 P0 реализует только list published definitions. Ответ не раскрывает `mistral_workflow_name`.
Detail/version lookup, standalone input validation endpoint and catalog mutation remain planned.
Изменение каталога — отдельный административный API с повышенным аудитом либо GitOps pipeline.
Для production предпочтительно GitOps-публикация.

### Operations

    POST /api/v1/operations
    GET  /api/v1/operations
    GET  /api/v1/operations/{operation_id}
    POST /api/v1/operations/{operation_id}/cancel

Backend принимает `workflow_key`, version, targets и input. Клиент не передает произвольный Mistral workflow name.
`POST /api/v1/operations` требует session, trusted Origin, CSRF, `Idempotency-Key`, `operation.read`
and workflow-specific execute capability. E06 P0 workflow is `maintenance-host-precheck@1.0.0`,
target type `host`, input `{reason, dry_run=true}`.

`GET /api/v1/operations` is actor/scope scoped, paginated with signed cursor, stable sorted by
`updated_at.desc`, and capped at 200. `GET /api/v1/operations/{operation_id}` returns operation state
and timeline events. `POST /api/v1/operations/{operation_id}/cancel` is exposed but fail-closed in P0
with `409 operation_not_cancelable` until Mistral cancel semantics are proven. Retry remains planned.

### Real-time events

    GET /api/v1/events/stream
    GET /api/v1/events
    GET /api/v1/operations/{operation_id}/events

`/events/stream` is the preferred SSE endpoint for browser live updates. It authenticates by server-side session, filters by capability/scope, sends heartbeat and supports resume cursor. `/events` is the polling fallback with `since`, `limit`, channel filters and adaptive backoff hints. WebSocket is not part of the baseline API until an ADR approves bidirectional semantics, backpressure and load evidence.

Event payloads are portal projections: operation progress, health changes, read-model freshness, notifications, audit tail metadata and module-specific status changes. They never expose raw OpenStack tokens, raw request bodies or unfiltered service notifications.

### Watcher

    GET /api/v1/watcher/goals
    GET /api/v1/watcher/strategies
    GET /api/v1/watcher/audit-templates
    GET /api/v1/watcher/audits
    GET /api/v1/watcher/continuous-audits
    GET /api/v1/watcher/action-plans
    GET /api/v1/watcher/actions
    GET /api/v1/watcher/recommendations

E06 P0 exposes read/status placeholders behind `operation.read`: recommendation payloads include
telemetry freshness, automatic-apply disabled state and risk markers. Creation/execution/abort/rollback,
where supported later, goes through `POST /api/v1/operations` with an allowlisted workflow definition.
UI must not execute arbitrary action plan IDs directly from a browser request.

### Masakari

    GET /api/v1/masakari/segments
    GET /api/v1/masakari/segments/{segment_id}
    GET /api/v1/masakari/segments/{segment_id}/hosts
    GET /api/v1/masakari/notifications
    GET /api/v1/masakari/notifications/{notification_id}
    GET /api/v1/masakari/recovery-timeline

E06 P0 exposes read/status placeholders behind `operation.read`. Segment responses include approval
gate, Consul hostmonitor matrix status and `processmonitor` unsupported state; notification responses
include Nova/Masakari conflict markers and `direct_recovery_enabled=false`.
Mutating recovery approval, evacuation or maintenance actions go through `POST /api/v1/operations`.
API responses include conflicting state markers when Nova, Masakari and portal projections disagree.

The portal does not expose a direct "evacuate from Consul event" or "evacuate from Prometheus alert" endpoint. Network-health-driven host failure recovery is represented as Masakari hostmonitor/notification state; portal actions remain approval-gated and policy-checked.

### Audit

    GET /api/v1/audit/events
    GET /api/v1/audit/events/{event_id}

Доступ только по `audit.read`. Backend может объединять собственный индекс и внешнюю audit search API, но не дает direct access к broker/index.

## Адаптеры OpenStack

### Keystone

Отвечает за token/federation context, service catalog, scopes, role assignments и identity references. Human auth не использует shared local admin account.

### Nova

Instances, hypervisors, services, aggregates, server groups и actions. Microversion фиксируется и проверяется на startup/readiness.

### Placement

Resource provider inventory/usage и дополнительные capacity данные. Не подменяет Nova status.

### Mistral

Запуск, получение состояния, отмена и workflow metadata. External execution ID всегда связан с internal operation ID. Mistral also backs the first-class operation center: workflow definition status, execution timeline, task progress, cancellation semantics and safe retry lookup by correlation.

E06 default evidence uses `InMemoryMistralAdapter`, including lost-response duplicate-prevention tests.
Optional P2 all-in-one smoke is `make test-integration` with `DAWN_MISTRAL_SMOKE=1` and performs only
a read-only workflow definition lookup; it does not prove production mutating workflow safety.

### Watcher

Goals, strategies, audit templates, audits, continuous audits, action plans, actions and recommendations. Adapter tracks status/history, telemetry datasource requirement, stale telemetry, conflict state and rollback/abort support where exposed. UI не запускает неопределенный action plan напрямую; используется каталог операций.

### Masakari

Failover segments, segment hosts, notifications, recovery methods, monitor events and recovery state. Adapter correlates Masakari state with Nova compute services, hypervisors, instance status, evacuate/live migration tasks and portal approval gates. For network-health-driven recovery the preferred authoritative path is Masakari hostmonitor `monitoring_driver=consul` with `matrix.yaml`; Consul Events are diagnostic only. Разрешенные действия зависят от роли и workflow.

`processmonitor` is not assumed production-ready in Kolla/container deployments until a representative lab proves expected behavior and documents coverage.

### Telemetry datasource

Ceilometer, Gnocchi, Prometheus and Aetos are treated as pluggable metric datasources. First Prometheus path uses exporter-backed telemetry: `openstack-exporter` for OpenStack API metrics and `node_exporter` for host metrics. Each datasource adapter must document metric names, label cardinality, retention/downsampling, freshness, tenant/scope filtering and coverage gaps. Metrics cannot be used for automatic Watcher apply or Masakari recovery trigger unless an ADR, datasource freshness, authorization and failover evidence explicitly allow it.

### Heat

Опциональный модуль. Stack operations должны использовать тот же operation/audit/idempotency механизм.

## Контракт адаптера

Каждый адаптер предоставляет:

- `capabilities()` для версии и доступных функций;
- методы с доменными DTO;
- typed exceptions: auth, forbidden, not found, conflict, rate limit, unavailable, timeout, invalid response;
- metrics по latency/outcome;
- mock/fake;
- contract fixtures с безопасными sample payload;
- mapping версии API.

## Retry

- GET/HEAD: ограниченный retry с jitter для timeout/502/503/504.
- POST: retry только при доказанной idempotency внешнего API либо после проверки существующего external execution ID.
- 401: один controlled re-auth/refresh, затем session revoke или явная ошибка.
- 403/404/409/422: без слепого retry.
- Любой retry ограничен deadline request/job.
- Circuit breaker opens per service/region after repeated unavailable/timeout responses and makes UI show partial/stale state instead of amplifying load.
- Bulk APIs chunk external calls and cap concurrent service requests per adapter.

## SSRF и endpoint security

Service catalog и внешние endpoint не принимаются от browser. Разрешенные clouds/regions и endpoints задаются trusted configuration. Redirects, scheme и private network access валидируются по deployment policy.

## Реестр API по ДКБ-77

Для каждого API/endpoint в `docs/generated/api-register.md` фиксируются:

- назначение;
- consumer;
- protocol/TLS/mTLS;
- auth method;
- scope/roles;
- network zone;
- version/microversion;
- timeout/retry;
- audit events;
- enabled/disabled status;
- технический механизм блокировки неиспользуемого интерфейса.
