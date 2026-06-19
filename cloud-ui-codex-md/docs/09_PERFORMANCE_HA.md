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

## Read model sync

Full sync разбивается на chunks. Каждый chunk имеет cursor, generation и retry state. Новый generation не удаляет старые записи, пока full scan не завершен. После завершения отсутствующие resources помечаются deleted/tombstone.

Event consumer выполняет upsert по version/timestamp и игнорирует duplicate/out-of-order event. Если порядок нельзя доказать, запускается targeted refresh.

## Connection и concurrency limits

- API ограничивает concurrent calls к каждому OpenStack endpoint.
- Worker concurrency согласуется с RabbitMQ, DB pool и OpenStack rate limits.
- DB pool задается на реплику, чтобы сумма не превышала предел MariaDB.
- Thundering herd после failover предотвращается jitter/leases.
- Bulk operation имеет лимит targets и chunking.

## Cache

Read model является основным persistent cache. In-process cache допустим только для immutable/short-lived metadata и не влияет на correctness. Введение Redis требует измерения и ADR.

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

## Нагрузочные сценарии

- list/filter/sort instances;
- hypervisor detail с related VM page;
- concurrent saved views;
- group preview;
- create operation with idempotent retry;
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
