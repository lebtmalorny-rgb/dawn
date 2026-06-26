# E09 Live Reconfigure Bundle / Preflight Design

## Purpose

Prepare a repository-side operator bundle for the next controlled E09 test-stand run. The bundle must
let an operator validate the Cloud UI Kolla-Ansible role inputs before any live deploy/reconfigure
attempt, without committing inventory, credentials, runtime secret values or stand logs.

This design responds to the current E09.8 live findings from 2026-06-26:

- four Cloud UI containers are running on one all-in-one host, not twelve containers on three nodes;
- backend readiness reaches MariaDB/RabbitMQ by TCP but fails DB/MQ authentication;
- remote Cloud UI custom role/config is not installed on the Ansible host;
- current repository role has repository-side contracts and validation, but no controlled operator
  path for transferring and validating the role on the test Ansible host.

## Selected Approach

Add a fail-closed live reconfigure preflight bundle, not a live reconfigure executor.

The bundle will provide:

- an Ansible preflight playbook that runs locally on the Ansible control host and imports only the
  Cloud UI role validation task path;
- an example variable file with placeholders/env lookups for approved secret delivery, never real
  values;
- documentation and generated evidence that explain how to copy/run the preflight and what remains
  pending before E09 acceptance;
- tests that reject unsafe drift: tag-only images, missing test marker, missing rollback window,
  missing DB/MQ runtime inputs, committed secret values and accidental `kolla-ansible reconfigure`
  execution inside the repository artifact.

The playbook validates prerequisites for a later approved live run. It must not run
`kolla-ansible deploy`, `kolla-ansible reconfigure`, `kolla_container`, shell commands, database
mutations or RabbitMQ mutations.

## Artifacts

Create:

- `deploy/kolla/ansible/playbooks/cloud-ui-preflight.yml`
- `deploy/kolla/ansible/examples/cloud-ui-vars.yml.example`
- `tests/test_e09_live_reconfigure_bundle.py`
- `docs/generated/e09-live-reconfigure-bundle.md`
- `docs/execplans/E09-live-reconfigure-bundle.md`

Modify:

- `deploy/kolla/ansible/README.md`
- `docs/11_DKB_TRACEABILITY.md`
- `docs/generated/risk-register.md`

## Playbook Contract

The preflight playbook runs on `localhost` with `connection: local` and `gather_facts: false`. It is
intended to be run from a copied repository bundle on the approved test Ansible host.

Required inputs:

- `cloud_ui_test_stand: true`
- `cloud_ui_rollback_window_open: true`
- `cloud_ui_enabled: true`
- `cloud_ui_backend_image_digest` matching `sha256:<64 lowercase hex>`
- `cloud_ui_frontend_image_digest` matching `sha256:<64 lowercase hex>`
- `cloud_ui_database_url` supplied by the approved secret mechanism
- `cloud_ui_rabbitmq_url` supplied by the approved secret mechanism

The playbook imports `cloud_ui` with `tasks_from: validate` after its own preflight asserts. It does
not import role `main.yml`, because `main.yml` can render runtime config when `cloud_ui_enabled=true`;
the preflight must validate inputs without writing DB/MQ URLs to files.

Secret-sensitive assertions use `no_log: true`. Failure messages are generic and must not echo secret
values.

## Example Variable File

The example vars file contains no real credentials, host-specific production URLs or passwords.

It may show environment lookups for runtime DB/MQ URLs:

- `cloud_ui_database_url: "{{ lookup('ansible.builtin.env', 'CLOUD_UI_DATABASE_URL') }}"`
- `cloud_ui_rabbitmq_url: "{{ lookup('ansible.builtin.env', 'CLOUD_UI_RABBITMQ_URL') }}"`

The file will keep digest values as explicit placeholders. Operators must create a non-committed
test-stand vars file from the example.

## Safety And Non-Goals

This slice must not:

- execute a live Kolla deploy/reconfigure/upgrade/destroy;
- start, stop or modify containers;
- create or rotate MariaDB/RabbitMQ/Vault objects;
- commit real inventory, DB/MQ URLs with credentials, tokens, keys, cookies, openrc, `clouds.yaml`,
  private keys or production hostnames;
- claim E09 acceptance, 12 live containers, HAProxy/TLS success, migration one-shot success,
  rollback success or DKB closure.

The first live follow-up after this slice is limited to copying the bundle to `192.168.10.15` and
running the preflight in a user-approved command. Any mutation after that needs separate explicit
approval and rollback window confirmation.

## Testing

Add static contract tests for the new playbook, example vars and evidence:

- required files exist;
- preflight playbook runs on localhost and imports only `tasks_from: validate`;
- preflight asserts marker, rollback window, digest shape and runtime DB/MQ inputs;
- playbook and examples do not contain `kolla-ansible reconfigure`, `kolla_container`, shell/command
  execution or real secrets;
- generated evidence and DKB traceability mark the bundle as preflight-only and keep live evidence
  pending;
- risk register keeps a unique risk row for treating preflight as deployment acceptance.

Verification commands:

- targeted pytest for the new test file and related E09 tests;
- Ruff on the new test file;
- `./scripts/secret-scan.sh`;
- `git diff --check`.

## Rollback

Repository rollback is a Git revert of this slice. Since the bundle does not mutate remote hosts,
there is no remote rollback for this repository-only change. If a later live preflight copies files to
the Ansible host, cleanup is removal of the copied bundle directory from that approved test host.
