# API register

- Stage: E06
- DKB: ДКБ-77 draft register
- Status: E06 operation catalog/API/worker/UI, P0 Watcher/Masakari read-status modules and optional read-only Mistral smoke implemented; Keystone/Nova/Placement adapter contracts remain offline/live-smoke pending

## Portal API

All portal APIs use prefix `/api/v1`, JSON UTF-8, UTC timestamps, server-side session cookie and correlation/request ID. Mutating APIs require CSRF; `Idempotency-Key` is required where the endpoint contract states retry-safe operation/member semantics.

| API | Purpose | Consumer | Auth | Stage | Audit | Blocking/disable mechanism |
|---|---|---|---|---|---|---|
| `GET /health/live` | process liveness | HAProxy/Kolla | none/internal route policy | E01 | no | HAProxy/internal routing |
| `GET /health/ready` | dependency readiness | HAProxy/Kolla | none/internal route policy | E01 | no | HAProxy/internal routing |
| `GET /session` | current session | frontend | session cookie | E02 | `session.required`, `session.timeout` | implemented in P0 |
| `POST /session/login` | login start/mock/test flow | frontend | flow-specific | E02 | login success/failure, session limit | implemented in P0; production mock hard-disabled |
| `POST /session/logout` | logout | frontend | session+CSRF | E02 | logout, CSRF denial | implemented in P0 |
| `GET /session/active` | active UI sessions | frontend | session+capability | E02 | protected access | implemented in P0; capability `session.manage` |
| `DELETE /session/active/{session_id}` | revoke session | frontend | session+CSRF+trusted Origin+capability | E02 | `session.revoke`, CSRF/origin denial | implemented in P0; capability `session.manage` |
| `GET /capabilities` | effective portal permissions | frontend | session | E02 | protected access | implemented in P0; response contains no policy expression |
| `POST /admin/role-bindings` | P0 role binding policy probe | frontend/admin future | session+CSRF+capability | E02 | authorization denial | implemented only as security contract path; full admin UI remains planned |
| `POST /operations/simulated-openstack-action` | P0 OpenStack-deny finality probe | security tests | session+CSRF+capability | E02 | portal denial or OpenStack denial | implemented only as security contract path; real operations start in E06 |
| `GET /inventory/modules` | inventory navigation descriptors and disabled module contracts | frontend | session | E04 | protected access policy | implemented in E04; enabled modules are capability-aware, future modules return explicit disabled descriptors |
| `GET /instances` | paged instance list from portal read model, optional `group_id` filter | frontend | session+capability; `group_id` additionally requires `group.read` and group scope access | E04/E05 | aggregate inventory read policy; group access denial | implemented in E04; E05 adds group filter; capability `instance.read`; server-side filters/sort/pagination, max limit 200 |
| `GET /instances/{cloud_id}/{region_id}/{instance_id}` | instance detail from portal read model | frontend | session+capability+scope | E04 | protected access policy | implemented in E04; capability `instance.read` |
| `POST /instances/{...}/refresh` | targeted refresh request contract | frontend/API clients | session+CSRF+capability+idempotency | E04 | `instance.refresh.requested` | implemented in E04 as protected request contract; returns `operation_id`; no Nova mutation/workflow execution |
| `GET /hypervisors` | paged hypervisor list from portal read model, optional `group_id` filter | frontend | session+capability; `group_id` additionally requires `group.read` and group scope access | E04/E05 | aggregate inventory read policy; group access denial | implemented in E04; E05 adds group filter; capability `hypervisor.read`; server-side filters/sort/pagination, max limit 200 |
| `GET /hypervisors/{cloud_id}/{region_id}/{hypervisor_id}` | hypervisor detail from portal read model | frontend | session+capability+scope | E04 | protected access policy | implemented in E04; capability `hypervisor.read` |
| `GET /compute-services` | paged Nova compute service health | frontend | session+capability | E04+ | aggregate health read policy | disabled descriptor only in E04; future capability `compute_service.read` |
| `GET /network-agents` | paged Neutron agent health | frontend | session+capability | E04+ | aggregate health read policy | disabled descriptor only in E04; future capability `network_agent.read` |
| `GET /volume-services` | paged Cinder service health | frontend | session+capability | E04+ | aggregate health read policy | disabled descriptor only in E04; future capability `volume_service.read` |
| `GET /image-tasks` | paged Glance image task status | frontend | session+capability | E04+ | protected access policy | disabled descriptor only in E04; future capability `image_task.read` |
| `GET /topology` | bounded topology/dependency graph page | frontend | session+capability+scope | E04+/E10 | protected access policy | disabled descriptor only in E04; future capability `topology.read` |
| `GET /capacity/summary` | aggregated capacity dashboard data | frontend | session+capability+scope | E04+/E10 | aggregate read policy | disabled descriptor only in E04; future capability `capacity.read` |
| `GET /capacity/timeseries` | downsampled metric series | frontend | session+capability+scope | E10 | aggregate read policy | capability `capacity.read` |
| `GET /search` | global capability-aware search | frontend | session+capability+scope | E04+/E10 | protected access policy | capability `search.read` |
| `GET /groups` | group list | frontend | session+capability+scope | E05 | group read policy | implemented in E05; capability `group.read`; limit max 200 |
| `POST /groups` | create group | frontend/API clients | session+CSRF+trusted Origin+capability | E05 | `group.create`, denial events | implemented in E05; capability `group.manage`; VM groups project-scoped; host/mixed require admin/system-like policy |
| `GET /groups/{group_id}` | group detail | frontend | session+capability+scope/owner | E05 | group read policy | implemented in E05; unauthorized scope returns safe 404 |
| `PATCH /groups/{group_id}` | update group metadata | frontend/API clients | session+CSRF+trusted Origin+capability+revision | E05 | `group.update`, denial events | implemented in E05; stale revision returns `409 group_revision_conflict` |
| `DELETE /groups/{group_id}` | soft-delete group | frontend/API clients | session+CSRF+trusted Origin+capability | E05 | `group.delete`, denial events | implemented in E05; no OpenStack side effect |
| `GET /groups/{group_id}/members` | explicit/imported member list | frontend | session+capability+scope/owner | E05 | group read policy | implemented in E05; max limit 200 |
| `POST /groups/{group_id}/members` | add explicit member | frontend/API clients | session+CSRF+trusted Origin+capability+idempotency | E05 | `group.member.add`, denial events | implemented in E05; capability `group.manage`; validates VM project scope or host admin; returns `operation_id` |
| `DELETE /groups/{group_id}/members/{resource_type}/{cloud_id}/{region_id}/{resource_id}` | remove explicit member | frontend/API clients | session+CSRF+trusted Origin+capability+idempotency | E05 | `group.member.remove`, denial events | implemented in E05; returns `status=deleted`; idempotency binding rejects same-key/different-payload |
| `POST /groups/rules/validate` | validate safe group rule AST | frontend/API clients | session+capability | E05 | authorization denial | implemented in E05; capability `group.read`; rejects arbitrary field/operator/value shape |
| `POST /groups/{group_id}/preview` | preview dynamic rule | frontend | session+capability+scope/owner+inventory read capability | E05 | `group.preview`, denial events | implemented in E05; capability `group.read` plus `instance.read`/`hypervisor.read`; bounded limit max 50 |
| `GET /workflow-definitions` | allowlisted workflow catalog without Mistral names | frontend | session+capability | E06 | catalog read policy | implemented in E06; capability `operation.read`; initial definition `maintenance-host-precheck@1.0.0` |
| `GET /workflow-definitions/{workflow_key}/versions/{version}` | workflow definition | frontend | session+capability | E06+ | catalog read policy | planned; not implemented in E06 P0 |
| `POST /workflow-definitions/{workflow_key}/validate-input` | validate input | frontend | session+CSRF+capability | E06+ | validation event if protected | planned; P0 validates input inside `POST /operations` |
| `POST /operations` | submit allowlisted operation | frontend | session+trusted Origin+CSRF+capability+idempotency | E06 | `operation.accepted`, authorization denial | implemented in E06; requires `operation.read` plus workflow-specific `workflow.execute.maintenance-host`; durable operation/outbox/idempotency before `202` |
| `GET /operations` | actor/scope-scoped operation list | frontend | session+capability+scope | E06 | protected access policy | implemented in E06; capability `operation.read`; signed cursor, `updated_at.desc`, max limit 200 |
| `GET /operations/{operation_id}` | operation status and timeline | frontend | session+capability+scope | E06 | protected access policy | implemented in E06; capability `operation.read`; returns correlation and external execution ID |
| `POST /operations/{operation_id}/cancel` | cancel operation request | frontend | session+trusted Origin+CSRF+capability | E06 | cancel request/denial | route implemented but fail-closed in E06 P0 with `409 operation_not_cancelable`; uses `operation.read` guard until cancel semantics are proven |
| `POST /operations/{operation_id}/retry` | retry operation | frontend | session+CSRF+capability | E06+ | retry request | planned; not implemented in E06 P0 |
| `GET /events/stream` | SSE live event stream | frontend | session+capability+scope | E06+/E10 | stream subscribe/denial | capability `realtime.stream.read` |
| `GET /events` | polling fallback for live events | frontend | session+capability+scope | E06+/E10 | protected access policy | capability `realtime.stream.read` |
| `GET /operations/{operation_id}/events` | operation timeline events | frontend | session+capability+scope | E06 | protected access policy | capability `operation.read` |
| `GET /watcher/goals` | Watcher goals status | frontend | session+capability | E06 | protected access policy | implemented in E06 P0; guarded by `operation.read`; static read/status payload |
| `GET /watcher/strategies` | Watcher strategies status | frontend | session+capability | E06 | protected access policy | implemented in E06 P0; guarded by `operation.read`; no direct apply |
| `GET /watcher/audit-templates` | Watcher audit templates status | frontend | session+capability | E06 | protected access policy | implemented in E06 P0; guarded by `operation.read`; dry-run template marker |
| `GET /watcher/audits` | Watcher audits | frontend | session+capability+scope | E06 | protected access policy | implemented in E06 P0; guarded by `operation.read` |
| `GET /watcher/continuous-audits` | Watcher continuous audit status | frontend | session+capability+scope | E06 | protected access policy | implemented in E06 P0; disabled state marker |
| `GET /watcher/action-plans` | Watcher action plans | frontend | session+capability+scope | E06 | protected access policy | implemented in E06 P0; direct apply disabled; operation path points to `/api/v1/operations` |
| `GET /watcher/actions` | Watcher actions | frontend | session+capability+scope | E06 | protected access policy | implemented in E06 P0; guarded by `operation.read` |
| `GET /watcher/recommendations` | Watcher recommendations with risk/conflict markers | frontend | session+capability+scope | E06 | protected access policy | implemented in E06 P0; `automatic_apply.enabled=false` |
| `GET /masakari/segments` | Masakari failover segments | frontend | session+capability+scope | E06 | protected access policy | implemented in E06 P0; guarded by `operation.read`; approval gate and Consul matrix markers |
| `GET /masakari/segments/{segment_id}` | Masakari segment detail | frontend | session+capability+scope | E06 | protected access policy | implemented in E06 P0; guarded by `operation.read` |
| `GET /masakari/segments/{segment_id}/hosts` | Masakari segment hosts | frontend | session+capability+scope | E06 | protected access policy | implemented in E06 P0; guarded by `operation.read` |
| `GET /masakari/notifications` | Masakari notifications | frontend | session+capability+scope | E06 | protected access policy | implemented in E06 P0; guarded by `operation.read`; direct recovery disabled |
| `GET /masakari/notifications/{notification_id}` | Masakari notification detail | frontend | session+capability+scope | E06 | protected access policy | implemented in E06 P0; guarded by `operation.read`; Nova/Masakari conflict marker |
| `GET /masakari/recovery-timeline` | HA recovery timeline | frontend | session+capability+scope | E06 | protected access policy | implemented in E06 P0; guarded by `operation.read` |
| `GET /audit/events` | audit search | frontend | session+capability+scope | E07 | audit access audited | capability `audit.read` |
| `GET /audit/events/{event_id}` | audit event detail | frontend | session+capability+scope | E07 | audit access audited | capability `audit.read` |

## External APIs used by portal

| External API | Purpose | Version/microversion | Stage | Status | Evidence required |
|---|---|---|---|---|---|
| Keystone Identity API v3 | version discovery and sanitized catalog fixture mapping | observed `v3.14`; E03 contract fixture | E02/E03 | offline adapter contract implemented; optional live smoke pending safe read-only credential | `backend/tests/integrations/test_keystone_adapter.py`; production PKI gap remains |
| Nova API | read-only instances, hypervisors, compute services, aggregates, server groups | microversion `2.96` | E03/E04 | offline adapter contract implemented; E04 read model/API/UI use synthetic reconciliation evidence; safe live Nova smoke still pending | `backend/tests/integrations/test_nova_adapter.py`, `backend/tests/inventory/test_reconciliation.py`, `docs/generated/e04-scale-report.md`; optional live smoke pending |
| Placement API | read-only resource providers, inventory, usage | microversion `1.39` | E03/E04 | offline adapter contract implemented; enrichment only | `backend/tests/integrations/test_placement_adapter.py`; optional live smoke pending |
| Mistral API v2 | workflow execution and read-only workflow lookup smoke | endpoint `/v2` | E06 | P0 uses `InMemoryMistralAdapter`; optional all-in-one smoke is skipped by default and performs read-only `GET /v2/workflows/{workflow_name}` only | `backend/tests/operations/test_mistral_mock.py`, `backend/tests/operations/test_operation_worker.py`, `backend/tests/integrations/test_mistral_live_smoke.py`, `docs/generated/e06-mistral-smoke.md` |
| Watcher API v1 | goals/strategies/audit templates/audits/continuous audits/action plans/actions/recommendations | endpoint observed | E06+ | E06 P0 exposes portal read/status placeholders with automatic apply disabled; live adapter contract pending | `backend/tests/operations/test_watcher_masakari_api.py`; telemetry datasource freshness tests pending |
| Masakari API | segments/hosts/notifications/recovery state | endpoint observed | E06+ | E06 P0 exposes portal read/status placeholders with approval/conflict/processmonitor markers; live adapter contract pending | `backend/tests/operations/test_watcher_masakari_api.py`; hostmonitor Consul matrix and Nova conflict live tests pending |
| Telemetry datasource APIs | metrics for capacity, health, Watcher recommendations and Masakari corroboration | Prometheus exporter-backed path first; Ceilometer/Gnocchi/Aetos pending | E10/P3 | Prometheus endpoints/coverage pending; selected exporters are `openstack-exporter` and `node_exporter` | adapter contracts, freshness/coverage/cardinality tests |
| Heat API | optional stack operations | endpoint observed | optional | reachable via HTTPS service catalog | ADR if included before pilot |
| SIEM API/syslog | audit delivery | ADR-008 | E07 | pending | delivery/heartbeat/failure tests |
| Vault API (SecMan) | secret lifecycle | ADR-009 | E08 | product identified; endpoint/auth/path policy pending | contract, rotation runbook |

## DKB-77 position

This file is only documentation evidence. ДКБ-77 also requires technical blocking: Kolla service enablement, firewall/ACL, HAProxy routing, OpenStack policy deny and disabled unused endpoints. Those controls are E08/E09/E12 evidence.

E06 implements `/api/v1/operations*`, `/api/v1/workflow-definitions`, P0 Watcher/Masakari read/status
endpoints and optional read-only Mistral smoke behind the portal BFF/API boundary. E05 implements
`/api/v1/groups*` and `group_id` filters for `/api/v1/instances` and `/api/v1/hypervisors`. Service
health, topology and capacity modules are not silently linked: E04 exposes explicit disabled
descriptors until adapters, policies and tests exist. Search remains a planned E04+/E10 API row and is
not enabled in the UI.

Inventory API source of truth is the portal read model populated from OpenStack APIs and reconciliation. Group membership is portal-owned MariaDB metadata and does not mutate OpenStack placement constructs. Synthetic E04/E05 evidence uses deterministic sources and local SQLite; production MariaDB, live Nova comparison and HA/load evidence remain separate gates. Telemetry APIs are enrichment sources and must not be used as inventory authority.

## Current endpoint observations

Post-baseline lab update on 2026-06-19:

- Public/internal endpoints use HTTPS on `192.168.10.250` after Kolla TLS enablement and `post-deploy`.
- OpenStack CLI authenticates through `/etc/kolla/admin-openrc.sh` with `OS_CACERT=/etc/pki/tls/certs/ca-bundle.crt`.
- Mistral, Watcher and Masakari are registered in Keystone service catalog.
- This satisfies lab reachability for E06 discovery, but production PKI/mTLS and service-specific contract tests remain pending.
