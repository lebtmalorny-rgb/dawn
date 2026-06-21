# E10 — Нагрузка, HA, failover и reconciliation

## Пользовательский результат

Команда знает измеренную емкость и поведение портала при отказе API, worker, RabbitMQ, MariaDB, OpenStack service, SIEM и одного control node. Дублирующие операции и silent data loss не происходят.

## Входные критерии

- E09 принят на трех test nodes.
- Scale profile утвержден.
- Test environment допускает controlled failure.
- Monitoring/metrics доступны.
- Recovery/rollback procedures существуют.

## Прочитать

- `docs/09_PERFORMANCE_HA.md`;
- `docs/13_TEST_STRATEGY.md`;
- `docs/14_DEFINITION_OF_DONE.md`;
- Kolla deployment ExecPlan/evidence.

## Единицы работы

### E10.1. Load harness/dataset

Воспроизводимые synthetic resources/audit dataset и scenarios. Фиксировать hardware, limits, images, versions.

### E10.2. Read workload

Instances/hypervisors/service-health/group/audit list under concurrency, reconciliation in background, filter/sort/page correctness, p95/p99, DB plans. Include large-table UX model, saved views, global search and bounded topology/dependency graph expansion.

### E10.3. Mutating workload

Operation submit/idempotent retry/status polling/SSE progress/polling fallback/partial results без destructive production effects. Include Watcher dry-run/recommendation projection and Masakari recovery timeline projection where enabled. For HA research include Consul-backed Masakari hostmonitor matrix fixtures; do not create a portal-side evacuation controller from Consul Events or Prometheus alerts.

### E10.4. Process failover

Kill/restart API, worker, events и entire node. Проверить session continuity, no duplicate execution, queue recovery.

### E10.5. Dependency failures

RabbitMQ outage/recovery, MariaDB failover, Nova/Placement/Mistral/Watcher/Masakari/Prometheus timeout, Consul unavailable for Masakari hostmonitor lab, SIEM outage, expired token.

### E10.6. Event consistency

Drop, duplicate, reorder events; reconciliation restores correct projection. Measure stale age.

### E10.6a. Real-time backpressure

SSE disconnect/reconnect, slow consumer, event burst aggregation, polling fallback, adaptive polling and circuit breaker behavior. Verify no uncontrolled OpenStack API amplification.

### E10.7. Rolling upgrade

Compatible frontend/backend versions, expand migration, rollback, queued/running operations preserved.

### E10.8. Bottleneck remediation

Исправлять только измеренные bottlenecks. Новая dependency требует ADR. Повторить tests и установить regression thresholds.

## Acceptance

- budgets measured, not estimated;
- p95/p99/error rate report;
- no correctness loss under load;
- one node failure tolerated;
- worker crash does not duplicate Mistral execution;
- event loss corrected;
- SSE/polling fallback preserves user-visible progress without raw notification leakage;
- adaptive polling/backpressure/circuit breakers prevent OpenStack API overload;
- SIEM outage does not silently drop;
- DB/RabbitMQ recovery observed;
- rolling update/rollback works;
- alerts/metrics sufficient;
- unresolved SLO gap has owner/decision.

## Затронутые ДКБ

- ДКБ-47/48/50.07: audit availability/heartbeat.
- ДКБ-66: HA/failover evidence.
- ДКБ-20/21: sessions under failover.
- ДКБ-77/82: operational documentation.
- ДКБ-72/storage remains external.

## Не делать

- разрушать production;
- считать replicas доказательством HA без failover;
- увеличивать retry до бесконечности;
- скрывать partial/stale data;
- добавлять Redis/search cluster без измерения/ADR.

## Итоговый запрос Codex

> Выполни E10 как controlled test campaign. Сохрани commands, metrics и evidence. Исправляй только доказанные bottlenecks. Любой duplicate destructive execution или silent audit loss является blocker.
