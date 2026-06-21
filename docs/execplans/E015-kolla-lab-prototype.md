# ExecPlan: E01.5 Kolla lab prototype

## Result

E01.5 adds a lab-only Kolla Build prototype for Dawn on branch
`feature/e015-kolla-prototype`. The repository now contains Kolla-compatible
templates for exactly two custom images:

- `cloud-ui-backend`
- `cloud-ui-frontend`

The backend image serves `api`, `worker`, `events`, `db-upgrade` and `smoke`.
The live lab deploy is running on `192.168.10.14`.

## Live Verification

Final live verification was run on 2026-06-21 from the build/control host
`192.168.10.15` against the AIO host `192.168.10.14`.

Build evidence:

- `kolla-build 20.4.0`
- registry: `192.168.10.15:5000`
- tag: `2025.1-rocky-9`
- full build/push succeeded for `base`, `openstack-base`, `cloud-ui-backend`
  and `cloud-ui-frontend`
- final frontend-only rebuild/push succeeded after the nginx runtime directory
  fix
- custom registry images present:
  - `192.168.10.15:5000/kolla/cloud-ui-backend:2025.1-rocky-9`
  - `192.168.10.15:5000/kolla/cloud-ui-frontend:2025.1-rocky-9`

Deploy evidence:

```bash
/root/venvs/kolla-epoxy/bin/ansible-playbook \
  -i deploy/kolla/lab/inventory.ini.example \
  -e @deploy/kolla/lab/group_vars/all.yml.example \
  -e @/root/dawn-cloud-ui-lab-secrets.yml \
  deploy/kolla/lab/playbooks/deploy.yml
```

Result: `failed=0`, containers started:

- `cloud_ui_api` on `0.0.0.0:18081->8080/tcp`
- `cloud_ui_worker`
- `cloud_ui_events`
- `cloud_ui_frontend` on `0.0.0.0:13080->8080/tcp`

Smoke evidence:

```bash
/root/venvs/kolla-epoxy/bin/ansible-playbook \
  -i deploy/kolla/lab/inventory.ini.example \
  -e @deploy/kolla/lab/group_vars/all.yml.example \
  -e @/root/dawn-cloud-ui-lab-secrets.yml \
  deploy/kolla/lab/playbooks/smoke.yml
```

Result: `failed=0`. The smoke playbook verified:

- API liveness
- API readiness through MariaDB and RabbitMQ checks
- frontend HTTP 200
- all four Dawn containers running the expected Kolla images
- Docker health status for all four Dawn containers
- absence of the supplied DB/RabbitMQ URLs in Dawn container logs

Default lab endpoints:

- API: `http://192.168.10.14:18081`
- frontend: `http://192.168.10.14:13080`

## Lab State

Secrets were generated only on the build/control host in
`/root/dawn-cloud-ui-lab-secrets.yml` with mode `0600`. No live passwords were
committed.

The live lab uses:

- MariaDB database/user: `cloud_ui`
- RabbitMQ vhost/user: `/cloud-ui` / `cloud_ui`
- Docker network: `cloud-ui`

The lab registry is intentionally configured as an insecure HTTP registry on
both the build/control host and AIO host. This is not the production TLS/DKB
closure.

## Issues Found And Fixed

- Kolla build work/log directories had to be created explicitly.
- UID/GID `42480` collided with Kolla `tempest`; Dawn now uses `42580`.
- Kolla local sources are exposed as archives and extract under `source/`.
- The backend image needs Python 3.11 on Rocky 9.
- Backend runtime pins must follow Kolla upper constraints for Epoxy.
- Alembic migrations must be packaged inside the installed wheel.
- Lab API port `18080` collided with existing cAdvisor; the lab now uses
  `18081`.
- Nginx needs writable `/var/lib/nginx` when running as `cloudui`.
- Smoke must check container health and supplied secret URL leakage in logs.

## Rollback

Rollback was not executed after final smoke because the lab deployment was left
running for inspection. The rollback path is:

```bash
/root/venvs/kolla-epoxy/bin/ansible-playbook \
  -i deploy/kolla/lab/inventory.ini.example \
  -e @deploy/kolla/lab/group_vars/all.yml.example \
  -e @/root/dawn-cloud-ui-lab-secrets.yml \
  deploy/kolla/lab/playbooks/rollback.yml
```

The rollback playbook is guarded to operate only on `/etc/cloud-ui` and
`cloud-ui*` lab network/container resources.

## Remaining Limits

- This is a lab prototype, not the final production Kolla-Ansible role.
- The registry is HTTP/insecure for the lab.
- Worker/events health checks are lab liveness checks using `cloud-ui smoke`;
  production worker health needs a domain-specific signal in a later stage.
- Credentials are generated lab secrets; production promotion should move them
  to Vault/secman.
- Docker reports IPv4 forwarding disabled on container start, but the final
  readiness and frontend smoke checks passed in this lab.
