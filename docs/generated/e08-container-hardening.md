# E08.5 Container Hardening Evidence

- Stage: E08.5
- Date: 2026-06-23
- Scope: local portal-owned app containers in `compose.yaml`
- Rule: this artifact contains no real secret, registry credential, production endpoint or private key.

## Covered Runtime Containers

This slice covers only the portal-owned app containers:

- `api`;
- `worker`;
- `events`;
- `frontend`.

The local PoC `db` and `rabbitmq` services are stateful dependency containers and are not treated as
custom portal runtime images in this evidence. Their production hardening, credentials, persistence and
TLS policy remain E09/deployment work.

## Implemented Controls

`compose.yaml` now applies the following controls to every covered app service:

- `read_only: true`;
- `cap_drop: ["ALL"]`;
- `security_opt: ["no-new-privileges:true"]`;
- no `privileged: true`;
- no Docker/Podman socket mount;
- no host-root mount;
- explicit `tmpfs` writable paths.

Backend app services use writable `/tmp` only. The frontend Nginx runtime uses writable `/tmp`,
`/var/cache/nginx` and `/var/run` tmpfs paths for runtime pid/cache/temp data while keeping the root
filesystem read-only. The Nginx writable tmpfs paths are owned by UID/GID `101`, matching the
unprivileged frontend runtime user.

## Dockerfile Evidence

Backend:

- uses separate `builder` and `runtime` stages;
- builds a wheel in the builder stage;
- installs only from the wheel directory in the runtime stage;
- runs as `USER cloudui`;
- does not copy `.env`, `tests`, `.venv` or `node_modules` into the runtime stage.

Frontend:

- uses Node only in the `build` stage;
- uses `nginxinc/nginx-unprivileged:1.27-alpine` in the runtime stage;
- copies only built static assets into runtime;
- sets explicit `USER 101`;
- does not run npm/node install commands in runtime.

## Tests

Repository regression coverage:

- `backend/tests/security/test_e08_container_hardening.py`
  - validates compose app-service read-only/capability/no-new-privileges/tmpfs settings;
  - rejects privileged app services and socket/host-root mounts;
  - validates frontend Nginx writable tmpfs ownership for UID/GID `101`;
  - validates backend Dockerfile build/runtime separation and non-root runtime;
  - validates frontend runtime excludes the Node toolchain path.

RED/GREEN evidence:

- RED: the new test file failed with 2 expected failures because `api` lacked `read_only` and `tmpfs`.
- RED: the frontend tmpfs ownership regression failed because `/var/cache/nginx` lacked `uid=101`.
- GREEN: the same test file passed `5 passed` after compose/frontend Dockerfile changes.

## Docker Build And Inspection

Local Docker evidence:

- `docker compose build api frontend` completed successfully and exported
  `cloud-ui-backend:dev` and `cloud-ui-frontend:dev`.
- `docker image inspect cloud-ui-backend:dev` reported `user=cloudui`,
  `cmd=["cloud-ui","api"]` and local image ID
  `sha256:c49afbd08617150145ca307a53eed93724ac35bd6034caa473a9a87a7bd4f555`.
- `docker image inspect cloud-ui-frontend:dev` reported `user=101`,
  `entrypoint=["/docker-entrypoint.sh"]`, `cmd=["nginx","-g","daemon off;"]` and local image ID
  `sha256:df8e9bf43ad3faa863f4f9fd6f360d55aa77d207a14fe1510a2daeabd8ea2705`.
- `docker run --rm --entrypoint id cloud-ui-backend:dev -u` returned `100`.
- `docker run --rm --entrypoint id cloud-ui-frontend:dev -u` returned `101`.
- `docker compose config --format json` confirmed the covered app services expand to
  `read_only: true`, `cap_drop: ["ALL"]`, `security_opt: ["no-new-privileges:true"]` and explicit
  `tmpfs` paths.
- `docker run --rm --read-only --cap-drop ALL --security-opt no-new-privileges --tmpfs ...`
  confirmed backend `cloud-ui --help` runs under the hardened runtime flags.
- `docker run --rm --read-only --cap-drop ALL --security-opt no-new-privileges --add-host
  api:127.0.0.1 --tmpfs ... cloud-ui-frontend:dev nginx -t` confirmed the frontend Nginx
  configuration test passes under the hardened runtime flags and UID/GID-owned tmpfs paths.

This artifact does not claim registry push, signed provenance or production digest evidence.

## Residual Gaps

- ДКБ-65: SELinux enforcing mode, labels and denial evidence require a Rocky test host and are not
  closed by local Docker Desktop checks.
- ДКБ-69: the backend requires a Python interpreter. The current base images may still include shell
  or package-manager components inherited from upstream images. This remains a formal waiver/gap; it
  must not be hidden by non-root/read-only/cap-drop evidence.
- ДКБ-70: no corporate registry push or immutable digest evidence is created in this slice.
- Supply-chain evidence such as SBOM, vulnerability policy, image signing/provenance and license
  inventory remains E08.6/E09.
- Kolla/Kolla-Ansible production container definitions are not restored or modified in this slice.

## Rollback

Revert the E08.5 commit. No database schema, external registry, remote host, Vault path, queue or
production secret is changed. Rollback returns local app containers to the previous default writable
root filesystem and default capability behavior.
