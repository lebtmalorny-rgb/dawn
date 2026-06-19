# E05 — Группы ВМ/хостов и прикладной доступ

## Пользовательский результат

Уполномоченный пользователь создает логические группы ВМ и хостов, добавляет явных участников, предварительно просматривает безопасное динамическое правило и фильтрует inventory по группе. Неуполномоченный пользователь не видит или не изменяет чужую группу.

## Входные критерии

- E04 принят.
- Dynamic group rule ADR принят.
- Утверждены scope/ownership semantics.
- Начальная permission matrix включает group actions.

## Прочитать

- `docs/04_DOMAIN_AND_DATA.md`;
- `docs/06_AUTH_RBAC_SESSIONS.md`;
- `docs/10_SECURITY_DKB.md`;
- `docs/13_TEST_STRATEGY.md`.

## Единицы работы

### E05.1. Group schema

Добавить resource groups, members, revisions и ACL/scope references. Миграция безопасна для rollback.

### E05.2. Explicit membership API

CRUD group и member operations с optimistic concurrency, audit и target existence/scope validation.

### E05.3. Dynamic rule language

Реализовать декларативный AST/JSON DSL с allowlisted fields/operators, complexity/depth limit и `additionalProperties=false`. Запрещены SQL/Jinja/Python/regex без отдельного review.

### E05.4. Preview и evaluation

Preview возвращает ограниченную страницу, explain и count estimate. Evaluation использует те же filter compiler/indexes, что inventory.

### E05.5. Imported membership

Опционально импортировать tags/metadata/host aggregates/AZ как источник, сохраняя provenance. Импорт не меняет OpenStack автоматически.

### E05.6. Frontend

Страницы group list/detail/editor, member selection и dynamic preview. UI показывает owner/scope/source/revision.

### E05.7. ACL и отрицательные тесты

Cross-project/system scope, IDOR, stale revision, deleted resource, service role и audit.

## Acceptance

- VM и host можно объединить по утвержденной модели;
- explicit membership идемпотентно;
- dynamic rule не допускает arbitrary code/SQL;
- preview ограничен и paginated;
- group filter работает в inventory;
- optimistic concurrency возвращает 409;
- ACL нельзя обойти прямым API;
- все изменения имеют audit event;
- DKB-60 demo воспроизводим;
- group membership snapshot готов для E06.

## Затронутые ДКБ

- ДКБ-60 — основная функциональная реализация.
- ДКБ-01–04/12 — roles, scope, SoD.
- ДКБ-46/49/50.10/51 — аудит и redaction.

## Не делать

- автоматически перемещать ВМ;
- менять Nova host aggregate из обычного group CRUD;
- разрешать workflow;
- free-form query;
- shared group без утвержденного scope.

## Итоговый запрос Codex

> Реализуй E05 от explicit group к безопасному dynamic preview. Не связывай логическую группу с placement side effect. Отрицательные ACL tests обязательны до frontend completion.
