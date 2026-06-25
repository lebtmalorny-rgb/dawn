# E09.8 Deployment Smoke Evidence Design

## Decision

Implement E09.8 as a controlled live smoke and evidence run on the approved test stand. The run uses
read-only preflight first, then a bounded test-inventory `kolla-ansible reconfigure` and idempotency
check only after the stand is positively identified as non-production.

This design intentionally does not support production execution. Any missing test-stand marker,
registry digest, rollback window, or explicit inventory path stops the run before a mutating command.

## Goals

- Prove the E09 deployment surface with observable test-stand evidence:
  - two custom images;
  - twelve permanent Cloud UI containers across three control/UI nodes;
  - one-shot migration evidence;
  - image digests;
  - user, capabilities, mounts, read-only filesystem and SELinux labels;
  - DB/RabbitMQ access boundaries;
  - HAProxy/TLS health;
  - no secret leakage in generated evidence;
  - API/UI smoke.
- Preserve the existing E09 contracts for build, provisioning, migration, process topology, HAProxy
  and lifecycle ordering.
- Record gaps honestly when an external control is still pending.

## Non-Goals

- No production deploy, reconfigure, rollback, stop, destroy or uninstall.
- No storage of real inventory, credentials, private keys, `.env`, `clouds.yaml`, `openrc`, cookies
  or tokens in Git.
- No direct browser calls to OpenStack APIs.
- No claim that ДКБ-69 is closed without the Python interpreter waiver and scanner/signature policy.
- No destructive cleanup of database, RabbitMQ vhost, Vault paths or logs.

## Execution Model

The implementation adds a repository evidence runner and tests, not hard-coded stand secrets.

The runner accepts explicit test-stand inputs through command-line options or environment variables:
inventory path, limit/group, expected external URL, previous and current image digests, and an output
path under `docs/generated/`. Credentials remain outside the repository and are consumed only by the
operator shell or approved secret mechanism.

The runner has three stages:

1. **Preflight, read-only**
   Validate that the inventory path is outside production naming, contains the required test marker,
   has exactly the expected Cloud UI groups, and uses digest-pinned images. Collect read-only
   repository and stand metadata. No mutating command is allowed in this stage.
2. **Controlled reconfigure and smoke**
   Run the approved test-inventory reconfigure command, then rerun it for idempotency. Collect
   container count, image digest, user/cap/mount/SELinux inspection, DB/MQ probe summaries, HAProxy
   health and API/UI smoke results.
3. **Rollback evidence gate**
   Record whether failed-update rollback was executed on the test stand. If rollback is not executed,
   evidence remains partial and E09 acceptance is not claimed.

## Fail-Closed Rules

The runner exits non-zero before mutating the stand when any of these conditions is true:

- inventory path is missing;
- inventory lacks the explicit test marker;
- inventory or command text resembles production;
- image references are tags without digests;
- expected container topology is not three nodes x four permanent services;
- rollback window is not explicitly marked open;
- output path is outside `docs/generated/`;
- evidence payload contains secret-like strings.

## Artifacts

- `docs/execplans/E09-deployment-smoke-evidence.md`
- `tests/test_e09_deployment_smoke_evidence.py`
- `deploy/kolla/scripts/collect-e09-evidence.sh` or an equivalent typed Python CLI if the repository
  patterns favor Python testing and structured output.
- `docs/generated/e09-deployment-smoke-evidence.md`
- Updates to `docs/11_DKB_TRACEABILITY.md` and `docs/generated/risk-register.md`.

## Testing

Tests cover both safe and unsafe paths:

- generated command plan refuses to run without a test marker;
- production-looking inventory names are rejected;
- non-digest image references are rejected;
- evidence schema requires the E09 acceptance fields;
- secret-like values are redacted or fail the run;
- partial evidence does not claim live rollback or full DKB closure;
- successful sample evidence records the two-image and twelve-container facts.

Repository verification remains:

- E09 targeted tests;
- root `tests`;
- `make lint`;
- `make typecheck`;
- `make security`;
- `make test`;
- `git diff --check`.

Live stand verification is recorded as command output summaries in the generated evidence document.

## DKB Scope

- ДКБ-22.02/24: TLS and health evidence can be linked if the test URL and certificate checks pass.
- ДКБ-42-44/77/80: network and ACL evidence can be attached only from the test stand.
- ДКБ-55/56: secret handling remains external; the runner must not store or print secrets.
- ДКБ-65: SELinux/capability/mount evidence is collected from container inspection.
- ДКБ-69/70: digest/SBOM/scan/signature evidence can be linked, but ДКБ-69 remains open without
  approved interpreter waiver.
- ДКБ-82: deployment lifecycle evidence improves, but full acceptance requires rollback execution.

## Rollback

Repository rollback is a Git revert of the E09.8 commits. Test-stand rollback follows the E09.7
failed-update rollback phases: stop rollout, restore previous config commit and image digests, rerun
test reconfigure, smoke previous version and preserve operations, audit events, read model and queued
messages.
