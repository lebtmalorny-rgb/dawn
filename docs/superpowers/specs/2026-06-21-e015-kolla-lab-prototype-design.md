# E01.5 Kolla Lab Prototype Design

## Purpose

E01.5 proves that the Dawn source application can be packaged and deployed through a Kolla-shaped flow in the lab before the project moves deeper into application features. This is a lab-only prototype, not full E09 production deployment acceptance.

The prototype targets:

- build two custom images with `kolla-build`;
- publish them to a test registry on the Ansible host;
- deploy a minimal single-node instance on the existing OpenStack AIO host;
- run smoke verification;
- provide a safe rollback path that removes the custom Dawn containers and config.

## Chosen Approach

Use a single-node lab prototype:

- control/build host: `192.168.10.15`;
- deploy target: `192.168.10.14`;
- test registry: `192.168.10.15:5000`;
- Kolla baseline: existing lab Kolla 2025.1 / Rocky 9 tooling;
- image count: exactly two custom images, `cloud-ui-backend` and `cloud-ui-frontend`.

This deliberately avoids the full three-node, 12-container E09 acceptance target. The goal is to validate image layout, registry flow and a minimal deploy shape early, without claiming hardening, HA, production TLS or DKB closure.

## Kolla Build Layout

Add a Kolla build layout under `deploy/kolla/`:

```text
deploy/kolla/
  README.md
  kolla-build.conf.example
  docker/
    cloud-ui-backend/
      Dockerfile.j2
    cloud-ui-frontend/
      Dockerfile.j2
```

The templates are consumed through `kolla-build --docker-dir deploy/kolla/docker`, matching the Kolla-supported external template mechanism. The backend image installs the Python package and keeps one image for `api`, `worker`, `events`, `db-upgrade` and `smoke`. The frontend image builds the React application and serves static assets with an unprivileged nginx runtime.

The E01 Dockerfiles remain the local-compose developer path. The Kolla templates are the lab/Kolla packaging path.

## Registry And Image Flow

The Ansible host owns image build and publish:

1. Ensure a lab registry is running on `192.168.10.15:5000`.
2. Build `cloud-ui-backend` and `cloud-ui-frontend` with Kolla tooling.
3. Tag images with the lab Kolla tag, for example `2025.1-rocky-9`.
4. Push both images to the test registry.
5. Configure the AIO host to pull from the test registry.

The prototype must not require production registry access and must not use `latest`.

## Deployment Prototype

Add a minimal lab deployment layer under `deploy/kolla/lab/`:

```text
deploy/kolla/lab/
  inventory.ini.example
  group_vars/
    all.yml.example
  playbooks/
    deploy.yml
    smoke.yml
    rollback.yml
```

The lab deploy starts custom Dawn containers on the AIO host using Kolla-compatible naming and config conventions, but it does not attempt to become the final Kolla-Ansible role.

Minimum runtime containers for the single-node prototype:

- `cloud_ui_api`;
- `cloud_ui_worker`;
- `cloud_ui_events`;
- `cloud_ui_frontend`;
- one migration execution before API rollout, either as a one-shot container or explicit command task.

The prototype may use lab MariaDB/RabbitMQ access from the existing OpenStack/Kolla environment or dedicated lab-local credentials created outside Git. Real secrets stay on the lab hosts and are never committed.

## Network And Smoke

The first smoke target is a direct lab endpoint exposed only on the AIO host or lab management network. HAProxy/TLS integration is allowed only if it can be done safely and reversibly without changing production-like OpenStack services.

Smoke verifies:

- backend live/readiness endpoints;
- frontend static response;
- worker/events containers running;
- image identity and tag;
- no secrets printed into logs;
- rollback removes custom containers.

If direct local port access is blocked by the Codex sandbox, smoke may be run through SSH on the lab host and recorded as such.

## Rollback

Rollback is part of the prototype, not a later cleanup:

- stop and remove custom Dawn containers;
- remove generated custom config files;
- leave unrelated OpenStack/Kolla services untouched;
- do not remove shared MariaDB/RabbitMQ services;
- preserve logs needed for evidence;
- prove the rollback with container listing after removal.

## Safety Boundaries

E01.5 must not:

- deploy to production;
- edit production inventory;
- store real credentials in Git;
- change OpenStack service databases;
- change existing Horizon/Keystone/HAProxy behavior unless explicitly isolated and reversible;
- claim E09 HA, hardening, SBOM, scan, digest pinning or three-node acceptance;
- create separate backend images for API, worker and events.

## Verification

The implementation plan must include these checks:

- `kolla-build --docker-dir deploy/kolla/docker --list-images cloud-ui`;
- `kolla-build --docker-dir deploy/kolla/docker --template-only cloud-ui`;
- build and push exactly two custom images to `192.168.10.15:5000`;
- inspect pushed image names and tags;
- deploy single-node lab containers on `192.168.10.14`;
- run smoke against the lab endpoint;
- run rollback and prove custom containers are gone;
- run repository quality checks and `./scripts/secret-scan.sh`.

## Documentation Updates

Implementation must update:

- `docs/execplans/` with E01.5 evidence;
- `docs/generated/current-state.md` with lab prototype state;
- `FILE_INDEX.md` with the new Kolla prototype files;
- deployment notes clarifying that full Kolla-Ansible role acceptance remains E09.

## Open Decisions Deferred To E09

The following are intentionally deferred:

- three-node rollout;
- HAProxy production route;
- production TLS policy;
- image digest pinning, SBOM and vulnerability scan evidence;
- SELinux/capability hardening acceptance;
- least-privilege DB/RabbitMQ production model;
- rolling upgrade and failed-update rollback.
