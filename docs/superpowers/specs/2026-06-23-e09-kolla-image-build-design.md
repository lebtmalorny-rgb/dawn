# E09.1 Kolla Image Build Design

## Purpose

E09 starts the Kolla deployment stage. The first slice creates repository-owned Kolla Build
artifacts for the portal images without pretending that a live registry push or Kolla-Ansible rollout
has happened.

After this slice, an operator can inspect and test a reproducible build contract for exactly two
custom images:

- `cloud-ui-backend`;
- `cloud-ui-frontend`.

The backend image remains the single runtime image for `cloud-ui api`, `cloud-ui worker`,
`cloud-ui events`, `cloud-ui db-upgrade` and `cloud-ui smoke`.

## Scope

This design covers only E09.1.

Included:

- Kolla Build configuration example for Rocky/Kolla 2025.1 baseline.
- Jinja Dockerfile templates for `cloud-ui-backend` and `cloud-ui-frontend`.
- A reproducible build script/runbook that rejects `latest` and requires an explicit test registry,
  tag and source pin before push.
- Generated evidence documenting the build contract, pending external registry/SBOM/scan evidence and
  DKB impact.
- Tests that validate the two-image contract, source pin/version label expectations, no committed
  secrets and no separate backend process images.
- DKB traceability and risk-register updates for deployment/supply-chain evidence.

Excluded:

- No live Kolla-Ansible deployment.
- No production or test-host SSH.
- No live registry login, push, signing or vulnerability scan without explicit test credentials.
- No DB/RabbitMQ provisioning, HAProxy/TLS rollout, migration job execution, SELinux host validation,
  container count proof or rollback execution. These remain E09.2-E09.8.

## Current Repository Facts

- `backend/Dockerfile` and `frontend/Dockerfile` already build local compose images with pinned base
  digests.
- `compose.yaml` runs one backend image as API, worker and events services, and one frontend image.
- `backend/src/cloud_ui/cli.py` already exposes `api`, `worker`, `events`, `db-upgrade` and `smoke`.
- `tests/test_e015_kolla_layout.py` already expects `deploy/kolla/...` files, but the current tree
  only has `deploy/AGENTS.md` and `deploy/env.example`.
- E08 security review allows continuing into deployment evidence but keeps corporate registry,
  signing, SELinux, network-zone proof and the DKB-69 interpreter waiver as external conditions.

## Architecture

The build artifacts live under `deploy/kolla/`:

- `kolla-build.conf.example` declares the local Kolla build settings and the two custom images.
- `docker/cloud-ui-backend/Dockerfile.j2` installs the portal backend package into a Kolla-compatible
  backend runtime image and documents the supported commands.
- `docker/cloud-ui-frontend/Dockerfile.j2` serves prebuilt frontend static assets and does not include
  Node/npm in runtime.
- `scripts/build-images.sh` is the operator entrypoint for deterministic build/push-by-digest flow.
- `README.md` explains the dry-run/build/push evidence flow and explicitly forbids `latest`.

The script should fail closed when required context is absent: test registry, immutable tag, source
pin and source archive/build context paths must be explicit. It must not embed secrets or production
endpoints.

## Data and Secret Flow

No runtime secret is baked into images.

The build contract allows only non-secret metadata:

- image names;
- immutable tag;
- source commit/archive pin;
- OCI labels;
- digest/SBOM/scan artifact paths.

Registry credentials, signing keys, scanner tokens and Kolla passwords stay outside Git and are
provided only by the test deployment mechanism in later slices.

## Error Handling

Build tooling errors should be early and explicit:

- missing test registry or tag;
- tag equal to `latest`;
- missing source pin;
- attempt to declare extra backend images;
- missing evidence artifact path when recording completed registry/SBOM/scan proof.

Live external failures are not simulated as success. If registry, scanner or signing service is not
available, evidence remains `pending_external_evidence`.

## Testing

The E09.1 test suite validates repository artifacts, not live infrastructure:

- exactly two custom image definitions exist;
- no `latest` tag appears in Kolla build config or scripts;
- backend template supports all required commands through one image;
- frontend template uses prebuilt static assets and has no Node/npm runtime;
- build/runbook artifacts do not contain committed passwords, tokens, private keys or production URLs;
- generated evidence names the pending registry/SBOM/scan gaps and affected DKB codes.

Relevant final checks for the implementation slice:

- targeted E09 deployment tests;
- `make lint`;
- `make typecheck`;
- `make test`;
- `make security`;
- `git diff --check`.

## DKB Impact

- ДКБ-69: this slice can improve image minimization evidence and document backend interpreter
  constraints, but it cannot close the Python interpreter conflict.
- ДКБ-70: this slice creates the registry/pull-by-digest contract; live corporate test registry push,
  signing and scanner evidence remain external until credentials and registry are provided.
- ДКБ-76/77/80: this slice documents deployment interfaces and Kolla image inputs; network ACLs,
  disabled unused interfaces and management-zone proof remain later E09 evidence.
- ДКБ-55/56: no secrets are added to Git; production secret injection and rotation remain later
  deployment evidence.

## Acceptance for This Slice

E09.1 is complete when the repository contains the build contract, tests pass, generated evidence is
updated, and traceability states what is implemented versus what remains pending. It is not complete
for the full E09 stage and must not claim 12 containers, HAProxy/TLS, DB/MQ provisioning, SELinux host
proof, registry signing or rollback execution.

## Rollback

Rollback is a normal Git revert of the E09.1 commit. No database schema, queue, registry, remote host,
Vault path, Kolla inventory or production credential is modified by this slice.
