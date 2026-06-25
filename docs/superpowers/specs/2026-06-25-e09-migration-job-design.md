# E09.4 Migration Job Design

## Goal

E09.4 adds a repository-side, tested migration job contract for Kolla deployment. Operators get a
separate one-shot `cloud-ui db-upgrade` path that is ordered before permanent API, worker, events and
frontend rollout. The slice does not run live migration on the lab stand; it prepares the contract and
evidence needed for a later approved deploy/reconfigure run.

## Selected Approach

Use the existing backend image and CLI entrypoint `cloud-ui db-upgrade`. The Kolla role will describe
`cloud_ui_db_migrate` as a one-shot job definition and keep it outside `cloud_ui_services`, so it
cannot count as one of the four permanent containers per node. The role will publish explicit
execution policy fields for precheck, lock, retry, log path and API-auto-migration prohibition.

## Components

- Backend CLI: keep `cloud-ui db-upgrade` as the only application migration command. Add a precheck
  mode if needed by tests, but do not make API startup run Alembic.
- Kolla role defaults: add non-secret migration job metadata using the backend image, the backend
  config directory and a `restart_policy: no` one-shot shape.
- Kolla role tasks: add `migration.yml` between config rendering and permanent container definition
  publishing. It publishes a migration job definition and execution policy, but does not execute a
  live remote migration unless the operator explicitly enables it in a later deployment run.
- Evidence: create `docs/generated/e09-migration-job.md`, update traceability and risk register.

## Data Flow

The job consumes the same backend runtime config and the migration MariaDB credential provisioned in
E09.3. The migration credential remains a Vault/SecMan material concern and is not written to Git.
The API process starts separately with `cloud-ui api`; it must not call Alembic during startup.

## Error Handling

The contract is fail-closed: mutable image tags remain rejected, the migration job uses the backend
image only, and validation rejects putting `cloud-ui db-upgrade` into permanent services. The
execution policy records a required lock, one-shot semantics, retry limits and log path. Live failure
and retry evidence remains pending until the approved test deployment run.

## Testing

Tests will assert that:

- the migration job is defined with the backend image and `cloud-ui db-upgrade`;
- the job is not part of permanent `cloud_ui_services`;
- `migration.yml` is imported before `containers.yml`;
- the role records lock, precheck, retry and log policy;
- the backend API path does not invoke Alembic migration commands;
- generated evidence and DKB traceability state the lab-only scope and remaining live-deploy gaps.

## Scope Boundaries

This design does not execute live migration on `192.168.10.15` or mutate the MariaDB schema. It does
not add HAProxy/TLS, process containers, three-node rollout, registry digest proof, image signing,
SELinux inspection or rollback execution. Those remain later E09 slices.
