# Локальные инструкции Codex: backend

Этот файл дополняет корневой `AGENTS.md`.

## Архитектура

- HTTP route выполняет parsing, dependency injection и response mapping; бизнес-правила находятся в service/use-case слоях.
- OpenStack/Vault/SIEM/Mistral вызовы выполняются только через interfaces/adapters.
- ORM model не возвращается напрямую как API schema.
- Все внешние ошибки преобразуются в typed domain errors.
- Sync SDK не блокирует async event loop.
- DB transaction boundaries явны.
- Business mutation, operation и outbox/audit создаются атомарно.
- Migrations не запускаются при импорте или старте API.

## Безопасность

- Authorization dependency обязательна для защищенного endpoint.
- Scope/target извлекаются из trusted data, не из client assertion.
- Mutating endpoint требует CSRF и при применимости idempotency.
- Token/secret не попадает в exception string, repr, logs, metrics labels или message.
- External URL не принимается от пользователя без allowlist.
- Workflow name/code не принимается от browser.
- Raw SQL только с bound parameters и архитектурным обоснованием.
- Audit fields allowlisted и sanitized.

## Данные

- UTC-aware datetime.
- External resource key включает cloud/region.
- List endpoint — cursor, stable sort, max limit.
- JSON не используется для ключевых фильтров.
- Migration для schema change и test upgrade/downgrade.
- Destructive changes — expand/migrate/contract.

## Тесты

Для каждого endpoint:

- success;
- unauthenticated;
- forbidden;
- invalid input;
- dependency timeout/error;
- audit/correlation;
- no secret leakage.

Для adapter:

- mapping;
- microversion;
- timeout/retry;
- 401/403/404/409/429/5xx;
- malformed payload;
- redaction.

Перед завершением запускайте backend lint, typecheck, unit и измененные integration tests.
