# E09.4 Migration Job Evidence

- Stage: E09.4 Migration job
- Date: 2026-06-25
- Scope: repository-side one-shot migration job contract
- Live migration execution: not executed in this slice
- Production action: none

## Repository Contract

The Kolla role now defines a separate one-shot migration job named `cloud_ui_db_migrate`.

| Field | Value |
|---|---|
| Image | `cloud-ui-backend` through `{{ cloud_ui_backend_image_full }}` |
| Command | `cloud-ui db-upgrade` |
| Precheck command | `cloud-ui db-upgrade --check` |
| Config directory | `cloud-ui-backend` |
| Restart policy | `no` |
| Permanent service membership | absent from `cloud_ui_services` |

The job preserves the E09 two-image contract: migration uses the backend image and does not introduce
a third image. It is intentionally separate from API, worker and events containers.

## Execution Policy

| Control | Status |
|---|---|
| one-shot semantics | recorded with `run_once: true` |
| lock | required before live execution |
| precheck | required before upgrade |
| retry policy | `max_attempts: 1`, no blind retry |
| rollback window | required before contract migration |
| API auto migration | disabled; API startup does not run Alembic upgrade |
| sanitized CLI output | `cloud-ui db-upgrade` prints revision only, not database URL or credentials |

Live failure/retry logs, lock acquisition output and copied-data downgrade proof remain
`pending_external_evidence` because the migration was not executed against the lab MariaDB schema in
this slice.

## External Evidence Status

| Evidence | Status | Reason |
|---|---|---|
| repository migration job contract | completed_repository_evidence | Role defaults/tasks define `cloud_ui_db_migrate` and execution policy. |
| API no-auto-migration test | completed_repository_evidence | CLI tests prove `cloud-ui api` does not call Alembic upgrade. |
| live `cloud-ui db-upgrade` execution | pending_external_evidence | Requires explicit approval for lab DB schema mutation. |
| failed migration retry/log evidence | pending_external_evidence | Requires an approved deployment run with controlled failure. |
| migration rollback on copied data | pending_external_evidence | Required before production contract migration claim. |
| three-node rollout ordering | pending_external_evidence | Owned by later E09 process-container and reconfigure slices. |

## DKB Impact

- ДКБ-55/56: migration material remains tied to the E09.3 Vault/SecMan-backed migration credential.
  This slice stores no credential in Git and does not print database URLs in CLI success output.
- ДКБ-69/70: the migration job uses the existing backend image and keeps the two-image deployment
  contract. Registry digest, scanner, signing and package provenance proof remain pending.
- ДКБ-76/77/80: the deployment interface now documents migration ordering and API no-auto-migration.
  Network ACL, management-zone and unused-interface evidence remain pending.
- ДКБ-82: rollback is repository-only in this slice. Live rollback, copied-data downgrade and failed
  update rollback remain pending.

## Safe Next Step

E09.5 can wire process containers while keeping the migration job as a separate pre-rollout step.
Live migration should be executed only after an approved lab run plan confirms backup/precheck,
advisory lock, sanitized logs and rollback window.
