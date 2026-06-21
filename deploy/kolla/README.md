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

## Lab registry prerequisite

The lab registry uses plain HTTP. Configure this only for the isolated lab.

On the build/control host, allow the registry in Podman:

```toml
# /etc/containers/registries.conf.d/999-dawn-lab.conf
[[registry]]
location = "192.168.10.15:5000"
insecure = true
```

Then restart the Podman API socket:

```bash
systemctl restart podman.socket
```

On the AIO Docker host, merge the registry into `/etc/docker/daemon.json`
without dropping existing keys:

```json
{
  "insecure-registries": ["192.168.10.15:5000"]
}
```

Then reload Docker:

```bash
systemctl reload docker
```

Example from the build/control host:

```bash
KOLLA_BUILD=/root/venvs/kolla-epoxy/bin/kolla-build \
  CLOUD_UI_REGISTRY=192.168.10.15:5000 \
  CLOUD_UI_TAG=2025.1-rocky-9 \
  deploy/kolla/scripts/build-images.sh
```

## Lab deploy and smoke

Create an untracked vars file on the build/control host, for example
`/root/dawn-cloud-ui-lab-secrets.yml`, containing:

```yaml
cloud_ui_database_url: "mysql+pymysql://..."
cloud_ui_rabbitmq_url: "amqp://..."
```

Then run:

```bash
/root/venvs/kolla-epoxy/bin/ansible-playbook \
  -i deploy/kolla/lab/inventory.ini.example \
  -e @deploy/kolla/lab/group_vars/all.yml.example \
  -e @/root/dawn-cloud-ui-lab-secrets.yml \
  deploy/kolla/lab/playbooks/deploy.yml

/root/venvs/kolla-epoxy/bin/ansible-playbook \
  -i deploy/kolla/lab/inventory.ini.example \
  -e @deploy/kolla/lab/group_vars/all.yml.example \
  -e @/root/dawn-cloud-ui-lab-secrets.yml \
  deploy/kolla/lab/playbooks/smoke.yml
```

The smoke playbook verifies API live/ready, frontend HTTP 200, expected image
pairs, Docker health status and absence of the supplied DB/RabbitMQ URLs in
Dawn container logs.

Default lab endpoints after deploy:

- API: `http://192.168.10.14:18081`
- frontend: `http://192.168.10.14:13080`

## Safety

- no production inventory;
- no real secrets in Git;
- no `latest` tag;
- no OpenStack service DB changes;
- rollback removes only Dawn custom containers and generated Dawn config.
