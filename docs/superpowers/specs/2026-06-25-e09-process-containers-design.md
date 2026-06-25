# E09.5 Process Containers Design

## Goal

E09.5 adds a repository-side and synthetic evidence contract for the permanent Cloud UI process
topology: one frontend, API, worker and events container on each of three control/UI nodes, for twelve
permanent containers total. The slice does not deploy containers on the lab stand; it proves the role
can describe the expected topology without adding images, leaking secrets or including the migration
job in the permanent set.

## Selected Approach

Use the existing `cloud_ui_services` definitions as the source of truth for the four permanent process
types and add a deterministic topology matrix derived from three node labels. The role publishes
`cloud_ui_process_topology` and summary counts as facts for later Kolla deployment tasks. The
repository evidence records the matrix as synthetic proof, while all live Kolla container inspection
remains pending for E09.7/E09.8.

## Components

- Kolla role defaults: add `cloud_ui_control_ui_nodes`, expected node/service/container counts and a
  `cloud_ui_process_topology` list with twelve entries.
- Kolla role container task: publish `cloud_ui_process_topology`, `cloud_ui_process_topology_summary`
  and existing `cloud_ui_container_definitions`.
- Validation: assert three expected nodes, four permanent services per node and twelve total
  permanent containers. Keep `cloud_ui_db_migrate` outside this topology.
- Evidence: add `docs/generated/e09-process-containers.md`, update traceability and risk register.

## Data Flow

Frontend uses the frontend image and nginx command. API, worker and events use the single backend
image with different commands and the same backend config directory. Migration remains a separate
one-shot job from E09.4 and is not part of `cloud_ui_process_topology`.

## Error Handling

The role fails closed if the expected count is not three nodes, four services per node or twelve
permanent containers total. Image tags still reject `latest`. The process topology does not include
secrets, production inventory names, registry credentials or live host output.

## Testing

Tests will assert:

- `cloud_ui_process_topology` contains exactly twelve entries for three nodes and four services;
- API, worker and events all use `cloud-ui-backend` with different commands;
- frontend uses `cloud-ui-frontend`;
- migration job is not included in permanent process topology;
- topology facts are published from `containers.yml`;
- generated evidence and traceability explicitly avoid live deployment claims.

## Scope Boundaries

This design does not start containers, create Kolla inventory, configure HAProxy/TLS, inspect SELinux
labels, validate image digests, run smoke tests through a URL or execute rollback. Those remain later
E09 slices.
