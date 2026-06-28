# E09 AIO Kolla CLI Path Design

## Goal

Move the already working all-in-one Cloud UI deployment from a direct `ansible-playbook`
role invocation to a bounded Kolla-Ansible CLI invocation, while preserving the current AIO
startup behavior and not claiming full E09 three-node acceptance.

## Context

Current live evidence proves that `/etc/kolla/cloud-ui-sync-bundle/playbooks/cloud-ui-aio-reconfigure.yml`
can converge four Cloud UI containers on `openstack-aio` through the Kolla virtualenv and inventory.
The remaining gap is the operator entry point: it is still a direct playbook command, not
`kolla-ansible reconfigure`.

Kolla-Ansible 20.4.1 on the lab host supports custom playbooks through `kolla-ansible reconfigure
-p <playbook>`. The installed upstream `site.yml` has a fixed list of service roles and enable flags,
so patching the venv-owned `site.yml` is intentionally out of scope for this slice.

## Selected Approach

Use `kolla-ansible reconfigure -p /etc/kolla/cloud-ui-sync-bundle/playbooks/cloud-ui-aio-reconfigure.yml`
as the supported AIO operator path.

The repository will provide:

- an allowlisted wrapper script that builds the Kolla CLI command safely;
- a non-secret AIO vars example for `/etc/kolla`;
- role/playbook tags so `-t cloud-ui` works as an operator filter;
- tests that reject unsafe Kolla verbs, production-looking inventories, tag-only images and secret
  material in generated command output;
- evidence updates that distinguish this path from upstream `site.yml`/three-node acceptance.

## Security

The wrapper must not read or print DB/MQ runtime URLs. Runtime secret values continue to come from a
non-committed vars file or approved secret source passed by the operator. The wrapper accepts only the
safe verbs needed by this slice: `preflight`, `reconfigure` and `reconfigure-no-migration`.

## Verification

Repository tests prove command construction and documentation behavior. Live AIO verification uses
the approved Ansible host and test inventory, then checks:

- frontend returns HTTP 200;
- API readiness returns HTTP 200;
- frontend `/api/v1/session` returns HTTP 401;
- all four containers keep non-root/read-only/cap-drop/no-new-privileges;
- repeat convergence with migration disabled has no permanent container changes.

## Non-goals

- No patching of upstream Kolla-Ansible `site.yml` in the venv.
- No HAProxy/VIP/TLS cutover.
- No three-node/twelve-container rollout.
- No full failed-update rollback acceptance.
- No secrets, inventory, openrc, `clouds.yaml` or credential values committed to Git.
