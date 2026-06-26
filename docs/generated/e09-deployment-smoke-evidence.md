# E09.8 Deployment smoke/evidence

- Stage: E09.8 Deployment smoke/evidence
- Live execution status: `partial_lab_evidence_blocked`
- Scope: `partial` `test-stand`
- Inventory: `/etc/kolla/all-in-one` on `192.168.10.15`; validated from a temporary copy outside the repository
- Backend image: `192.168.10.15:5000/kolla/cloud-ui-backend@sha256:8ff5287ad21048f9f249e4e28f9bd7c3a31b2d345b265a48a7ee03f46d46a822`
- Frontend image: `192.168.10.15:5000/kolla/cloud-ui-frontend@sha256:182debc7d8c13091b29dc37cd422bf5c6a5bdf7d8b2bbff1636b578388c671cb`

## Evidence rows

| Check | Status | Sanitized summary |
|---|---|---|
| scope | partial | test-stand evidence only; production approval absent |
| preflight | passed | User-approved test marker was added to `/etc/kolla/all-in-one` on `192.168.10.15` with a backup on the test host; runner accepted the marker, digest-pinned images and open rollback window. |
| two_images | partial_lab_evidence | Backend and frontend digest refs were found in the local test registry on `192.168.10.15`; registry signing/provenance and deployed pull-by-digest proof remain pending. |
| container count | partial_lab_evidence_blocked | Read-only Ansible inspection found four healthy Cloud UI containers on one all-in-one host: frontend, api, worker and events. E09 requires twelve permanent containers across three test nodes, so acceptance remains blocked. |
| migration | pending_external_evidence | No `cloud_ui_db_migrate` or `cloud-ui db-upgrade` container was found in read-only container history. One-shot migration execution and failure/retry evidence remain pending. |
| DB/RabbitMQ | failed_lab_check | E09.3 DB/RabbitMQ all-in-one provisioning evidence remains separate. Read-only API-container probes on 2026-06-26 reached `192.168.10.14:3306` and `192.168.10.14:5672`, but application-level auth failed: MariaDB returned `1045 Access denied` for `cloud_ui`; RabbitMQ returned `403 ACCESS_REFUSED` on `/cloud-ui`. This points to stale/wrong runtime DB/MQ secret injection or principal permissions, not Keystone RBAC. |
| HAProxy/TLS | pending_external_evidence | No same-origin HAProxy/TLS route smoke was collected in this run. |
| container hardening | failed_lab_check | Containers run as `cloudui`, but read-only root filesystem is `false` and cap/security options are unset in Docker inspect output. SELinux label evidence was not collected. |
| API/UI smoke | partial_lab_evidence_blocked | Frontend test port returned HTTP 200; backend `/api/v1/health/ready` returned HTTP 503. API readiness blocks smoke acceptance. |
| rollback | pending | rollback pending before full E09 acceptance |
| live reconfigure | not_run | Remote Cloud UI custom role/config was not found on the Ansible host, so `kolla-ansible reconfigure --tags cloud-ui` was not run as acceptance evidence. |

## Live discovery on 2026-06-26

The following commands were run only against the approved test stand. No production host, inventory,
credential, private key, cookie, token or full command log is stored in this evidence.

| Item | Result |
|---|---|
| Inventory marker | Added `cloud_ui_test_stand=true` to `/etc/kolla/all-in-one` on `192.168.10.15`; backup was created on that host before the edit. |
| Preflight runner | Passed with digest-pinned backend/frontend images and open rollback window. |
| Remote Cloud UI role/config | Not found under `/etc/kolla`, `/usr/share/kolla-ansible` or the Kolla venv; only the inventory backup matched the Cloud UI file search. |
| Container topology | Four Cloud UI containers observed on `openstack-aio`, not twelve across three nodes. |
| Container health | `cloud_ui_frontend`, `cloud_ui_api`, `cloud_ui_worker` and `cloud_ui_events` were up and Docker-reported healthy. |
| Container hardening | `user=cloudui`; `readonly=false`; `capadd=null`; `capdrop=null`; `securityopt=null`; `restart=unless-stopped`. |
| API/UI smoke | frontend HTTP 200; API readiness HTTP 503. |
| DB/RabbitMQ readiness root cause | TCP connectivity from the API container to MariaDB/RabbitMQ succeeded, but Cloud UI health probes failed on DB/MQ authentication: MariaDB `1045 Access denied`; RabbitMQ `403 ACCESS_REFUSED`. |
| Migration job | No `cloud_ui_db_migrate` or `cloud-ui db-upgrade` container found in read-only container history. |
| Rollback | Not executed. |

## Auth model clarification

Keystone service users and service tokens are for OpenStack API/service-to-service authorization.
MariaDB runtime access and RabbitMQ transport access are separate deployment-secret domains. For
RabbitMQ, `oslo.messaging` uses a broker transport URL; the broker still validates user/password,
vhost and permissions. The current readiness failure is therefore tracked as DB/MQ secret injection
or principal drift between E09.3 provisioning and the manually observed Cloud UI containers.

## DKB scope

- ДКБ-22.02/24: TLS and health rows are test-stand evidence only.
- ДКБ-42-44/77/80: network, ACL and container evidence remain external until linked.
- ДКБ-55/56: secret-like output is redacted from this evidence. The observed DB/MQ auth failure keeps
  runtime secret delivery and rotation evidence open.
- ДКБ-65: user/caps/mount inspection was collected and failed the target hardening checks; SELinux
  label evidence remains pending.
- ДКБ-69/70: image digest evidence is recorded; ДКБ-69 still needs a waiver.
- ДКБ-82: rollback pending status prevents full deployment acceptance.
