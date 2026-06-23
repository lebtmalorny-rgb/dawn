# ExecPlan: E08 Container Hardening

## Цель и наблюдаемый результат

После E08.5 локальные runtime definitions для собственных контейнеров портала (`api`, `worker`,
`events`, `frontend`) будут запускаться с проверяемыми hardening controls: non-root runtime user,
`read_only` root filesystem, `cap_drop: ALL`, `no-new-privileges`, controlled writable `tmpfs` paths
and no container/host socket mounts. Backend and frontend Dockerfiles will have repository tests that
prove the app runtime images keep build toolchains out of the final stage where the current base allows
it, and generated evidence will state the remaining ДКБ-69 shell/interpreter/package-manager gaps.

Before this slice, backend and frontend Dockerfiles exist and are multi-stage, but there is no
repository test/evidence for image user/capability/mount policy. `compose.yaml` starts app containers
without explicit read-only root filesystem, capability drop or no-new-privileges settings.

## Контекст и текущее состояние

- Repository root for this slice:
  `/Users/dmitry/Desktop/dawn/.worktrees/e08-container-hardening`.
- Branch/worktree: `e08-container-hardening`.
- Base commit: `3f57dce Merge pull request #4 from lebtmalorny-rgb/e08-session-token-protection`.
- Existing local images:
  - `backend/Dockerfile`: Python 3.11 slim builder + Python 3.11 slim runtime, adds `cloudui` user,
    installs local wheel and uses `USER cloudui`.
  - `frontend/Dockerfile`: Node 24 Alpine build stage and `nginxinc/nginx-unprivileged:1.27-alpine`
    runtime stage.
- Existing local compose:
  - `compose.yaml` uses `cloud-ui-backend:dev` for `api`, `worker`, `events` and
    `cloud-ui-frontend:dev` for `frontend`.
  - `db` and `rabbitmq` are local PoC stateful dependencies, not custom portal runtime images.
- Existing Kolla prototype test `tests/test_e015_kolla_layout.py` references `deploy/kolla/*`, but
  those files are absent in current root state; this is already tracked as risk R-052 and is not an
  E08.5 gate unless the Kolla prototype is restored explicitly.
- Baseline setup:
  - `make bootstrap PYTHON=/Users/dmitry/Desktop/dawn/backend/.venv/bin/python` succeeded.
  - `make lint` passed.
  - `make typecheck` passed.
  - `make test` passed: backend `311 passed, 1 skipped`; frontend `35 passed`.
  - Local Node is `v25.9.0`, outside declared frontend engine `>=24 <25`, but baseline gates pass.

## Scope

- Add repository tests for Dockerfile and compose hardening.
- Harden only the portal-owned local compose app services: `api`, `worker`, `events`, `frontend`.
- Make Dockerfile runtime intent explicit where safe: non-root runtime user and build-stage isolation.
- Add generated E08.5 evidence for container hardening, SELinux blocker/gap and ДКБ-69 conflict.
- Update risk register and DKB traceability for container hardening evidence.
- Run local Docker build/inspection where the daemon supports it, without production credentials or
  external registry push.

## Non-goals

- No E09 Kolla role/template restoration in this slice.
- No corporate registry, image signing, SBOM/vulnerability policy closure; those remain E08.6/E09.
- No production SELinux host validation. If no Rocky test host is used in this slice, document the
  blocker explicitly.
- No distroless/base-image replacement without ADR. Python backend still needs a Python interpreter;
  frontend Nginx image may still contain a shell/package manager inherited from the base.
- No secrets, `.env`, openrc, `clouds.yaml`, private keys or production URLs.
- No changes to DB schema, API contracts, sessions, RBAC, workflow execution or audit delivery.

## Требования и ограничения

- Browser still talks only to frontend/BFF/API; no direct OpenStack calls.
- Containers must not mount Docker/Podman socket or host root.
- Runtime containers should run non-root, drop Linux capabilities, set no-new-privileges and use a
  read-only root filesystem where possible.
- Writable paths must be explicit tmpfs/named volumes. For this slice only app containers get tmpfs;
  stateful MariaDB/RabbitMQ hardening is out of scope for custom portal image evidence.
- Build/runtime separation must keep Node/npm out of the frontend runtime and avoid copying source
  secrets or `.env` into image contexts.
- ДКБ-69 cannot be claimed closed for the Python backend because an interpreter is required and the
  current base image may still include shell/package-manager components.

## Связь с ДКБ

- ДКБ-65: this slice documents container hardening controls and SELinux evidence gap. Full Rocky
  SELinux enforcing/label/denial proof remains external/E09.
- ДКБ-69: this slice reduces container runtime risk with non-root, read-only FS, cap drop and build
  isolation tests, but does not claim interpreter/shell absence for Python backend.
- ДКБ-70: no registry push/signing is implemented; evidence notes that digest/registry proof remains
  E08.6/E09.
- ДКБ-76: containerization controls are partially evidenced for portal app containers; full runtime
  platform requirements remain to be detailed.
- ДКБ-77/80: unused direct host/socket interfaces are blocked in compose by tests; network/firewall
  deployment proof remains E09.

## Milestones

1. RED tests for Dockerfile and compose hardening.
2. Minimal compose/Dockerfile hardening until tests pass.
3. Generated evidence and DKB/risk updates.
4. Docker build/inspection and full verification.
5. Commit, push and PR.

## Progress

- [x] 2026-06-23: Baseline setup and checks passed before changes. Evidence: `make lint`,
  `make typecheck`, `make test` passed; `make test` reported backend `311 passed, 1 skipped` and
  frontend `35 passed`.
- [x] RED tests for Dockerfile/compose hardening. Evidence: `cd backend && .venv/bin/python -m
  pytest tests/security/test_e08_container_hardening.py -q` failed with 2 expected failures because
  `api` lacked `read_only` and `tmpfs`.
- [x] Minimal hardening implementation. Evidence: same targeted test passed `4 passed`.
- [x] RED/GREEN follow-up for frontend tmpfs ownership. Evidence: hardened `nginx -t` smoke exposed
  root-owned tmpfs for `/var/cache/nginx`; a regression test then failed because `uid=101` was
  missing, and passed after adding UID/GID-owned frontend tmpfs paths.
- [x] Evidence docs and traceability. Evidence: added
  `docs/generated/e08-container-hardening.md`, updated `docs/generated/risk-register.md` and
  `docs/11_DKB_TRACEABILITY.md`.
- [x] Final verification and review. Evidence: targeted E08.5 test `5 passed`; `make lint`,
  `make typecheck`, `make test`, `make test-integration`, `make security`,
  `docker compose build api frontend`, `docker compose config --quiet` and `git diff --check`
  passed. `make test` reported backend `316 passed, 1 skipped` and frontend `35 passed`;
  `make test-integration` reported `21 passed, 1 skipped`.

## Неожиданные открытия

- 2026-06-23: `python3.11` is still absent on PATH; bootstrap reused the main checkout's Python 3.11
  venv interpreter to create this worktree's local `.venv`.
- 2026-06-23: `tests/test_e015_kolla_layout.py` references missing `deploy/kolla/*` files. This
  confirms R-052 and keeps E08.5 focused on current local Dockerfiles/compose rather than Kolla
  prototype restoration.
- 2026-06-23: Docker daemon is available locally (`29.0.1`) with Compose `v2.40.3-desktop.1`.
- 2026-06-23: Frontend Nginx needs UID/GID-owned tmpfs for `/var/cache/nginx` and `/var/run` when
  running as `USER 101` with a read-only root filesystem. Root-owned tmpfs caused `nginx -t` to fail
  with permission denied before the compose tmpfs options were tightened.

## Журнал решений

- 2026-06-23: Scope E08.5 to local portal-owned app containers and reproducible repository tests.
  Alternatives: restore Kolla prototype first, or switch base images to distroless. Reason: E09 owns
  Kolla deployment, and changing base images would require ADR/package compatibility work. Consequence:
  this slice produces concrete hardening and evidence without claiming full production image closure.
- 2026-06-23: Leave DB/RabbitMQ local PoC service hardening out of this slice. Reason: they are not
  custom portal runtime images and need stateful storage/credential work in E09. Consequence: evidence
  must clearly say app-container-only.

## Детальный план реализации

### Task 1: Hardening Tests

- Create `backend/tests/security/test_e08_container_hardening.py`.
- Parse `compose.yaml` with `yaml.safe_load`.
- Assert app services `api`, `worker`, `events`, `frontend` have:
  - `read_only: true`;
  - `cap_drop: ["ALL"]`;
  - `security_opt` containing `no-new-privileges:true`;
  - no `privileged: true`;
  - no bind to `/var/run/docker.sock`, `/run/podman/podman.sock` or host root;
  - controlled `tmpfs` paths.
- Assert backend Dockerfile:
  - has separate builder/runtime stages;
  - runtime stage has `USER cloudui`;
  - runtime stage does not copy `.env`, `tests`, `.venv`, `node_modules` or package lock secrets;
  - build stage creates wheels, runtime stage installs from wheels.
- Assert frontend Dockerfile:
  - has Node build stage and Nginx unprivileged runtime stage;
  - runtime stage does not contain Node/npm install commands;
  - runtime stage sets an explicit non-root user or uses an unprivileged image.
- Verify RED with:
  `cd backend && .venv/bin/python -m pytest tests/security/test_e08_container_hardening.py -q`.

### Task 2: Compose/Dockerfile Hardening

- Modify `compose.yaml` app services.
- Add shared hardening blocks if supported by Compose YAML anchors to keep duplication low:
  - backend services share read-only/caps/security/tmpfs settings;
  - frontend gets Nginx writable tmpfs paths.
- Make frontend runtime user explicit with `USER 101` if compatible with
  `nginxinc/nginx-unprivileged`.
- Keep backend runtime `USER cloudui`.
- Verify GREEN with the new targeted test.

### Task 3: Evidence Docs

- Create `docs/generated/e08-container-hardening.md` with:
  - app services covered;
  - Dockerfile build/runtime separation;
  - compose hardening controls;
  - Docker build/inspection command results;
  - SELinux blocker/gap;
  - ДКБ-69 interpreter/shell/package-manager limitation;
  - rollback procedure.
- Update `docs/generated/risk-register.md` for container hardening/DKB-69 risk.
- Update `docs/11_DKB_TRACEABILITY.md` with E08.5 evidence and residual conditions.

### Task 4: Verification And Commit

Run:

```bash
cd backend && .venv/bin/python -m pytest tests/security/test_e08_container_hardening.py -q
make lint
make typecheck
make test
make test-integration
make security
docker compose build api frontend
docker image inspect cloud-ui-backend:dev cloud-ui-frontend:dev
git diff --check
```

Review diff for:

- no secrets or production endpoints;
- no false claim that ДКБ-69 is closed;
- app containers have no socket/host-root mounts;
- mutating API/session/auth behavior unchanged.

Commit:

```bash
git add compose.yaml backend/Dockerfile frontend/Dockerfile backend/tests/security/test_e08_container_hardening.py docs/generated/e08-container-hardening.md docs/generated/risk-register.md docs/11_DKB_TRACEABILITY.md docs/execplans/E08-container-hardening.md
git commit -m "chore: harden portal app containers"
```

## Миграции и совместимость

No database migration. The compose changes are local/deployment configuration changes for app
containers. API behavior remains unchanged. Rolling update compatibility is unaffected because no
public contract or schema changes are introduced.

## Проверка

The final commands are listed in Task 4. Docker build/inspect evidence is local and does not push
images to a registry. If Docker build cannot pull base images due network/cache limits, record the
failure and keep repository tests as reproducible evidence; do not claim image inspection success.

## Доказательства

- `backend/tests/security/test_e08_container_hardening.py`.
- `docs/generated/e08-container-hardening.md`.
- Updated `docs/generated/risk-register.md`.
- Updated `docs/11_DKB_TRACEABILITY.md`.
- Docker build/inspect command output:
  - `docker compose build api frontend` built `cloud-ui-backend:dev` and
    `cloud-ui-frontend:dev`;
  - backend image inspect reported `user=cloudui`, and `id -u` in the image returned `100`;
  - frontend image inspect reported `user=101`, and `id -u` in the image returned `101`.
  - hardened one-off Docker runs confirmed backend `cloud-ui --help` and frontend `nginx -t` work
    with read-only rootfs, dropped capabilities, no-new-privileges and controlled tmpfs.
- This ExecPlan progress log.

## Откат и восстановление

Revert the E08.5 commit. No DB schema, external registry, remote host, queue, Vault path or production
secret is changed. If local compose hardening breaks a developer environment, rollback restores the
previous writable/default-capability app containers.

## Итог и остаточные риски

Implementation completed for E08.5. Residual risks:

- production Kolla/Kolla-Ansible templates and registry digest evidence remain E09;
- SBOM, vulnerability scan, provenance/signing remain E08.6;
- SELinux enforcing/labels/denial evidence requires a Rocky test host;
- ДКБ-69 interpreter/shell/package-manager absence remains a formal waiver/gap for Python backend and
  possibly inherited Nginx runtime base.
