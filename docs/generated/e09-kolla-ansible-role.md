# E09.2 Kolla-Ansible Role Evidence

- Stage: E09.2 Ansible role skeleton
- Date: 2026-06-24
- Scope: repository-side role skeleton for Cloud UI Kolla-Ansible integration
- Live deployment: not executed in this slice
- Production action: none

## Role Contract

The role skeleton is located at `deploy/kolla/ansible/roles/cloud_ui`.

It declares four permanent Cloud UI services per control/UI node:

| Service | Image contract | Command |
|---|---|---|
| `cloud_ui_frontend` | `cloud-ui-frontend` | `nginx -g 'daemon off;'` |
| `cloud_ui_api` | `cloud-ui-backend` | `cloud-ui api` |
| `cloud_ui_worker` | `cloud-ui-backend` | `cloud-ui worker` |
| `cloud_ui_events` | `cloud-ui-backend` | `cloud-ui events` |

The service layout preserves the E09.1 two-image contract: one frontend image and one backend image.
The API, worker and events processes use the backend image with different commands.

## Repository-Side Skeleton

This evidence covers repository-side role skeleton artifacts only:

- role defaults for service names, groups, images, image tags/digests, ports, volumes and hardening
  dimensions;
- validation tasks that reject `latest` image tags and missing image names;
- non-secret config templates for backend environment and frontend nginx runtime config;
- handler names for later restart integration;
- `cloud_ui_container_definitions` fact data for later Kolla-Ansible container tasks.

No Kolla-Ansible inventory, remote host, registry credential, runtime secret, DB/MQ credential,
certificate or live deployment output was added.

## External Evidence Status

| Evidence | Status | Reason |
|---|---|---|
| corporate test registry digest pull | pending_external_evidence | Requires an approved registry flow with immutable image digests from E09.1 artifacts. |
| SBOM tied to deployed digests | pending_external_evidence | Requires approved SBOM tooling against the exact backend/frontend digests used by the stand. |
| vulnerability scan | pending_external_evidence | Requires approved scanner output and policy threshold for the deployed images. |
| image signature verification | pending_external_evidence | Requires approved signing keys and pull-time verification policy. |
| Kolla-Ansible syntax/render against test inventory | pending_external_evidence | Requires an approved non-production test inventory and host group mapping. |
| live Kolla-Ansible deploy/reconfigure | pending_external_evidence | Requires a test stand with approved registry digests and runtime secrets. |
| MariaDB schema/user and RabbitMQ vhost/user provisioning | pending_external_evidence | Later E09 slices own database, broker and secret integration. |
| one-shot `cloud-ui db-upgrade` migration ordering | completed_repository_evidence | E09.4 adds `cloud_ui_db_migrate` job metadata outside the permanent container set; live execution remains pending. |
| HAProxy/TLS routing | pending_external_evidence | Requires Kolla TLS/HAProxy configuration and certificate evidence. |
| SELinux labels and host enforcement proof | pending_external_evidence | Requires Rocky/Kolla host inspection. |
| 12-container topology contract | completed_repository_evidence | E09.5 adds synthetic three-node process topology for 12 permanent containers. |
| 12 live containers on three control/UI nodes | pending_external_evidence | Requires the deployment stand and container inspection. |
| rollback/reconfigure execution | pending_external_evidence | Requires live deployment state. |

## DKB Impact

- ДКБ-69: the role keeps the two portal-owned images from E09.1 and records container hardening
  dimensions, but the Python backend interpreter conflict remains open and needs a formal waiver plus
  approved scanner/signing evidence.
- ДКБ-70: image names, tags and digest placeholders are wired into role defaults, and `latest` tags are
  rejected. Registry push, digest, SBOM, vulnerability scan and signature evidence remain pending.
- ДКБ-76/77/80: the role documents deployment interfaces and disabled live-deploy scope for later
  Kolla-Ansible integration. Network ACLs, management-zone placement, unused-interface blocking,
  HAProxy/TLS and runtime inspection remain external E09 evidence.
- ДКБ-55/56: this slice stores no secret values. Vault/SecMan delivery, Kolla service credentials,
  MariaDB/RabbitMQ credentials and rotation evidence remain later deployment work.
- ДКБ-82: rollback is repository-only by Git revert in this slice. Live rollback proof remains later
  E09 evidence.

## E09.4 Update

E09.4 extends this role with `deploy/kolla/ansible/roles/cloud_ui/tasks/migration.yml` and
`cloud_ui_migration_job` defaults. The migration job uses `cloud-ui db-upgrade`, remains outside
`cloud_ui_services`, and preserves the four-permanent-containers-per-node contract. This is
repository evidence only; live migration execution, failure logs and rollback proof remain pending.

## E09.5 Update

E09.5 extends this role with `cloud_ui_process_topology`, `cloud_ui_control_ui_nodes` and topology
summary facts. The role now records the expected three-node, twelve-permanent-container layout while
keeping `cloud_ui_db_migrate` outside the permanent set. This is synthetic repository evidence only;
live container inspection remains pending.

## Rollback

Revert the E09.2 role skeleton commits. This slice changes only repository files and does not modify a
database schema, queue state, registry contents, remote hosts, Vault paths, Kolla inventory or
production credentials.
