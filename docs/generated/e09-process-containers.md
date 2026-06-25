# E09.5 Process Containers Evidence

- Stage: E09.5 Process containers
- Date: 2026-06-25
- Scope: synthetic repository evidence for permanent Cloud UI process topology
- Live deployment: not executed in this slice
- Production action: none

## Topology Contract

E09.5 records the expected topology for 3 control/UI nodes and 12 permanent containers:

| Node | Permanent processes |
|---|---|
| `control-ui-01` | `cloud_ui_frontend`, `cloud_ui_api`, `cloud_ui_worker`, `cloud_ui_events` |
| `control-ui-02` | `cloud_ui_frontend`, `cloud_ui_api`, `cloud_ui_worker`, `cloud_ui_events` |
| `control-ui-03` | `cloud_ui_frontend`, `cloud_ui_api`, `cloud_ui_worker`, `cloud_ui_events` |

The role publishes `cloud_ui_process_topology_effective` and
`cloud_ui_process_topology_summary` for later Kolla deployment tasks. This is synthetic repository
evidence, not live container inspection.

## Image and Process Mapping

| Process | Service | Image contract | Command |
|---|---|---|---|
| frontend | `cloud_ui_frontend` | `cloud-ui-frontend` | `nginx -g 'daemon off;'` |
| API | `cloud_ui_api` | `cloud-ui-backend` | `cloud-ui api` |
| worker | `cloud_ui_worker` | `cloud-ui-backend` | `cloud-ui worker` |
| events | `cloud_ui_events` | `cloud-ui-backend` | `cloud-ui events` |

API, worker and events use the same backend image with different commands/config roles. The
`cloud_ui_db_migrate` one-shot job is not part of the permanent topology and is not counted in the
12 permanent containers.

## External Evidence Status

| Evidence | Status | Reason |
|---|---|---|
| 3x4 process topology contract | completed_repository_evidence | Defaults declare three synthetic nodes and twelve permanent entries. |
| two-image process mapping | completed_repository_evidence | Tests verify frontend/backend image mapping and distinct backend commands. |
| migration excluded from permanent containers | completed_repository_evidence | Tests verify `cloud_ui_db_migrate` is absent from permanent topology. |
| 12 live containers on test nodes | pending_external_evidence | Requires approved Kolla deploy/reconfigure and container inspection. |
| image digest pull | pending_external_evidence | Requires approved registry digests and pull evidence. |
| non-root/caps/mounts/SELinux inspection | pending_external_evidence | Requires live host/container inspection. |
| HAProxy/TLS URL smoke | pending_external_evidence | Owned by E09.6/E09.8. |

## DKB Impact

- ДКБ-69/70: E09.5 preserves the two-image contract and records process-to-image mapping. Registry
  digest pull, scanner, signature/provenance evidence and the ДКБ-69 Python interpreter waiver remain
  pending.
- ДКБ-76/77/80: E09.5 documents permanent deployment interfaces and expected process placement.
  Network ACL, management-zone, unused-interface blocking, HAProxy/TLS and live container inspection
  remain pending.
- ДКБ-82: repository rollback is a Git revert. Live reconfigure, rolling update and failed-update
  rollback remain later E09 evidence.

## Safe Next Step

E09.6 can add HAProxy/TLS/network route contracts while using this topology as the expected backend
pool shape. It must not claim live 12-container proof until a later deploy/reconfigure run inspects
actual containers on the test nodes.
