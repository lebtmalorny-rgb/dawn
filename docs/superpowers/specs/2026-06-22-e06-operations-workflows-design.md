# E06 Operations And Workflows Design

Дата: 2026-06-22
Статус: design approved, written-spec review pending
Ветка/worktree: `e06-workflows` / `.worktrees/e06-workflows`

## Цель

E06 добавляет operations-first контур для утвержденных workflow: пользователь выбирает
allowlisted операцию, заполняет валидируемую форму, получает `operation_id` сразу после
durable записи и видит состояние execution/timeline. Повтор запроса с тем же
`Idempotency-Key` и тем же body возвращает существующую operation, а не запускает второй
execution.

Первый безопасный vertical slice: `maintenance-host-precheck` для host target как dry-run/precheck.
Он не меняет состояние OpenStack, не запускает Nova evacuate/live migration и не применяет Watcher
action plan. Реальный Mistral на all-in-one хосте используется только как отдельный P2
integration-smoke, тогда как основной P0 путь воспроизводим через строгий mock.

## Утвержденные решения

- Использовать operations-first порядок: state machine, idempotency и worker safety до UI.
- Первый workflow definition: `maintenance-host-precheck`, version `1.0.0`, target type `host`,
  risk `low`, approval mode `none`, cancel policy по definition.
- Browser передает только `workflow_key`, `version`, `targets`, `input` и `Idempotency-Key`.
  Browser не передает Mistral workflow name, YAML, task graph, Python/Jinja/shell input или endpoint.
- P0 Mistral mock обязан моделировать start/get/cancel/list-by-correlation, lost response и duplicate
  lookup by correlation.
- P2 all-in-one Mistral integration-smoke является opt-in, не требует production credential и явно
  маркируется как не production action.
- `unknown` является отдельным состоянием для потери связи и требует reconciliation. Оно не
  превращается в `failed` без проверки внешнего состояния.
- Watcher/Masakari в E06 становятся first-class read/status modules, но опасные действия остаются
  disabled unless allowlisted workflow + capability + approval + audit + ADR.

## Data Model

Добавляются таблицы через Alembic migration с downgrade:

- `workflow_definitions`
  - `workflow_key`, `version`
  - `title`, `description`
  - `target_type`
  - `input_schema_json`
  - `ui_schema_json`
  - `mistral_workflow_name`
  - `required_capability`
  - `required_scope_type`
  - `risk_level`
  - `approval_mode`
  - `cancel_policy`
  - `enabled_environments_json`
  - `checksum`
  - `enabled`
  - `created_at`, `updated_at`

- `operations`
  - `operation_id`
  - `workflow_key`, `workflow_version`
  - `definition_checksum`
  - `actor_subject_id`
  - `scope_type`, `scope_id`
  - `status`
  - `request_hash`
  - `idempotency_key_hash`
  - `target_snapshot_json`
  - `input_json`
  - `correlation_id`
  - `external_execution_id`
  - `created_at`, `updated_at`, `accepted_at`, `started_at`, `completed_at`

- `operation_targets`
  - `operation_id`
  - `target_type`
  - `cloud_id`, `region_id`, `resource_id`
  - `snapshot_json`
  - `status`
  - `created_at`, `updated_at`

- `operation_events`
  - append-only timeline: state transition, adapter result, reconciliation, cancel request,
    partial result and safe error code.

- `operation_attempts`
  - worker dispatch attempts, external lookup result, start outcome and retry boundary.

- `operation_outbox`
  - durable dispatch item created in the same transaction as `operations`.

- `operation_idempotency_keys`
  - primary key over actor, workflow, scope and key hash;
  - stores normalized request hash and `operation_id`, never raw idempotency key.

## Operation State Machine

Allowed states:

- `accepted`
- `queued`
- `dispatching`
- `running`
- `cancel_requested`
- `succeeded`
- `partially_succeeded`
- `failed`
- `cancelled`
- `unknown`

Transition rules are implemented and unit-tested. Terminal states are immutable except append-only
events. Worker crash recovery can move `dispatching` or `unknown` through reconciliation, but not by
blindly starting a new external execution.

## Workflow Catalog

The catalog is server-side and versioned. In P0 it can be loaded from trusted local code/config and
seeded into the repository; production publication remains GitOps per `docs/07_WORKFLOWS.md`.

Definition validation includes:

- `additionalProperties=false` for workflow input schema;
- bounded string lengths and enum values;
- target type allowlist;
- required portal capability;
- enabled environment check;
- checksum match;
- no browser-supplied Mistral name.

The initial `maintenance-host-precheck` input is intentionally small: a maintenance window or reason
string, dry-run flag enforced server-side, and acknowledgement fields only if the definition requires
them. It must not accept URL, host path, shell, Python, Jinja or arbitrary workflow identifiers.

## Submit API

Endpoints:

- `GET /api/v1/workflow-definitions`
- `GET /api/v1/workflow-definitions/{workflow_key}/versions/{version}`
- `POST /api/v1/workflow-definitions/{workflow_key}/validate-input`
- `POST /api/v1/operations`
- `GET /api/v1/operations`
- `GET /api/v1/operations/{operation_id}`
- `POST /api/v1/operations/{operation_id}/cancel`

`POST /api/v1/operations` requires session, trusted Origin, CSRF, capability, `Idempotency-Key`,
definition lookup, input schema validation, target validation and target snapshot. It creates operation,
targets, timeline event, idempotency row and outbox row in one transaction, then returns `202`.

For host targets, P0 authorization follows the existing admin/system-like constraint: ordinary
project-scoped users cannot use host-level operations unless the role matrix grants the workflow
capability and the backend validates the target. Keystone/OpenStack policy remains final for future
mutating OpenStack calls.

## Mistral Adapter And Worker

Adapter contract:

- `start_execution(definition, operation, correlation_id)`;
- `get_execution(external_execution_id)`;
- `cancel_execution(external_execution_id)`;
- `list_executions_by_correlation(correlation_id)`;
- typed errors for auth, forbidden, not found, conflict, unavailable, timeout and invalid response.

Retry rules:

- no blind POST retry after timeout/lost response;
- worker first performs lookup by correlation before another start attempt;
- duplicate lookup result attaches existing external execution ID to the operation;
- external unavailable can produce `unknown`, not immediate `failed`;
- reconciliation keeps checking unknown/running operations until a bounded terminal result or safe
  partial result is available.

The CLI `cloud-ui worker` becomes a bounded worker entrypoint suitable for tests. Long orchestration
stays in Mistral; the portal worker only dispatches and reconciles operation state.

## Watcher And Masakari Modules

E06 exposes first-class read/status contracts for Watcher and Masakari, initially with P0 strict
adapters/mocks if live endpoints are not configured.

Watcher visible resources:

- goals;
- strategies;
- audit templates;
- audits and continuous audits;
- action plans;
- actions;
- recommendations;
- telemetry freshness and automatic-apply risk markers.

Masakari visible resources:

- failover segments;
- segment hosts;
- notifications;
- recovery methods;
- monitor/recovery timeline;
- Consul hostmonitor matrix coverage;
- Nova/Masakari conflict markers;
- approval gate status.

Automatic Watcher apply is denied by default and tested. Masakari recovery/evacuation remains a
disabled workflow path unless represented by allowlist, capability, approval, audit, ADR and rollback
or abort policy. `processmonitor` is shown as unsupported/diagnostic in Kolla/container context unless
lab evidence enables it.

## Frontend

Frontend work starts only after operation state/idempotency/worker behavior is covered.

User-facing additions:

- catalog list for available operations;
- `maintenance-host-precheck` form generated from server-provided schema;
- host target preview and risk/precondition summary;
- explicit confirm before submit;
- operation detail page with timeline, status, correlation ID and external execution ID when present;
- adaptive polling with backoff;
- visible `unknown`, partial result and cancel semantics.

Frontend uses capabilities for UX only. Backend remains the enforcement point.

## Tests And Evidence

Backend tests:

- migration upgrade/downgrade for operation tables;
- state machine allowed and rejected transitions;
- catalog checksum/schema/permission/enabled-environment validation;
- arbitrary workflow name/input rejection;
- idempotency same key/same request returns same operation;
- same key/different request returns `409`;
- operation submit returns `202` after durable operation and outbox row;
- forbidden target and stale/missing target rejection;
- target snapshot persists and does not change after group/member edits;
- worker crash before external response does not create duplicate execution;
- lost Mistral response performs lookup by correlation before start retry;
- Mistral unavailable moves to `unknown` and reconciliation can recover;
- cancel allowed/denied according to definition and current state;
- audit metadata redacts raw idempotency key and full input body.

Frontend tests:

- operation navigation visibility by capability;
- catalog load/forbidden states;
- form validation and submit behavior;
- operation page renders `accepted`, `running`, `unknown`, partial, terminal and cancel states;
- polling/backoff without full inventory load.

Integration evidence:

- P0 mock test report is mandatory.
- P2 all-in-one Mistral smoke is opt-in and must record exact command, endpoint source, workflow key,
  correlation ID and proof that no production action was executed.

Final gates:

- `make lint`
- `make typecheck`
- `make test`
- `make security`

`make test-integration` is used only when the all-in-one Mistral test configuration is present.

## Documentation Updates

Implementation must update:

- `docs/05_API_AND_INTEGRATIONS.md`
- `docs/06_AUTH_RBAC_SESSIONS.md`
- `docs/07_WORKFLOWS.md`
- `docs/08_AUDIT_OBSERVABILITY.md`
- `docs/10_SECURITY_DKB.md` only if security gates or risks change
- `docs/11_DKB_TRACEABILITY.md`
- generated API/integration/risk registers as needed
- `docs/execplans/E06-workflows.md`

## DKB Scope

- ДКБ-01-07/12/13: portal capability, service identity separation and denial tests. Production IAM,
  PAM and SoD evidence remain external.
- ДКБ-46-52: operation audit, safe user error, redaction and unknown/error handling. Full SIEM
  delivery remains E07/P3 unless explicitly added.
- ДКБ-60: group target snapshot for operations. E06 proves snapshot persistence, not broad group
  governance.
- ДКБ-77: Mistral/Watcher/Masakari API contracts and disabled/allowed status are documented in
  generated registers.

E06 does not claim production Mistral/Watcher/Masakari action safety without approved credentials,
GitOps publication evidence, SIEM delivery, security review and owner approval.

## Non-goals

- No arbitrary script executor.
- No browser-supplied Mistral YAML, workflow name, task graph or template.
- No Nova evacuate/live migration.
- No automatic Watcher apply.
- No portal-side evacuation from Consul Events or Prometheus alerts.
- No production admin credential.
- No long orchestration inside portal worker.
- No blind retry of irreversible external POST.
- No completion claim for ДКБ-69 interpreter/shell conflict.

## Rollback

Rollback removes the E06 API/UI/worker code and runs the Alembic downgrade for E06 tables before
deploying the previous backend image. Because the first workflow is dry-run/precheck and P0 mock is the
default evidence path, rollback should not require OpenStack resource cleanup. If P2 all-in-one Mistral
smoke created a test execution, cleanup is limited to the test project/workflow evidence recorded by the
integration command.
