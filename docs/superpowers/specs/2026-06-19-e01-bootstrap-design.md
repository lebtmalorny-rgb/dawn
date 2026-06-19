# E01 Bootstrap Design

## Goal

Implement the first reproducible project slice for the cloud UI repository. E01 creates the monorepo skeleton, local development profile, two runtime images and quality commands. It does not implement authentication, RBAC, OpenStack adapters, inventory, workflows or production Kolla deployment.

## Accepted Decisions

- Git repository: `https://github.com/lebtmalorny-rgb/dawn.git` as `origin`.
- Backend runtime: Python 3.11.
- Frontend runtime: Node.js 24 LTS with npm.
- Backend dependency workflow: lockable Python environment compatible with Rocky/Kolla images; no reliance on local Python 3.14.
- Development location: source editing may happen locally; container build/smoke evidence should run on Rocky/ansible host when local Docker is unavailable.
- Custom runtime images: exactly two, one frontend image and one backend image.

## Repository Shape

E01 creates or normalizes:

```text
backend/
frontend/
deploy/
tests/
docs/execplans/
docs/adr/
artifacts/
compose.yaml
Makefile
```

Existing local `AGENTS.md` files remain in place and continue to scope backend, frontend, deploy and security work.

## Backend Design

The backend is one Python package exposing four commands:

- `cloud-ui api`
- `cloud-ui worker`
- `cloud-ui events`
- `cloud-ui db-upgrade`

The API provides `/health/live` and `/health/ready`. Liveness only proves the process is responsive. Readiness checks MariaDB and RabbitMQ using bounded timeouts and returns a safe structured error when dependencies are down. API startup must not run migrations automatically; migrations are a separate command/job.

Settings are typed and loaded from environment variables. Logs are JSON and include request ID/correlation ID. Config values and secrets are never written to logs.

## Frontend Design

The frontend is a minimal application shell with a status view. It calls the backend readiness endpoint and renders service state without exposing config or secrets. There is no OpenStack UI in E01.

The frontend uses Node.js 24 LTS and npm lock files. It should be small, functional and operational rather than decorative.

## Local Services

`compose.yaml` starts:

- backend API
- backend worker
- backend events
- optional migration job/command path
- frontend
- MariaDB
- RabbitMQ

Development credentials are dummy-only and must be documented as local test values. They must not resemble real OpenStack, Vault, SIEM or production credentials.

## Images

E01 produces exactly two custom runtime images:

- frontend runtime image
- backend runtime image

The same backend image runs API, worker, events and migrations via different commands. Containers run as non-root and have health checks. Image build must not bake secrets into layers, environment or frontend assets.

## Commands

The Makefile exposes:

```text
make bootstrap
make format
make lint
make typecheck
make test
make build
make up
make down
make smoke
```

`make smoke` verifies that frontend, API, MariaDB and RabbitMQ are reachable and that readiness reflects dependency state.

## Error Handling

Dependency failures return bounded, typed readiness failures. API config errors fail startup with safe messages. Worker/events processes log startup, shutdown and dependency errors without dumping config values.

## Testing

E01 includes unit tests that run without network access. Smoke tests may use compose and are allowed to require a container runtime. Negative tests cover missing required config, dependency readiness failure and secret redaction.

## Out Of Scope

- Auth, session security and RBAC.
- OpenStack API calls.
- Mistral workflow publication.
- Inventory/read model beyond health scaffolding.
- Production Kolla role and registry push.
- SIEM/Vault integration beyond config placeholders and no-secret rules.

## Acceptance

- Git repo is initialized locally with `origin` set to the approved GitHub URL.
- ADR-006 is accepted for E01 runtimes.
- `make up` starts the local stack.
- UI displays API readiness.
- `make smoke` passes in the supported container environment.
- API, worker and events use one backend image.
- There are exactly two custom runtime images.
- Migration is a separate command/job.
- Required commands exist and run.
- Containers run non-root.
- Secret scan does not find real secrets or provided lab passwords.
