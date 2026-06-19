# API register

- Stage: E00
- DKB: ДКБ-77 draft register
- Status: planned interfaces, not blocking evidence yet

## Portal API

All portal APIs use prefix `/api/v1`, JSON UTF-8, UTC timestamps, server-side session cookie and correlation/request ID. Mutating APIs require CSRF and `Idempotency-Key` where applicable.

| API | Purpose | Consumer | Auth | Stage | Audit | Blocking/disable mechanism |
|---|---|---|---|---|---|---|
| `GET /health/live` | process liveness | HAProxy/Kolla | none/internal route policy | E01 | no | HAProxy/internal routing |
| `GET /health/ready` | dependency readiness | HAProxy/Kolla | none/internal route policy | E01 | no | HAProxy/internal routing |
| `GET /session` | current session | frontend | session cookie | E02 | access/session events | route disabled until E02 |
| `POST /session/login` | login start/mock/test flow | frontend | flow-specific | E02 | login success/failure | production mock hard-disabled |
| `POST /session/logout` | logout | frontend | session+CSRF | E02 | logout | route disabled until E02 |
| `GET /session/active` | active UI sessions | frontend | session+capability | E02 | protected access | capability `session.manage` |
| `DELETE /session/active/{session_id}` | revoke session | frontend | session+CSRF+capability | E02 | revoke | capability `session.manage` |
| `GET /capabilities` | effective portal permissions | frontend | session | E02 | optional protected access | route disabled until E02 |
| `GET /instances` | paged instance list | frontend | session+capability | E04 | aggregate inventory read policy | capability `instance.read` |
| `GET /instances/{cloud_id}/{region_id}/{instance_id}` | instance detail | frontend | session+capability+scope | E04 | protected access policy | capability `instance.read` |
| `POST /instances/{...}/refresh` | targeted refresh | frontend | session+CSRF+capability | E04 | admin refresh | capability `instance.refresh` |
| `GET /hypervisors` | paged hypervisor list | frontend | session+capability | E04 | aggregate inventory read policy | capability `hypervisor.read` |
| `GET /hypervisors/{cloud_id}/{region_id}/{hypervisor_id}` | hypervisor detail | frontend | session+capability+scope | E04 | protected access policy | capability `hypervisor.read` |
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
| `GET /audit/events` | audit search | frontend | session+capability+scope | E07 | audit access audited | capability `audit.read` |
| `GET /audit/events/{event_id}` | audit event detail | frontend | session+capability+scope | E07 | audit access audited | capability `audit.read` |

## External APIs used by portal

| External API | Purpose | Version/microversion | Stage | Status | Evidence required |
|---|---|---|---|---|---|
| Keystone Identity API v3 | auth context, scopes, roles, catalog | observed `v3.14` discovery | E02/E03 | reachable at `https://192.168.10.250:5000` with Kolla CA | contract tests, redaction, production PKI gap |
| Nova API | instances, hypervisors, services, aggregates | microversion pending | E03/E04 | reachable via HTTPS service catalog | microversion smoke, contract fixtures |
| Placement API | resource provider capacity | microversion pending | E03/E04 | reachable via HTTPS service catalog | contract fixtures |
| Mistral API v2 | workflow execution | endpoint `/v2` | E06 | enabled; internal/public endpoint `https://192.168.10.250:8989/v2` | idempotency/lost response tests |
| Watcher API v1 | audit templates/audits/results | endpoint observed | E06+ | enabled; internal/public endpoint `https://192.168.10.250:9322` | contract fixtures |
| Masakari API | segments/hosts/notifications | endpoint observed | E06+ | enabled; internal/public endpoint `https://192.168.10.250:15868` | contract fixtures; monitor/HA-cluster scope decision |
| Heat API | optional stack operations | endpoint observed | optional | reachable via HTTPS service catalog | ADR if included before pilot |
| SIEM API/syslog | audit delivery | ADR-008 | E07 | pending | delivery/heartbeat/failure tests |
| Vault API (SecMan) | secret lifecycle | ADR-009 | E08 | product identified; endpoint/auth/path policy pending | contract, rotation runbook |

## DKB-77 position

This file is only documentation evidence. ДКБ-77 also requires technical blocking: Kolla service enablement, firewall/ACL, HAProxy routing, OpenStack policy deny and disabled unused endpoints. Those controls are E08/E09/E12 evidence.

## Current endpoint observations

Post-baseline lab update on 2026-06-19:

- Public/internal endpoints use HTTPS on `192.168.10.250` after Kolla TLS enablement and `post-deploy`.
- OpenStack CLI authenticates through `/etc/kolla/admin-openrc.sh` with `OS_CACERT=/etc/pki/tls/certs/ca-bundle.crt`.
- Mistral, Watcher and Masakari are registered in Keystone service catalog.
- This satisfies lab reachability for E06 discovery, but production PKI/mTLS and service-specific contract tests remain pending.
