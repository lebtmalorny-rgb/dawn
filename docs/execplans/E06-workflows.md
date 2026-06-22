# ExecPlan: E06 Operations-first workflow catalog and Mistral safety

## Цель и наблюдаемый результат

После E06 уполномоченный оператор сможет открыть каталог утвержденных операций, выбрать
`maintenance-host-precheck`, отправить dry-run/precheck для host target, получить `operation_id` из
`POST /api/v1/operations` со статусом `202`, открыть страницу операции и увидеть state/timeline,
correlation ID и Mistral execution ID when available. Повтор запроса с тем же `Idempotency-Key` и тем
же body возвращает ту же operation; повтор с тем же key и другим body возвращает `409`.

До E06 в коде есть security/session/RBAC, E04 inventory read model, E05 groups and group-aware
inventory filters, но нет durable operation model, workflow catalog, Mistral adapter, worker dispatch
semantics, operation timeline или frontend operation page. Единственный старый operation-like endpoint
`/api/v1/operations/simulated-openstack-action` является security-test stub, не durable workflow.

## Контекст и текущее состояние

- Repository root: `/Users/dmitry/Desktop/dawn`.
- Active worktree: `/Users/dmitry/Desktop/dawn/.worktrees/e06-workflows`.
- Current branch: `e06-workflows`.
- Base commit: `38dc427 docs: close E05 resource groups`.
- Design spec: `docs/superpowers/specs/2026-06-22-e06-operations-workflows-design.md`.
- Design commit: `4341a6e docs: add E06 workflow design`.
- Baseline verification in this worktree:
  - `UV_CACHE_DIR=/tmp/dawn-uv-cache UV_PYTHON_INSTALL_DIR=/tmp/dawn-uv-python uv sync --python 3.11 --project backend --extra dev` -> created `backend/.venv` with CPython 3.11.15;
  - `npm ci --prefix frontend` -> installed frontend dependencies, with Node `25.9.0` warning because `package.json` requires `>=24 <25`;
  - `make test` -> backend `162 passed`, frontend `28 passed`.
- Current app assembly: `backend/src/cloud_ui/api.py`.
- Current CLI/worker: `backend/src/cloud_ui/cli.py` and `backend/src/cloud_ui/worker.py`; worker is only a sleep loop.
- Current security/session/capability layer: `backend/src/cloud_ui/security/`.
- Current inventory repository has host and instance detail lookup in `backend/src/cloud_ui/inventory/repository.py`.
- Current group repository has owner/scope checks and explicit members in `backend/src/cloud_ui/groups/`.
- Current frontend is in `frontend/src/App.tsx`, API helpers in `frontend/src/api.ts`, group types in `frontend/src/groups.ts`.

## Scope

- Add operation schema and Alembic migration with downgrade.
- Add operation state machine and tests for allowed/rejected transitions.
- Add repository methods for operations, targets, timeline events, attempts, outbox and idempotency.
- Add server-side workflow catalog with initial `maintenance-host-precheck` definition.
- Add bounded JSON Schema subset validator for P0 catalog input schemas without adding a permanent
  dependency.
- Add strict P0 Mistral mock adapter that supports start/get/cancel/list-by-correlation, lost response
  and duplicate lookup behavior.
- Add worker dispatch/reconciliation service that never blindly retries Mistral POST after lost
  response.
- Add `GET /api/v1/workflow-definitions`, `POST /api/v1/workflow-definitions/{key}/validate-input`,
  `POST /api/v1/operations`, `GET /api/v1/operations`, `GET /api/v1/operations/{id}` and
  `POST /api/v1/operations/{id}/cancel`.
- Add first-class P0 Watcher and Masakari status modules with disabled mutation paths and risk markers.
- Add frontend operation catalog/form/detail/timeline and route visibility by capabilities.
- Add optional P2 all-in-one Mistral smoke path that is skipped unless explicit test configuration is
  present.
- Update documentation, generated registers, ДКБ traceability and this plan after each milestone.

## Non-goals

- No browser-supplied Mistral workflow name, YAML, task graph, Python, Jinja, shell command or endpoint.
- No Nova evacuate/live migration.
- No automatic Watcher apply.
- No portal-side recovery trigger from Consul Events or Prometheus alerts.
- No production admin credential.
- No long orchestration in the portal worker.
- No blind retry of irreversible external POST.
- No new permanent dependency for generic JSON Schema validation unless an ADR is added first.
- No claim that P2 all-in-one Mistral smoke proves production action safety.
- No claim that ДКБ-69 interpreter/shell conflict is closed.

## Требования и ограничения

- Browser talks only to frontend and portal BFF/API.
- Backend re-checks authorization for every operation submit, detail and cancel action.
- Workflow definitions are loaded server-side; client cannot choose external workflow name.
- Mutating operation endpoints require session, trusted Origin, CSRF and `Idempotency-Key`.
- `Idempotency-Key` binding includes actor, workflow, version, scope and normalized request hash.
- Target facts come from trusted read model or group repository, not from browser assertions.
- Host operations require the explicit `workflow.execute.maintenance-host` capability and admin/system-like
  P0 treatment until production IAM/OpenStack policy integration exists.
- Dynamic group targets must be expanded into a concrete target snapshot before operation acceptance.
- `unknown` is a recoverable state and must not be converted to `failed` without reconciliation.
- Audit metadata cannot store raw idempotency key or full unredacted workflow input.
- All list endpoints must stay server-side paginated and stable sorted.
- The default test path uses P0 mock and no production action.

## Связь с ДКБ

- ДКБ-01-07/12/13: E06 adds operation capability checks, service identity separation in adapter
  boundaries and negative authorization tests. Full IAM/PAM/SoD evidence remains external.
- ДКБ-46-52: E06 records operation accepted/dispatched/completed/failed/cancelled/unknown audit
  metadata with safe error codes and redaction. Full SIEM delivery and heartbeat remain E07/P3 unless
  separately implemented.
- ДКБ-60: E06 stores immutable target snapshots for operation execution, including group expansion.
  This proves portal snapshot persistence, not full resource governance.
- ДКБ-77: E06 documents Mistral/Watcher/Masakari API usage, enabled/disabled state and blocking
  mechanism in generated registers.

## Milestones

1. Operation schema/state machine: migration, table metadata, models and transition tests.
2. Operation repository/idempotency/outbox: durable accept path and replay/conflict tests.
3. Workflow catalog/input validation: `maintenance-host-precheck` definition, checksum and negative
   arbitrary workflow/input tests.
4. Submit/detail/cancel API: session/CSRF/capability/target/snapshot/audit and 202 durable response.
5. Mistral mock adapter and worker: dispatch, lost response lookup, duplicate prevention, unknown and
   reconciliation tests.
6. Group target snapshot support: group member expansion and stale group snapshot tests.
7. Watcher/Masakari read/status modules: first-class visible modules, disabled mutating operations and
   risk/conflict markers.
8. Frontend operations UX: catalog, form, submit, operation page, timeline, cancel state and polling.
9. Optional P2 Mistral smoke evidence: skipped by default, enabled only with explicit all-in-one test
   configuration.
10. Documentation, generated registers, ДКБ evidence and final verification gates.

## Progress

- [x] 2026-06-22: E05 accepted and pushed to origin as `e05-resource-groups`. Evidence:
  `git push -u origin e05-resource-groups` succeeded.
- [x] 2026-06-22: E06 worktree created from E05 closeout. Evidence:
  `git worktree add .worktrees/e06-workflows -b e06-workflows e05-resource-groups`.
- [x] 2026-06-22: E06 baseline verified. Evidence: `make test` -> backend `162 passed`, frontend
  `28 passed`.
- [x] 2026-06-22: E06 design approved and committed. Evidence: commit
  `4341a6e docs: add E06 workflow design`.
- [ ] 2026-06-22: Operation schema/state machine.
- [ ] 2026-06-22: Operation repository/idempotency/outbox.
- [ ] 2026-06-22: Workflow catalog/input validation.
- [ ] 2026-06-22: Submit/detail/cancel API.
- [ ] 2026-06-22: Mistral mock adapter and worker.
- [ ] 2026-06-22: Group target snapshot.
- [ ] 2026-06-22: Watcher/Masakari modules.
- [ ] 2026-06-22: Frontend operations UX.
- [ ] 2026-06-22: Documentation/registers/final verification.

## Неожиданные открытия

- `make bootstrap` expects `python3.11`, which is not installed as a direct executable in the current
  shell. Workaround: create `backend/.venv` with `uv sync --python 3.11` and the sandbox-safe cache
  directories `/tmp/dawn-uv-cache` and `/tmp/dawn-uv-python`.
- The current Node runtime is `25.9.0`, while the frontend package declares `>=24 <25`. `npm ci`
  warns but tests pass. This is environment drift, not an E06 code change.
- `backend/src/cloud_ui/worker.py` is currently only a sleep loop, so E06 must introduce a testable
  bounded worker service before claiming dispatch/reconciliation evidence.
- The old `/api/v1/operations/simulated-openstack-action` route is a security-foundation stub and must
  not be treated as the E06 operation API contract.

## Журнал решений

- 2026-06-22: Use `maintenance-host-precheck` as the first allowlisted workflow. Alternative: use an
  already published all-in-one Mistral workflow. Reason: the chosen flow is dry-run/precheck and avoids
  OpenStack state changes while proving the operation pipeline. Consequence: production action safety is
  not claimed.
- 2026-06-22: Make P0 strict mock mandatory and P2 all-in-one Mistral smoke optional. Alternative:
  require live Mistral for E06 tests. Reason: local verification must remain reproducible without
  production credentials or external endpoint availability. Consequence: final evidence must clearly
  distinguish P0 mock from P2 integration.
- 2026-06-22: Implement a bounded JSON Schema subset validator instead of adding `jsonschema`.
  Alternative: add a new dependency. Reason: `AGENTS.md` requires ADR for new permanent dependencies,
  and the first catalog schema is small. Consequence: supported schema keywords are documented and
  negative tests prove unsupported shapes fail closed.

## Детальный план реализации

### 1. Operation schema and state machine

Create:

- `backend/src/cloud_ui/operations/__init__.py`
- `backend/src/cloud_ui/operations/models.py`
- `backend/src/cloud_ui/operations/state_machine.py`
- `backend/src/cloud_ui/operations/schema.py`
- `backend/src/cloud_ui/migrations/versions/0005_operations.py`
- `backend/tests/operations/test_operation_migration.py`
- `backend/tests/operations/test_state_machine.py`

Implementation details:

- Define `OperationStatus` literal values from `docs/07_WORKFLOWS.md`.
- Add `assert_transition_allowed(current, desired)` and `is_terminal(status)`.
- Allow initial `accepted -> queued -> dispatching -> running`.
- Allow `running -> succeeded|partially_succeeded|failed|unknown|cancel_requested`.
- Allow `dispatching -> running|unknown|failed`.
- Allow `unknown -> running|succeeded|partially_succeeded|failed|cancelled`.
- Reject transitions out of `succeeded`, `partially_succeeded`, `failed` and `cancelled`.
- Add SQLAlchemy metadata for workflow definitions, operations, operation targets, events, attempts,
  outbox and idempotency keys.

Verification:

- `cd backend && .venv/bin/python -m pytest tests/operations/test_operation_migration.py tests/operations/test_state_machine.py -q`
- `cd backend && .venv/bin/python -m ruff check src/cloud_ui/operations tests/operations`
- `cd backend && .venv/bin/python -m mypy src/cloud_ui/operations`

Commit:

- `git add backend/src/cloud_ui/operations backend/src/cloud_ui/migrations/versions/0005_operations.py backend/tests/operations`
- `git commit -m "feat: add operation state schema"`

### 2. Operation repository, idempotency and outbox

Create:

- `backend/src/cloud_ui/operations/repository.py`
- `backend/tests/operations/test_operation_repository.py`

Implementation details:

- Add `OperationRepository(engine)`.
- Add `accept_operation(...)` that inserts operation, targets, first timeline event,
  `operation_idempotency_keys` and `operation_outbox` in one transaction.
- If the same idempotency key hash exists with same request hash, return the existing operation.
- If the same key hash exists with a different request hash, raise `OperationIdempotencyConflict`.
- Add page methods for operations/events using stable sort.
- Add `claim_next_outbox_item`, `mark_outbox_dispatched`, `record_attempt`,
  `attach_external_execution`, `transition_operation` and `append_event`.
- Store only HMAC idempotency key hash and normalized request hash.

Verification:

- `cd backend && .venv/bin/python -m pytest tests/operations/test_operation_repository.py -q`
- `cd backend && .venv/bin/python -m ruff check src/cloud_ui/operations tests/operations`
- `cd backend && .venv/bin/python -m mypy src/cloud_ui/operations`

Commit:

- `git add backend/src/cloud_ui/operations/repository.py backend/tests/operations/test_operation_repository.py`
- `git commit -m "feat: add durable operation repository"`

### 3. Workflow catalog and input validation

Create:

- `backend/src/cloud_ui/operations/catalog.py`
- `backend/src/cloud_ui/operations/input_validation.py`
- `backend/tests/operations/test_workflow_catalog.py`
- `backend/tests/operations/test_input_validation.py`

Implementation details:

- Add immutable `WorkflowDefinition`.
- Add built-in `maintenance-host-precheck` definition with:
  - `workflow_key="maintenance-host-precheck"`;
  - `version="1.0.0"`;
  - `target_type="host"`;
  - `mistral_workflow_name="portal.maintenance_host_precheck.v1"`;
  - `required_capability="workflow.execute.maintenance-host"`;
  - `risk_level="low"`;
  - `approval_mode="none"`;
  - `cancel_policy="best_effort"`;
  - `enabled_environments=["local", "test"]` initially;
  - server-enforced dry-run input.
- Compute checksum from canonical definition payload.
- Validate input schemas with fail-closed support for object, string, boolean, integer, enum,
  required, properties, additionalProperties, minLength, maxLength and minimum/maximum.
- Reject unsupported schema keywords instead of ignoring them.

Verification:

- `cd backend && .venv/bin/python -m pytest tests/operations/test_workflow_catalog.py tests/operations/test_input_validation.py -q`
- `cd backend && .venv/bin/python -m ruff check src/cloud_ui/operations tests/operations`
- `cd backend && .venv/bin/python -m mypy src/cloud_ui/operations`

Commit:

- `git add backend/src/cloud_ui/operations/catalog.py backend/src/cloud_ui/operations/input_validation.py backend/tests/operations`
- `git commit -m "feat: add workflow catalog"`

### 4. Operation API

Create:

- `backend/src/cloud_ui/operations/routes.py`
- `backend/tests/operations/test_operation_api.py`

Modify:

- `backend/src/cloud_ui/api.py`
- `backend/src/cloud_ui/security/mock_identity.py`
- `backend/tests/security/test_mock_identity.py`
- `backend/tests/security/test_security_api.py`

Implementation details:

- Add `OperationServices` with operation repository, inventory repository, group repository and catalog.
- Include operations router under `/api/v1`.
- Add route response models for definitions, submit response, operation detail, event page and cancel.
- Add `workflow.execute.maintenance-host` to the P0 operator only if host precheck should be usable by
  operator; otherwise restrict to `portal_admin`. The first implementation uses `portal_admin` for host
  target submit and keeps `cloud_operator` forbidden unless requirements change.
- Validate session, Origin, CSRF, capability, idempotency key, definition, input and target before
  accepting.
- For host targets, load hypervisor from E04 read model and snapshot host fields.
- Return `202` only after operation and outbox row are committed.
- Record `operation.accepted`, `authorization.denied`, `operation.cancel.requested` audit metadata
  without raw idempotency key or full input body.

Verification:

- `cd backend && .venv/bin/python -m pytest tests/operations/test_operation_api.py tests/security/test_mock_identity.py tests/security/test_security_api.py -q`
- `cd backend && .venv/bin/python -m ruff check src tests/operations tests/security/test_mock_identity.py tests/security/test_security_api.py`
- `cd backend && .venv/bin/python -m mypy src`

Commit:

- `git add backend/src/cloud_ui/api.py backend/src/cloud_ui/operations/routes.py backend/src/cloud_ui/security/mock_identity.py backend/tests/operations/test_operation_api.py backend/tests/security/test_mock_identity.py backend/tests/security/test_security_api.py`
- `git commit -m "feat: add operation submit API"`

### 5. Mistral mock adapter and worker safety

Create:

- `backend/src/cloud_ui/operations/mistral.py`
- `backend/src/cloud_ui/operations/worker.py`
- `backend/tests/operations/test_mistral_mock.py`
- `backend/tests/operations/test_operation_worker.py`

Modify:

- `backend/src/cloud_ui/worker.py`
- `backend/src/cloud_ui/cli.py`
- `backend/tests/test_cli.py`

Implementation details:

- Define adapter protocol and typed exceptions.
- Implement `InMemoryMistralAdapter` with configurable lost response behavior.
- Implement `OperationWorker.run_once()` that:
  - claims one outbox item;
  - records attempt;
  - transitions `queued -> dispatching`;
  - checks `list_executions_by_correlation` before calling start;
  - attaches existing external execution if lookup finds one;
  - starts only when lookup is empty;
  - handles lost response by setting `unknown` and leaving correlation evidence;
  - reconciles `unknown` via lookup before any new start.
- Replace the generic sleep-only worker with a CLI path that can run one bounded iteration in tests and
  keep a loop for runtime.

Verification:

- `cd backend && .venv/bin/python -m pytest tests/operations/test_mistral_mock.py tests/operations/test_operation_worker.py tests/test_cli.py -q`
- `cd backend && .venv/bin/python -m ruff check src tests/operations tests/test_cli.py`
- `cd backend && .venv/bin/python -m mypy src`

Commit:

- `git add backend/src/cloud_ui/operations/mistral.py backend/src/cloud_ui/operations/worker.py backend/src/cloud_ui/worker.py backend/src/cloud_ui/cli.py backend/tests/operations/test_mistral_mock.py backend/tests/operations/test_operation_worker.py backend/tests/test_cli.py`
- `git commit -m "feat: dispatch operations through mistral mock"`

### 6. Group target snapshot

Modify:

- `backend/src/cloud_ui/operations/routes.py`
- `backend/src/cloud_ui/operations/repository.py`
- `backend/tests/operations/test_operation_api.py`
- `backend/tests/operations/test_operation_repository.py`

Implementation details:

- Add support for submit target references of type `group`.
- Load group through `GroupRepository`, verify owner/scope access and `group.read`.
- Expand explicit members into concrete `operation_targets` before accept.
- Persist group id, group revision and member list in `target_snapshot_json`.
- Reject empty group and stale group revision if request supplies an expected revision.
- Prove later group member edits do not change the operation target snapshot.

Verification:

- `cd backend && .venv/bin/python -m pytest tests/operations/test_operation_api.py tests/operations/test_operation_repository.py tests/groups/test_group_api.py -q`
- `cd backend && .venv/bin/python -m ruff check src tests/operations`
- `cd backend && .venv/bin/python -m mypy src`

Commit:

- `git add backend/src/cloud_ui/operations backend/tests/operations`
- `git commit -m "feat: snapshot group operation targets"`

### 7. Watcher and Masakari first-class status modules

Create:

- `backend/src/cloud_ui/watcher/__init__.py`
- `backend/src/cloud_ui/watcher/models.py`
- `backend/src/cloud_ui/watcher/routes.py`
- `backend/src/cloud_ui/masakari/__init__.py`
- `backend/src/cloud_ui/masakari/models.py`
- `backend/src/cloud_ui/masakari/routes.py`
- `backend/tests/operations/test_watcher_masakari_api.py`

Modify:

- `backend/src/cloud_ui/api.py`

Implementation details:

- Add read-only mock/status endpoints from `docs/05_API_AND_INTEGRATIONS.md`.
- Return explicit status fields that show automatic Watcher apply disabled.
- Return Masakari recovery approval/conflict markers and Consul matrix coverage status.
- Return `processmonitor` as unsupported/diagnostic in Kolla/container context.
- Keep mutating recovery/apply paths available only through `/api/v1/operations`; no direct execute
  endpoints are added.

Verification:

- `cd backend && .venv/bin/python -m pytest tests/operations/test_watcher_masakari_api.py -q`
- `cd backend && .venv/bin/python -m ruff check src/cloud_ui/watcher src/cloud_ui/masakari tests/operations/test_watcher_masakari_api.py`
- `cd backend && .venv/bin/python -m mypy src`

Commit:

- `git add backend/src/cloud_ui/watcher backend/src/cloud_ui/masakari backend/src/cloud_ui/api.py backend/tests/operations/test_watcher_masakari_api.py`
- `git commit -m "feat: add watcher masakari status APIs"`

### 8. Frontend operations UX

Create:

- `frontend/src/operations.ts`

Modify:

- `frontend/src/api.ts`
- `frontend/src/App.tsx`
- `frontend/src/App.test.tsx`
- `frontend/src/styles.css`

Implementation details:

- Add typed API helpers for workflow definitions, input validation, operation submit/detail/events and
  cancel.
- Add `view=operations` and operation detail routing state.
- Add catalog list and `maintenance-host-precheck` form.
- Use existing host inventory API for bounded target selection/search.
- Submit with CSRF value only when available from login; restored sessions without CSRF show a safe
  disabled submit state until a future CSRF refresh endpoint exists.
- Add operation detail/timeline rendering for `accepted`, `queued`, `dispatching`, `running`,
  `unknown`, `partially_succeeded`, `succeeded`, `failed` and `cancelled`.
- Add adaptive polling with bounded delay and no full inventory load.

Verification:

- `cd frontend && npm test -- --run src/App.test.tsx`
- `cd frontend && npm run typecheck`
- `cd frontend && npm run lint`

Commit:

- `git add frontend/src/operations.ts frontend/src/api.ts frontend/src/App.tsx frontend/src/App.test.tsx frontend/src/styles.css`
- `git commit -m "feat: add operation frontend"`

### 9. Optional P2 all-in-one Mistral smoke

Create:

- `backend/tests/integrations/test_mistral_smoke.py`
- `docs/generated/e06-mistral-smoke.md`

Implementation details:

- Skip unless explicit env/config values are present for the all-in-one test endpoint.
- Use only the approved `maintenance-host-precheck` workflow.
- Record endpoint source, workflow key, operation/correlation ID and external execution ID.
- Assert the smoke does not submit production action, does not use production admin credential and does
  not mutate OpenStack state.

Verification:

- Default: `cd backend && .venv/bin/python -m pytest tests/integrations/test_mistral_smoke.py -q`
  returns skipped.
- With explicit test config: run the same command and capture the sanitized result in
  `docs/generated/e06-mistral-smoke.md`.

Commit:

- `git add backend/tests/integrations/test_mistral_smoke.py docs/generated/e06-mistral-smoke.md`
- `git commit -m "test: add optional mistral smoke"`

### 10. Documentation and final gates

Modify:

- `docs/05_API_AND_INTEGRATIONS.md`
- `docs/06_AUTH_RBAC_SESSIONS.md`
- `docs/07_WORKFLOWS.md`
- `docs/08_AUDIT_OBSERVABILITY.md`
- `docs/10_SECURITY_DKB.md`
- `docs/11_DKB_TRACEABILITY.md`
- `docs/generated/api-register.md`
- `docs/generated/integration-register.md`
- `docs/generated/risk-register.md`
- `docs/execplans/E06-workflows.md`

Verification:

- `make lint`
- `make typecheck`
- `make test`
- `make security`
- `git diff --check HEAD`

Commit:

- `git add docs backend frontend`
- `git commit -m "docs: document E06 operations workflows"`

## Миграции и совместимость

E06 migration is expand-only for the existing app: it creates new operation tables and indexes without
modifying E02-E05 tables. Existing API, inventory and groups continue to work before the E06 routes are
enabled. Rolling update order:

1. Deploy backend image containing migration and code.
2. Run explicit `cloud-ui db-upgrade`.
3. Start API/worker/events commands.

Rollback order:

1. Stop E06 worker to prevent new dispatch.
2. Disable or roll back frontend routes to remove operation submit UI.
3. Deploy previous API image.
4. Run Alembic downgrade for `0005_operations` only after no E06 worker/API instance can write
   operation rows.

No OpenStack cleanup is required for the default P0 mock path and first dry-run workflow. If optional
P2 Mistral smoke runs, any cleanup is limited to the documented test project/workflow execution.

## Проверка

Targeted verification after each milestone is listed in the detailed plan. Final verification is:

- `make lint` from repo root -> backend Ruff, frontend ESLint and secret scan pass.
- `make typecheck` from repo root -> backend mypy and frontend TypeScript pass.
- `make test` from repo root -> backend and frontend tests pass.
- `make security` from repo root -> secret scan passes.
- `git diff --check HEAD` -> no whitespace or conflict marker issues.

P2 Mistral smoke is not part of `make test` by default. It is run only when explicit all-in-one test
configuration exists and its output is sanitized.

## Доказательства

- Migration and repository tests for durable operations and downgrade.
- State machine tests for accepted and rejected transitions.
- API contract tests for allowlist, idempotency, CSRF, capability denial and target validation.
- Worker tests proving lost Mistral response does not create duplicate execution.
- Audit redaction tests proving raw idempotency key and full input body are absent from audit metadata.
- Frontend tests for catalog/form/detail/timeline states.
- Generated API/integration/risk register updates for E06.
- DKB traceability update for ДКБ-01-07/12/13, ДКБ-46-52, ДКБ-60 and ДКБ-77.
- Optional sanitized P2 all-in-one Mistral smoke evidence.

## Откат и восстановление

To safely roll back E06:

1. Stop `cloud-ui worker` and any operation polling/submit frontend route.
2. Deploy the previous backend/frontend images from E05.
3. Run Alembic downgrade from `0005_operations` to `0004_resource_groups`.
4. Verify E05 health with `make smoke` or API health checks.
5. If a P2 Mistral smoke was run, retain its sanitized evidence and do not delete external test
   execution records unless the test workflow owner explicitly requires cleanup.

Partial failed implementation recovery:

- If tests fail before migration commit, drop the in-memory test DB and rerun the targeted pytest.
- If an outbox worker test leaves unknown operations in a local DB, rerun from a clean SQLite fixture.
- If frontend state gets out of sync, reset URL query params; no operation data is stored in
  localStorage/sessionStorage.

## Итог и остаточные риски

This section is updated after implementation. Known initial risks:

- P2 all-in-one Mistral endpoint details and credentials are external to the repo and must not be
  committed.
- P0 mock proves portal safety semantics but not production Mistral HA, TLS, mTLS, SIEM or OpenStack
  policy enforcement.
- Host operations remain admin/system-like until production IAM and OpenStack policy evidence exists.
- Generic JSON Schema support is intentionally limited to the first allowlisted workflow subset.
- Full audit delivery, SIEM heartbeat and external audit source correlation remain E07/P3.
