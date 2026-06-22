# Audit action dictionary

- Stage: E07
- Source: `backend/src/cloud_ui/audit/taxonomy.py`
- Scope: portal audit actions only. External OpenStack, host, storage and IdP actions are mapped in `audit-source-map.md`.

## DKB-49 field mapping

| DKB code | Portal field |
|---|---|
| ДКБ-49.01 | `occurred_at` |
| ДКБ-49.02 | `actor.id`, `actor.display` |
| ДКБ-49.03 | `action` |
| ДКБ-49.04 | `event_type` |
| ДКБ-49.05 | `outcome` |
| ДКБ-49.08 | `target.type`, `target.id` |

## Registered actions

| Action | Event type | Outcomes | Metadata policy | Primary evidence |
|---|---|---|---|---|
| `session.login` | `auth` | `success`, `failure` | allowlisted | `backend/tests/security/test_audit.py` |
| `session.logout` | `auth` | `success` | allowlisted | `backend/tests/security/test_security_api.py` |
| `session.revoke` | `auth` | `success`, `failure` | allowlisted | `backend/tests/security/test_security_api.py` |
| `session.timeout` | `auth` | `failure` | allowlisted | `backend/tests/security/test_sessions.py` |
| `session.limit_reached` | `auth` | `failure` | allowlisted | `backend/tests/security/test_sessions.py` |
| `session.required` | `auth` | `failure` | allowlisted | `backend/tests/security/test_security_api.py` |
| `csrf.denied` | `security_denial` | `failure` | allowlisted | `backend/tests/security/test_security_api.py` |
| `origin.denied` | `security_denial` | `failure` | allowlisted | `backend/tests/security/test_security_api.py` |
| `authorization.denied` | `authorization` | `failure` | allowlisted | `backend/tests/audit/test_audit_api.py` |
| `openstack.denied` | `authorization` | `failure` | allowlisted | `backend/tests/security/test_security_api.py` |
| `instance.refresh.requested` | `inventory` | `success`, `failure` | allowlisted | `backend/tests/inventory/test_inventory_api.py` |
| `group.create` | `group` | `success`, `failure` | allowlisted | `backend/tests/groups/test_group_api.py` |
| `group.update` | `group` | `success`, `failure` | allowlisted | `backend/tests/groups/test_group_api.py` |
| `group.delete` | `group` | `success`, `failure` | allowlisted | `backend/tests/groups/test_group_api.py` |
| `group.member.add` | `group` | `success`, `failure` | allowlisted | `backend/tests/groups/test_group_api.py` |
| `group.member.remove` | `group` | `success`, `failure` | allowlisted | `backend/tests/groups/test_group_api.py` |
| `group.preview` | `group` | `success`, `failure` | allowlisted | `backend/tests/groups/test_group_api.py` |
| `operation.accepted` | `operation` | `success` | allowlisted | `backend/tests/operations/test_operation_api.py` |
| `operation.dispatched` | `operation` | `success`, `unknown`, `failure` | allowlisted | `backend/tests/operations/test_operation_worker.py` |
| `operation.completed` | `operation` | `success`, `failure`, `unknown` | allowlisted | `backend/tests/operations/test_operation_worker.py` |
| `operation.cancelled` | `operation` | `success`, `failure` | allowlisted | route is fail-closed in E06 P0; live cancel evidence pending |
| `watcher.view` | `openstack_module` | `success`, `failure` | allowlisted | `backend/tests/operations/test_watcher_masakari_api.py` |
| `masakari.view` | `openstack_module` | `success`, `failure` | allowlisted | `backend/tests/operations/test_watcher_masakari_api.py` |
| `audit.events.list` | `audit_access` | `success`, `failure` | allowlisted | `backend/tests/audit/test_audit_api.py` |
| `audit.event.detail` | `audit_access` | `success`, `failure` | allowlisted | `backend/tests/audit/test_audit_api.py` |
| `audit.export.requested` | `audit_access` | `success`, `failure` | allowlisted | `backend/tests/audit/test_audit_api.py`, `frontend/src/App.test.tsx` |
| `audit.delivery.failed` | `audit_delivery` | `failure` | allowlisted | `backend/tests/audit/test_delivery_worker.py` |
| `audit.delivery.recovered` | `audit_delivery` | `success` | allowlisted | `backend/tests/audit/test_delivery_worker.py` |
| `audit.delivery.heartbeat` | `audit_delivery` | `success`, `failure`, `unknown` | allowlisted | `backend/tests/audit/test_heartbeat.py` |

## Notes

- Unknown action names fail closed through `UnknownAuditAction`.
- Delivery payloads use `AuditEvent.to_delivery_envelope()` and are sanitized before storage and delivery.
- `audit.export.requested` accepts and audits a bounded export request only; E07 does not write CSV/files with audit content.
