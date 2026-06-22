# E07 Audit Delivery And Search Design

Дата: 2026-06-22
Статус: design approved, written-spec review pending
Ветка/worktree: `e07-audit` / `.worktrees/e07-audit`

## Цель

E07 добавляет доказуемый порталный аудит: события действий портала имеют обязательные поля,
редактируются до записи, сохраняются в durable projection/outbox, доставляются в test sink с
ack/retry/dead-letter/heartbeat и доступны security auditor через backend API/UI с раздельными
`audit.read` и `audit.export`.

До E07 audit-события существуют как in-process `InMemoryAuditSink` и базовая таблица
`audit_events` из E02. E05/E06 уже пишут события по группам и операциям, но durable delivery,
test SIEM/syslog adapter, heartbeat, replay/idempotency, search/export API and source map еще не
реализованы.

## Утвержденные решения

- Сначала реализуется portal audit, а не полный инфраструктурный аудит OpenStack/Kolla/host.
- Авторитетное долговременное хранилище аудита остается внешним SIEM/OpenSearch или equivalent
  protected audit system. MariaDB портала является operational projection и backlog, не immutable SIEM.
- Для E07 production SIEM credentials не требуются и не коммитятся. Production protocol/auth/TLS/mTLS
  остаются внешним owner-provided contract по ADR-008/E08.
- Для локального и CI evidence используется test sink adapter с управляемыми success/failure/recovery.
- Для lab evidence используется Fluentd/OpenSearch-compatible path на all-in-one стенде. На момент
  design проверки `fluentd` container уже запущен на `192.168.10.14`, а `enable_opensearch`,
  `enable_opensearch_dashboards` и `enable_central_logging` в `/etc/kolla/globals.yml` выключены.
  Развертывание OpenSearch фиксируется manual runbook/evidence, не добавляется в portal runtime.
- `cloud-ui events` становится bounded audit delivery worker для audit outbox. Долгие бизнес-операции
  по-прежнему выполняются через Mistral/operation worker.
- Все новые публичные audit API имеют server-side pagination/filtering/stable sort и OpenAPI schema.
- Audit access itself is audited. Прямой доступ к DB/log files/RabbitMQ/Fluentd/OpenSearch index не
  считается прикладным доступом и остается внешним control.

## Scope

E07 включает:

- versioned audit event schema and JSON Schema artifact;
- action/event taxonomy with ДКБ-49.01-49.08 mapping;
- central sanitizer for audit/log/error payloads;
- Alembic migration for durable audit projection, audit outbox, delivery attempts and heartbeat state;
- repository/service API for atomic business event + audit/outbox creation;
- compatibility path for existing route-level `AuditEvent` calls;
- delivery worker with retry, dead-letter, replay idempotency and queue age evidence;
- local contract test sink and Fluentd/OpenSearch-compatible envelope;
- heartbeat/failure/recovery events and observable delivery status;
- `GET /api/v1/audit/events`, `GET /api/v1/audit/events/{event_id}`,
  `POST /api/v1/audit/export` or equivalent export request endpoint;
- frontend audit search view for `security_auditor`;
- `docs/generated/audit-source-map.md` separating portal-covered sources from external sources;
- DKB traceability update for ДКБ-46-53 and evidence summaries.

## Non-goals

- No production SIEM credential, endpoint or certificate material in the repo.
- No claim that portal MariaDB audit is immutable SIEM.
- No claim that ДКБ-50 is closed by portal audit alone.
- No direct browser access to Fluentd, OpenSearch, RabbitMQ, MariaDB or log files.
- No raw stack traces or raw request bodies in browser-facing audit events.
- No logging of every ordinary inventory list read with excessive personal or business metadata.
- No Kolla/OpenSearch deployment automation in portal runtime images. Lab deployment is runbook/evidence.

## Data Model

E07 expands audit storage with additive tables/indexes:

- `audit_events`
  - either migrated in place or shadow-expanded from E02;
  - stores the normalized, redacted event projection;
  - includes mandatory fields: `event_id`, `event_version`, `occurred_at`, actor, session,
    action/event/outcome, target, scope, source, request/correlation IDs, operation/external IDs,
    service/component, safe error code, `metadata_json`, `delivery_state`;
  - timestamp is UTC and serialized to second precision for external envelope.

- `audit_outbox`
  - one row per event delivery item;
  - `state`: `pending`, `claimed`, `delivered`, `retry_wait`, `dead_letter`;
  - retry counters, `not_before_at`, `last_error_code`, `last_error_at`, `delivered_at`,
    `sink_message_id`, `event_hash`;
  - unique idempotency key based on `event_id`, `event_version`, sink id and event hash.

- `audit_delivery_attempts`
  - append-only attempt records;
  - captures adapter result, safe error code, ack id, duration and retry decision.

- `audit_heartbeats`
  - periodic event or state row proving delivery path health;
  - contains `last_success_at`, `last_failure_at`, queue depth/age snapshot and sink id.

No table stores raw tokens, cookies, raw `Authorization`, raw workflow input, raw request/response body,
private keys, certificates private material or production URLs with credentials.

## Event Schema And Taxonomy

`backend/src/cloud_ui/audit/` owns the new domain:

- `schema.py`: SQLAlchemy table definitions for audit tables;
- `models.py`: immutable Pydantic DTOs for normalized events and delivery state;
- `taxonomy.py`: action dictionary, event categories and DKB mapping;
- `redaction.py`: central sanitizer used by audit, logs and safe errors;
- `repository.py`: transactional writes, list/detail/export queries and outbox claim/update;
- `delivery.py`: worker orchestration;
- `sinks.py`: adapter protocol, local test sink and Fluentd/OpenSearch-compatible envelope;
- `routes.py`: audit search/export API.

The taxonomy starts with existing E02-E06 actions:

- session login/logout/timeout/revoke/limit;
- CSRF/origin/session/authorization/OpenStack denial;
- inventory refresh requested and reconciliation anomalies;
- group create/update/delete/member/preview events and denials;
- workflow catalog/operation accepted/dispatched/completed/failed/cancelled/unknown;
- Watcher/Masakari read/status/recovery approval request markers;
- audit read/export access and denial;
- SIEM/test sink delivery failure/recovery/heartbeat.

Each action has allowed target types, allowed outcomes, field classification and DKB coverage notes.
Unknown or unsupported action codes fail closed in schema/taxonomy tests unless explicitly registered.

## Redaction And Error Boundary

Central sanitizer is allowlist-first:

- scalar fields with known safe names pass through;
- secret-like keys and values become `"***"`;
- nested objects are recursively sanitized only when the schema marks them allowed;
- raw request bodies are denied by default;
- workflow input is represented by safe summary and hash, not full body;
- client-facing audit contains safe `error_code` and safe message only;
- protected service logs may keep sanitized internal error detail with the same correlation ID.

Canary tests cover password, token, cookie, authorization header, private key, application credential,
Vault response, database URL, RabbitMQ URL, workflow secret and stack trace samples across audit
projection, delivery payload and API response.

## Transactional Audit/Outbox

Existing route code currently calls `security.audit_sink.record(AuditEvent(...))`. E07 introduces a
compatibility `AuditSink` implementation that:

1. normalizes and sanitizes the event;
2. writes `audit_events`;
3. writes `audit_outbox`;
4. exposes in-memory events only in tests where existing assertions need compatibility.

For new mutating services, repository methods should accept an optional audit event and write the
business change + audit projection + outbox in one database transaction. Existing E02-E06 route-level
events can be migrated incrementally to the durable sink without broad route refactors in the first
milestone.

Delivery is at-least-once from portal to sink. Sink idempotency is enforced by `event_id` and event
hash. Duplicate replay is accepted only when the payload hash matches; mismatched replay becomes a
dead-letter/security finding.

## Delivery Worker And Sink Contract

`cloud-ui events` processes audit outbox in bounded iterations:

- claim oldest deliverable item by stable sort;
- send sanitized envelope to configured sink;
- record attempt with ack/failure;
- mark delivered on ack;
- schedule bounded retry for temporary failure;
- move to dead-letter after max attempts or permanent schema/auth failure;
- emit delivery failure/recovery audit events and heartbeat state.

Sink adapter protocol:

```text
send(event_envelope) -> SinkAck | TemporarySinkError | PermanentSinkError
heartbeat() -> SinkAck | TemporarySinkError | PermanentSinkError
```

The local test sink stores sanitized envelopes in memory or a local test table and can be configured to
fail, recover, duplicate ack or reject schema. The Fluentd/OpenSearch-compatible adapter sends a JSON
envelope suitable for Fluentd HTTP input or forward-compatible transport, but E07 tests do not require
production Fluentd/OpenSearch to be present.

## Fluentd/OpenSearch Lab Path

Lab evidence is manual and sanitized:

- all-in-one host: `192.168.10.14`;
- ansible host: `192.168.10.15`;
- observed current state: Kolla `fluentd` container is running, OpenSearch and central logging are
  disabled in `/etc/kolla/globals.yml`;
- E07 runbook documents enabling the lab sink only on the test stand, expected Kolla commands,
  rollback steps and smoke query;
- event payloads use synthetic subject IDs and canary-safe values only;
- no production credentials, tokens, `clouds.yaml`, openrc or private keys are copied into Git.

The lab runbook proves a narrow path: portal audit worker can deliver sanitized events to a Fluentd/
OpenSearch-compatible endpoint and recover after outage. It does not prove corporate SIEM retention,
mTLS authorization, FIM/auditd anti-disable control or full ДКБ-50 coverage.

## Audit API And UI

Backend endpoints:

- `GET /api/v1/audit/events`
  - requires `audit.read`;
  - filters: time range, outcome, action, actor reference, target type/id, request/correlation ID,
    operation ID, delivery state and safe error code;
  - cursor pagination with stable sort `occurred_at desc, event_id desc`;
  - field-level projection by capability/scope.

- `GET /api/v1/audit/events/{event_id}`
  - requires `audit.read`;
  - returns one sanitized event if visible.

- `POST /api/v1/audit/export`
  - requires `audit.export`;
  - requires CSRF and trusted Origin;
  - bounded export window/limit;
  - returns an `operation_id` or export artifact metadata without direct DB/index access.

Frontend adds an audit search view visible to `security_auditor`. It uses server filters and pagination,
does not fetch the whole audit table, and shows delivery state/queue health without raw internal
details. Export controls appear only with `audit.export`; `audit.read` alone can search but not export.

Audit read/export success and denial generate audit events. This avoids treating audit observation as
out-of-band access.

## Authorization

Existing mock roles are adjusted conservatively:

- `security_auditor`: `audit.read`, `operation.read`; no mutating workflow capability;
- `portal_admin`: may receive `audit.export` only if tests prove separation from `audit.read`;
- `cloud_operator`: no audit search/export by default;
- `cloud_viewer`: no audit search/export.

Backend enforces capabilities on every audit endpoint. Frontend uses capabilities only for visibility.
Negative tests cover unauthenticated, viewer/operator denied, auditor export denied, CSRF/origin
denied on export and direct URL access.

## Observability And Alerts

E07 exposes portal-owned evidence:

- audit outbox depth and oldest age from repository/service API;
- heartbeat status and last delivery failure/recovery;
- dead-letter count and latest safe error code;
- delivery worker CLI output for one bounded iteration in tests.

If the sink is unavailable, the API and business mutations continue to create durable audit backlog.
Outage is visible through delivery state, heartbeat/failure events and generated evidence. Silent drop
is treated as a test failure.

## Documentation And Evidence

E07 updates:

- `docs/08_AUDIT_OBSERVABILITY.md`;
- `docs/10_SECURITY_DKB.md`;
- `docs/11_DKB_TRACEABILITY.md`;
- `docs/13_TEST_STRATEGY.md`;
- `docs/generated/api-register.md`;
- `docs/generated/integration-register.md`;
- `docs/generated/risk-register.md`;
- `docs/generated/secret-inventory.md`;
- `docs/generated/audit-source-map.md`;
- optional sanitized lab summary for Fluentd/OpenSearch evidence.

Evidence includes:

- JSON Schema audit event artifact;
- action dictionary and DKB mapping;
- sample success/failure/unknown/heartbeat events;
- redaction canary test report;
- delivery success/failure/recovery/dead-letter tests;
- replay/idempotency tests;
- audit read/export authorization tests;
- frontend audit search tests;
- lab runbook for all-in-one Fluentd/OpenSearch path.

## DKB Boundary

E07 can create portal-scoped evidence for:

- ДКБ-46: portal can transmit audit/security events to an external/test sink;
- ДКБ-47: portal delivery contract has protected-channel placeholders and test delivery semantics;
- ДКБ-49/49.01-49.08: mandatory fields and mapping exist for portal events;
- ДКБ-51: canary redaction tests cover portal audit/log/error sinks;
- ДКБ-52: safe audit error plus correlation ID links to protected sanitized service log;
- ДКБ-53: application audit read/export is capability-scoped and itself audited.

E07 does not fully close:

- ДКБ-48: root/operator can still disable host/container logging without external FIM/auditd/IaC and
  SIEM absence-of-flow alerts;
- ДКБ-50: complete audit requires Keystone CADF, Nova/Neutron/Glance/Cinder notifications,
  Mistral/Watcher/Masakari events, HAProxy/API logs, container runtime, systemd/sudo/PAM/auditd,
  libvirt/QEMU/OVS/OVN, storage/backup, IdP/IAM and monitoring sources;
- ДКБ-47 production channel security: mTLS/cert authorization and corporate SIEM retention require
  owner-provided evidence in later stages.

## Testing Strategy

Implementation follows TDD:

1. schema/taxonomy tests fail first;
2. migration tests prove upgrade/downgrade and indexes;
3. redaction canary tests fail first across all sinks;
4. repository tests prove transaction, outbox, idempotent replay and dead-letter;
5. worker tests prove success, temporary failure, recovery, permanent failure and heartbeat;
6. API tests prove read/export RBAC, pagination, filters, field scope and audit access audited;
7. frontend tests prove security auditor search UX and export visibility;
8. integration smoke proves default local sink; optional lab evidence uses Fluentd/OpenSearch runbook;
9. final gates: `make lint`, `make typecheck`, `make test`, `make test-integration`,
   `make security`, `git diff --check`, and `make build` when Docker is available.

## Rollback

Rollback is safe because E07 migrations are additive until the old in-process audit path is removed.

1. Stop `cloud-ui events` audit delivery worker.
2. Disable audit search/export UI route if needed.
3. Deploy previous E06 backend/frontend images.
4. Run Alembic downgrade for E07 audit tables/columns only after no E07 API/events instance writes
   audit rows.
5. For lab Fluentd/OpenSearch, run the documented Kolla rollback on the test all-in-one only and keep
   sanitized evidence.

No OpenStack resource cleanup is required for the local/test sink path.
