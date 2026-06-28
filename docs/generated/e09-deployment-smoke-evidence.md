# E09.8 Deployment smoke/evidence

- Stage: E09.8 Deployment smoke/evidence
- Live execution status: `partial_lab_kolla_cli_reconfigured_all_in_one`
- Scope: `partial` `test-stand` `all-in-one`
- Inventory: `/etc/kolla/all-in-one` on `192.168.10.15`; validated from a temporary copy outside the repository
- Target node: `openstack-aio` reached through the approved Ansible host
- Backend image: `192.168.10.15:5000/kolla/cloud-ui-test/cloud-ui-backend@sha256:7e8a4bae48bbc2b3539b33babe39d290b22ae2d61e21d0f886434af1ac2bc438`
- Frontend image: `192.168.10.15:5000/kolla/cloud-ui-test/cloud-ui-frontend@sha256:750ac3131e9ea9868d0893ff6df4eb603641b31c413c204c6a1470c20d17e790`
- Rollback snapshot: `/root/cloud-ui-aio-rollback-20260628T122556Z` on the test host; contents are not committed because runtime env/inspect files can contain secrets

## Evidence rows

| Check | Status | Sanitized summary |
|---|---|---|
| scope | partial | Test-stand all-in-one evidence only; production approval absent. Full E09 acceptance is not claimed. |
| preflight | passed | The approved inventory marker `cloud_ui_test_stand=true`, digest-pinned images and open rollback window were validated before mutating the lab target. The Kolla-Ansible-side preflight playbook completed with `ok=10 changed=0 failed=0`. |
| two_images | passed_lab | Backend and frontend were built through the Kolla image path and deployed by immutable digest from the test registry on `192.168.10.15`. Registry signing, provenance and corporate repository acceptance remain pending. |
| container count | partial_lab_evidence | Four permanent Cloud UI containers are running on one all-in-one host: frontend, api, worker and events. E09 still requires twelve permanent containers across three test nodes, so acceptance remains blocked. |
| migration | passed_lab_kolla_cli_aio | The Kolla CLI custom-playbook path ran `cloud-ui db-upgrade --check` before the one-shot migration command `cloud-ui db-upgrade`; the migration-enabled recap was `openstack-aio : ok=36 changed=2 failed=0 skipped=1`. The AIO role can skip both one-shot tasks for repeat convergence with `cloud_ui_aio_run_migration=false`; the idempotency run used that flag. |
| DB/RabbitMQ | passed_lab | After no-log lab remediation of the existing Cloud UI MariaDB and RabbitMQ principals, API readiness reports database and RabbitMQ `reachable`. The earlier failure was MariaDB `1045 Access denied` and RabbitMQ `403 ACCESS_REFUSED`, i.e. runtime DB/MQ principal or secret drift, not Keystone RBAC. Secret values were not printed or committed. Full rotation/revoke evidence remains pending. |
| HAProxy/TLS | pending_external_evidence | Smoke was collected through direct all-in-one test ports `13080` and `18081`. Same-origin HAProxy/VIP/TLS and negative certificate evidence were not collected in this run. |
| container hardening | partial_lab_evidence | Sanitized Docker inspect shows all four containers run as `cloudui` with `readonly=true`, `cap_drop=["ALL"]`, `security_opt=["no-new-privileges:true"]` and `kolla_logs:/var/log/kolla`. SELinux label evidence was not collected. |
| API/UI smoke | passed_lab | API readiness returned HTTP 200 with DB/RabbitMQ reachable. Frontend returned HTTP 200 and referenced `/assets/index-CPtHnxYH.js`. Frontend proxy to `/api/v1/session` returned HTTP 401 `not_authenticated`, proving BFF routing without exposing a session. |
| rollback | partial_lab_evidence | Rollback pending for full E09 acceptance. The migration-enabled Kolla CLI path run created rollback snapshot `/root/cloud-ui-aio-rollback-20260628T122556Z`; snapshot files are retained only on the test host because inspect/env backups can contain secrets. |
| live reconfigure | passed_aio_kolla_cli_path_with_migration | `playbooks/cloud-ui-aio-reconfigure.yml` was synced to the Ansible host and executed through `kolla-ansible reconfigure -p ... -t cloud-ui`. Preflight completed with `ok=10 changed=0 failed=0`; migration-enabled reconfigure completed with `ok=36 changed=2 failed=0 skipped=1`; the idempotent reconfigure with migration disabled completed with `ok=34 changed=0 failed=0 skipped=3`. This is a bounded AIO Kolla CLI custom-playbook path, not full upstream `site.yml` service integration or three-node acceptance. |

## Live execution on 2026-06-28

The following checks were run only against the approved test stand. No production host, inventory,
credential, private key, cookie, token or full runtime env is stored in this evidence.

| Item | Result |
|---|---|
| New-image debug smoke | Temporary debug containers started from the backend/frontend digest refs; API status `running`, frontend status `running`, API readiness `ok`, frontend `/api/v1/session` returned HTTP 401. Debug containers were removed. |
| Manual baseline deploy | The earlier bounded lab deploy script completed with `rc=0`, ran Alembic in MySQL mode, replaced four Cloud UI containers and printed only sanitized image refs, readiness JSON and session status. |
| Role sync | The updated `deploy/kolla/ansible` content was copied to `/etc/kolla/cloud-ui-sync-bundle` on the Ansible host without committing host inventory, runtime vars or credentials. |
| Role preflight | `playbooks/cloud-ui-preflight.yml` completed on the Ansible host with recap `localhost : ok=10 changed=0 failed=0` using digest image refs and a non-committed runtime secret vars file. |
| AIO role reconfigure | `playbooks/cloud-ui-aio-reconfigure.yml` completed against `/etc/kolla/all-in-one` with recap `openstack-aio : ok=35 changed=6 failed=0 skipped=1`. The run used `community.docker` modules from the Kolla-Ansible environment and converged the four AIO containers. |
| AIO idempotency | The same playbook with `cloud_ui_aio_run_migration=false` completed with recap `openstack-aio : ok=34 changed=0 failed=0 skipped=2`; no permanent container changed. |
| Kolla CLI AIO preflight | `run-cloud-ui-aio-kolla.py preflight` invoked `kolla-ansible reconfigure -p /etc/kolla/cloud-ui-sync-bundle/playbooks/cloud-ui-preflight.yml -t cloud-ui`; recap `localhost : ok=10 changed=0 failed=0`. |
| Kolla CLI AIO reconfigure with migration | `run-cloud-ui-aio-kolla.py reconfigure` invoked `kolla-ansible reconfigure -p /etc/kolla/cloud-ui-sync-bundle/playbooks/cloud-ui-aio-reconfigure.yml -t cloud-ui`; migration precheck and one-shot upgrade ran as disposable containers and recap was `openstack-aio : ok=36 changed=2 failed=0 skipped=1`. |
| Kolla CLI AIO idempotency | `run-cloud-ui-aio-kolla.py reconfigure-no-migration` invoked the same custom playbook with `cloud_ui_aio_run_migration=false`; recap `openstack-aio : ok=34 changed=0 failed=0 skipped=3`. |
| Stale digest diagnostic | An initial migration-enabled run used stale digest inputs and stopped before permanent container changes with `changed=0`; diagnostic playbooks showed schema `0006_audit_delivery (head)` and isolated the failure to registry 404 for the stale backend digest. The wrapper now checks backend/frontend digest manifests before non-dry-run execution: the stale digest pair returns exit code `2` before Kolla-Ansible starts, while the current digest pair still passes preflight with `localhost : ok=10 changed=0 failed=0`. |
| Running containers | `cloud_ui_frontend`, `cloud_ui_api`, `cloud_ui_worker` and `cloud_ui_events` are up from the digest-pinned images. Frontend publishes `13080->8080`; API publishes `18081->8080`; worker/events expose no host port. |
| Container hardening | Sanitized inspect confirmed `user=cloudui`, `readonly=true`, `cap_drop=["ALL"]`, `security_opt=["no-new-privileges:true"]`, restart policy `unless-stopped` and `kolla_logs:/var/log/kolla` for all four containers. |
| API readiness after migration-enabled Kolla CLI convergence | `http://127.0.0.1:18081/api/v1/health/ready` returned HTTP 200 with `database.reachable` and `rabbitmq.reachable` at `Sun, 28 Jun 2026 17:40:31 GMT`. |
| Frontend index after migration-enabled Kolla CLI convergence | `http://127.0.0.1:13080/` returned HTTP 200 and referenced `/assets/index-CPtHnxYH.js` plus `/assets/index-XcqiXUF-.css` at `Sun, 28 Jun 2026 17:40:39 GMT`. |
| Frontend BFF route after migration-enabled Kolla CLI convergence | `http://127.0.0.1:13080/api/v1/session` returned HTTP 401 with machine-readable `not_authenticated` and Russian user message `Требуется вход` at `Sun, 28 Jun 2026 17:40:45 GMT`. |

## DKB scope

- ДКБ-22.02/24: direct HTTP all-in-one smoke is collected, but HAProxy/VIP/TLS, corporate PKI/mTLS
  approval and negative certificate tests remain external.
- ДКБ-42-44/77/80: container network evidence is limited to the Docker `cloud-ui` network on one
  all-in-one node. Management VLAN, firewall/ACL and disabled unused-interface proof remain pending.
- ДКБ-55/56: runtime DB/MQ access works on the lab target and no secret values are stored in Git.
  Full SecMan/Kolla/OpenStack secret rotation, revoke and owner approval remain pending.
- ДКБ-65: user/capability/read-only-rootfs hardening now has live all-in-one evidence. SELinux label
  and host policy evidence remain pending.
- ДКБ-69/70: digest-pinned images from the test registry are deployed. ДКБ-69 still needs a formal
  Python interpreter/shell waiver; corporate registry signing, scanner and provenance evidence remain
  pending.
- ДКБ-82: rollback snapshot, AIO role reconfigure evidence, Kolla CLI custom-playbook path evidence
  with migration, idempotency and smoke evidence exist for the test all-in-one deployment. Full
  upstream Kolla `site.yml` service integration, three-node Kolla-Ansible reconfigure/upgrade and
  failed-rollback acceptance remain pending.
