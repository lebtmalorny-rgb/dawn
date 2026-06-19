# E03 — OpenStack adapters и контрактный слой

## Пользовательский результат

Backend безопасно получает тестовые данные Keystone/Nova/Placement через типизированные адаптеры, нормализует ошибки и не блокирует event loop. Тот же код работает с mock services без реального credential.

## Входные критерии

- E02 принят.
- OpenStack client ADR принят.
- Есть test project/credential с read-only минимальными правами либо mock-only режим.
- Зафиксированы Nova/Placement microversions.

## Прочитать

- `docs/02_TARGET_ARCHITECTURE.md`;
- `docs/03_TECH_STACK.md`;
- `docs/05_API_AND_INTEGRATIONS.md`;
- `docs/13_TEST_STRATEGY.md`.

## Единицы работы

### E03.1. Adapter framework

Создать base contracts, DTO, typed errors, timeout/retry, metrics и correlation propagation. Route handlers не вызывают SDK напрямую.

### E03.2. Mock OpenStack

Создать deterministic mock HTTP/service layer для Keystone, Nova и Placement: pagination, microversion, 401/403/404/409/429/5xx/timeout/malformed payload.

### E03.3. Keystone adapter

Service catalog, token context, scope/role references и capability discovery. Не логировать token.

### E03.4. Nova adapter

Read-only list/detail instances, hypervisors, services, aggregates/server groups по утвержденной microversion. Bounded concurrency.

### E03.5. Placement adapter

Read-only provider inventory/usage для enrichment. Graceful degradation при недоступности.

### E03.6. Contract tests

Fixtures, mapping tests, error tests и test against mock. При наличии test cloud — optional smoke без записи.

### E03.7. API registry

Обновить `docs/generated/api-register.md`: endpoints, versions, auth, network, timeout, retry, audit и blocking.

## Acceptance

- adapter tests проходят без сети;
- optional test-cloud smoke read-only;
- sync SDK не блокирует event loop;
- 401/403/timeout различаются;
- retry не выполняется для permanent errors;
- token/header redacted;
- route/service separation соблюдена;
- microversions документированы;
- frontend пока не зависит от raw OpenStack schema.

## Затронутые ДКБ

- ДКБ-01/03/12: сохранение авторизации на API-уровне.
- ДКБ-46/49: correlation/logging.
- ДКБ-77: реестр используемых API.
- ДКБ-22.02/24: только contract для TLS; deployment evidence позже.

## Не делать

- собственную read model;
- массовый live fan-out;
- mutating Nova;
- event consumer;
- Mistral.

## Итоговый запрос Codex

> Реализуй E03 через contracts-first. Сначала mock и ошибки, затем adapters. При отсутствии test cloud не фальсифицируй smoke: сохрани command и pending evidence.
