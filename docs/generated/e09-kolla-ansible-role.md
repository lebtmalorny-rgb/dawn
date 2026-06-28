# E09.2 Kolla-Ansible Role Evidence

- Stage: E09.2 Ansible role skeleton
- Date: 2026-06-24
- Scope: repository-side role skeleton for Cloud UI Kolla-Ansible integration, plus default-off AIO live mode
- Live deployment: partial all-in-one role evidence collected on 2026-06-28
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
- secret-backed runtime URL inputs `cloud_ui_database_url` and `cloud_ui_rabbitmq_url`, with
  `cloud_ui_secret_references` documenting the expected Vault/SecMan lab paths;
- config templates for backend environment and frontend nginx runtime config; the backend template
  writes `CLOUD_UI_DATABASE_URL` and `CLOUD_UI_RABBITMQ_URL` from runtime variables and uses
  `no_log: true`;
- handler names for later restart integration;
- `cloud_ui_container_definitions` fact data for later Kolla-Ansible container tasks.

No Kolla-Ansible inventory, remote host, registry credential, runtime secret value, DB/MQ credential
value or certificate was added. The role fails closed when `cloud_ui_enabled` is true and the DB/MQ
runtime URLs are not supplied by the approved secret mechanism.

## AIO Live Role Mode

`playbooks/cloud-ui-aio-reconfigure.yml` enables a bounded all-in-one lab path by setting
`cloud_ui_aio_live_reconfigure_enabled=true` and applying the `cloud_ui` role only to
`openstack-aio`. The normal role default remains `cloud_ui_aio_live_reconfigure_enabled=false`.

The AIO path uses `tasks/live-aio.yml` and `community.docker` modules through the Kolla-Ansible
virtual environment. It creates the `cloud-ui` Docker network, ensures the `kolla_logs` volume/log
directories, optionally runs one-shot `cloud-ui db-upgrade --check` and `cloud-ui db-upgrade`
containers, and converges
`cloud_ui_frontend`, `cloud_ui_api`, `cloud_ui_worker` and `cloud_ui_events`.

Live AIO evidence collected on 2026-06-28:

- preflight playbook recap: `localhost : ok=10 changed=0 failed=0`;
- AIO role reconfigure recap: `openstack-aio : ok=35 changed=6 failed=0 skipped=1`;
- AIO idempotency recap with `cloud_ui_aio_run_migration=false`: `openstack-aio : ok=34 changed=0
  failed=0 skipped=2`;
- post-role API readiness HTTP 200 with DB/RabbitMQ reachable;
- post-role frontend `/api/v1/session` HTTP 401 through the frontend;
- sanitized Docker inspect for all four containers confirmed `cloudui`, `readonly=true`,
  `cap_drop=["ALL"]` and `security_opt=["no-new-privileges:true"]`.

The follow-up AIO Kolla CLI path uses `deploy/kolla/scripts/run-cloud-ui-aio-kolla.py` to invoke the
same custom playbook through `kolla-ansible reconfigure -p ... -t cloud-ui`. On 2026-06-28 the Kolla
CLI preflight completed with `localhost : ok=10 changed=0 failed=0`; the Kolla CLI
`reconfigure` run completed with `openstack-aio : ok=36 changed=2 failed=0 skipped=1`; and the
follow-up `reconfigure-no-migration` run completed with `openstack-aio : ok=34 changed=0 failed=0
skipped=3`.
This is still partial all-in-one lab evidence. It does not prove upstream Kolla `site.yml` service
integration, HAProxy/VIP/TLS, SELinux labels, three-node/twelve-container rollout, corporate registry
policy or failed-update rollback.

## External Evidence Status

| Evidence | Status | Reason |
|---|---|---|
| corporate test registry digest pull | pending_external_evidence | Requires an approved registry flow with immutable image digests from E09.1 artifacts. |
| SBOM tied to deployed digests | pending_external_evidence | Requires approved SBOM tooling against the exact backend/frontend digests used by the stand. |
| vulnerability scan | pending_external_evidence | Requires approved scanner output and policy threshold for the deployed images. |
| image signature verification | pending_external_evidence | Requires approved signing keys and pull-time verification policy. |
| Kolla-Ansible syntax/render against test inventory | partial_lab_evidence | AIO preflight and Kolla CLI custom playbook path run against `/etc/kolla/all-in-one`; full upstream `site.yml` integration remains pending. |
| live Kolla-Ansible deploy/reconfigure | partial_lab_evidence | AIO Kolla CLI custom playbook path converges four all-in-one containers. Three-node/twelve-container rollout and upstream `site.yml` path remain pending. |
| MariaDB schema/user and RabbitMQ vhost/user provisioning | pending_external_evidence | Later E09 slices own database, broker and secret integration. |
| one-shot `cloud-ui db-upgrade` migration ordering | partial_lab_evidence | E09.4 adds `cloud_ui_db_migrate` job metadata outside the permanent container set; the AIO Kolla CLI path executed precheck before migration and can skip both one-shot tasks for repeat convergence with `cloud_ui_aio_run_migration=false`. |
| HAProxy/TLS routing | pending_external_evidence | Requires Kolla TLS/HAProxy configuration and certificate evidence. |
| SELinux labels and host enforcement proof | pending_external_evidence | Requires Rocky/Kolla host inspection. |
| 12-container topology contract | completed_repository_evidence | E09.5 adds synthetic three-node process topology for 12 permanent containers. |
| 12 live containers on three control/UI nodes | pending_external_evidence | AIO evidence covers four containers on one node only. |
| rollback/reconfigure execution | partial_lab_evidence | AIO rollback snapshot, reconfigure and idempotency evidence exist; failed-update rollback remains pending. |

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
  MariaDB/RabbitMQ credentials and rotation evidence remain later deployment work. The role now
  records `cloud_ui_secret_references` and renders `CLOUD_UI_DATABASE_URL`/`CLOUD_UI_RABBITMQ_URL`
  only from runtime variables with `no_log: true`; no runtime secret value is committed.
- ДКБ-82: AIO rollback snapshot, migration-enabled Kolla CLI reconfigure and role idempotency
  evidence now exist for one test node. Failed update rollback, rolling upgrade and three-node
  acceptance remain later E09 evidence.

## AIO Role Evidence Update

The 2026-06-28 all-in-one role run narrows ДКБ-65/69/70/76/77/80/82 by proving a default-off role
path can converge the current lab UI without manual Docker replacement. The follow-up Kolla CLI path
uses `kolla-ansible reconfigure -p` for the same bounded AIO playbook and has live preflight,
migration, idempotency, endpoint and hardening evidence. Full E09 acceptance remains blocked until the approved
stand proves upstream `site.yml` integration, the three-node layout, HAProxy/VIP/TLS, SELinux labels,
corporate registry policy, formal ДКБ-69 waiver and failed-update rollback.

## E09.4 Update

E09.4 extends this role with `deploy/kolla/ansible/roles/cloud_ui/tasks/migration.yml` and
`cloud_ui_migration_job` defaults. The migration job uses `cloud-ui db-upgrade`, remains outside
`cloud_ui_services`, and preserves the four-permanent-containers-per-node contract. The AIO Kolla CLI
path now has live migration precheck and upgrade evidence; three-node migration, failure logs and
failed-rollback proof remain pending.

## E09.5 Update

E09.5 extends this role with `cloud_ui_process_topology`, `cloud_ui_control_ui_nodes` and topology
summary facts. The role now records the expected three-node, twelve-permanent-container layout while
keeping `cloud_ui_db_migrate` outside the permanent set. This is synthetic repository evidence only;
live container inspection remains pending.

## Rollback

Revert the E09.2 role skeleton commits. This slice changes only repository files and does not modify a
database schema, queue state, registry contents, remote hosts, Vault paths, Kolla inventory or
production credentials.
