# E09.3 Database/RabbitMQ Provisioning Design

## Context

E09.3 continues the Kolla deployment track after:

- E09.1 repository-side Kolla Build contract for the two Cloud UI images;
- E09.2 repository-side Kolla-Ansible role skeleton for the four permanent services.

This slice is approved for live test-stand work only. The test Ansible host is `192.168.10.15`, the
Kolla inventory is `/etc/kolla/all-in-one`, and the work is limited to Cloud UI-owned MariaDB,
RabbitMQ and Vault/SecMan resources. No production host, production inventory or production credential
is used.

The selected secret mechanism is a lab Vault/SecMan path on `192.168.10.15`. Precheck found Vault is
not currently active on that host, so E09.3 must first bootstrap a lab Vault before provisioning
MariaDB and RabbitMQ secrets.

## Goals

- Bootstrap lab Vault on `192.168.10.15` according to the E08 runbook without exposing root tokens,
  unseal keys, client tokens, private keys or secret values to the local workspace, logs or Git.
- Store Cloud UI DB/RabbitMQ secret material in Vault rather than repository files.
- Provision a Cloud UI-owned MariaDB schema and least-privilege users on the test Kolla deployment.
- Provision a Cloud UI-owned RabbitMQ vhost/user/exchange/queues/DLX with no access to OpenStack RPC
  exchanges.
- Add repository-side role/task contracts and static tests that document and guard the E09.3
  behavior.
- Record sanitized evidence and DKB traceability without claiming production compliance.

## Non-Goals

- No production Vault/SecMan claim.
- No corporate PKI claim; a lab CA is acceptable only as lab evidence if corporate/test PKI is not
  available.
- No Kolla role execution for permanent Cloud UI containers.
- No migration execution; E09.4 owns `cloud-ui db-upgrade`.
- No HAProxy/TLS portal route, 12-container rollout, rolling upgrade or rollback proof.
- No storage of `clouds.yaml`, openrc, `.env`, tokens, passwords, private keys or DB dumps in Git.

## Architecture

E09.3 has two layers.

### 1. Lab Vault Bootstrap

The remote host `192.168.10.15` becomes the lab secret store for E09.3:

- user/group: `vault:vault`;
- config: `/etc/vault.d/vault.hcl`, owned by `root:vault`, mode `0640`;
- data: `/opt/vault/data`, owned by `vault:vault`, mode `0700`;
- TLS cert/key: `/etc/vault.d/tls/vault.crt` and `/etc/vault.d/tls/vault.key`;
- listener: `192.168.10.15:8200`;
- cluster listener: `192.168.10.15:8201`;
- audit file: `/var/log/vault/audit.log`;
- KV v2 mount: `kv/`;
- Cloud UI lab secret paths under `kv/cloud-ui/local/*`.

Root token and unseal keys are written only to a root-only remote file if Vault initialization is
required. They are never printed in terminal output, copied locally or committed. Sanitized evidence
records only initialized/sealed state, listener state, CA fingerprint, certificate SANs and negative
access results.

### 2. DB/RabbitMQ Provisioning

The Cloud UI deployment resources are scoped to the test Kolla deployment:

- MariaDB database/schema: `cloud_ui`;
- MariaDB runtime user: `cloud_ui`;
- MariaDB migration user: `cloud_ui_migration`;
- RabbitMQ vhost: `/cloud-ui`;
- RabbitMQ user: `cloud_ui`;
- RabbitMQ resources:
  - `cloud-ui.events`;
  - `cloud-ui.jobs`;
  - `cloud-ui.audit`;
  - `cloud-ui.dlx`;
  - queues bound only to Cloud UI-owned exchanges.

Secret values are generated on the remote host and stored under Vault paths such as:

- `kv/cloud-ui/local/mariadb/runtime`;
- `kv/cloud-ui/local/mariadb/migration`;
- `kv/cloud-ui/local/rabbitmq/runtime`.

Repository files contain only secret references and sanitized evidence. The live provisioning path
uses Kolla/MariaDB/RabbitMQ administrative credentials already present on the test stand, but those
values are not read into repository files or displayed in evidence.

## Safety Rules

- Remote commands must disable shell tracing before sourcing openrc/password files or handling secret
  material.
- Commands may print object names, privilege summaries, health states and allow/deny outcomes.
- Commands must not print secret values, tokens, private keys, `passwords.yml`, `clouds.yaml`, openrc
  contents or SQL dumps.
- Negative checks must verify least privilege without selecting or dumping sensitive data.
- Any live command that would affect resources outside `cloud_ui` or `/cloud-ui` is out of scope.

## Repository Changes

Planned repository artifacts:

- static contract tests for E09.3 role/task/evidence behavior;
- Ansible task files for DB/RabbitMQ provisioning under the existing `cloud_ui` role or a tightly
  scoped role subdirectory;
- defaults that contain object names, Vault paths and least-privilege policy shape, not secret values;
- sanitized evidence in `docs/generated/e09-db-rabbitmq-provisioning.md`;
- updates to `docs/11_DKB_TRACEABILITY.md` and `docs/generated/risk-register.md`;
- an ExecPlan in `docs/execplans/E09-db-rabbitmq-provisioning.md`.

## Verification

Repository verification:

- E09.3 contract tests pass;
- existing E09.1/E09.2 tests still pass;
- `make lint`, `make typecheck`, `make test`, `make security` pass;
- secret scan and self-review grep find no secret material or production claim.

Live verification on `192.168.10.15`:

- Vault health reports initialized and unsealed without printing tokens;
- KV v2 and file audit are enabled;
- scoped Cloud UI policy can read allowed synthetic paths and cannot read unrelated paths;
- MariaDB `cloud_ui` database exists;
- runtime user can access only the Cloud UI schema;
- migration user has the extra privileges needed for future migrations and no OpenStack service DB
  access;
- RabbitMQ `/cloud-ui` vhost exists;
- RabbitMQ user permissions are limited to Cloud UI-owned resources;
- attempts to access OpenStack RPC exchanges/vhosts are denied or absent.

## DKB Impact

- ДКБ-55/56: adds lab Vault-backed secret storage for Cloud UI DB/RabbitMQ material, but does not close
  production SecMan, HA, backup, auto-unseal, rotation or owner-approval gaps.
- ДКБ-42-44/76/77/80: adds deployment dependency boundaries and least-privilege evidence for DB/MQ,
  but network ACL and unused-interface blocking remain external.
- ДКБ-69/70: no change to image interpreter/signing status; image registry and scanner evidence remain
  pending.
- ДКБ-82: live rollback of DB/MQ provisioning is documented separately from repository revert and must
  avoid destructive secret disclosure.

## Rollback

Repository rollback is a Git revert of E09.3 commits.

Live rollback, if explicitly approved, disables/removes only Cloud UI-owned test resources:

- revoke Cloud UI lab Vault tokens and/or delete Cloud UI lab secret paths;
- drop MariaDB users `cloud_ui` and `cloud_ui_migration`;
- drop MariaDB schema `cloud_ui` only after confirming no required test data remains;
- delete RabbitMQ user `cloud_ui`, vhost `/cloud-ui` and Cloud UI-owned exchanges/queues.

Vault service rollback follows the E08 runbook: stop/disable Vault while preserving `/opt/vault/data`
unless destructive cleanup is explicitly approved.
