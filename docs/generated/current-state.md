# Current state baseline

- Date: 2026-06-20
- Workspace: `/Users/dmitry/Desktop/dawn`
- Stage: E01 bootstrap implemented
- Evidence status: local and lab evidence, sanitized

## Repository state

Fact: current workspace is a Git repository.

Current branch and pushed state:

| Item | Observed value |
|---|---|
| repository root | `/Users/dmitry/Desktop/dawn` |
| branch | `feature/e01-bootstrap` |
| remote | `https://github.com/lebtmalorny-rgb/dawn.git` |
| local HEAD | current `feature/e01-bootstrap` branch tip |
| origin branch | `origin/feature/e01-bootstrap` exists; push after this docs commit updates it |

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
- `artifacts/`

## E01 bootstrap implementation state

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

- E01 is a source application bootstrap, not the Kolla Build integration step;
- Kolla-compatible image template/build integration remains a later deployment stage.

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
