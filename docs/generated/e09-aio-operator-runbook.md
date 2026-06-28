# Cloud UI AIO Operator Runbook

- Stage: E09 AIO operator baseline
- Date: 2026-06-28
- Scope: approved all-in-one test stand only
- Ansible host: `192.168.10.15`
- Inventory: `/etc/kolla/all-in-one`
- Target group: `openstack-aio`
- Status: current AIO UI baseline is usable for test UI work; this is not full E09 acceptance

## Boundary

The three-node rollout is paused. This runbook keeps the current AIO UI path reproducible while the
project continues UI and backend work in test mode. It does not prove upstream Kolla `site.yml`
integration, HAProxy/VIP/TLS, SELinux labels, corporate registry signing/scanning/provenance,
twelve permanent containers on three nodes, rolling upgrade or failed-update rollback.

Do not copy runtime secret files into Git. The operator supplies `/root/dawn-cloud-ui-lab-secrets.yml`
or an equivalent approved test secret source on the Ansible host. The repository stores no runtime secret value.

## Baseline Inputs

Use the current test registry digest refs from the running AIO containers or the approved registry
manifest. The wrapper performs digest availability checks before non-dry-run execution.

Current verified digest pair:

```text
backend:  sha256:7e8a4bae48bbc2b3539b33babe39d290b22ae2d61e21d0f886434af1ac2bc438
frontend: sha256:750ac3131e9ea9868d0893ff6df4eb603641b31c413c204c6a1470c20d17e790
```

Current rollback evidence point:

```text
/root/cloud-ui-aio-rollback-20260628T122556Z
```

## Preflight

Run this from the Ansible host. It checks the test inventory marker, rollback window, runtime DB/MQ
input presence, digest format and digest availability before any mutating reconfigure.

```bash
/usr/bin/python3 /etc/kolla/cloud-ui-sync-bundle/scripts/run-cloud-ui-aio-kolla.py preflight \
  --inventory /etc/kolla/all-in-one \
  --bundle-dir /etc/kolla/cloud-ui-sync-bundle \
  --runtime-vars /root/dawn-cloud-ui-lab-secrets.yml \
  --registry 192.168.10.15:5000/kolla/cloud-ui-test \
  --backend-digest sha256:7e8a4bae48bbc2b3539b33babe39d290b22ae2d61e21d0f886434af1ac2bc438 \
  --frontend-digest sha256:750ac3131e9ea9868d0893ff6df4eb603641b31c413c204c6a1470c20d17e790 \
  --kolla-ansible /root/venvs/kolla-epoxy/bin/kolla-ansible \
  --rollback-window-open
```

Expected recap:

```text
localhost : ok=10 changed=0 failed=0
```

If a stale digest is provided, the wrapper exits with code `2` before Kolla-Ansible starts.

## Reconfigure With Migration

Use this when the schema may need to be moved to Alembic head. The role runs
`cloud-ui db-upgrade --check` before `cloud-ui db-upgrade`, then converges the four permanent AIO
containers.

```bash
/usr/bin/python3 /etc/kolla/cloud-ui-sync-bundle/scripts/run-cloud-ui-aio-kolla.py reconfigure \
  --inventory /etc/kolla/all-in-one \
  --bundle-dir /etc/kolla/cloud-ui-sync-bundle \
  --runtime-vars /root/dawn-cloud-ui-lab-secrets.yml \
  --registry 192.168.10.15:5000/kolla/cloud-ui-test \
  --backend-digest sha256:7e8a4bae48bbc2b3539b33babe39d290b22ae2d61e21d0f886434af1ac2bc438 \
  --frontend-digest sha256:750ac3131e9ea9868d0893ff6df4eb603641b31c413c204c6a1470c20d17e790 \
  --kolla-ansible /root/venvs/kolla-epoxy/bin/kolla-ansible \
  --rollback-window-open
```

Observed recap:

```text
openstack-aio : ok=36 changed=2 failed=0 skipped=1
```

The two changed tasks are the disposable migration precheck and upgrade containers.

## Repeat Convergence

After the schema is already at head, use the no-migration mode to confirm idempotency without rerunning
the disposable migration containers.

```bash
/usr/bin/python3 /etc/kolla/cloud-ui-sync-bundle/scripts/run-cloud-ui-aio-kolla.py reconfigure-no-migration \
  --inventory /etc/kolla/all-in-one \
  --bundle-dir /etc/kolla/cloud-ui-sync-bundle \
  --runtime-vars /root/dawn-cloud-ui-lab-secrets.yml \
  --registry 192.168.10.15:5000/kolla/cloud-ui-test \
  --backend-digest sha256:7e8a4bae48bbc2b3539b33babe39d290b22ae2d61e21d0f886434af1ac2bc438 \
  --frontend-digest sha256:750ac3131e9ea9868d0893ff6df4eb603641b31c413c204c6a1470c20d17e790 \
  --kolla-ansible /root/venvs/kolla-epoxy/bin/kolla-ansible \
  --rollback-window-open
```

Observed recap:

```text
openstack-aio : ok=34 changed=0 failed=0 skipped=3
```

## Smoke

Run smoke on `openstack-aio` after reconfigure. These checks use direct AIO test ports, not
HAProxy/VIP/TLS.

```bash
curl -4 -fsS http://127.0.0.1:18081/api/v1/health/ready
curl -4 -fsSI http://127.0.0.1:13080/
curl -4 -fsS -o /tmp/cloud-ui-session.json -w '%{http_code}\n' http://127.0.0.1:13080/api/v1/session
```

Expected:

- API readiness returns HTTP 200 with database and RabbitMQ reachable.
- Frontend returns HTTP 200 and serves the built asset bundle.
- `/api/v1/session` through the frontend returns HTTP 401 `not_authenticated`.

## Container Inspection

Inspect only sanitized fields. The expected permanent containers are:

- `cloud_ui_frontend`;
- `cloud_ui_api`;
- `cloud_ui_worker`;
- `cloud_ui_events`.

Expected hardening:

- `user=cloudui`;
- `readonly=true`;
- `cap_drop=["ALL"]`;
- `security_opt=["no-new-privileges:true"]`;
- no container socket mount.

## Rollback

If the AIO reconfigure fails after a rollback point is recorded, restore the previous digest pair and
config from the test host snapshot, then rerun `run-cloud-ui-aio-kolla.py reconfigure-no-migration`
with the previous known-good digest pair. The current snapshot is:

```text
/root/cloud-ui-aio-rollback-20260628T122556Z
```

The snapshot stays off-repo because inspect and environment backups can contain secret material.

## Evidence Limits

This runbook is an AIO operator baseline for continued test UI work. It is not full E09 acceptance.
The remaining gates are the paused three-node rollout, twelve permanent containers, upstream Kolla
service integration, HAProxy/VIP/TLS, SELinux host labels, corporate registry policy and failed-update
rollback execution.
