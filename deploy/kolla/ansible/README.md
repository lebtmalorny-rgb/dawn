# Cloud UI Kolla-Ansible Role

This directory contains the E09.2 repository-side Kolla-Ansible role skeleton for Cloud UI.

The role declares four permanent services per control/UI node:

- `cloud_ui_frontend`
- `cloud_ui_api`
- `cloud_ui_worker`
- `cloud_ui_events`

The role preserves the E09.1 two-image contract:

- `cloud-ui-frontend` for `cloud_ui_frontend`
- `cloud-ui-backend` for `cloud_ui_api`, `cloud_ui_worker` and `cloud_ui_events`

## Default Scope

E09.2 does not run a deployment. It provides defaults, validation, config templates, handler names and
container definition data for later Kolla-Ansible integration.

Database provisioning, message broker provisioning, one-shot migration, HAProxy/TLS, live container
inspection, SELinux proof, registry digest evidence, rollback and three-node smoke remain later E09
slices.

The role now also contains a default-off all-in-one live mode for the approved lab path. That mode is
not enabled by the normal role defaults and does not change the three-node E09 target.

## Runtime Secret Inputs

The service role renders the backend runtime environment with:

- `CLOUD_UI_DATABASE_URL`
- `CLOUD_UI_RABBITMQ_URL`

These values come from `cloud_ui_database_url` and `cloud_ui_rabbitmq_url`, which default to empty
strings and must be supplied by the approved test secret mechanism when `cloud_ui_enabled=true`.
`cloud_ui_secret_references` records the expected Vault/SecMan lab paths, but no runtime secret value,
password, token, openrc file or `clouds.yaml` is stored in this repository.

The backend environment template task uses `no_log: true` because the rendered file on a deployment
host contains DB/MQ runtime URLs.

## E09.3 DB/RabbitMQ Provisioning

`roles/cloud_ui_provisioning` is the repository contract for one-time Cloud UI dependency
provisioning. It stores only object names and Vault secret references. It must not contain DB
passwords, RabbitMQ passwords, Vault tokens, openrc files or `clouds.yaml`.

Live E09.3 evidence is recorded in `docs/generated/e09-db-rabbitmq-provisioning.md`.

## E09 live reconfigure preflight bundle

The E09 live reconfigure preflight bundle is preflight only. It validates the approved test marker,
rollback window, image digest inputs and runtime DB/MQ secret inputs, then imports `cloud_ui` role
validation with `tasks_from: validate`.

It does not run live mutating Kolla actions, start containers, render runtime config files, run
migrations, mutate DB/MQ/Vault or claim E09 acceptance. The bundle checks that runtime secret inputs
are present without storing any runtime secret value in the repository.

Operators should create a non-committed vars file from
`examples/cloud-ui-vars.yml.example` and inject runtime secret values through the approved secret
mechanism. When invoking the preflight playbook from this repository, set
`ANSIBLE_ROLES_PATH=deploy/kolla/ansible/roles` or use an equivalent Ansible roles path
configuration so the `cloud_ui` role resolves correctly.

Evidence and remaining live follow-up are recorded in
`docs/generated/e09-live-reconfigure-bundle.md`.

## AIO live reconfigure role mode

`playbooks/cloud-ui-aio-reconfigure.yml` is the bounded all-in-one role path used to move the current
lab UI away from one-off Docker scripts. It targets only `openstack-aio`, enables
`cloud_ui_aio_live_reconfigure_enabled=true`, and imports the `cloud_ui` role. The mode remains
default-off in `roles/cloud_ui/defaults/main.yml`.

The AIO mode uses `community.docker` modules through the Kolla-Ansible virtual environment and the
approved `/etc/kolla/all-in-one` inventory. It creates the private Docker network `cloud-ui`, reuses
the `kolla_logs` volume, runs the optional one-shot `cloud-ui db-upgrade` container first, and then
converges the four permanent all-in-one containers:

- `cloud_ui_frontend` on host port `13080`;
- `cloud_ui_api` on host port `18081` with network alias `api`;
- `cloud_ui_worker`;
- `cloud_ui_events`.

The permanent containers keep the hardening contract from the manual lab baseline: non-root
`cloudui`, read-only root filesystem, `cap_drop: [ALL]`, `no-new-privileges:true`, bounded tmpfs and
no container socket mount. Runtime DB/MQ URLs must be passed from a non-committed vars file or another
approved secret mechanism; secret-referencing tasks use `no_log: true`.

For repeat convergence after the schema is already at head, set `cloud_ui_aio_run_migration=false`.
The 2026-06-28 lab idempotency run completed with no changes using that flag.

`deploy/kolla/scripts/run-cloud-ui-aio-kolla.py` is the bounded Kolla CLI entry point for this AIO
path. It builds:

```text
kolla-ansible reconfigure -i /etc/kolla/all-in-one \
  -p /etc/kolla/cloud-ui-sync-bundle/playbooks/cloud-ui-aio-reconfigure.yml \
  -t cloud-ui ...
```

The wrapper has three allowlisted modes: `preflight`, `reconfigure` and
`reconfigure-no-migration`. It rejects production-looking inventories, non-digest image inputs and a
closed rollback window. `examples/cloud-ui-aio-kolla-vars.yml.example` is non-secret only; runtime
DB/MQ URL values must still come from an external non-committed vars file or approved secret source.

This is Kolla CLI custom-playbook AIO evidence, not full upstream Kolla `site.yml` service
integration. It does not prove HAProxy/VIP/TLS routing, SELinux labels, corporate registry policy,
failed-update rollback, or twelve containers across three nodes.

## E09 Ansible sync bundle

The E09 Ansible sync bundle is a local-only export for the approved test-stand preparation path. It
packages the `cloud_ui` role, preflight playbook, placeholder example vars and a manifest with file
checksums. It contains no runtime secret value, inventory, SSH material, DB/MQ URL, token, private key
or host-specific credential.

The bundle now includes the AIO reconfigure playbook, `tasks/live-aio.yml` and the non-secret AIO
Kolla vars example so an operator can copy the same bounded lab role path that was validated on
2026-06-28. It is still a local-only export: remote sync, DB/MQ auth remediation, live reconfigure
and rollback evidence must be collected from the approved stand as `pending_external_evidence`, and
the copied bundle should use `ANSIBLE_ROLES_PATH=roles` or an equivalent Ansible roles path
configuration.

Evidence: `docs/generated/e09-ansible-sync-bundle.md`.
