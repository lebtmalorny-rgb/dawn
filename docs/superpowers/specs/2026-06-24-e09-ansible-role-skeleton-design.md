# E09.2 Ansible Role Skeleton Design

## User Result

E09.2 adds a repository-side Kolla-Ansible role skeleton for Cloud UI without running a live deploy.
Operators and reviewers will see where the Cloud UI role, defaults, templates, handlers and container
definitions live, and tests will prove the role describes exactly the expected frontend/API/worker/events
process layout while preserving the two-image contract from E09.1.

## Scope

This slice creates role structure and dry-run/contract evidence only:

- role path: `deploy/kolla/ansible/roles/cloud_ui`;
- defaults for enable flags, image names, digest placeholders, service groups, ports, config paths and
  container properties;
- task files for validation, config rendering, container definition wiring and handler entry points;
- templates for non-secret backend/frontend runtime config;
- static tests that parse YAML/Jinja text and assert the role does not manage DB/RabbitMQ provisioning,
  migrations, HAProxy/TLS listeners or production inventory;
- generated evidence and DKB traceability update for E09.2.

## Non-Goals

E09.2 does not execute Kolla-Ansible, contact hosts, create registry artifacts, provision MariaDB or
RabbitMQ, run `cloud-ui db-upgrade`, configure HAProxy/TLS, prove SELinux labels, count live containers
or claim production approval.

## Approach Options

1. Repository-only Kolla-Ansible role skeleton and contract tests. This is the selected approach
   because the test inventory and registry are not available yet, and it gives a reviewable vertical
   artifact for E09.2 without pretending deployment evidence exists.
2. Full Kolla-Ansible role plus single-node smoke. This would be useful later, but it needs the test
   registry, inventory, image digests and secrets mechanism, so it belongs after E09.3/E09.4 inputs are
   ready.
3. Generate a generic Ansible role from a scaffold and fill details later. This is rejected because it
   would create many files without proving Cloud UI-specific invariants.

## Role Shape

The role uses the service name `cloud_ui` for Ansible identifiers and underscore container names:

- `cloud_ui_frontend`;
- `cloud_ui_api`;
- `cloud_ui_worker`;
- `cloud_ui_events`.

The role references two images only:

- `cloud-ui-frontend`;
- `cloud-ui-backend`.

The backend image is reused for API, worker and events with different commands. Migration remains a
declared later hook only; no permanent migration container is created in E09.2.

## Files

Expected new files:

- `deploy/kolla/ansible/README.md`;
- `deploy/kolla/ansible/roles/cloud_ui/defaults/main.yml`;
- `deploy/kolla/ansible/roles/cloud_ui/handlers/main.yml`;
- `deploy/kolla/ansible/roles/cloud_ui/tasks/main.yml`;
- `deploy/kolla/ansible/roles/cloud_ui/tasks/validate.yml`;
- `deploy/kolla/ansible/roles/cloud_ui/tasks/config.yml`;
- `deploy/kolla/ansible/roles/cloud_ui/tasks/containers.yml`;
- `deploy/kolla/ansible/roles/cloud_ui/templates/cloud-ui-backend.env.j2`;
- `deploy/kolla/ansible/roles/cloud_ui/templates/cloud-ui-frontend.conf.j2`;
- `tests/test_e09_kolla_ansible_role.py`;
- `docs/generated/e09-kolla-ansible-role.md`;
- `docs/execplans/E09-kolla-ansible-role.md`.

Existing docs updated:

- `deploy/kolla/README.md`;
- `docs/generated/risk-register.md`;
- `docs/11_DKB_TRACEABILITY.md`.

## Validation Rules

Tests will assert:

- exactly four permanent service containers are declared per node;
- API, worker and events use `cloud-ui-backend`;
- frontend uses `cloud-ui-frontend`;
- image references require digest/tag inputs and never use `latest`;
- role files do not contain passwords, private keys, production hosts, `.env` secrets or live inventory;
- DB/RabbitMQ provisioning and migration execution are absent from E09.2 role tasks;
- HAProxy/TLS is explicitly marked as later E09.6 scope;
- generated evidence keeps 12 live containers, registry digest, SBOM, scan, signing and deploy proof as
  pending external evidence.

## Testing

The primary test is a root-level Python contract test that uses `pathlib`, `yaml.safe_load` and text
assertions. It does not require Ansible or a test stand. Project gates remain:

- targeted E09.2 test;
- `make lint`;
- `make typecheck`;
- `make test`;
- `make security`;
- `git diff --check`.

## DKB Impact

E09.2 updates deployment traceability for ДКБ-22.02, 23.02, 24, 42-44, 55/56, 65, 69/70, 76/77, 80
and 82 only as repository-side role evidence. Full closure remains blocked on live registry, secret
mechanism, TLS/mTLS, SELinux, network ACL, DB/MQ least privilege, rollback and deployment smoke
evidence.

## Rollback

Rollback is a Git revert of the E09.2 commits. No database, queue, registry, remote host, Vault path,
Kolla inventory or production credential is changed by this slice.
