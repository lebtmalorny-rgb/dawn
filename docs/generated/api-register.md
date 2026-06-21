# API register

- Stage: E02
- DKB: ДКБ-77 draft register
- Status: E02 P0 session/capability endpoints implemented; remaining inventory/workflow/audit APIs are planned interfaces, not blocking evidence yet

## Portal API

All portal APIs use prefix `/api/v1`, JSON UTF-8, UTC timestamps, server-side session cookie and correlation/request ID. Mutating APIs require CSRF and `Idempotency-Key` where applicable.

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
| `GET /instances` | paged instance list | frontend | session+capability | E04 | aggregate inventory read policy | capability `instance.read` |
| `GET /instances/{cloud_id}/{region_id}/{instance_id}` | instance detail | frontend | session+capability+scope | E04 | protected access policy | capability `instance.read` |
| `POST /instances/{...}/refresh` | targeted refresh | frontend | session+CSRF+capability | E04 | admin refresh | capability `instance.refresh` |
| `GET /hypervisors` | paged hypervisor list | frontend | session+capability | E04 | aggregate inventory read policy | capability `hypervisor.read` |
| `GET /hypervisors/{cloud_id}/{region_id}/{hypervisor_id}` | hypervisor detail | frontend | session+capability+scope | E04 | protected access policy | capability `hypervisor.read` |
| `GET /compute-services` | paged Nova compute service health | frontend | session+capability | E04+ | aggregate health read policy | capability `service-health.read` |
| `GET /network-agents` | paged Neutron agent health | frontend | session+capability | E04+ | aggregate health read policy | capability `service-health.read` |
| `GET /volume-services` | paged Cinder service health | frontend | session+capability | E04+ | aggregate health read policy | capability `service-health.read` |
| `GET /image-tasks` | paged Glance image task status | frontend | session+capability | E04+ | protected access policy | capability `image-task.read` |
| `GET /topology` | bounded topology/dependency graph page | frontend | session+capability+scope | E04+/E10 | protected access policy | capability `topology.read` |
| `GET /capacity/summary` | aggregated capacity dashboard data | frontend | session+capability+scope | E04+/E10 | aggregate read policy | capability `capacity.read` |
| `GET /capacity/timeseries` | downsampled metric series | frontend | session+capability+scope | E10 | aggregate read policy | capability `capacity.read` |
| `GET /search` | global capability-aware search | frontend | session+capability+scope | E04+/E10 | protected access policy | capability `search.read` |
| `GET /resource-groups` | group list | frontend | session+capability | E05 | group read policy | capability `group.read` |
| `POST /resource-groups` | create group | frontend | session+CSRF+capability | E05 | group create | capability `group.manage` |
| `GET /resource-groups/{group_id}` | group detail | frontend | session+capability+scope | E05 | group read | capability `group.read` |
| `PATCH /resource-groups/{group_id}` | update group | frontend | session+CSRF+capability+revision | E05 | group update | capability `group.manage` |
| `DELETE /resource-groups/{group_id}` | delete group | frontend | session+CSRF+capability | E05 | group delete | capability `group.manage` |
| `POST /resource-groups/{group_id}/members` | add members | frontend | session+CSRF+capability | E05 | membership update | capability `group.manage` |
| `DELETE /resource-groups/{group_id}/members/{member_id}` | remove member | frontend | session+CSRF+capability | E05 | membership update | capability `group.manage` |
| `POST /resource-groups/{group_id}/preview` | preview dynamic rule | frontend | session+CSRF+capability | E05 | group preview | capability `group.read` |
| `GET /workflow-definitions` | workflow catalog | frontend | session+capability | E06 | catalog read policy | capability `workflow.read` |
| `GET /workflow-definitions/{workflow_key}/versions/{version}` | workflow definition | frontend | session+capability | E06 | catalog read policy | capability `workflow.read` |
| `POST /workflow-definitions/{workflow_key}/validate-input` | validate input | frontend | session+CSRF+capability | E06 | validation event if protected | capability `workflow.execute.*` |
| `POST /operations` | submit operation | frontend | session+CSRF+capability+idempotency | E06 | operation accepted/denied | capability `workflow.execute.*` |
| `GET /operations` | operation list | frontend | session+capability+scope | E06 | protected access policy | capability `operation.read` |
| `GET /operations/{operation_id}` | operation status | frontend | session+capability+scope | E06 | protected access policy | capability `operation.read` |
| `POST /operations/{operation_id}/cancel` | cancel operation | frontend | session+CSRF+capability | E06 | cancel request | capability `operation.cancel` |
| `POST /operations/{operation_id}/retry` | retry operation | frontend | session+CSRF+capability | E06 | retry request | capability `operation.retry` |
| `GET /events/stream` | SSE live event stream | frontend | session+capability+scope | E06+/E10 | stream subscribe/denial | capability `realtime.stream.read` |
| `GET /events` | polling fallback for live events | frontend | session+capability+scope | E06+/E10 | protected access policy | capability `realtime.stream.read` |
| `GET /operations/{operation_id}/events` | operation timeline events | frontend | session+capability+scope | E06 | protected access policy | capability `operation.read` |
| `GET /watcher/goals` | Watcher goals | frontend | session+capability | E06+ | protected access policy | capability `watcher.read` |
| `GET /watcher/strategies` | Watcher strategies | frontend | session+capability | E06+ | protected access policy | capability `watcher.read` |
| `GET /watcher/audit-templates` | Watcher audit templates | frontend | session+capability | E06+ | protected access policy | capability `watcher.read` |
| `GET /watcher/audits` | Watcher audits and continuous audits | frontend | session+capability+scope | E06+ | protected access policy | capability `watcher.read` |
| `GET /watcher/action-plans` | Watcher action plans | frontend | session+capability+scope | E06+ | protected access policy | capability `watcher.read` |
| `GET /watcher/actions` | Watcher actions | frontend | session+capability+scope | E06+ | protected access policy | capability `watcher.read` |
| `GET /watcher/recommendations` | Watcher recommendations with risk/conflict markers | frontend | session+capability+scope | E06+ | protected access policy | capability `watcher.read` |
| `GET /masakari/segments` | Masakari failover segments | frontend | session+capability+scope | E06+ | protected access policy | capability `masakari.read` |
| `GET /masakari/segments/{segment_id}/hosts` | Masakari segment hosts | frontend | session+capability+scope | E06+ | protected access policy | capability `masakari.read` |
| `GET /masakari/notifications` | Masakari notifications | frontend | session+capability+scope | E06+ | protected access policy | capability `masakari.read` |
| `GET /masakari/recovery-timeline` | HA recovery timeline | frontend | session+capability+scope | E06+ | protected access policy | capability `masakari.read` |
| `GET /audit/events` | audit search | frontend | session+capability+scope | E07 | audit access audited | capability `audit.read` |
| `GET /audit/events/{event_id}` | audit event detail | frontend | session+capability+scope | E07 | audit access audited | capability `audit.read` |

## External APIs used by portal

| External API | Purpose | Version/microversion | Stage | Status | Evidence required |
|---|---|---|---|---|---|
| Keystone Identity API v3 | auth context, scopes, roles, catalog | observed `v3.14` discovery | E02/E03 | reachable at `https://192.168.10.250:5000` with Kolla CA | contract tests, redaction, production PKI gap |
| Nova API | instances, hypervisors, services, aggregates | microversion pending | E03/E04 | reachable via HTTPS service catalog | microversion smoke, contract fixtures |
| Placement API | resource provider capacity | microversion pending | E03/E04 | reachable via HTTPS service catalog | contract fixtures |
| Mistral API v2 | workflow execution | endpoint `/v2` | E06 | enabled; internal/public endpoint `https://192.168.10.250:8989/v2` | idempotency/lost response tests |
| Watcher API v1 | goals/strategies/audit templates/audits/continuous audits/action plans/actions/recommendations | endpoint observed | E06+ | enabled; internal/public endpoint `https://192.168.10.250:9322` | contract fixtures; telemetry datasource freshness tests |
| Masakari API | segments/hosts/notifications/recovery state | endpoint observed | E06+ | enabled; internal/public endpoint `https://192.168.10.250:15868`; Consul-backed hostmonitor path selected but not deployed on current test node | contract fixtures; hostmonitor Consul matrix fixtures; Nova conflict tests |
| Telemetry datasource APIs | metrics for capacity, health, Watcher recommendations and Masakari corroboration | Prometheus exporter-backed path first; Ceilometer/Gnocchi/Aetos pending | E10/P3 | Prometheus endpoints/coverage pending; selected exporters are `openstack-exporter` and `node_exporter` | adapter contracts, freshness/coverage/cardinality tests |
| Heat API | optional stack operations | endpoint observed | optional | reachable via HTTPS service catalog | ADR if included before pilot |
| SIEM API/syslog | audit delivery | ADR-008 | E07 | pending | delivery/heartbeat/failure tests |
| Vault API (SecMan) | secret lifecycle | ADR-009 | E08 | product identified; endpoint/auth/path policy pending | contract, rotation runbook |

## DKB-77 position

This file is only documentation evidence. ДКБ-77 also requires technical blocking: Kolla service enablement, firewall/ACL, HAProxy routing, OpenStack policy deny and disabled unused endpoints. Those controls are E08/E09/E12 evidence.

Inventory API source of truth is the portal read model populated from OpenStack APIs and reconciliation. Telemetry APIs are enrichment sources and must not be used as inventory authority.

## Current endpoint observations

Post-baseline lab update on 2026-06-19:

- Public/internal endpoints use HTTPS on `192.168.10.250` after Kolla TLS enablement and `post-deploy`.
- OpenStack CLI authenticates through `/etc/kolla/admin-openrc.sh` with `OS_CACERT=/etc/pki/tls/certs/ca-bundle.crt`.
- Mistral, Watcher and Masakari are registered in Keystone service catalog.
- This satisfies lab reachability for E06 discovery, but production PKI/mTLS and service-specific contract tests remain pending.
