# Audit source map

- Stage: E07
- Status vocabulary: `implemented_by_portal`, `lab_contract_only`, `external_required`, `not_in_scope`.
- Purpose: show which audit sources E07 implements and which sources remain outside the portal boundary. This document is evidence for ДКБ-46-53 analysis, not a compliance closure.

## Portal-owned sources

| Source | Status | Covered events | Evidence | Residual condition |
|---|---|---|---|---|
| Portal auth/session/RBAC | implemented_by_portal | login, logout, timeout, revoke, session required, session limit, CSRF/origin/authorization denial | `backend/tests/security/test_audit.py`, `backend/tests/security/test_security_api.py`, `backend/tests/security/test_sessions.py` | Production federation/IdP evidence remains external. |
| Portal inventory refresh contract | implemented_by_portal | `instance.refresh.requested`, authorization denial | `backend/tests/inventory/test_inventory_api.py` | No Nova mutation in E07. |
| Portal resource groups | implemented_by_portal | group create/update/delete/member/preview success and denial | `backend/tests/groups/test_group_api.py` | P0 mock scope is not production IAM evidence. |
| Portal operations/workflow | implemented_by_portal | operation accepted/dispatched/completed, worker attempt state, idempotency metadata | `backend/tests/operations/test_operation_api.py`, `backend/tests/operations/test_operation_worker.py` | Mistral production workflow execution remains gated by E08/E09 evidence. |
| Portal Watcher/Masakari status views | implemented_by_portal | protected read/status access and denial | `backend/tests/operations/test_watcher_masakari_api.py` | Live adapters and service audit integration pending. |
| Portal audit search/detail/export access | implemented_by_portal | `audit.events.list`, `audit.event.detail`, `audit.export.requested` | `backend/tests/audit/test_audit_api.py`, `frontend/src/App.test.tsx` | Export request is accepted only; file generation is not in E07. |
| Portal audit durable outbox | implemented_by_portal | stored event, outbox row, replay idempotency, delivery state | `backend/tests/audit/test_audit_repository.py`, `backend/tests/audit/test_durable_sink.py` | Existing E02-E06 audit calls remain route-level side effects until later targeted refactors. |
| Portal audit delivery worker | implemented_by_portal | success, retry, dead-letter, heartbeat, recovery state | `backend/tests/audit/test_delivery_worker.py`, `backend/tests/audit/test_heartbeat.py` | E07 local/test sink does not prove production SIEM retention or mTLS. |
| Local test audit sink | implemented_by_portal | acked envelopes, temporary/permanent failure modelling | `backend/tests/audit/test_sinks.py` | Test double only. |

## Lab and contract-only sources

| Source | Status | Covered events | Evidence | Residual condition |
|---|---|---|---|---|
| Fluentd HTTP payload contract | lab_contract_only | sanitized JSON wrapper with `tag`, `time`, `record` | `backend/tests/audit/test_sinks.py`, `docs/generated/e07-fluentd-opensearch-lab.md` | Unit contract only; live HTTP delivery not executed in E07 without explicit approval. |
| All-in-one Kolla Fluentd container | lab_contract_only | observed Kolla `fluentd` container presence | `docs/generated/e07-fluentd-opensearch-lab.md` | Kolla central logging and OpenSearch are currently disabled. |
| All-in-one OpenSearch/OpenSearch Dashboards | lab_contract_only | manual runbook target for sanitized smoke query | `docs/generated/e07-fluentd-opensearch-lab.md` | Not deployed by E07 code; requires manual Kolla change on test stand. |

## External sources required for full ДКБ-50

| Source | Status | Required event families | Evidence owner | Residual condition |
|---|---|---|---|---|
| Keystone CADF/audit notifications | external_required | auth, federation, user/group/role/application credential changes | OpenStack/IAM owner | Must be enabled and delivered to SIEM with user and request correlation. |
| Nova notifications/API audit | external_required | VM create/delete/start/stop/evacuate/live migration, compute service changes | OpenStack owner | Direct libvirt/host actions need host audit too. |
| Neutron notifications/API audit | external_required | networks, routers, ports, security groups and network segment changes | OpenStack owner | OVS/OVN direct changes need host/network audit. |
| Glance notifications/API audit | external_required | image create/update/delete/import/copy | OpenStack/storage owner | Storage backend access must be audited separately. |
| Cinder notifications/API audit | external_required | volume/snapshot/backup operations | OpenStack/storage owner | Backend storage copy/delete is outside portal evidence. |
| Mistral engine/API audit | external_required | workflow executions, state transitions, action errors | Workflow/platform owner | E07 only records portal operation state and mock adapter events. |
| Watcher service audit | external_required | goals/strategies/audit templates/audits/action plans/actions | OpenStack owner | E07 status views are not service audit. |
| Masakari service audit | external_required | segments, hosts, notifications, recovery workflow state | OpenStack owner | Hostmonitor/Consul matrix evidence remains later. |
| HAProxy/API access logs | external_required | management/API access, source IP/proxy chain, request IDs | Platform owner | Must avoid tokens and request bodies. |
| Kolla/container runtime events | external_required | container start/stop/restart, image changes, config mount changes | Platform owner | Required for ДКБ-48 and ДКБ-50.17. |
| systemd/sudo/PAM/auditd/FIM | external_required | admin shell, config change, service stop, file integrity change | Security/platform owner | Portal cannot prevent root disabling logging. |
| libvirt/QEMU/OVS/OVN logs | external_required | hypervisor/network actions outside OpenStack API | Platform/OpenStack owner | Needed for virtualization component actions. |
| Monitoring/alerting | external_required | component unavailability, missing audit flow, queue age alerts | Monitoring owner | Portal heartbeat is only one signal. |
| SIEM storage/RBAC/retention | external_required | authoritative audit retention and controlled read/export | SIEM/security owner | MariaDB portal audit is not immutable SIEM. |
| IdP/IAM audit | external_required | MFA, federation policy, group membership and role source changes | IAM owner | Required when identity lives outside Keystone. |
| Storage/backup audit | external_required | backup, restore, storage-side copy/delete and admin access | Storage/backup owner | Required for ДКБ-72-related evidence. |

## Explicitly not in portal scope

| Source | Status | Reason |
|---|---|---|
| Guest OS user audit inside tenant VMs | not_in_scope | Portal can correlate VM/resource actions, but guest authentication and business logs are tenant/guest controls unless a separate requirement brings them into scope. |
| Direct DB/index/log-file read by administrators | not_in_scope | Application-layer `audit.read`/`audit.export` is implemented, but direct root/DB/SIEM index access is governed by external PAM/DB/SIEM controls. |
