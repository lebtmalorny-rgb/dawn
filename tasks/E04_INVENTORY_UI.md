# E04 — Inventory read model и UI ВМ/гипервизоров

## Пользовательский результат

Оператор открывает страницы ВМ и гипервизоров, использует server-side filters/sort/pagination, видит freshness и частичные ошибки. Backend не опрашивает весь OpenStack на каждый page request.

## Входные критерии

- E03 принят.
- Scale profile существует.
- Согласованы минимальные поля instance/hypervisor.
- Выбран provisional freshness target.

## Прочитать

- `docs/01_SCOPE_AND_REQUIREMENTS.md`;
- `docs/04_DOMAIN_AND_DATA.md`;
- `docs/05_API_AND_INTEGRATIONS.md`;
- `docs/09_PERFORMANCE_HA.md`;
- `docs/13_TEST_STRATEGY.md`.

## Единицы работы

### E04.1. Схема read model

Добавить Alembic migrations для clouds/regions, instances, hypervisors, sync runs/cursors/failures и необходимых справочников. Индексы обосновать query cases.

### E04.2. Full reconciliation

Worker выполняет chunked full sync с generation, cursor, retry и tombstone. Повторный запуск идемпотентен. Частичный сбой не удаляет корректные данные.

### E04.3. Incremental refresh

Добавить targeted refresh и базовый periodic reconciliation. Event consumer может сначала принимать собственные synthetic events; подключение реальных notifications — отдельная единица после contract.

### E04.4. Inventory API

Реализовать list/detail instances/hypervisors:

- signed cursor;
- typed filter allowlist;
- stable sort;
- max limit;
- freshness;
- partial warnings;
- capability checks.

### E04.5. Frontend tables

Страницы Instances и Hypervisors:

- URL-controlled filters/sort/page;
- loading/empty/error/partial/stale states;
- linked navigation;
- no full inventory client load;
- table virtualization only for visible page/window, not as replacement for server pagination;
- saved-view-ready state model for filters/sort/columns/density;
- accessibility;
- capability-aware columns/actions.

### E04.6. Synthetic scale test

Сгенерировать dataset из scale profile. Проверить correctness, p95, `EXPLAIN`, memory и отсутствие N+1. Сохранить sanitized report.

### E04.7. Real test-cloud read-only smoke

При доступности test cloud выполнить reconciliation и сравнить выборочно read model с Nova. Не использовать production.

### E04.8. Service health and visualization extension points

Описать и протестировать contract placeholders for compute services, Neutron agents, Cinder services, image tasks, topology graph and capacity summary without enabling modules that lack adapters. Disabled modules must appear as explicit capability/feature flags, not broken links.

## Acceptance

- таблица 10 000 synthetic instances работает через server pagination;
- page size ограничен;
- cursor tampering rejected;
- фильтры/sort дают стабильный результат;
- large-table UX does not fetch full inventory into browser;
- saved view state can round-trip through URL/local user preference model without storing result rows;
- full sync можно повторить;
- пропущенное событие исправляется reconciliation;
- stale/partial visible;
- list request не делает fan-out по всем resources;
- service health/topology placeholders are feature-flagged and capability-aware;
- p95 соответствует provisional budget либо есть finding;
- audit фиксирует protected refresh/admin actions;
- DKB/API docs обновлены.

## Затронутые ДКБ

- ДКБ-01/03/12: scope и access к inventory.
- ДКБ-46/49: request/correlation/freshness events.
- ДКБ-60: данные для будущих групп.
- ДКБ-77/82: API и документация.

## Не делать

- arbitrary bulk action;
- dynamic groups;
- mutating Nova;
- Mistral workflow;
- production event binding до E07/E08 review.

## Итоговый запрос Codex

> Выполни E04 как первый ценный vertical slice. Сначала schema и full reconciliation, затем API, затем UI, затем load evidence. Не оптимизируй без измерения и не загружай весь inventory в browser.
