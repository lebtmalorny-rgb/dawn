# ExecPlan: E00 first-class operations and real-time requirements

## Цель и наблюдаемый результат

Новый блок требований должен быть отражен в baseline-документах так, чтобы Mistral, Watcher и Masakari планировались как first-class модули интерфейса, а real-time UX, высокая плотность данных и защита OpenStack API были явно учтены в будущих этапах. Наблюдаемый результат: документы больше не описывают Watcher/Masakari как второстепенные linked views, а фиксируют их доменную модель, API, UX, риски автоматизации, тесты и evidence.

## Контекст и текущее состояние

- Репозиторий находится на ветке `feature/e01-bootstrap`; рабочее дерево перед началом правки было чистым.
- `docs/generated/current-state.md` фиксирует, что E01 bootstrap реализован, а Mistral, Watcher и Masakari включены в lab service catalog после обновления Kolla 2026-06-19.
- `docs/01_SCOPE_AND_REQUIREMENTS.md` до этой правки относил `SSE` и `Watcher/Masakari linked views` к `Should для P2`, что слабее нового требования.
- `docs/07_WORKFLOWS.md` описывал Watcher/Masakari только как примеры allowlisted функций.
- `docs/generated/poc-scope.md` содержал устаревшее утверждение, что test cloud не exposes Mistral, Watcher или Masakari.

## Scope

- Обновить требования и архитектурные документы без реализации кода.
- Зафиксировать first-class scope для Mistral, Watcher и Masakari.
- Зафиксировать real-time delivery strategy: SSE, WebSocket conditions, polling fallback, adaptive polling, backpressure, fan-out и protection OpenStack API.
- Зафиксировать high-density UX и visualization requirements: capacity/health dashboards, topology/dependency graph, inventory tree, large tables and partial-permission behavior.
- Обновить future-stage tasks, API/integration/scale registers, test strategy и DKB traceability.

## Non-goals

- Не начинать E02 или последующие этапы реализации.
- Не добавлять runtime dependency, Redis/search cluster/WebSocket infrastructure или новый image.
- Не заявлять production readiness, DKB closure или full HA evidence.
- Не выполнять реальные mutating OpenStack actions.

## Требования и ограничения

- Browser обращается только к frontend и BFF/API; прямой OpenStack API из JavaScript запрещен.
- OpenStack credentials не попадают в browser, localStorage/sessionStorage, logs, audit payload или RabbitMQ messages.
- Все list/read APIs остаются server-side paginated, filtered and sorted.
- Long-running actions remain allowlisted Mistral workflows or explicitly bounded service adapters.
- Watcher recommendations and Masakari recovery actions require portal capability, OpenStack policy and audit; automatic apply is disabled until explicitly approved.
- Event delivery accelerates UX but reconciliation remains correctness authority.

## Связь с ДКБ

- ДКБ-01/03/12: расширяется surface прав и capability matrix для Mistral/Watcher/Masakari, topology, health and event streams.
- ДКБ-46–53: расширяется перечень audit/observability events and external event sources.
- ДКБ-66: Masakari HA/recovery visualization and failover evidence are future E10/P3 evidence, not current compliance.
- ДКБ-77/82: расширяется реестр API/interfaces and documentation obligations.
- ДКБ-72 remains external storage architecture evidence; Nova evacuate/live migration visualization does not close storage requirements.

## Milestones

1. Requirements alignment: `docs/01_SCOPE_AND_REQUIREMENTS.md`, `docs/generated/poc-scope.md`.
2. Architecture and data model: `docs/02_TARGET_ARCHITECTURE.md`, `docs/04_DOMAIN_AND_DATA.md`.
3. API/workflow/performance contracts: `docs/05_API_AND_INTEGRATIONS.md`, `docs/07_WORKFLOWS.md`, `docs/09_PERFORMANCE_HA.md`.
4. Verification scope: `docs/13_TEST_STRATEGY.md`, `tasks/E04_INVENTORY_UI.md`, `tasks/E06_WORKFLOWS.md`, `tasks/E10_SCALE_HA.md`.
5. Evidence registers: `docs/generated/api-register.md`, `docs/generated/integration-register.md`, `docs/generated/scale-profile.md`, `docs/15_DECISIONS_AND_OPEN_QUESTIONS.md`, `docs/11_DKB_TRACEABILITY.md`.

## Progress

- [x] 2026-06-21: Исследование фактического состояния.
- [x] 2026-06-21: Документы требований и архитектуры обновлены.
- [x] 2026-06-21: Generated/register docs reconciled with current lab state.
- [x] 2026-06-21: Проверки и self-review выполнены. Evidence: `git diff --check`, `./scripts/secret-scan.sh`, `make lint`, `make test`.
- [x] 2026-06-21: Primary documentation research applied to Masakari/Consul/Prometheus decisions. Evidence: `docs/15_DECISIONS_AND_OPEN_QUESTIONS.md` research links, updated generated registers, `git diff --check`, `./scripts/secret-scan.sh`, `make lint`, `make test`.
- [x] 2026-06-21: Risk register added for E00/E02 transition. Evidence: `docs/generated/risk-register.md`.
- [x] 2026-06-21: Resume verification repeated before E02 implementation. Evidence: `git diff --check`, `./scripts/secret-scan.sh`, stale-statement `rg`, `make lint`, `make typecheck`, `make test`; review fixed Masakari deferral wording and WebSocket ADR wording.

## Неожиданные открытия

- `docs/generated/poc-scope.md` противоречил `docs/generated/current-state.md` и `docs/generated/api-register.md`: он все еще описывал Mistral/Watcher/Masakari как отсутствующие в service catalog.
- 2026-06-21 research: Masakari hostmonitor officially supports Consul driver and matrix-based recovery action. Consul Events are not durable authoritative transport, and Masakari processmonitor has a documented container/pod deployment caveat.

## Журнал решений

- 2026-06-21: Treat Mistral, Watcher and Masakari as first-class portal modules from requirements onward. Reason: new user requirement explicitly rejects secondary linked pages.
- 2026-06-21: Keep SSE as default browser real-time channel and WebSocket as ADR-gated option. Reason: most portal updates are server-to-browser streams, and adding bidirectional infrastructure without measured need would violate dependency discipline.
- 2026-06-21: Keep reconciliation as correctness authority. Reason: event ordering and notification transport are still unverified.
- 2026-06-21: Use Masakari hostmonitor Consul driver + `matrix.yaml` as the preferred network-health recovery authority; use Prometheus exporter metrics and Consul Events only as diagnostic/corroborating signals. Reason: this matches Masakari monitor architecture and avoids duplicating evacuation decisions in the portal.

## Детальный план реализации

- Update `docs/01_SCOPE_AND_REQUIREMENTS.md` with first-class module requirements, real-time UX and high-performance visualization requirements.
- Update `docs/02_TARGET_ARCHITECTURE.md` with direct first-class adapters and event delivery architecture.
- Update `docs/04_DOMAIN_AND_DATA.md` with Watcher, Masakari, service health, topology and event stream projections.
- Update `docs/05_API_AND_INTEGRATIONS.md` with planned API surfaces and adapter responsibilities.
- Update `docs/07_WORKFLOWS.md` with Watcher/Masakari workflows, approval gates, rollback/abort and Mistral operation center semantics.
- Update `docs/09_PERFORMANCE_HA.md` with real-time/backpressure/API-protection strategy and visualization performance model.
- Update task files and generated registers so future stages consume the new requirements.

## Миграции и совместимость

Документарная правка не меняет БД, OpenAPI snapshot or runtime behavior. Future schema/API changes must use Alembic, OpenAPI and contract tests in their own stages.

## Проверка

- `git diff --check`
- `./scripts/secret-scan.sh`
- `make lint` if local dependencies remain available
- `make typecheck` if local dependencies remain available
- `make test` if local dependencies remain available
- `rg` checks for stale statements that Mistral/Watcher/Masakari are absent

## Доказательства

- This ExecPlan.
- Updated requirements/docs/registers.
- Command results in final report.

## Откат и восстановление

Safe rollback: revert this documentation patch or restore the changed Markdown files from the previous commit. No runtime state or database migration is affected.

## Итог и остаточные риски

Документы требований, архитектуры, API, workflow, performance/HA, тестирования, ДКБ-трассировки и future-stage tasks обновлены. Secret scan scope исправлен, чтобы ignored `.worktrees/` не ломал проверку локальными worktree copies; добавлен regression test.

Остаточные риски: Prometheus endpoint/retention/cardinality, Ceilometer/Gnocchi/Aetos ownership, Masakari hostmonitor Consul deployment in non-AIO HA lab, `matrix.yaml` ownership, processmonitor container viability, real notification transport, production scale numbers and WebSocket necessity remain unresolved external decisions.
