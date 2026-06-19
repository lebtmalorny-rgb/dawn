# ADR-006: Runtime and package versions

- Status: accepted
- Stage: E01
- Owner: user/platform, accepted 2026-06-19

## Context

E01 requires accepted runtime/package versions before code. Local macOS versions are not target evidence. Target must align with Rocky Linux, Kolla base image and currently supported LTS runtimes.

## Decision

- Backend: Python 3.11.
- Frontend: Node.js 24 LTS.
- Frontend package manager: npm.
- Backend dependency workflow: lockable Python environment compatible with Rocky/Kolla images; do not rely on local Python 3.14.
- All versions pinned by lock files.
- Container build/smoke evidence should run on Rocky/ansible host when local Docker is unavailable.

## Remaining non-blocking gaps

- Ansible host is Rocky Linux 9.5; OpenStack all-in-one host is Rocky Linux 9.8.
- Kolla containers use images tagged `quay.io/openstack.kolla/*:2025.1-rocky-9`; exact base digest is still unknown.
- CI runner OS unknown.

## Consequences

- E01 is unblocked.
- Do not use local Python 3.14 or Node 25 as target runtime.
- Use npm rather than pnpm for E01 to reduce bootstrap dependencies.
- Revisit runtimes before production pilot if corporate policy requires a different LTS line.

## Verification

- `python --version`, `node --version`, package manager versions from target/CI.
- Lock files committed in E01.
- Build works on approved Rocky/Kolla baseline.

## Observed deployment versions

- Kolla-Ansible: `20.4.1.dev5` in `/root/venvs/kolla-epoxy`.
- Ansible core in Kolla venv: `2.18.17`.
- OpenStack CLI in Kolla venv: `7.5.0`.
- OpenStack host Docker: `29.5.2`.
- Kolla Build: `20.4.0` in `/root/venvs/kolla-epoxy`.
- Ansible host build runtime: Podman `5.2.2`, Python `podman` package `5.8.0`.
