# Локальные инструкции Codex: frontend

Этот файл дополняет корневой `AGENTS.md`.

## Архитектура

- Frontend обращается только к BFF `/api/v1`.
- OpenAPI-generated types являются базой клиента.
- Server state управляется TanStack Query; page/filter/sort находятся в URL.
- Большие таблицы используют server-side pagination/filter/sort.
- Не хранить полный inventory в глобальном state.
- Не дублировать backend authorization rules в компонентах.
- Capabilities используются для UX, а 403 обрабатывается как нормальный защищенный исход.
- Route modules изолированы по домену.

## Безопасность

- Никаких OpenStack token, password, secret или private endpoint в assets/storage.
- Не использовать `dangerouslySetInnerHTML` без отдельного security review.
- Workflow form строится только из server-approved JSON Schema.
- Не отправлять arbitrary fields.
- CSRF token/flow реализуется по backend contract.
- Ошибка показывает safe message и request/correlation ID, не stack trace.
- External links ограничены trusted destinations.
- Не считать disabled/hidden control авторизацией.

## UX больших данных

- debounce/cancel устаревших запросов;
- page size ограничен;
- loading/empty/error/partial/stale states различаются;
- bulk action показывает allowed/denied/stale targets;
- operation page доступна сразу после 202;
- polling имеет backoff и останавливается на terminal state;
- accessibility и keyboard navigation обязательны.

## Тесты

- component tests для states/capabilities;
- direct URL forbidden;
- filter URL round-trip;
- no full dataset fetch;
- partial/stale warning;
- form schema validation;
- operation failure/unknown/partial;
- Playwright critical path и negative role.

Перед завершением запускайте frontend lint, typecheck, unit и релевантный Playwright.
