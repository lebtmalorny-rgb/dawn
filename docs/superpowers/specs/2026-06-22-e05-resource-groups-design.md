# E05 Resource Groups Design

Дата: 2026-06-22  
Статус: approved for ExecPlan  
Ветка/worktree: `e05-resource-groups` / `.worktrees/e05-resource-groups`

## Цель

E05 добавляет прикладные группы ВМ и хостов поверх E04 inventory read model. Уполномоченный пользователь сможет создать логическую группу, добавить явных участников, проверить безопасное динамическое правило через preview и затем фильтровать inventory по группе. Backend остается единственным enforcement point для ownership, scope, ACL, optimistic concurrency и audit.

Первый vertical slice идет по консервативному пути: explicit groups first, dynamic preview second. Это дает проверяемое поведение до появления DSL-компилятора и снижает риск IDOR/cross-scope ошибок.

## Утвержденные решения

- Использовать вариант A: сначала schema, explicit membership API, ACL/audit и inventory `group_id` filter; затем safe dynamic rule validation/preview/evaluation.
- В первом срезе разрешены только project-scoped группы. `owner_subject_id` равен создателю группы.
- Shared/cross-project groups не входят в E05 и фиксируются как non-goal.
- VM membership в project-scoped группе требует совпадения `instances.project_id` со `resource_groups.scope_id`.
- Host groups не получают project ownership автоматически, потому что `hypervisors` не имеют `project_id`. Для P0 host-группы требуют отдельной admin/system-like capability policy; смешанные группы не должны скрыто расширять project scope.
- Tags/metadata dynamic rules остаются documented gap, пока нет нормализованных tag/member lookup таблиц.
- UI не содержит правил авторизации. Он использует capabilities только для UX, а backend повторно проверяет каждое действие.

## Data Model

Добавляются таблицы через Alembic migration с downgrade:

- `resource_groups`
  - `group_id`
  - `name`
  - `description`
  - `resource_type`: `vm`, `host`, `mixed`
  - `scope_type`: initially `project`
  - `scope_id`
  - `membership_mode`: `explicit`, `dynamic`, `imported`
  - `rule_version`
  - `rule_body_json`
  - `owner_subject_id`
  - `revision`
  - `created_at`, `updated_at`, `deleted_at`

- `resource_group_members`
  - `group_id`
  - `resource_type`: `vm`, `host`
  - `cloud_id`
  - `region_id`
  - `resource_id`
  - `source`
  - `added_by`
  - `added_at`
  - `expires_at`

- `resource_group_revisions`
  - compact append-only change evidence for audit/debug
  - not the source of truth for group state

Initial indexes cover:

- list groups by owner/scope/deleted/name;
- members by group/page;
- reverse lookup by resource key for inventory `group_id` filtering;
- revision conflict checks by `group_id`.

## Backend API

Initial endpoints:

- `GET /api/v1/groups`
- `POST /api/v1/groups`
- `GET /api/v1/groups/{group_id}`
- `PATCH /api/v1/groups/{group_id}`
- `DELETE /api/v1/groups/{group_id}`
- `GET /api/v1/groups/{group_id}/members`
- `POST /api/v1/groups/{group_id}/members`
- `DELETE /api/v1/groups/{group_id}/members/{resource_type}/{cloud_id}/{region_id}/{resource_id}`
- `POST /api/v1/groups/rules/validate`
- `POST /api/v1/groups/{group_id}/preview`

Inventory list endpoints gain optional `group_id`. The repository applies this filter server-side after group access is checked. Cursor payloads include the changed filter hash, so cursor reuse across groups is rejected by existing tamper logic.

Mutating endpoints require session, trusted origin, CSRF, capability check, target validation, optimistic revision check where applicable, and audit event. Idempotency is required for membership add/remove where retrying the same request is expected.

## Authorization And Scope

Capabilities:

- `group.read`: read accessible groups and use them as inventory filters.
- `group.manage`: create/update/delete own project-scoped groups and manage their explicit members.
- `portal_admin`: P0 portal administration path, not an OpenStack admin-all shortcut.

Rules:

- Backend derives actor and scope from server-side session and trusted read model, not from client assertions.
- Direct API access without capability returns `403`.
- Cross-project VM membership returns `403` or `404` according to safe existence-disclosure behavior selected in the implementation plan.
- Deleted or missing targets cannot be added.
- Stale `revision` returns `409`.
- Service subjects are not treated as human group owners.
- Portal group access cannot expand OpenStack policy. E05 only operates on portal-owned group metadata and E04 read model projections.

## Dynamic Rule DSL

Dynamic rules use ADR-010 JSON AST, compiled to allowlisted SQLAlchemy expressions. Raw SQL, Python, Jinja and regex are not accepted.

Allowed combinators:

- `all`
- `any`
- `not`

Allowed operators:

- `eq`
- `in`
- `prefix`
- `exists`

Initial VM fields:

- `project_id`
- `status`
- `host_name`
- `availability_zone`
- `flavor_id`

Initial host fields:

- `host_name`
- `service_status`
- `service_state`
- `availability_zone`
- `maintenance_status`

Safety limits:

- `additionalProperties=false` for every node shape;
- max depth;
- max node count;
- max `in` list length;
- value type validation per field/operator;
- preview max limit lower than normal inventory max, initially 50;
- dynamic VM rules are scope-clamped to `resource_groups.scope_id`.

`POST /api/v1/groups/rules/validate` validates shape and returns safe errors. `POST /api/v1/groups/{group_id}/preview` returns bounded `items`, `count_estimate`, `explain` and warnings without storing result rows. Saved dynamic groups store only rule body/version and revision.

Preview and actual inventory filtering must use the same compiler path.

## Frontend

Frontend extends the current PatternFly shell without new table or form dependencies unless implementation evidence shows a local need.

User-facing additions:

- navigation entry `Группы`;
- group list with loading/empty/error/forbidden states;
- group detail showing owner, scope, source/mode and revision;
- editor for name, description, resource type and membership mode;
- explicit member picker backed by server-side inventory search and pagination;
- dynamic preview panel with a P0 JSON editor, validation errors and bounded preview;
- inventory `group_id` URL filter, for example `?view=instances&group_id=...`.

Large-data constraints:

- no full inventory load into browser;
- no storage of result rows in local/session storage;
- filters/page/sort stay URL-controlled where they affect inventory;
- capability-aware controls are UX only, not authorization.

## Tests And Evidence

Backend tests:

- migration upgrade/downgrade for group tables;
- repository CRUD, soft delete, revision conflict and idempotent membership add/remove;
- target existence validation for VM and host resources;
- API unauthenticated/forbidden/direct access;
- cross-scope denial and IDOR tests;
- stale revision `409`;
- deleted/missing resource behavior;
- audit events for create/update/delete/member changes/preview denial;
- rule validation invalid field/operator, extra properties, max depth, node count and value limits;
- inventory `group_id` filter stable sort/page/cursor tamper rejection.

Frontend tests:

- group navigation visibility by capability;
- direct forbidden state;
- group list/detail/editor states;
- member picker uses paginated API and does not fetch all inventory;
- dynamic preview success/error/empty states;
- inventory URL group filter round-trip.

Final gates:

- `make lint`
- `make typecheck`
- `make test`
- `make security`

If group filter scale behavior changes E04 assumptions, extend sanitized load evidence through `make test-load` or a new generated report.

## Documentation Updates

Implementation must update:

- `docs/04_DOMAIN_AND_DATA.md`
- `docs/05_API_AND_INTEGRATIONS.md`
- `docs/06_AUTH_RBAC_SESSIONS.md`
- `docs/11_DKB_TRACEABILITY.md`
- generated API/integration/risk registers as needed
- `docs/execplans/E05-resource-groups.md`

## DKB Scope

- ДКБ-60: primary functional evidence for resource grouping and future operation target snapshots.
- ДКБ-01-04/12: portal role/scope checks, negative authorization tests and IDOR resistance. Full IAM/SoD compliance remains external.
- ДКБ-46/49/50.10/51: audit events and redaction for group changes. Authoritative external SIEM remains later-stage evidence.

E05 does not claim production IAM, SIEM, OpenStack policy or Kolla hardening compliance.

## Non-goals

- No automatic Nova host aggregate changes.
- No VM migration, placement change or workflow execution.
- No arbitrary query language.
- No shared group ACL beyond owner/admin P0 policy.
- No production OpenStack credentials or live cloud dependency.
- No tag/metadata dynamic rules until normalized read-model support exists.
- No Mistral/Watcher/Masakari operation trigger.

## Rollback

Rollback is safe if migration downgrade drops E05 tables before removing E05 API/UI code. Since E05 stores portal-owned metadata only, rollback does not mutate OpenStack resources. Any test data can be recreated from E04 synthetic inventory and group API calls.

