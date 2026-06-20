# Dawn Kolla lab prototype

This directory contains the lab-only E01.5 Kolla Build prototype for Dawn. It is not the final E09 production Kolla-Ansible role.

It packages Dawn as exactly two custom images for the lab:

- `cloud-ui-backend`
- `cloud-ui-frontend`

The backend image is shared by these commands:

```text
cloud-ui api
cloud-ui worker
cloud-ui events
cloud-ui db-upgrade
cloud-ui smoke
```

## Lab topology

- build/control host: `192.168.10.15`
- test registry: `192.168.10.15:5000`
- deploy target: `192.168.10.14`

## Required operator inputs

Real database and RabbitMQ connection strings are never committed. Operators must supply these values through an untracked file, environment-specific secret store, or lab host environment:

- `cloud_ui_database_url`
- `cloud_ui_rabbitmq_url`

## Kolla Build checks

```bash
kolla-build --config-file deploy/kolla/kolla-build.conf.example \
  --docker-dir deploy/kolla/docker \
  --list-images '^cloud-ui-(backend|frontend)$'

kolla-build --config-file deploy/kolla/kolla-build.conf.example \
  --docker-dir deploy/kolla/docker \
  --template-only '^cloud-ui-(backend|frontend)$'
```

Use the later `deploy/kolla/scripts/build-images.sh` script for the lab build and push flow.

## Safety

- no production inventory;
- no real secrets in Git;
- no `latest` tag;
- no OpenStack service DB changes;
- rollback removes only Dawn custom containers and generated Dawn config.
