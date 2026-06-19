# API и интеграционные контракты

## Общие правила API

- Prefix: `/api/v1`.
- JSON, UTF-8, UTC timestamps.
- OpenAPI — обязательный контракт.
- Auth через server-side session cookie.
- Mutating requests требуют CSRF и `Idempotency-Key`.
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

### Hypervisors

    GET /api/v1/hypervisors
    GET /api/v1/hypervisors/{cloud_id}/{region_id}/{hypervisor_id}

### Resource groups

    GET    /api/v1/resource-groups
    POST   /api/v1/resource-groups
    GET    /api/v1/resource-groups/{group_id}
    PATCH  /api/v1/resource-groups/{group_id}
    DELETE /api/v1/resource-groups/{group_id}
    POST   /api/v1/resource-groups/{group_id}/members
    DELETE /api/v1/resource-groups/{group_id}/members/{member_id}
    POST   /api/v1/resource-groups/{group_id}/preview

Preview dynamic rule возвращает ограниченную страницу и explain, но не принимает SQL.

### Workflow catalog

    GET  /api/v1/workflow-definitions
    GET  /api/v1/workflow-definitions/{workflow_key}/versions/{version}
    POST /api/v1/workflow-definitions/{workflow_key}/validate-input

Изменение каталога — отдельный административный API с повышенным аудитом либо GitOps pipeline. Для production предпочтительно GitOps-публикация.

### Operations

    POST /api/v1/operations
    GET  /api/v1/operations
    GET  /api/v1/operations/{operation_id}
    POST /api/v1/operations/{operation_id}/cancel
    POST /api/v1/operations/{operation_id}/retry

Backend принимает `workflow_key`, version, targets и input. Клиент не передает произвольный Mistral workflow name.

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

Запуск, получение состояния, отмена и workflow metadata. External execution ID всегда связан с internal operation ID.

### Watcher

Audits/action plans/actions. UI не запускает неопределенный action plan напрямую; используется каталог операций.

### Masakari

Segments, hosts, notifications и recovery state. Разрешенные действия зависят от роли и workflow.

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
