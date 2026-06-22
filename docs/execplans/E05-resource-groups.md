# ExecPlan: E05 Resource groups and portal access

## Цель и наблюдаемый результат

После E05 уполномоченный пользователь сможет создать project-scoped группу ВМ, добавить явных
участников из E04 read model, открыть detail группы, увидеть revision/owner/scope, проверить
безопасное dynamic rule preview и отфильтровать страницы inventory по `group_id`. Неуполномоченный
пользователь не сможет прочитать, изменить или использовать чужую группу через прямой API request.

До E05 в коде есть E04 inventory read model, paginated instance/hypervisor API и frontend tables, но
нет собственных таблиц групп, API управления группами, group-aware inventory filters или DSL preview.

## Контекст и текущее состояние

- Repository root: `/Users/dmitry/Desktop/dawn`.
- Active worktree: `/Users/dmitry/Desktop/dawn/.worktrees/e05-resource-groups`.
- Current branch: `e05-resource-groups`.
- Base commit: `fd461bd docs: close E04 inventory execplan`.
- Design spec: `docs/superpowers/specs/2026-06-22-e05-resource-groups-design.md`.
- Design commit: `b92f1f5 docs: add E05 resource groups design`.
- Baseline verification before E05 branch creation on `main`:
  - `make test` -> backend `112 passed`, frontend `22 passed`;
  - `make lint` -> passed;
  - `make typecheck` -> passed;
  - `make security` -> passed;
  - `make test-load` -> success, SQL max `5`, p95 below provisional E04 budget.
- Existing backend app assembly: `backend/src/cloud_ui/api.py`.
- Existing security/session/capability layer: `backend/src/cloud_ui/security/`.
- Current `Subject` has capabilities but no explicit project scope. E05 must introduce a P0 trusted
  scope field before project-owned groups can be enforced.
- Existing inventory package: `backend/src/cloud_ui/inventory/` with SQLAlchemy Core schema,
  repository, signed cursor, reconciliation and routes.
- Existing frontend is a compact PatternFly app in `frontend/src/App.tsx` with typed runtime
  response validation in `frontend/src/api.ts`.

## Scope

- Add P0 project scope to authenticated subjects/capability response without claiming production
  federation semantics.
- Add group tables and migration with downgrade: groups, members and group revisions.
- Add SQLAlchemy table metadata and focused group models/repository/rule compiler modules.
- Add explicit group CRUD and membership API with CSRF, capability checks, optimistic concurrency,
  idempotent membership operations and audit events.
- Add safe JSON AST dynamic rule validation and bounded preview.
- Add `group_id` server-side inventory filters for instances and hypervisors after backend group
  access checks.
- Add frontend group list/detail/editor/member picker/dynamic preview and inventory group filter
  controls without loading full inventory into the browser.
- Update API/register/DKB/risk documentation and evidence.

## Non-goals

- No shared/cross-project group ACL beyond owner and P0 admin/system-like policy.
- No automatic Nova host aggregate, placement, migration or OpenStack mutation.
- No Mistral workflow execution.
- No arbitrary SQL, Python, Jinja, regex or free-form query language.
- No tag/metadata dynamic rules until normalized tag/member read-model tables exist.
- No real production OpenStack credential or live cloud dependency.
- No claim that P0 mock scope closes IAM/SoD requirements.

## Требования и ограничения

- Browser talks only to frontend and portal BFF/API.
- Backend re-checks authorization for every group and group-filtered inventory endpoint.
- Scope and target facts come from server-side session and trusted read model, not client assertions.
- VM membership in project-scoped groups requires `instances.project_id == resource_groups.scope_id`.
- Host groups do not inherit project ownership from VMs; host group management requires explicit
  admin/system-like P0 policy.
- Mutating group endpoints require session, trusted origin, CSRF and audit.
- Membership add/remove operations are safe to retry and require idempotency keys.
- List and preview APIs use server-side pagination/filtering/stable sort; no full inventory load.
- Dynamic rules compile only from allowlisted fields/operators to SQLAlchemy expressions.
- Migration must be safe to run before API/UI rollout and reversible through downgrade.
- No secrets, OpenStack tokens, raw service URLs or production payloads are stored in groups or audit.

## Связь с ДКБ

- ДКБ-60: E05 implements portal-owned resource groups and creates membership snapshots suitable for
  future operation targeting. Evidence: schema, API tests, UI tests and demo data. It does not mutate
  OpenStack aggregates or placement.
- ДКБ-01-04/12: E05 adds portal capability/scope checks, negative authorization tests and IDOR
  coverage. Full SoD/IAM enforcement remains external to the portal and must not be claimed.
- ДКБ-46/49/50.10/51: E05 records group create/update/delete/member/preview authorization outcomes
  in portal audit. Authoritative external SIEM delivery remains E07.
- ДКБ-77/82: E05 updates API and traceability documentation for new public endpoints and explicit
  constraints.

## Milestones

1. P0 scope model is explicit and tested in security/capability responses.
2. Group schema and migration tests pass for upgrade/downgrade order and indexes.
3. Group repository tests pass for CRUD, revision conflict, soft delete and membership idempotency.
4. Dynamic rule compiler tests pass for allowlisted fields/operators and safety limits.
5. Group API tests pass for happy path, CSRF, idempotency, audit and negative ACL/IDOR cases.
6. Inventory API supports authorized `group_id` filters with cursor tamper rejection.
7. Frontend tests pass for group navigation, pages, member picker, preview and inventory filter UX.
8. Documentation/evidence updates land and final gates pass.

## Progress

- [x] 2026-06-22: E04 accepted and reproduced on `main`. Evidence: `make test`, `make lint`,
  `make typecheck`, `make security`, `make test-load` all passed before E05 worktree creation.
- [x] 2026-06-22: E05 design approved and committed. Evidence: commit
  `b92f1f5 docs: add E05 resource groups design`.
- [x] 2026-06-22: E05 ExecPlan and implementation plan created. Evidence: this file and
  `docs/superpowers/plans/2026-06-22-e05-resource-groups.md`.
- [x] 2026-06-22: P0 scope model implemented and tested. Evidence: commit
  `8d79942 feat: add project scope to mock subjects`; targeted tests
  `tests/security/test_mock_identity.py tests/security/test_security_api.py` -> `17 passed`;
  `mypy src` -> success; spec review approved; code quality review found no Critical/Important
  issues.
- [x] 2026-06-22: Group schema implemented and tested. Evidence: commits
  `7a94d8e feat: add resource group schema`,
  `e0790be fix: harden resource group migration schema`,
  `8105628 fix: tighten resource group migration evidence`; targeted tests
  `tests/groups/test_group_migration.py tests/inventory/test_inventory_migration.py` -> `3 passed`;
  scoped Ruff and mypy passed; spec review approved; final code quality review found no
  Critical/Important/Minor issues.
- [ ] Group repository and rule compiler implemented and tested.
- [ ] Group API and group-aware inventory filters implemented and tested.
- [ ] Frontend group UX implemented and tested.
- [ ] Documentation, DKB evidence and final verification completed.

## Неожиданные открытия

- Current `Subject` lacks project scope. E05 cannot safely enforce project-owned groups until the P0
  mock identity and capability response expose a trusted `scope={"type":"project","id":"..."}` for
  viewer/operator test subjects.
- Task 1 kept `Subject.scope_type` and `Subject.scope_id` as simple Pydantic fields. Review noted
  this permits inconsistent states such as project scope with null id. This is acceptable for P0 mock
  data but should become a typed scope value or validator before production identity integration.
- Existing E04 inventory rows have `project_id` only for instances. Hypervisors are not project-owned,
  so host groups require an explicit P0 admin/system-like rule and must not be silently treated as
  project-owned.
- Task 2 changed the group-member page index to
  `(group_id, added_at, resource_type, cloud_id, region_id, resource_id)` so it does not duplicate the
  member primary key and can support stable member listing.
- Task 2 review recommended deciding in Task 3 whether revision history needs a unique
  `(group_id, revision)` constraint. This is not blocking for the schema slice but should be
  considered when repository write semantics land.
- `make test` runs backend tests from `backend/` and frontend Vitest. A root-level `pytest` also
  collects `tests/test_e015_kolla_layout.py`, which expects future Kolla files and is not part of the
  current project gate.

## Журнал решений

- 2026-06-22: Use project-scoped groups only for the first E05 slice. Alternative: shared groups.
  Reason: shared ACL semantics are not approved and would expand IDOR risk. Consequence: cross-project
  collaboration remains a documented non-goal.
- 2026-06-22: Implement explicit membership before dynamic preview. Alternative: DSL first. Reason:
  explicit membership gives a smaller vertical slice with simpler ACL and audit evidence.
  Consequence: dynamic rules reuse the same group/scope enforcement instead of defining ownership
  separately.
- 2026-06-22: Keep group logic in a new `cloud_ui.groups` backend package. Alternative: add it to
  `cloud_ui.inventory`. Reason: groups are portal-owned domain data, while inventory is an OpenStack
  projection. Consequence: inventory receives only a narrow group-filter integration.
- 2026-06-22: No new frontend dependency for group tables/forms in P0. Alternative: add a table/form
  package. Reason: current PatternFly/Core and semantic HTML are enough for server-paginated PoC.

## Детальный план реализации

Implementation plan: `docs/superpowers/plans/2026-06-22-e05-resource-groups.md`.

Files to create:

- `backend/src/cloud_ui/migrations/versions/0004_resource_groups.py`
- `backend/src/cloud_ui/groups/__init__.py`
- `backend/src/cloud_ui/groups/models.py`
- `backend/src/cloud_ui/groups/schema.py`
- `backend/src/cloud_ui/groups/repository.py`
- `backend/src/cloud_ui/groups/rules.py`
- `backend/src/cloud_ui/groups/routes.py`
- `backend/tests/groups/test_group_migration.py`
- `backend/tests/groups/test_group_repository.py`
- `backend/tests/groups/test_group_rules.py`
- `backend/tests/groups/test_group_api.py`
- `frontend/src/groups.ts`

Files to modify:

- `backend/src/cloud_ui/api.py`
- `backend/src/cloud_ui/inventory/models.py`
- `backend/src/cloud_ui/inventory/repository.py`
- `backend/src/cloud_ui/inventory/routes.py`
- `backend/src/cloud_ui/security/identity.py`
- `backend/src/cloud_ui/security/mock_identity.py`
- `backend/src/cloud_ui/security/routes.py`
- `backend/tests/inventory/test_inventory_api.py`
- `backend/tests/inventory/test_repository.py`
- `backend/tests/security/test_mock_identity.py`
- `backend/tests/security/test_security_api.py`
- `frontend/src/App.tsx`
- `frontend/src/App.test.tsx`
- `frontend/src/api.ts`
- `frontend/src/styles.css`
- `docs/04_DOMAIN_AND_DATA.md`
- `docs/05_API_AND_INTEGRATIONS.md`
- `docs/06_AUTH_RBAC_SESSIONS.md`
- `docs/11_DKB_TRACEABILITY.md`
- `docs/generated/api-register.md`
- `docs/generated/integration-register.md`
- `docs/generated/risk-register.md`
- this ExecPlan.

Implementation sequence:

1. Extend P0 subject scope and update security tests.
2. Add group migration/schema tests and implementation.
3. Add group repository models/tests and implementation.
4. Add dynamic rule compiler tests and implementation.
5. Add group API tests/routes and audit.
6. Integrate group filters into inventory API/repository tests.
7. Add frontend group UX and tests.
8. Update docs/evidence and run final gates.

## Миграции и совместимость

- `0004_resource_groups` is expand-only: it creates new portal-owned tables and indexes.
- Old API/UI code ignores new tables, so migration can run before deployment of E05 code.
- Downgrade drops group indexes and tables in reverse dependency order: members/revisions first, then
  groups.
- No OpenStack resource is mutated; rollback deletes only portal-owned group metadata.
- If API code is rolled back after migration, unused tables remain harmless until downgrade.
- If migration fails before completion, rerunning Alembic should either resume from the previous
  revision or fail before partial production rollout; implementation tests must cover ordering.

## Проверка

Targeted commands during implementation:

- `cd backend && .venv/bin/python -m pytest tests/security/test_mock_identity.py tests/security/test_security_api.py -q`
- `cd backend && .venv/bin/python -m pytest tests/groups -q`
- `cd backend && .venv/bin/python -m pytest tests/inventory/test_repository.py tests/inventory/test_inventory_api.py -q`
- `cd frontend && npm test -- --run src/App.test.tsx`
- `cd backend && .venv/bin/python -m ruff check src tests`
- `cd backend && .venv/bin/python -m mypy src`

Final gates:

- `make lint`
- `make typecheck`
- `make test`
- `make security`

If group filtering changes measured inventory plans, run `make test-load` and update sanitized scale
evidence with an explicit E05 finding.

## Доказательства

- Committed design spec and this ExecPlan.
- Migration tests proving table/index creation and downgrade order.
- Group repository/API/rule negative tests proving ACL, revision, idempotency and DSL safety.
- Frontend tests proving group UX does not fetch full inventory.
- Updated generated API/integration/risk registers.
- Updated DKB traceability for ДКБ-60, ДКБ-01-04/12, ДКБ-46/49/50.10/51 and ДКБ-77/82.
- Final command results recorded in Progress.

## Откат и восстановление

- Roll back application code by reverting E05 commits.
- Run Alembic downgrade from `0004_resource_groups` to `0003_inventory_read_model` before removing
  E05 code in environments where the migration was applied.
- Delete only portal-owned group test data; do not touch OpenStack resources.
- Re-run E04 inventory reconciliation or synthetic seed if tests need baseline inventory rows.

## Итог и остаточные риски

Not implemented yet. Current state is design plus plan only. Known risks before implementation:

- P0 mock project scope is not production IAM evidence.
- Host group semantics need strict tests because hypervisors are not project-owned.
- Dynamic rules must remain small and allowlisted until query telemetry justifies additional fields.
- Browser-level evidence is limited to Vitest unless a Playwright command is introduced in a later
  stage.
