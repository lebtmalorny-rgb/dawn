# ExecPlan: E07 portal audit delivery and search

## Цель и наблюдаемый результат

После E07 security auditor сможет открыть защищенный журнал действий портала, отфильтровать события
по времени/action/outcome/actor/target/correlation ID, увидеть mandatory fields, delivery state,
safe error code and redacted metadata. Пользователь с `audit.read` сможет читать scoped audit events,
но не экспортировать их; `audit.export` будет отдельной capability. Просмотр и экспорт аудита сами
будут создавать audit events.

Оператор сможет запустить bounded `cloud-ui events --once` или `make test-integration` и увидеть, что
audit outbox доставляет sanitized events в test sink, сохраняет backlog при outage, выполняет
bounded retry, переводит permanent failure в dead-letter, отправляет heartbeat and recovery event.
Для all-in-one lab будет создан runbook/evidence path: Kolla Fluentd already running, OpenSearch
currently disabled, deployment remains manual and not part of portal runtime.

До E07 в коде есть E02 `AuditEvent` and `InMemoryAuditSink`, а E05/E06 routes пишут audit metadata
в memory sink. Durable audit delivery, redaction canaries across all sinks, audit search/export API,
heartbeat and full audit source map do not exist.

## Контекст и текущее состояние

- Repository root: `/Users/dmitry/Desktop/dawn`.
- Active worktree: `/Users/dmitry/Desktop/dawn/.worktrees/e07-audit`.
- Branch: `e07-audit`.
- Base commit: `25fec35 docs: close E06 workflow evidence`.
- Current HEAD: `f7f9177 docs: add E07 audit design`.
- Design spec: `docs/superpowers/specs/2026-06-22-e07-audit-design.md`.
- Current stage file: `tasks/E07_AUDIT.md`.
- Baseline verification in this worktree:
  - `UV_CACHE_DIR=/tmp/dawn-uv-cache UV_PYTHON_INSTALL_DIR=/tmp/dawn-uv-python uv sync --python 3.11 --project backend --extra dev` -> created backend venv with CPython 3.11.15.
  - `npm ci --prefix frontend` -> installed frontend dependencies; warning remains because local Node is `25.9.0` while package requires `>=24 <25`.
  - `make test` -> backend `243 passed, 1 skipped`; frontend `31 passed`.
- Current audit code:
  - `backend/src/cloud_ui/security/audit.py` defines `AuditEvent`, `AuditSink`, `InMemoryAuditSink`.
  - `backend/src/cloud_ui/migrations/versions/0002_security_foundation.py` creates the narrow
    E02 `audit_events` table.
  - `backend/src/cloud_ui/security/dependencies.py` always wires `InMemoryAuditSink`.
  - Existing routes in `security`, `inventory`, `groups`, `operations`, `watcher`, `masakari` call
    `services.audit_sink.record(AuditEvent(...))`.
- Current background processes:
  - `cloud-ui worker` can run E06 operation worker once.
  - `cloud-ui events` is still a sleep loop through `cloud_ui.worker.run_loop("events")`.
- Lab observation:
  - On all-in-one `192.168.10.14`, Kolla `fluentd` container is running.
  - On ansible host `/etc/kolla/globals.yml`: `enable_central_logging: "no"`,
    `enable_opensearch: "no"`, `enable_opensearch_dashboards: "no"`.
  - OpenSearch deployment is a manual lab/runbook activity after E07 code can generate evidence.

## Scope

- Add a new `cloud_ui.audit` domain with normalized event models, schema/taxonomy, central redaction,
  durable repository, delivery worker, sink adapters and API routes.
- Expand audit persistence with Alembic migration `0006_audit_delivery.py` without destroying existing
  E02/E06 data.
- Preserve compatibility for existing route-level `security.audit_sink.record(AuditEvent(...))` calls.
- Make `cloud-ui events --once` process one bounded audit delivery iteration for tests and keep loop
  semantics for runtime.
- Add local test sink and Fluentd/OpenSearch-compatible JSON envelope contract.
- Add audit search/detail/export API and frontend search view.
- Add generated evidence artifacts: audit JSON Schema, action dictionary/mapping, sample events,
  audit source map and lab runbook.
- Update DKB traceability for ДКБ-46-53 without claiming full ДКБ-48/50 compliance.

## Non-goals

- No production SIEM endpoint, token, client certificate or credential in the repository.
- No Kolla/OpenSearch automation in portal compose/runtime images.
- No claim that MariaDB portal audit is immutable SIEM.
- No claim that full ДКБ-50 is closed by portal audit.
- No direct browser access to MariaDB, RabbitMQ, Fluentd, OpenSearch, log files or SIEM index.
- No raw stack traces, raw request bodies, raw workflow inputs, tokens, cookies, private keys or
  production URLs in audit events, delivery payloads or browser responses.
- No mass refactor of every existing route to transactional service-layer audit in the first slice;
  compatibility durable sink closes the observable E07 path, and targeted transactional calls are added
  where E07 introduces new mutations.

## Требования и ограничения

- Browser talks only to frontend and portal BFF/API.
- Backend re-checks `audit.read` and `audit.export` for every audit API action.
- Frontend capabilities are presentation only; direct API access must return `401/403`.
- Audit list/search uses server-side filtering, cursor pagination and stable sort. It must not load the
  full audit table in the browser.
- Mutating export request requires session, trusted Origin and CSRF.
- Audit read/export access itself creates sanitized audit events.
- Audit delivery is at-least-once with sink-side replay idempotency based on `event_id`, sink id and
  event hash.
- Sink outage must create durable backlog and visible failure/heartbeat state, never silent drop.
- Redaction is applied before storage and before delivery.
- Lab Fluentd/OpenSearch path remains test evidence only. Production TLS/mTLS, retention and
  authorization are external owner evidence.

## Связь с ДКБ

- ДКБ-46: E07 implements portal event delivery to test sink and documents Fluentd/OpenSearch lab path.
  Evidence: delivery worker tests, sink contract tests, lab runbook. Full OpenStack/Kolla logging
  remains external.
- ДКБ-47: E07 defines protected-channel configuration fields and Fluentd/OpenSearch-compatible envelope.
  Evidence: integration register, sink contract and failure tests. Production mTLS/auth remains E08/E09.
- ДКБ-48: E07 adds heartbeat, queue age and delivery failure/recovery events. It does not prevent root
  from disabling host/container logging. External evidence required: FIM/auditd/IaC and absence-of-flow
  SIEM alerting.
- ДКБ-49/49.01-49.08: E07 normalizes mandatory portal fields and publishes JSON Schema/mapping.
  Evidence: schema/taxonomy tests and generated samples.
- ДКБ-50/50.x: E07 creates `docs/generated/audit-source-map.md` showing portal-covered events and
  external sources: Keystone CADF, Nova/Neutron/Glance/Cinder notifications, Mistral/Watcher/Masakari,
  HAProxy/API logs, container runtime, systemd/sudo/PAM/auditd, libvirt/QEMU/OVS/OVN, storage/backup,
  IdP/IAM and monitoring. Full compliance remains external/P3.
- ДКБ-51: E07 central redaction and canary tests cover audit projection, delivery payload and API
  response. Evidence: redaction tests with password/token/cookie/private key/workflow secret canaries.
- ДКБ-52: E07 records safe audit error and correlation ID; protected service log can hold sanitized
  internal detail. Evidence: internal-error correlation tests.
- ДКБ-53: E07 provides application-layer audit read/export with separate capabilities and audited
  access. Direct DB/index/log access remains external control.

## Milestones

1. Audit schema/taxonomy/redaction: event DTO, JSON Schema, action dictionary, ДКБ-49 mapping and
   canary sanitizer tests.
2. Migration/repository/durable sink: expand audit tables, compatibility durable sink and repository
   outbox writes.
3. Delivery worker/sinks/heartbeat: local test sink, Fluentd/OpenSearch-compatible envelope, retry,
   dead-letter, replay idempotency and heartbeat.
4. Audit API/backend authorization: search/detail/export routes, filters, signed cursor, field scope,
   audited read/export access.
5. Frontend audit search UX: security auditor view, filters, pagination, detail drawer and export
   capability separation.
6. Documentation/evidence/lab runbook: generated schemas/samples/source map/register updates and final
   verification.

## Progress

- [x] 2026-06-22: E06 accepted on `main`. Evidence: current base commit
  `25fec35 docs: close E06 workflow evidence`.
- [x] 2026-06-22: E07 worktree created. Evidence: `.worktrees/e07-audit`, branch `e07-audit`.
- [x] 2026-06-22: E07 baseline verified. Evidence: `make test` -> backend `243 passed, 1 skipped`,
  frontend `31 passed`.
- [x] 2026-06-22: E07 design spec approved and committed. Evidence: commit
  `f7f9177 docs: add E07 audit design`.
- [x] 2026-06-22: E07 ExecPlan created. Evidence: this document.
- [x] 2026-06-22: Audit models/taxonomy/redaction implemented and tested. Evidence:
  `cd backend && .venv/bin/python -m pytest tests/audit/test_models.py
  tests/audit/test_taxonomy.py tests/audit/test_audit_redaction.py tests/security/test_audit.py
  tests/test_redaction.py -q` -> `14 passed`;
  `cd backend && .venv/bin/python -m ruff check src/cloud_ui/audit src/cloud_ui/security/audit.py
  src/cloud_ui/logging.py tests/audit tests/security/test_audit.py tests/test_redaction.py` ->
  all checks passed;
  `cd backend && .venv/bin/python -m mypy src/cloud_ui/audit src/cloud_ui/security/audit.py
  src/cloud_ui/logging.py` -> success;
  `git diff --check` -> success.
- [ ] Migration/repository/durable sink implemented and tested.
- [ ] Delivery worker/sinks/heartbeat implemented and tested.
- [ ] Audit API/backend authorization implemented and tested.
- [ ] Frontend audit search UX implemented and tested.
- [ ] Documentation/evidence/lab runbook and final verification completed.

## Неожиданные открытия

- Direct SSH to all-in-one `192.168.10.14` from the local workstation requested password and failed,
  but access through ansible host `192.168.10.15` succeeded.
- Kolla `fluentd` container is already running on all-in-one even though `enable_central_logging`,
  `enable_opensearch` and `enable_opensearch_dashboards` are set to `"no"`. This means E07 can document
  Fluentd/OpenSearch lab integration as a runbook, but should not claim current OpenSearch evidence.
- `uv sync` in a fresh worktree generated untracked `backend/uv.lock` and `backend/src/cloud_ui.egg-info/`;
  they were removed before committing design/plan docs.
- Local Node is `25.9.0`, while frontend package requires `>=24 <25`. `npm ci` warns but baseline tests
  pass. This is environment drift, not an E07 code change.

## Журнал решений

- 2026-06-22: Use option 2 from design discussion: local/contract test adapter plus optional
  Fluentd/OpenSearch lab path. Alternative: pure local sink only. Reason: Fluentd/OpenSearch is closer
  to the target logging path and the all-in-one already has Fluentd. Consequence: OpenSearch deployment
  is documented as manual lab evidence, not a portal runtime dependency.
- 2026-06-22: Keep audit delivery in `cloud-ui events`. Alternative: add a new container/process name.
  Reason: project invariant keeps one backend image with API/worker/events/migration commands; events
  is currently available and idle. Consequence: E07 changes the `events` command from sleep loop into
  bounded audit delivery loop.
- 2026-06-22: Preserve existing `security.audit_sink.record(AuditEvent)` call shape initially.
  Alternative: refactor every route to pass audit events into domain repositories atomically. Reason:
  compatibility lowers blast radius and lets E07 add durable storage/delivery without rewriting E02-E06
  routes. Consequence: new E07 export mutation gets atomic audit/outbox immediately; older route events
  are durable but remain route-level side effects until later targeted refactors.
- 2026-06-22: `security_auditor` receives `audit.read` only; `audit.export` is reserved for
  `portal_admin` in P0 tests. Alternative: give auditor export by default. Reason: E07 acceptance
  requires read/export separation and export denial. Consequence: UI must hide export for auditor and
  backend must return `403` for direct export attempts.

## Детальный план реализации

### 1. Audit schema, taxonomy and redaction

Create:

- `backend/src/cloud_ui/audit/__init__.py`
- `backend/src/cloud_ui/audit/models.py`
- `backend/src/cloud_ui/audit/taxonomy.py`
- `backend/src/cloud_ui/audit/redaction.py`
- `backend/src/cloud_ui/audit/json_schema.py`
- `backend/tests/audit/test_models.py`
- `backend/tests/audit/test_taxonomy.py`
- `backend/tests/audit/test_redaction.py`

Modify:

- `backend/src/cloud_ui/security/audit.py`
- `backend/src/cloud_ui/logging.py`
- `backend/tests/security/test_audit.py`
- `backend/tests/test_redaction.py`

Implementation details:

- Move the normalized `AuditEvent` DTO to `cloud_ui.audit.models` with the E07 mandatory fields:
  actor display/auth/session, action/event/outcome, target, cloud/region/project/scope, source IP,
  proxy chain, request ID, correlation ID, operation ID, external execution ID, service/component,
  safe error code, redacted metadata and delivery state.
- Keep `cloud_ui.security.audit.AuditEvent`, `AuditOutcome`, `AuditSink`, `InMemoryAuditSink` as
  compatibility re-exports/wrappers so existing imports continue to pass.
- Add `normalize_audit_event(...)` that converts missing E02-era optional fields to explicit safe
  defaults such as `source_ip=None`, `scope_type=None`, `delivery_state="not_queued"` for in-memory tests.
- Add action taxonomy entries for existing E02-E06 event codes and E07 audit/delivery events.
- Add JSON Schema generation for sanitized audit event envelope and write a deterministic schema artifact
  later in the docs milestone.
- Replace shallow `redact_mapping` behavior with recursive sanitizer in `audit.redaction`, while keeping
  `cloud_ui.logging.redact_mapping` as a small wrapper for existing call sites.
- Canary strings:
  - `password=DKB_CANARY_PASSWORD`
  - `token=DKB_CANARY_TOKEN`
  - `cookie=DKB_CANARY_COOKIE`
  - `authorization=Bearer DKB_CANARY_AUTH`
  - `private_key=-----BEGIN PRIVATE KEY-----DKB_CANARY_KEY`
  - `workflow_secret=DKB_CANARY_WORKFLOW_SECRET`
  - `database_url=mysql://user:DKB_CANARY_DB@db/cloud_ui`
  - `rabbitmq_url=amqp://user:DKB_CANARY_RABBIT@rabbitmq/%2Fcloud-ui`

Verification:

- `cd backend && .venv/bin/python -m pytest tests/audit/test_models.py tests/audit/test_taxonomy.py tests/audit/test_redaction.py tests/security/test_audit.py tests/test_redaction.py -q`
- `cd backend && .venv/bin/python -m ruff check src/cloud_ui/audit src/cloud_ui/security/audit.py src/cloud_ui/logging.py tests/audit tests/security/test_audit.py tests/test_redaction.py`
- `cd backend && .venv/bin/python -m mypy src/cloud_ui/audit src/cloud_ui/security/audit.py src/cloud_ui/logging.py`
- `git diff --check`

Commit:

- `git add backend/src/cloud_ui/audit backend/src/cloud_ui/security/audit.py backend/src/cloud_ui/logging.py backend/tests/audit backend/tests/security/test_audit.py backend/tests/test_redaction.py`
- `git commit -m "feat: add audit event taxonomy and redaction"`

### 2. Migration, repository and durable sink

Create:

- `backend/src/cloud_ui/audit/schema.py`
- `backend/src/cloud_ui/audit/repository.py`
- `backend/src/cloud_ui/audit/sink.py`
- `backend/src/cloud_ui/migrations/versions/0006_audit_delivery.py`
- `backend/tests/audit/test_audit_migration.py`
- `backend/tests/audit/test_repository.py`
- `backend/tests/audit/test_durable_sink.py`

Modify:

- `backend/src/cloud_ui/security/dependencies.py`
- `backend/src/cloud_ui/api.py`
- existing route tests only where assertions need to inspect durable sink compatibility.

Implementation details:

- Add E07 tables:
  - `audit_outbox`
  - `audit_delivery_attempts`
  - `audit_heartbeats`
- Expand `audit_events` using nullable/additive columns for E07 fields:
  - `actor_display`
  - `authentication_method`
  - `session_reference`
  - `cloud_id`
  - `region_id`
  - `project_id`
  - `scope_type`
  - `scope_id`
  - `source_ip`
  - `trusted_proxy_chain_json`
  - `operation_id`
  - `external_execution_id`
  - `component`
  - `safe_error_code`
  - `delivery_state`
  - `event_hash`
  - `created_at`
- Migration remains expand-only and has downgrade that drops E07 tables/indexes/columns without touching
  pre-E07 core event fields.
- `AuditRepository.record_event(event, queue_delivery=True)` writes `audit_events` and `audit_outbox`
  in one transaction. It returns a stored event model with sanitized metadata and stable `event_hash`.
- `AuditRepository.list_events(...)` supports filters and cursor later used by routes.
- `DurableAuditSink` implements current `AuditSink.record(event)` protocol and appends to an optional
  test-visible `events` list for backward-compatible unit tests.
- `build_security_services(settings, audit_sink=None)` accepts injected sink. In production app
  assembly, `create_app` wires `DurableAuditSink` when an engine exists and keeps `InMemoryAuditSink`
  for dependency-free health/unit tests.

Verification:

- `cd backend && .venv/bin/python -m pytest tests/audit/test_audit_migration.py tests/audit/test_repository.py tests/audit/test_durable_sink.py -q`
- `cd backend && .venv/bin/python -m pytest tests/security tests/groups tests/inventory tests/operations -q`
- `cd backend && .venv/bin/python -m ruff check src/cloud_ui/audit src/cloud_ui/migrations/versions/0006_audit_delivery.py src/cloud_ui/security src/cloud_ui/api.py tests/audit`
- `cd backend && .venv/bin/python -m mypy src`
- `git diff --check`

Commit:

- `git add backend/src/cloud_ui/audit backend/src/cloud_ui/migrations/versions/0006_audit_delivery.py backend/src/cloud_ui/security/dependencies.py backend/src/cloud_ui/api.py backend/tests/audit backend/tests/security backend/tests/groups backend/tests/inventory backend/tests/operations`
- `git commit -m "feat: add durable audit repository"`

### 3. Delivery worker, sinks and heartbeat

Create:

- `backend/src/cloud_ui/audit/sinks.py`
- `backend/src/cloud_ui/audit/delivery.py`
- `backend/tests/audit/test_sinks.py`
- `backend/tests/audit/test_delivery_worker.py`
- `backend/tests/audit/test_heartbeat.py`

Modify:

- `backend/src/cloud_ui/cli.py`
- `backend/src/cloud_ui/worker.py` if a shared loop helper is needed.
- `backend/src/cloud_ui/config.py`
- `backend/tests/test_cli.py`
- `backend/tests/test_config.py`

Implementation details:

- Add settings with safe local defaults:
  - `audit_sink_type: Literal["local", "fluentd_http"] = "local"`
  - `audit_delivery_max_attempts: int = 3`
  - `audit_delivery_retry_delay_seconds: int = 30`
  - `audit_delivery_batch_size: int = 20`
  - optional `audit_fluentd_http_url` rejected in production unless explicitly configured by environment.
- Add sink protocol:
  - `send(envelope: AuditEnvelope) -> SinkAck`
  - `heartbeat(envelope: AuditEnvelope) -> SinkAck`
  - typed `TemporarySinkError` and `PermanentSinkError`.
- `LocalTestAuditSink` stores acked envelopes and supports fail/recover/permanent rejection in tests.
- `FluentdHttpAuditSink` produces/sends JSON envelope compatible with Fluentd HTTP input. Unit tests
  verify payload shape without live Fluentd.
- `AuditDeliveryWorker.run_once()` claims one outbox row or a small bounded batch, sends, records attempt,
  marks delivered/retry/dead-letter and updates heartbeat.
- Temporary failure leaves `audit_outbox` durable with `retry_wait` and `not_before_at`.
- Permanent schema/auth failure moves to `dead_letter` and records safe `last_error_code`.
- Recovery after a previous failure records `audit.delivery.recovered`.
- `cloud-ui events --once` runs one bounded delivery iteration. Without `--once`, `cloud-ui events`
  loops using the same bounded worker with sleep.

Verification:

- `cd backend && .venv/bin/python -m pytest tests/audit/test_sinks.py tests/audit/test_delivery_worker.py tests/audit/test_heartbeat.py tests/test_cli.py tests/test_config.py -q`
- `cd backend && .venv/bin/python -m ruff check src/cloud_ui/audit src/cloud_ui/cli.py src/cloud_ui/config.py tests/audit tests/test_cli.py tests/test_config.py`
- `cd backend && .venv/bin/python -m mypy src`
- `git diff --check`

Commit:

- `git add backend/src/cloud_ui/audit backend/src/cloud_ui/cli.py backend/src/cloud_ui/worker.py backend/src/cloud_ui/config.py backend/tests/audit backend/tests/test_cli.py backend/tests/test_config.py`
- `git commit -m "feat: deliver audit events to test sink"`

### 4. Audit API and authorization

Create:

- `backend/src/cloud_ui/audit/cursor.py`
- `backend/src/cloud_ui/audit/routes.py`
- `backend/tests/audit/test_audit_api.py`
- `backend/tests/audit/test_audit_cursor.py`

Modify:

- `backend/src/cloud_ui/api.py`
- `backend/src/cloud_ui/config.py`
- `backend/src/cloud_ui/security/mock_identity.py`
- `backend/tests/security/test_mock_identity.py`
- `backend/tests/security/test_security_api.py`

Implementation details:

- Add settings:
  - `audit_default_limit=50`
  - `audit_max_limit=200`
  - `audit_cursor_signing_key` with dev default rejected in production.
- Add signed cursor codec for stable sort `occurred_at desc, event_id desc`.
- Add `AuditServices(repository, cursor_codec, default_limit, max_limit)`.
- Add routes:
  - `GET /api/v1/audit/events`
  - `GET /api/v1/audit/events/{event_id}`
  - `POST /api/v1/audit/export`
- Filters:
  - `from`, `to`
  - `action`
  - `outcome`
  - `actor_id`
  - `target_type`
  - `target_id`
  - `request_id`
  - `correlation_id`
  - `operation_id`
  - `delivery_state`
  - `safe_error_code`
- `audit.read` is required for list/detail. `audit.export` is required for export.
- Export is bounded by time range and limit; P0 returns an export request id and audit event
  rather than writing a file with potentially sensitive data.
- Audit list/detail/export success and denial call durable audit sink.
- Update mock identity:
  - `security_auditor`: `audit.read`, `operation.read`
  - `portal_admin`: `audit.read`, `audit.export`, existing admin capabilities.
- Negative tests:
  - unauthenticated list -> `401`
  - viewer/operator list -> `403`
  - security auditor export -> `403`
  - export missing CSRF/trusted Origin -> `403`
  - tampered cursor -> `400 cursor_tampered`
  - audit access creates `audit.read`/`audit.export` event without raw query secrets.

Verification:

- `cd backend && .venv/bin/python -m pytest tests/audit/test_audit_api.py tests/audit/test_audit_cursor.py tests/security/test_mock_identity.py tests/security/test_security_api.py -q`
- `cd backend && .venv/bin/python -m ruff check src/cloud_ui/audit src/cloud_ui/api.py src/cloud_ui/config.py src/cloud_ui/security/mock_identity.py tests/audit tests/security`
- `cd backend && .venv/bin/python -m mypy src`
- `git diff --check`

Commit:

- `git add backend/src/cloud_ui/audit backend/src/cloud_ui/api.py backend/src/cloud_ui/config.py backend/src/cloud_ui/security/mock_identity.py backend/tests/audit backend/tests/security`
- `git commit -m "feat: add audit search API"`

### 5. Frontend audit search UX

Create:

- `frontend/src/audit.ts`

Modify:

- `frontend/src/api.ts`
- `frontend/src/App.tsx`
- `frontend/src/App.test.tsx`
- `frontend/src/styles.css`

Implementation details:

- Add typed API helpers:
  - `listAuditEvents(params)`
  - `getAuditEvent(eventId)`
  - `requestAuditExport(body, csrf)`
- Add `view=audit` route visible only when capabilities include `audit.read`.
- Render compact audit table with:
  - occurred at with explicit timezone;
  - action;
  - outcome;
  - actor display/id;
  - target;
  - request/correlation ID;
  - delivery state;
  - safe error code.
- Filters are controlled inputs that submit server-side query params. The UI must not fetch full audit
  data for local filtering.
- Event detail panel shows only sanitized metadata.
- Export button appears only with `audit.export` and is disabled without CSRF.
- Tests cover:
  - security auditor sees audit view and can page results;
  - cloud operator/viewer do not see audit navigation;
  - security auditor does not see export button;
  - portal admin sees export button;
  - canary secret in fixture metadata is not rendered if backend returns redacted marker.

Verification:

- `cd frontend && npm test -- --run src/App.test.tsx`
- `cd frontend && npm run lint`
- `cd frontend && npm run typecheck`
- `cd frontend && npm test`
- `git diff --check`

Commit:

- `git add frontend/src/audit.ts frontend/src/api.ts frontend/src/App.tsx frontend/src/App.test.tsx frontend/src/styles.css`
- `git commit -m "feat: add audit search frontend"`

### 6. Documentation, generated evidence and final gates

Create:

- `docs/generated/audit-event-schema.json`
- `docs/generated/audit-action-dictionary.md`
- `docs/generated/audit-sample-events.md`
- `docs/generated/audit-source-map.md`
- `docs/generated/e07-fluentd-opensearch-lab.md`

Modify:

- `FILE_INDEX.md`
- `docs/08_AUDIT_OBSERVABILITY.md`
- `docs/10_SECURITY_DKB.md`
- `docs/11_DKB_TRACEABILITY.md`
- `docs/13_TEST_STRATEGY.md`
- `docs/15_DECISIONS_AND_OPEN_QUESTIONS.md`
- `docs/generated/api-register.md`
- `docs/generated/integration-register.md`
- `docs/generated/network-flow-matrix.md`
- `docs/generated/risk-register.md`
- `docs/generated/secret-inventory.md`
- `docs/execplans/E07-audit.md`

Implementation details:

- Generate schema/sample artifacts from code or maintain deterministic checked-in summaries. Do not
  include large logs.
- `audit-source-map.md` must mark each source as:
  - `implemented_by_portal`
  - `lab_contract_only`
  - `external_required`
  - `not_in_scope`
- Fluentd/OpenSearch lab doc includes:
  - observed pre-state;
  - safe Kolla commands for test all-in-one only;
  - expected smoke query;
  - rollback commands;
  - statement that no production secrets are used or committed.
- Update DKB traceability with E07 evidence and residual risks for ДКБ-48/50/47 production channel.
- Run self-review for authorization bypass, secret leakage, direct index access and false compliance claims.

Verification:

- `make lint`
- `make typecheck`
- `make test`
- `make test-integration`
- `make security`
- `make build`
- `git diff --check`
- Optional lab after code exists and user approves stand changes:
  - run documented Kolla/OpenSearch steps on test stand;
  - send synthetic audit event through configured lab adapter;
  - query sanitized event in OpenSearch;
  - store only sanitized summary in `docs/generated/e07-fluentd-opensearch-lab.md`.

Commit:

- `git add FILE_INDEX.md docs backend frontend`
- `git commit -m "docs: close E07 audit evidence"`

## Миграции и совместимость

E07 migration is expand-first:

1. Existing `audit_events` table stays present.
2. New E07 columns are nullable or have safe server/application defaults.
3. New `audit_outbox`, `audit_delivery_attempts` and `audit_heartbeats` tables are additive.
4. Old E06 API instances can continue writing old narrow events while new code is deployed, provided the
   old columns are not removed.
5. New E07 API/events instances can write and deliver expanded events after `cloud-ui db-upgrade`.

Rolling update order:

1. Deploy backend image containing migration and E07 code.
2. Run explicit `cloud-ui db-upgrade`.
3. Start/roll API.
4. Start/roll `cloud-ui events`.
5. Deploy frontend after audit API is available.

Rollback order:

1. Stop `cloud-ui events` to prevent new delivery attempts.
2. Deploy E06 frontend/backend images.
3. Keep E07 audit tables temporarily for forensic/backlog inspection, or run Alembic downgrade only
   after no E07 instance can write.
4. If lab OpenSearch was enabled, run the documented Kolla rollback on the test stand and retain
   sanitized evidence.

No OpenStack resource cleanup is required for default local/test sink.

## Проверка

Targeted verification is listed under each milestone. Final verification from repository root:

- `make lint` -> backend Ruff, frontend ESLint and secret scan pass.
- `make typecheck` -> backend mypy and frontend TypeScript pass.
- `make test` -> backend and frontend tests pass.
- `make test-integration` -> integration tests pass or optional live tests skip with explicit reason.
- `make security` -> secret scan passes.
- `make build` -> backend/frontend images build when Docker is available.
- `git diff --check` -> no whitespace/conflict marker issues.

Security-specific checks:

- unauthorized audit access denied;
- `audit.read` cannot export;
- export requires CSRF and trusted Origin;
- canary secrets absent from audit projection, delivery payload and API response;
- outage leaves durable backlog and visible failure;
- recovery delivers without duplicate/mismatched replay;
- dead-letter is visible and not silent;
- audit access creates audit events;
- internal error response is safe and linked by correlation ID.

## Доказательства

- Unit tests for event schema, taxonomy and mandatory fields.
- Redaction canary tests for audit/log/error/sink payloads.
- Migration tests for upgrade/downgrade and indexes.
- Repository tests for durable outbox and idempotent replay.
- Delivery worker tests for success, temporary outage, recovery, permanent failure, dead-letter and
  heartbeat.
- API tests for audit read/export RBAC, filters, pagination, cursor tampering and audit-access audit.
- Frontend tests for audit search visibility, pagination and export separation.
- Generated audit JSON Schema, action dictionary, sample events and source map.
- DKB traceability update for ДКБ-46-53.
- Optional all-in-one Fluentd/OpenSearch sanitized lab summary.

## Откат и восстановление

Safe rollback:

1. Stop `cloud-ui events`.
2. Disable E07 frontend audit route by deploying E06 frontend.
3. Deploy E06 backend API/worker/events image.
4. Keep E07 audit tables unless storage pressure requires downgrade; keeping them is safer for forensic
   continuity.
5. If downgrade is required, run Alembic downgrade from `0006_audit_delivery` to `0005_operations`
   only after all E07 instances are stopped.
6. For lab OpenSearch, revert `enable_opensearch`, `enable_opensearch_dashboards` and
   `enable_central_logging` to previous values on the test stand and run Kolla reconfigure/check per
   runbook.

Partial failure recovery:

- If delivery worker crashes after claiming an outbox item, a later worker can retry once
  `not_before_at` permits.
- If sink ack is duplicated, event hash/idempotency prevents duplicate mismatch from being treated as
  success.
- If tests leave SQLite rows, fixtures recreate databases per test.
- If frontend audit filters become stale, clearing query params recovers; no audit data is stored in
  `localStorage` or `sessionStorage`.

## Итог и остаточные риски

This section is updated as milestones complete. Initial residual risks:

- Production SIEM protocol, auth, retention, mTLS and certificate authorization are unknown.
- Fluentd is present in lab, but OpenSearch and central logging are disabled until a manual test-stand
  change is approved and executed.
- Portal heartbeat cannot prove host/container logging cannot be disabled by root; ДКБ-48 needs
  external FIM/auditd/IaC and SIEM absence-of-flow alert.
- Portal audit source map does not close ДКБ-50; complete coverage needs external OpenStack, host,
  storage, IdP and monitoring sources.
- Existing E02-E06 route-level audit is made durable through sink compatibility, but not every business
  mutation is refactored into a single domain transaction in this stage.
