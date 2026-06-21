# ExecPlan: E04 Inventory read model and UI

## Цель и наблюдаемый результат

После E04 оператор входит в портал и открывает страницы ВМ и гипервизоров. Списки работают через
server-side pagination/filter/sort из MariaDB read model, показывают freshness, stale/partial state
и не вызывают OpenStack API на каждый page request. Backend умеет выполнить deterministic synthetic
full reconciliation для 10 000 ВМ и 1 000 гипервизоров, а sanitized scale report фиксирует p95 и
`EXPLAIN` для критичных запросов.

До E04 в коде есть E03 adapters, но нет read-model tables, inventory API, reconciliation service или
frontend inventory pages.

## Контекст и текущее состояние

- Repository root: `/Users/dmitry/Desktop/dawn`.
- Active worktree: `/Users/dmitry/Desktop/dawn/.worktrees/e04-inventory-ui`.
- Current base commit: `4537e6a feat: add OpenStack adapter contracts`.
- Design spec: `docs/superpowers/specs/2026-06-21-e04-inventory-ui-design.md`.
- Baseline verification in E04 worktree: `make test` -> backend `58 passed`, frontend `6 passed`.
- Existing backend app assembly: `backend/src/cloud_ui/api.py`.
- Existing security/session/capability layer: `backend/src/cloud_ui/security/`.
- Existing migrations:
  - `backend/src/cloud_ui/migrations/versions/0001_schema_info.py`;
  - `backend/src/cloud_ui/migrations/versions/0002_security_foundation.py`.
- Existing OpenStack adapter package: `backend/src/cloud_ui/integrations/`.
- Existing frontend: compact PatternFly app in `frontend/src/App.tsx` with typed fetch helpers in
  `frontend/src/api.ts`.

## Scope

- Add inventory read-model schema for clouds, regions, instances, hypervisors, sync runs, cursors
  and failures.
- Add SQLAlchemy table definitions used by repository tests and runtime queries.
- Add deterministic synthetic inventory source and chunked full reconciliation.
- Add idempotent full sync behavior, partial failure recording and tombstone after successful full
  run completion.
- Add signed cursor, typed filters, stable sort and limit enforcement.
- Add read-only list/detail APIs for instances and hypervisors.
- Add protected instance refresh contract path with CSRF/capability/audit, without Nova mutation.
- Add capability-aware disabled module descriptors for compute services, network agents, volume
  services, image tasks, topology and capacity.
- Add frontend navigation and pages for instances and hypervisors.
- Add synthetic scale report and `make test-load`.
- Update API, integration, risk and DKB traceability documents.

## Non-goals

- No dynamic groups or group preview.
- No Mistral workflow execution.
- No mutating Nova operation.
- No real OpenStack notification binding.
- No production credential or admin credential usage.
- No real compute-service, Neutron, Cinder, Glance, topology or capacity module implementation.
- No Redis or new persistent infrastructure dependency.
- No claim that synthetic scale evidence is production MariaDB/HA evidence.

## Требования и ограничения

- Browser talks only to frontend and portal BFF/API.
- Browser must not receive OpenStack tokens, application credentials, raw service URLs or raw
  OpenStack schemas.
- Route handlers must not import `httpx`, OpenStack SDK or E03 HTTP transport directly.
- Backend re-checks authorization for each inventory endpoint.
- List APIs use server-side pagination, filters and stable sort; page size maximum is 200.
- Inventory list requests read from read model and must not perform live fan-out across OpenStack.
- Synthetic tests contain no production payloads.
- DB migration must have downgrade and be safe to run before rolling out API/UI code.
- E04 uses provisional scale profile from `docs/generated/scale-profile.md`: 10 000 instances,
  1 000 hypervisors, default page size 50, max page size 200, p95 read-model list budget <= 2 s.

## Связь с ДКБ

- ДКБ-01/03/12: E04 implements backend capability checks for inventory read/refresh and
  capability-aware UI navigation. Evidence: API negative tests and frontend capability tests.
  Full OpenStack policy coverage remains external and service-level.
- ДКБ-46/49: E04 records request/correlation/freshness metadata for sync and protected refresh.
  Full audit delivery remains E07/SIEM. Evidence: refresh audit test and sync run records.
- ДКБ-60: E04 creates data foundation for future groups through instance/hypervisor projections
  only. It does not implement groups. Evidence: schema fields and risk note.
- ДКБ-77/82: E04 updates API/register docs for new endpoints and disabled descriptors. Technical
  blocking of unused OpenStack APIs remains E08/E09/P3 evidence.

## Milestones

1. Schema and migration tests pass for E04 tables and rollback order.
2. Cursor, DTO and repository tests pass for filter/sort/page/detail and tamper rejection.
3. Synthetic full reconciliation tests pass for idempotency, partial failure and tombstone.
4. Inventory API tests pass for capabilities, validation, partial warnings, OpenAPI and refresh
   audit.
5. Frontend tests pass for navigation, URL state, current-page-only rendering and stale/partial
   states.
6. Synthetic scale report is generated and documented.
7. Full gates pass in E04 worktree and after merge.

## Progress

- [x] 2026-06-21: Design spec approved and committed. Evidence: commit
  `9caac49 docs: add E04 inventory UI design`.
- [x] 2026-06-21: Baseline verified. Evidence: `make test` -> backend `58 passed`, frontend
  `6 passed`.
- [x] 2026-06-21: Schema and migration implemented. Evidence: commit
  `f638dea feat: add inventory read model migration`; targeted tests
  `tests/inventory/test_inventory_migration.py tests/security/test_security_migration.py` -> `2 passed`;
  spec and quality reviews approved.
- [x] 2026-06-21: Cursor, DTO and repository implemented. Evidence: commits
  `079919f feat: add inventory repository and cursors`,
  `6c5b163 fix: harden inventory pagination and config`,
  `8fd3f3e fix: bound inventory warning freshness`; targeted tests
  `tests/inventory/test_cursor.py tests/inventory/test_repository.py tests/inventory/test_inventory_migration.py tests/test_config.py`
  -> `23 passed`; scoped Ruff and mypy passed; final quality review approved with no blocking issues.
- [x] 2026-06-21: Synthetic reconciliation implemented. Evidence: commits
  `14a08e7 feat: add synthetic inventory reconciliation`,
  `d17abaf fix: harden synthetic reconciliation state`; targeted tests
  `tests/inventory/test_reconciliation.py tests/test_cli.py` -> `12 passed`; regression inventory/config tests
  -> `23 passed`; scoped Ruff and mypy passed; final quality review approved with no blocking issues.
- [x] 2026-06-21: Inventory API and authorization implemented. Evidence: commits
  `8559c34 feat: add inventory API routes`,
  `b5ebae4 test: cover inventory API authorization denials`,
  `a088056 test: update inventory auth expectations`,
  `4de9fa2 fix: require idempotency for inventory refresh`,
  `945f5c1 fix: harden inventory API contract`,
  `f620e7e fix: align inventory API filters and limits`; targeted API/security tests
  `tests/security/test_mock_identity.py tests/inventory/test_inventory_api.py tests/security/test_security_api.py`
  -> `33 passed`; full backend `tests -q` -> `107 passed`; scoped Ruff and mypy passed; final
  spec and quality reviews approved with no blocking issues.
- [x] 2026-06-21: Frontend inventory pages implemented. Evidence: commits
  `1260448 feat: add inventory frontend pages`,
  `acb7d01 fix: make inventory workspace full width`,
  `9e1537d fix: complete inventory frontend spec gaps`,
  `7f5d57a fix: harden inventory frontend request controls`,
  `b9d9d39 fix: keep refresh affordance inert`; targeted frontend tests
  `npm test -- --run src/App.test.tsx` -> `22 passed`; `npm run typecheck`,
  `npm run lint`, `git diff --check 50f3a0d..HEAD`, browser-storage/direct-URL scans passed;
  final spec and quality reviews approved with no blocking issues.
- [x] 2026-06-21: Synthetic scale evidence generated and documented. Evidence: commits
  `72a9da0 feat: add E04 synthetic scale report`,
  `1dec331 docs: refresh E04 scale evidence`,
  `551f38c fix: explain measured inventory queries`,
  `764fa97 docs: refresh measured E04 scale report`; `make test-load` generated
  `docs/generated/e04-scale-report.md` for 10 000 instances / 1 000 hypervisors with
  `success=True`, SQL max `5`, p95 below 2 s in all scenarios, SQLite `EXPLAIN QUERY PLAN`
  from captured measured repository SQL, and peak Python memory `3.622 MiB`; targeted tests
  `tests/inventory/test_scale_report.py tests/inventory/test_reconciliation.py tests/inventory/test_repository.py`
  -> `28 passed`; scoped Ruff, scoped mypy, secret scan and final spec/quality reviews approved.
- [ ] Final verification, review and integration.

## Неожиданные открытия

- Current backend has no ORM model layer; E04 will add focused SQLAlchemy table definitions under
  `cloud_ui.inventory.schema` while keeping Alembic migration scripts manual.
- Current FastAPI app can be constructed in tests without runtime settings. E04 inventory services
  must remain injectable so existing security tests do not start requiring runtime DB settings.
- Current mock identity already grants `instance.read` and `hypervisor.read` to viewer/operator, but
  does not grant `instance.refresh`; E04 will add refresh capability only where tests require it.
- Null-bucket keyset ordering uses portable SQL `CASE WHEN` expressions. E04.6 scale evidence must
  include `EXPLAIN` for representative sorts and warning queries before claiming p95/index behavior.
- Synthetic reconciliation generation allocation is sequentially correct for current tests but is
  not a distributed lock. HA scheduling or multi-worker reconciliation needs a lease/atomic
  allocation design before production enablement.
- Finalization failures are visible through region partial state, but they do not yet create a
  generic `inventory_sync_failures` row. E04 API/UI can surface the region warning; operational
  failure detail may need a later audit/log event.
- Inventory API list parameters are safely clamped at runtime. OpenAPI currently exposes integer
  `limit` but not configured maximum/default metadata; update this when generated API docs are
  finalized.
- The runtime inventory DB engine is held in FastAPI app state and relies on process shutdown for
  disposal. Add explicit lifespan disposal before production deployment hardening.
- Frontend refresh affordance is capability-aware but intentionally disabled until the frontend has
  a complete CSRF/idempotency request contract for the mutating refresh flow. Backend refresh
  authorization/audit remains covered by API tests.
- No Playwright/e2e command exists yet in this worktree, so E04.5 browser-level evidence is limited
  to Vitest/RTL component coverage and static checks.
- E04.6 synthetic scale report is local SQLite evidence only, not production MariaDB/HA evidence.
  The measured default instance and hypervisor scenarios include SQLite `USE TEMP B-TREE FOR ORDER BY`
  because repository null-bucket ordering is part of the real list SQL; this is documented rather
  than hidden.

## Журнал решений

- 2026-06-21: Use deterministic synthetic source as first reconciliation backend. Alternative:
  live Nova/Placement smoke. Reason: no approved read-only test credential exists outside git, and
  E04 requires reproducible 10k/1k scale evidence. Consequence: live smoke remains pending.
- 2026-06-21: Add SQLAlchemy Core tables and repository functions instead of a full ORM. Alternative:
  declarative ORM. Reason: existing code uses SQLAlchemy Core-style DB helpers and manual migrations;
  Core keeps query/index behavior explicit for E04.
- 2026-06-21: Keep table UI as semantic HTML with PatternFly shell instead of adding a table package.
  Alternative: add `@patternfly/react-table`. Reason: no new dependency is needed for current page
  rendering; server-side pagination is the core requirement.
- 2026-06-21: Add `make test-load` for the E04 synthetic report. Alternative: leave load command
  undocumented. Reason: E04 acceptance requires reproducible load evidence.

## Детальный план реализации

Implementation plan: `docs/superpowers/plans/2026-06-21-e04-inventory-ui.md`.

Files to create:

- `backend/src/cloud_ui/migrations/versions/0003_inventory_read_model.py`
- `backend/src/cloud_ui/inventory/__init__.py`
- `backend/src/cloud_ui/inventory/models.py`
- `backend/src/cloud_ui/inventory/schema.py`
- `backend/src/cloud_ui/inventory/cursor.py`
- `backend/src/cloud_ui/inventory/synthetic.py`
- `backend/src/cloud_ui/inventory/repository.py`
- `backend/src/cloud_ui/inventory/reconciliation.py`
- `backend/src/cloud_ui/inventory/routes.py`
- `backend/src/cloud_ui/inventory/scale_report.py`
- `backend/tests/inventory/test_inventory_migration.py`
- `backend/tests/inventory/test_cursor.py`
- `backend/tests/inventory/test_repository.py`
- `backend/tests/inventory/test_reconciliation.py`
- `backend/tests/inventory/test_inventory_api.py`
- `backend/tests/inventory/test_scale_report.py`
- `scripts/e04_scale_report.py`
- `docs/generated/e04-scale-report.md`

Files to modify:

- `Makefile`
- `backend/src/cloud_ui/api.py`
- `backend/src/cloud_ui/cli.py`
- `backend/src/cloud_ui/config.py`
- `backend/src/cloud_ui/security/mock_identity.py`
- `backend/tests/test_cli.py`
- `backend/tests/test_config.py`
- `frontend/src/App.tsx`
- `frontend/src/App.test.tsx`
- `frontend/src/api.ts`
- `frontend/src/styles.css`
- `docs/11_DKB_TRACEABILITY.md`
- `docs/generated/api-register.md`
- `docs/generated/integration-register.md`
- `docs/generated/risk-register.md`
- this ExecPlan.

Implementation sequence:

1. Write failing tests for migration and schema shape, then add `0003_inventory_read_model.py` and
   `inventory/schema.py`.
2. Write failing tests for cursor signing and repository queries, then add `models.py`,
   `cursor.py`, `repository.py` and settings.
3. Write failing reconciliation tests, then add deterministic synthetic source and reconciliation
   service.
4. Write failing API tests, then add inventory routes and app wiring.
5. Write failing frontend tests, then evolve `api.ts`, `App.tsx` and CSS.
6. Write failing scale report tests, add report script and `make test-load`, generate sanitized
   report.
7. Update docs/registers/ExecPlan and run final gates.

## Миграции и совместимость

E04 migration is additive. It creates new inventory tables and indexes and does not modify E01/E02
tables. Safe rollout order:

1. Run `cloud-ui db-upgrade` before enabling E04 routes in production-like deployment.
2. Deploy backend with E04 routes.
3. Run synthetic or real read-only reconciliation.
4. Deploy frontend navigation.

During rolling update, old code ignores new tables. New frontend expects new endpoints, so frontend
should roll after backend. Downgrade drops E04 tables in dependency order and removes read-model
data. No existing sessions/audit records are dropped by E04 downgrade.

## Проверка

Required commands from `/Users/dmitry/Desktop/dawn/.worktrees/e04-inventory-ui`:

- `cd backend && .venv/bin/python -m pytest tests/inventory -q` -> all E04 backend tests pass.
- `cd frontend && npm test -- --run src/App.test.tsx` -> frontend inventory tests pass.
- `make test-load` -> writes sanitized `docs/generated/e04-scale-report.md` and exits 0.
- `git diff --check` -> no output, exit 0.
- `./scripts/secret-scan.sh` -> no output, exit 0.
- `make lint` -> backend Ruff, frontend ESLint and secret scan pass.
- `make typecheck` -> backend mypy and frontend `tsc -b` pass.
- `make test` -> backend pytest and frontend Vitest pass.

Review commands:

- `rg -n "httpx|OpenStackHttpClient|requests" backend/src/cloud_ui/api.py backend/src/cloud_ui/inventory backend/src/cloud_ui/security` -> only inventory tests/docs may mention the boundary; routes must not import `httpx`.
- `rg -n "localStorage|sessionStorage" frontend/src` -> no inventory result rows stored in browser storage.
- `git diff --stat` and `git diff --name-only` -> only E04 files and docs changed.

## Доказательства

- Alembic migration tests and downgrade order.
- Cursor tamper rejection tests.
- Repository filter/sort/page tests.
- Reconciliation idempotency, partial failure and tombstone tests.
- API capability, validation, OpenAPI and refresh audit tests.
- Frontend capability/URL-state/partial/stale tests.
- `docs/generated/e04-scale-report.md` with sanitized p95 and `EXPLAIN` summary.
- Updated DKB traceability and generated registers.
- Final command summary in the task report.

## Откат и восстановление

- Revert E04 commits.
- If DB migration was applied, run Alembic downgrade from `0003_inventory_read_model` to
  `0002_security_foundation`; this drops only E04 inventory tables.
- Re-run `cloud-ui db-upgrade` to reapply if retrying.
- Synthetic reconciliation is deterministic and can be re-run after partial failure.
- Remove regenerated `docs/generated/e04-scale-report.md` only by reverting the E04 commit that
  created it.

## Итог и остаточные риски

Pending until implementation completes:

- Real test-cloud smoke may remain pending without approved read-only credentials.
- Synthetic scale evidence is not production MariaDB/HA evidence.
- Service health, topology and capacity remain disabled descriptors, not implemented modules.
- E05 still owns resource groups and saved view persistence beyond URL state.
