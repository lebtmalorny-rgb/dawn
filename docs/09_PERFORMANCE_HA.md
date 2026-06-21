# Производительность, масштабирование и HA

## Сначала измерение

E00 утверждает scale profile. До этого любые цифры являются provisional. Нагрузочные тесты должны использовать синтетические данные и фиксировать hardware/container limits.

## Основные budgets

После утверждения в `docs/generated/scale-profile.md` фиксируются:

- число clouds/regions;
- ВМ, hypervisors, projects, groups;
- change rate;
- audit event rate;
- concurrent users;
- list/detail/action latency p50/p95/p99;
- maximum stale age;
- full and incremental reconciliation time;
- RPO/RTO;
- availability target.

## List API

- keyset pagination;
- stable indexed sort;
- allowlist фильтров;
- максимальный page size;
- query timeout;
- slow query logging без sensitive values;
- `EXPLAIN` evidence для критических запросов;
- no N+1;
- batch enrichment;
- response compression по proxy policy;
- ETag/conditional request для справочников.

Frontend отменяет устаревший request при изменении фильтра и не делает uncontrolled prefetch.

## Real-time UX strategy

Real-time UX обслуживает operation progress, live tasks, health status, notifications, events stream, audit log tail and enabled resource status updates. Baseline strategy:

1. Server events are normalized into portal projections and operation/audit timelines.
2. Browser subscribes to `GET /api/v1/events/stream` over SSE.
3. SSE events are filtered by session, scope, capability, policy revision and channel.
4. Payloads are aggregated and bounded; raw OpenStack notification payloads are never forwarded.
5. Client uses resume cursor after reconnect and receives heartbeat.
6. If SSE is unavailable, client falls back to `GET /api/v1/events?since=...` and resource-specific status polling.

WebSocket is ADR-gated. It is used only if bidirectional low-latency interaction is required and load/backpressure tests prove that SSE + HTTP commands are insufficient.

## Adaptive polling and UI request control

- Polling intervals adapt by state: fast for active operation detail, slower for list pages, very slow for stable/hidden tabs.
- Server responses can include `retry_after_ms`, `stale_after_ms` and `next_refresh_not_before`.
- UI debounces filter/search input and throttles resize/scroll/cross-filter updates.
- Client cancels superseded requests with abort signals.
- Infinite scroll is allowed only for append-like feeds or stable keyset windows; inventory tables keep explicit page/cursor state.
- Optimistic UI is limited to local pending markers after durable `operation_id`; it never pretends an OpenStack mutation succeeded before authoritative confirmation.
- Eventual consistency is visible through freshness, pending/unknown state, reconciliation warning and safe refresh affordance.

## Event fan-out, aggregation and backpressure

- Fan-out happens from portal event projections, not from OpenStack APIs.
- Events are coalesced by channel/resource/window for high-churn resources.
- Operation timelines keep detailed state; dashboards receive aggregated counters and latest status.
- Per-session and per-tenant stream rate limits prevent one user from consuming unbounded memory.
- Slow consumers are disconnected with a resumable cursor rather than accumulating unlimited buffers.
- Event consumer writes a durable backlog; API stream nodes are stateless and can drop stream connections without losing source events.
- Audit events are not silently dropped; audit delivery uses its own outbox/dead-letter path.

## Read model sync

Full sync разбивается на chunks. Каждый chunk имеет cursor, generation и retry state. Новый generation не удаляет старые записи, пока full scan не завершен. После завершения отсутствующие resources помечаются deleted/tombstone.

Event consumer выполняет upsert по version/timestamp и игнорирует duplicate/out-of-order event. Если порядок нельзя доказать, запускается targeted refresh.

## Connection и concurrency limits

- API ограничивает concurrent calls к каждому OpenStack endpoint.
- Worker concurrency согласуется с RabbitMQ, DB pool и OpenStack rate limits.
- DB pool задается на реплику, чтобы сумма не превышала предел MariaDB.
- Thundering herd после failover предотвращается jitter/leases.
- Bulk operation имеет лимит targets и chunking.
- Per-adapter circuit breakers prevent repeated failing calls from overloading Nova, Placement, Mistral, Watcher, Masakari, telemetry and other OpenStack services.
- Bulk reads use service-native pagination/bulk endpoints where available and otherwise bounded batches with deadlines.
- Reconciliation, targeted refresh and user-triggered refresh share global concurrency budgets per cloud/region/service.

## OpenStack API protection

Portal read paths prefer MariaDB read model and aggregated projections. Live UX never polls all OpenStack services per browser. Protection controls:

- bounded thread pools for synchronous OpenStack clients;
- per-service/region concurrency limits;
- request deadline per adapter call and per background job;
- limited retry with jitter only for temporary safe failures;
- no blind retry for irreversible POST;
- circuit breaker with partial/stale UI state;
- queue-based reconciliation chunks;
- collapse duplicate refresh requests for the same resource;
- rate-limit admin refresh and global search;
- backoff when OpenStack returns 429/503 or adapter latency crosses threshold;
- metrics for upstream call count, latency, error rate and breaker state.

## Cache

Read model является основным persistent cache. In-process cache допустим только для immutable/short-lived metadata и не влияет на correctness. Введение Redis требует измерения и ADR.

## High-performance visualization

Dashboards and topology must be server-driven:

- Performance graphs use pre-aggregated/downsampled metric series with explicit datasource/freshness.
- Capacity dashboards query aggregate tables or telemetry rollups, not per-VM live fan-out.
- Health dashboards combine service health projections, dependency warnings and recent operation/event aggregates.
- Network topology and dependency maps return bounded graph expansions with node/edge limits, not full inventory dumps.
- Dependency graph layout is computed incrementally or cached per query scope; large graph queries return clusters and drill-down handles.
- Cross-filtering sends compact filter state to backend and receives paged/aggregated results.
- Data density controls change visible columns/row height/client rendering only; they do not change authorization or query scope.
- Tables for hundreds of thousands of rows rely on server-side pagination/keyset cursors. Row virtualization is a rendering optimization for the current page/window.
- Lazy loading is used for details, related resources, graph expansion and inventory tree children.
- Saved views store filter/sort/columns/density, not copied result sets.
- Global search is indexed, rate-limited, capability-aware and returns partial/redacted results when permissions are incomplete.

## Deployment topology

Для трех UI/control nodes:

| Процесс | На узел | Всего |
|---|---:|---:|
| frontend | 1 | 3 |
| API | 1 | 3 |
| worker | 1 | 3 |
| events | 1 | 3 |
| migration | 0 постоянно | 1 одноразово |

Scheduler не добавляется, пока periodic jobs могут использовать безопасный single-leader механизм или Mistral/внешний scheduler. Решение оформляется ADR.

## HA

- HAProxy health checks и rolling updates.
- API/frontend без local state.
- MariaDB HA и backup проверяются как внешняя зависимость.
- RabbitMQ quorum/HA и dead-letter проверяются.
- Worker crash после external call не создает duplicate workflow.
- Event consumer restart восстанавливает cursor/reconciliation.
- Migration выполняется до несовместимого кода.
- Feature flags позволяют выключить risky module.
- Real-time clients reconnect to another API replica with resume cursor.
- Watcher automatic apply and high-risk Masakari recovery remain feature-flagged and approval-gated.
- Masakari network-health-driven recovery follows hostmonitor Consul driver + `matrix.yaml`; portal-side recovery from Consul Events, Prometheus alerts or exporter metrics is forbidden until separate ADR and failover evidence.
- `processmonitor` remains a Kolla/container R&D risk unless representative lab evidence proves the monitor observes the intended service failures.

## Failover-сценарии E10

1. Удаление одной API-реплики во время list load.
2. Удаление worker после отправки request в Mistral до сохранения response.
3. RabbitMQ unavailable и recovery.
4. MariaDB primary failover.
5. OpenStack Nova/Placement timeout.
6. SIEM unavailable.
7. Event loss/duplicate/out-of-order.
8. Stale read model.
9. Rolling update frontend/backend разных совместимых версий.
10. Failure migration job до commit.
11. Loss of one control/UI node.
12. Expired Keystone token during operation status sync.
13. SSE disconnect/reconnect under operation progress load.
14. Watcher/Masakari/telemetry timeout while inventory remains readable.
15. Circuit breaker open/half-open/close behavior for a noisy OpenStack service.
16. Consul-backed Masakari hostmonitor matrix produces recovery notification in lab; portal observes timeline without duplicating evacuation decision.

## Нагрузочные сценарии

- list/filter/sort instances;
- hypervisor detail с related VM page;
- service health lists and dashboard aggregates;
- topology/dependency graph expansion;
- inventory tree lazy expansion;
- concurrent saved views;
- group preview;
- create operation with idempotent retry;
- operation timeline and SSE stream under concurrent active operations;
- Watcher recommendation list/action-plan status projection;
- Masakari recovery timeline/notification projection;
- audit search;
- reconciliation while users read;
- event burst;
- region unavailable with partial response.

## SLO evidence

Отчет содержит:

- environment;
- image digests;
- dataset;
- command and scenario;
- percentile latency;
- throughput;
- error rate;
- CPU/RAM/DB/RabbitMQ metrics;
- slow queries;
- bottleneck conclusion;
- regression threshold.

## Backpressure

При перегрузке:

- API возвращает 429/503 с retry guidance;
- worker queue age metric alerts;
- event consumer сохраняет durable backlog;
- reconciliation снижает concurrency;
- UI не запускает aggressive retry;
- operations remain accepted/queued only when durable record exists.
