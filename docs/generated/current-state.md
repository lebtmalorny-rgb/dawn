# Current state baseline

- Date: 2026-06-28
- Workspace: `/Users/dmitry/Desktop/dawn`
- Stage: E09.8 deployment smoke/evidence handoff
- Evidence status: all-in-one test UI is role-reconfigured, Kolla CLI custom-playbook path is migration- and smoke-passed, AIO operator runbook is recorded, and full three-node E09 acceptance remains pending

## Repository state

Fact: current workspace is a Git repository.

Current branch and pushed state observed on 2026-06-28:

| Item | Observed value |
|---|---|
| repository root | `/Users/dmitry/Desktop/dawn` |
| branch | `main` |
| remote | `https://github.com/lebtmalorny-rgb/dawn.git` |
| local HEAD | feature worktree contains the AIO operator baseline runbook update |
| origin branch | `origin/main` contains the AIO digest availability preflight through `1e0782e`; this runbook update is pending merge |

## Current E09 handoff

E09 is the active stage. Repository-side evidence exists for E09.1-E09.8:

- E09.1 Kolla image build contract and wrapper;
- E09.2 Kolla-Ansible role skeleton plus a default-off AIO live role mode;
- E09.3 all-in-one lab Vault/MariaDB/RabbitMQ provisioning evidence;
- E09.4 one-shot migration job contract;
- E09.5 three-node/twelve-container process topology contract;
- E09.6 HAProxy/TLS/network route contract;
- E09.7 reconfigure, rolling update and rollback lifecycle contract;
- E09.8 fail-closed deployment evidence runner and redaction tests.

All-in-one test UI status on 2026-06-28:

- approved test inventory `/etc/kolla/all-in-one` was used through Ansible host `192.168.10.15`;
- `deploy/kolla/ansible` was synced to `/etc/kolla/cloud-ui-sync-bundle` on the Ansible host;
- `playbooks/cloud-ui-aio-reconfigure.yml` was executed through the Kolla-Ansible environment against
  host group `openstack-aio`;
- backend image `192.168.10.15:5000/kolla/cloud-ui-test/cloud-ui-backend@sha256:7e8a4bae48bbc2b3539b33babe39d290b22ae2d61e21d0f886434af1ac2bc438` is live;
- frontend image `192.168.10.15:5000/kolla/cloud-ui-test/cloud-ui-frontend@sha256:750ac3131e9ea9868d0893ff6df4eb603641b31c413c204c6a1470c20d17e790` is live;
- four Cloud UI containers are running on `openstack-aio`: frontend, api, worker and events;
- API readiness on `127.0.0.1:18081` returns HTTP 200 with DB/RabbitMQ reachable;
- frontend on `127.0.0.1:13080` returns HTTP 200 and references bundle `index-CPtHnxYH.js`;
- frontend proxy to `/api/v1/session` returns HTTP 401 `not_authenticated`;
- sanitized inspect shows all four containers run as `cloudui` with read-only root filesystem,
  dropped capabilities and `no-new-privileges`.
- Kolla CLI migration-enabled `reconfigure` completed with `openstack-aio : ok=36 changed=2 failed=0
  skipped=1`; the changes were the disposable migration precheck and upgrade containers.
- follow-up AIO idempotency with `cloud_ui_aio_run_migration=false` completed with no changes:
  `openstack-aio : ok=34 changed=0 failed=0 skipped=3`.
- operator runbook for the current AIO baseline is recorded in
  `docs/generated/e09-aio-operator-runbook.md`.

Full E09 acceptance is not claimed. The live deployment evidence remains partial until the approved
test stand provides:

- 12 live Cloud UI permanent containers on three test nodes;
- accepted upstream Kolla `site.yml` service integration or another approved full role path;
- HAProxy/VIP/TLS health and negative TLS evidence;
- SELinux label and host policy evidence;
- corporate registry signing, scanner/provenance and ДКБ-69 waiver evidence;
- executed failed-update rollback evidence.

Latest local verification for the handoff:

| Command | Result |
|---|---|
| E09.8 all-in-one debug smoke via Ansible script | passed: new API/frontend debug containers started, API readiness `ok`, frontend `/api/v1/session` returned HTTP 401 |
| E09.8 all-in-one live deploy via Ansible script | passed: rollback snapshot created, `cloud-ui db-upgrade` returned success, four live containers replaced by digest images |
| E09 AIO rollback snapshot before role reconfigure | passed: `/root/cloud-ui-aio-rollback-20260628T081816Z` created on the test host; files remain off-repo because they can contain runtime env/inspect data |
| E09 AIO role preflight | passed: `playbooks/cloud-ui-preflight.yml` recap `localhost : ok=10 changed=0 failed=0` |
| E09 AIO role reconfigure | passed: `playbooks/cloud-ui-aio-reconfigure.yml` recap `openstack-aio : ok=35 changed=6 failed=0 skipped=1` |
| E09 AIO role idempotency | passed: same playbook with `cloud_ui_aio_run_migration=false` recap `openstack-aio : ok=34 changed=0 failed=0 skipped=2` |
| E09 AIO Kolla CLI preflight | passed: `run-cloud-ui-aio-kolla.py preflight` via `kolla-ansible reconfigure -p` recap `localhost : ok=10 changed=0 failed=0` |
| E09 AIO Kolla CLI stale digest gate | passed: stale backend/frontend digest inputs returned wrapper exit code `2` before Kolla-Ansible started |
| E09 AIO Kolla CLI reconfigure with migration | passed: `run-cloud-ui-aio-kolla.py reconfigure` via `kolla-ansible reconfigure -p` recap `openstack-aio : ok=36 changed=2 failed=0 skipped=1` |
| E09 AIO Kolla CLI idempotency | passed: `run-cloud-ui-aio-kolla.py reconfigure-no-migration` via `kolla-ansible reconfigure -p` recap `openstack-aio : ok=34 changed=0 failed=0 skipped=3` |
| E09.8 sanitized Docker inspect via Ansible script | passed: four containers non-root, read-only rootfs, `cap_drop=["ALL"]`, `no-new-privileges`, expected ports/alias |
| E09.8 live endpoint checks via Ansible `uri` | passed: API ready HTTP 200, frontend index HTTP 200, frontend `/api/v1/session` HTTP 401 |
| `UV_CACHE_DIR=/tmp/dawn-uv-cache UV_PYTHON_INSTALL_DIR=/tmp/dawn-uv-python UV_PROJECT_ENVIRONMENT=/tmp/dawn-backend-venv uv run --python 3.11 --project backend --extra dev pytest tests/test_e09_deployment_smoke_evidence.py tests/test_e09_reconfigure_rollback.py tests/test_e09_kolla_ansible_role.py tests/test_e09_haproxy_tls_network.py tests/test_e09_process_containers.py tests/test_e09_migration_job.py tests/test_e09_db_rabbitmq_provisioning.py tests/test_e09_kolla_image_build.py backend/tests/test_cli.py -q` | passed: 81 tests |
| `./scripts/secret-scan.sh` | passed |
| `git diff --check` | passed |

Primary handoff documents:

- `docs/execplans/E09-deployment-smoke-evidence.md`;
- `docs/generated/e09-aio-operator-runbook.md`;
- `docs/generated/e09-deployment-smoke-evidence.md`;
- `deploy/kolla/scripts/collect-e09-evidence.py`;
- `tests/test_e09_deployment_smoke_evidence.py`;
- `docs/generated/risk-register.md` rows R-056-R-068.

## Files observed

Top-level files:

- `README.md`
- `AGENTS.md`
- `CODEX_START.md`
- `FILE_INDEX.md`
- `PLANS.md`
- `Makefile`
- `compose.yaml`

Document directories:

- `docs/`
- `tasks/`
- `templates/`
- `backend/`
- `frontend/`
- `deploy/`
- `security/`

Generated directories:

- `docs/generated/`
- `docs/execplans/`
- `docs/adr/`
- `artifacts/` where present

## Historical E01 bootstrap implementation state

The following E01 section is retained as historical baseline evidence from 2026-06-20.

E01 implemented the first runnable application slice:

- backend Python package under `backend/`;
- backend API, worker, events and migration CLI commands;
- FastAPI health endpoints and request-id middleware;
- Alembic scaffold and initial `schema_info` migration;
- React/Vite/PatternFly frontend status shell under `frontend/`;
- local compose stack with MariaDB, RabbitMQ, backend API, backend worker, backend events and frontend;
- backend and frontend runtime images;
- `Makefile` quality/runtime commands;
- `scripts/secret-scan.sh` with exact dummy allowlist and fallback scanning when `rg` is absent;
- `tests/smoke.py` for compose smoke verification.

Final E01 verification on 2026-06-20:

| Command | Result |
|---|---|
| `make lint` | passed: backend ruff, frontend eslint, secret scan |
| `make typecheck` | passed: backend mypy for 11 source files, frontend `tsc -b` |
| `make test` | passed: backend 14 tests, frontend 4 tests |
| `make build` | passed: `cloud-ui-backend:dev` and `cloud-ui-frontend:dev` built |
| `make up` | passed: compose started db, rabbitmq, api, worker, events, frontend |
| `make smoke` | passed: `smoke ok` |
| `docker compose images --format json` | confirmed api/worker/events use `cloud-ui-backend:dev`; frontend uses `cloud-ui-frontend:dev` |
| `./scripts/secret-scan.sh` | passed: no matches |
| `make down` | passed: compose containers and network removed |

Codex sandbox note:

- direct loopback access to published compose ports is blocked inside the sandbox with `Operation not permitted`;
- `make smoke` was run outside the sandbox for final evidence;
- container healthchecks and logs confirmed the API itself was healthy.

Kolla status:

- E01 was a source application bootstrap, not the Kolla Build integration step;
- E09 later added repository-side Kolla Build/Kolla-Ansible contracts and evidence, but live
  three-node deployment acceptance remains pending as described in the current E09 handoff above.

## Local host

Fact: local host is not the target Rocky Linux/Kolla host.

Observed:

```text
OS: macOS 26.5.1, Darwin 25.5.0, arm64
```

Impact:

- local tool availability is useful for authoring only;
- target Rocky/Kolla facts must come from the test hosts, not from local macOS tools;
- E01 uses Python backend tooling, npm frontend tooling and Docker Compose for local verification.

## Available local tools

| Tool | Observed result | Evidence status |
|---|---|---|
| `git` | 2.49.0 | verified locally |
| `python3` | 3.14.0 | verified locally; not target runtime |
| `node` | v25.9.0 | verified locally; not target runtime |
| `npm` | 11.12.1 | verified locally |
| `pnpm` | command not found | not used by E01; frontend bootstrap uses npm |
| `uv` | 0.11.7 | verified locally |
| `make` | GNU Make 3.81 | verified locally |
| `docker` CLI | 29.0.1 | client verified |
| Docker daemon | available through approved Docker commands | used for E01 compose verification |
| `podman` | command not found | unavailable locally |
| `ansible` | core 2.18.6 with `/tmp` local temp override | verified locally |
| `kolla-build` | command not found | unavailable locally |
| `kolla-ansible` | command not found | unavailable locally |
| `openssl` | 3.6.1 | verified locally |
| `rg` | 15.1.0 | verified locally |

## Target environment facts

Known from input documents:

- Target platform: OpenStack Epoxy 2025.1.
- Target deployment tools: Kolla Build and Kolla-Ansible.
- Target OS: Rocky Linux.
- Test Ansible host: `192.168.10.15`, root SSH access provided out-of-band.
- Test OpenStack all-in-one host: `192.168.10.14`, root SSH access provided out-of-band.
- Test API/Horizon VIP: `192.168.10.250`.
- Credentials exist on the Ansible host and in Kolla config; real values must not be copied into Git.

Verified via read-only SSH/OpenStack CLI on 2026-06-19:

| Item | Observed value | Evidence command summary |
|---|---|---|
| Ansible host hostname | `ansible.example.local` | SSH to `192.168.10.15`, `hostname` |
| Ansible host OS | Rocky Linux 9.5 | `/etc/os-release` |
| OpenStack host hostname | `openstack-aio` | SSH to `192.168.10.14`, `hostname` |
| OpenStack host OS | Rocky Linux 9.8 | `/etc/os-release` |
| Kolla-Ansible venv | `/root/venvs/kolla-epoxy` | path discovery under `/root/venvs` |
| Kolla-Ansible version | `20.4.1.dev5` | `kolla-ansible --version` in venv |
| Kolla Build version | `20.4.0` | `kolla-build --version` in venv after installing `kolla==20.*` |
| Ansible core in Kolla venv | `2.18.17` | `ansible --version` in venv |
| OpenStack CLI in Kolla venv | `7.5.0` | `openstack --version` in venv |
| Ansible host build runtime | Podman `5.2.2`; Buildah present | `podman version`, `command -v buildah` |
| OpenStack host container runtime | Docker `29.5.2` | `docker --version` on `192.168.10.14` |
| Kolla image tag | `2025.1-rocky-9` | `docker ps` image names on `192.168.10.14` |
| Horizon/API VIP | `192.168.10.250` on `br0` | `ip -brief addr`, `curl` |
| Horizon over HTTPS VIP | HTTP/2 302 to `/auth/login/` | `curl --cacert /etc/kolla/certificates/ca/root.crt -I https://192.168.10.250` |
| Keystone HTTPS version discovery | `v3.14` | `curl --cacert /etc/kolla/certificates/ca/root.crt https://192.168.10.250:5000/v3` |
| VIP TLS certificate | issuer `KollaTestCA`, SAN `IP Address:192.168.10.250`, valid 2026-06-19 to 2027-06-19 | `openssl x509 -in /etc/kolla/certificates/haproxy.pem -noout -dates -ext subjectAltName` |
| Live Keystone TLS verification | TLSv1.3, `Verification: OK` | `openssl s_client -brief -connect 192.168.10.250:5000 -CAfile /etc/kolla/certificates/ca/root.crt` |

OpenStack service catalog verified via `/etc/kolla/admin-openrc.sh`:

- `keystone` identity
- `nova` compute
- `placement` placement
- `neutron` network
- `glance` image
- `cinder` block-storage / `cinderv3` volumev3
- `heat` orchestration / `heat-cfn` cloudformation
- `mistral` workflowv2
- `watcher` infra-optim
- `masakari` instance-ha

Post-baseline Kolla update on 2026-06-19:

- `enable_mistral`, `enable_watcher`, `enable_masakari`, `enable_redis`, `kolla_enable_tls_internal`, `kolla_enable_tls_external`, `kolla_copy_ca_into_containers`, `openstack_cacert` and `kolla_admin_openrc_cacert` were enabled in `/etc/kolla/globals.yml`.
- Masakari API/engine are enabled. Masakari instance and host monitors remain disabled in this all-in-one lab because enabling them would also enable HA cluster/Pacemaker/Corosync roles.
- User-provided update on 2026-06-21: Consul is deployed and under R&D outside the current test node; the current test node does not have Consul. Intended use is network health checks that feed a decision about evacuation. Research decision: prefer Masakari hostmonitor Consul driver and `matrix.yaml` rather than portal-side recovery from Consul Events.
- `kolla-ansible prechecks -i /etc/kolla/all-in-one` completed with `failed=0`.
- `kolla-ansible pull -i /etc/kolla/all-in-one` completed with `failed=0`.
- `kolla-ansible reconfigure -i /etc/kolla/all-in-one` completed with `failed=0`.
- `kolla-ansible post-deploy -i /etc/kolla/all-in-one` regenerated `/etc/kolla/admin-openrc.sh` and `clouds.yaml`; `OS_AUTH_URL` now uses `https://192.168.10.250:5000` and `OS_CACERT=/etc/pki/tls/certs/ca-bundle.crt`.
- `kolla-ansible check -i /etc/kolla/all-in-one` completed with recap `ok=51 changed=0 failed=0`.

New service containers observed running:

- `mistral_api`, `mistral_engine`, `mistral_executor`, `mistral_event_engine`
- `watcher_api`, `watcher_engine`, `watcher_applier`
- `masakari_api`, `masakari_engine`
- `redis`, `redis_sentinel`

Safe inventory counts from OpenStack CLI:

| Resource | Count |
|---|---:|
| projects | 2 |
| users | 8 |
| hypervisors | 1 |
| servers all projects | 0 |
| images | 0 |
| networks | 2 |
| volumes all projects | 0 |

Host/service status:

- one hypervisor: `openstack-aio`, QEMU, up;
- Nova scheduler/conductor/compute: enabled/up;
- Cinder scheduler and LVM volume service: enabled/up;
- Neutron metadata/L3/DHCP/Open vSwitch agents: alive/up.

Important credential/config finding:

- `/root/openrc` and `/root/openrc.sh` point to `http://192.168.10.50:5000/v3`, which is unreachable from the Ansible host.
- `/etc/kolla/admin-openrc.sh` and `/etc/kolla/clouds.yaml` now point to HTTPS VIP endpoints after `kolla-ansible post-deploy`.
- Horizon Mistral dashboard needs an explicit Python requests CA bundle. A Kolla-supported custom settings file exists at `/etc/kolla/config/horizon/_9999-custom-settings.py`; it sets `REQUESTS_CA_BUNDLE` and `CURL_CA_BUNDLE` from `OPENSTACK_SSL_CACERT`.

Not yet verified:

- whether a separate Kolla build venv exists under `/opt/kolla-venv`;
- current Kolla base image digest;
- test project credentials for non-admin least-privilege flows;
- test registry;
- RabbitMQ notification transport;
- MariaDB backup/failover;
- SIEM/Vault(SecMan)/PKI/PAM/storage/network interfaces.

Build tooling update:

- `kolla==20.*` was installed into `/root/venvs/kolla-epoxy`, making `kolla-build` available.
- Python package `podman==5.8.0` was installed into the same venv.
- `/etc/kolla/kolla-build.conf` was created with `engine = podman`, `base = rocky`, `base_tag = 9`, `openstack_release = 2025.1`, `namespace = kolla`, `tag = 2025.1-rocky-9`.
- `kolla-build --config-file /etc/kolla/kolla-build.conf --template-only --profile aux` generated Dockerfiles successfully under `/tmp/kolla-build-config-dryrun/docker`.

Horizon/Mistral TLS client fix on 2026-06-19:

- Symptom: Horizon Mistral dashboard showed `Unable to retrieve workbooks` with `SSLCertVerificationError` against `https://192.168.10.250:8989/v2/workbooks`.
- Root cause: `mistraldashboard` creates `mistralclient` without passing Horizon `OPENSTACK_SSL_CACERT`; Python `requests` therefore used the `certifi` bundle inside the Horizon venv, which did not include the Kolla CA.
- Fix: `/etc/kolla/config/horizon/_9999-custom-settings.py` sets `REQUESTS_CA_BUNDLE` and `CURL_CA_BUNDLE` to `OPENSTACK_SSL_CACERT`; `kolla-ansible reconfigure -i /etc/kolla/all-in-one --tags horizon` copied the file and restarted Horizon.
- Verification: after loading Django settings in the Horizon container, `mistralclient.workbooks.list()` with a real admin token returned `workbooks_count=0` instead of an SSL error; `kolla-ansible check -i /etc/kolla/all-in-one --tags horizon` completed with `failed=0`.

## Safe inventory commands for operator

Run only on a test/admin workstation with approved read-only access:

```bash
cat /etc/os-release
kolla-ansible --version
kolla-build --version
ansible --version
docker --version || podman --version
openstack --version
openstack endpoint list
openstack compute service list
openstack hypervisor list
openstack server list --all-projects --limit 1
openstack network agent list
openstack volume service list
openstack image list --limit 1
```

For Kolla inventory and TLS/network state, use sanitized outputs only:

```bash
kolla-ansible -i <test-inventory> globals --check
kolla-ansible -i <test-inventory> certificates --check
```

Do not paste passwords, tokens, private keys, `clouds.yaml`, openrc files or production URLs with credentials into repository documents.

## Open questions with owner/method

| Question | Current value | Owner/method |
|---|---|---|
| Exact Kolla/Rocky baseline | partially known | platform owner to confirm Kolla Build/base image and intended baseline |
| Test OpenStack endpoints | verified in lab | service catalog uses `https://192.168.10.250` for enabled services |
| Test IdP/federation flow | unknown | IAM owner, ADR-001 |
| Test SIEM protocol | unknown | SIEM owner, ADR-008 |
| Test Vault (SecMan) API | product identified; endpoint/auth/path policy unknown | Vault owner, ADR-009 |
| Notification transport | unknown | OpenStack messaging owner, ADR-003; RabbitMQ exists as Kolla container |
| Storage architecture for ДКБ-72 | unknown | storage owner |
| Management VLAN/ACL | unknown | network owner |
| Registry/signing product | unknown | platform/supply-chain owner |
| Mistral/Watcher/Masakari availability | enabled in lab catalog | production owner to confirm whether Masakari monitors/HA cluster are required outside AIO |
