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

## Scope

E09.2 does not run a deployment. It provides defaults, validation, config templates, handler names and
container definition data for later Kolla-Ansible integration.

Database provisioning, message broker provisioning, one-shot migration, HAProxy/TLS, live container
inspection, SELinux proof, registry digest evidence, rollback and three-node smoke remain later E09
slices.

## E09.3 DB/RabbitMQ Provisioning

`roles/cloud_ui_provisioning` is the repository contract for one-time Cloud UI dependency
provisioning. It stores only object names and Vault secret references. It must not contain DB
passwords, RabbitMQ passwords, Vault tokens, openrc files or `clouds.yaml`.

Live E09.3 evidence is recorded in `docs/generated/e09-db-rabbitmq-provisioning.md`.
