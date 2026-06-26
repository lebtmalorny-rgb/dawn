# E09 Ansible Remote Sync Design

## Goal

Deliver the already exported Cloud UI Kolla-Ansible bundle to the approved test Ansible host so the
previous blocker "remote Cloud UI role/config not found" becomes observable remote evidence.

This slice is not a live deployment slice. It prepares and verifies a copied operator bundle only.

## Approved Target

- Ansible host: `192.168.10.15`.
- Inventory marker source: `/etc/kolla/all-in-one` on the Ansible host, read-only for this slice.
- Remote bundle path: `/etc/kolla/cloud-ui-sync-bundle`.
- Role resolution note: future preflight/reconfigure commands can use
  `ANSIBLE_ROLES_PATH=/etc/kolla/cloud-ui-sync-bundle/roles`, but this slice does not execute
  `kolla-ansible reconfigure`.

## Scope

The slice may:

- build a fresh local bundle from `deploy/kolla/scripts/export-ansible-bundle.py`;
- copy that bundle to `192.168.10.15:/etc/kolla/cloud-ui-sync-bundle`;
- create a timestamped backup of an existing remote bundle before replacement;
- verify the remote bundle file list, manifest schema, bytes and SHA256 values;
- verify that `roles/cloud_ui`, `playbooks/cloud-ui-preflight.yml` and
  `examples/cloud-ui-vars.yml.example` exist on the remote host;
- record sanitized evidence in the repository.

The slice must not:

- run `kolla-ansible deploy`, `reconfigure`, `upgrade`, `destroy`, `pull`, `prechecks`, `check` or
  any live mutating Kolla command;
- copy runtime secret values, non-committed vars, `clouds.yaml`, openrc, `.env`, private keys,
  tokens, cookies or database dumps;
- modify MariaDB, RabbitMQ, Vault, Keystone, OpenStack services, containers or HAProxy;
- install the role into `/usr/share/kolla-ansible` or a Kolla venv role path;
- claim twelve-container deployment, DB/MQ remediation, migration, HAProxy/TLS, SELinux or rollback
  evidence.

## Data Flow

1. Local exporter creates a fresh bundle under `/tmp`.
2. The local manifest is treated as the copy contract.
3. The remote host receives the bundle under a staging path below `/etc/kolla`.
4. The remote staging path is promoted to `/etc/kolla/cloud-ui-sync-bundle` only after copy
   completion.
5. Remote verification computes SHA256 and bytes for every manifest entry.
6. Evidence records only sanitized paths, counts, hashes and pass/fail summaries.

## Safety And Rollback

If `/etc/kolla/cloud-ui-sync-bundle` already exists, the sync flow creates a timestamped backup under
`/etc/kolla/cloud-ui-sync-bundle.backup-<UTC>`. Rollback is restoring that backup or removing the
new bundle path if there was no previous bundle.

Remote cleanup must be path-scoped. It may remove only the staging path created by this slice and the
target path when replacing it with a verified local bundle. It must not remove `/etc/kolla`, Kolla
configuration, inventories, certificates, logs, images or container state.

## Evidence

Create:

- `docs/generated/e09-ansible-remote-sync.md`;
- `docs/execplans/E09-ansible-remote-sync.md`;
- a traceability update in `docs/11_DKB_TRACEABILITY.md`;
- a risk-register row for the copied bundle being mistaken for live deployment evidence.

Evidence must include:

- host `192.168.10.15`;
- remote path `/etc/kolla/cloud-ui-sync-bundle`;
- local bundle manifest schema and source commit;
- remote file count and SHA256 verification result;
- explicit `pending_external_evidence` rows for live reconfigure, DB/MQ auth remediation, migration,
  twelve containers, HAProxy/TLS, SELinux and rollback;
- rollback path summary without secret material.

## Testing

Repository tests should drive the evidence contract before remote execution. The tests should cover:

- generated evidence has the required local-only/remote-sync wording;
- remote evidence cannot claim live deployment acceptance;
- manifest file count and required bundle artifacts are documented;
- risk ID is unique;
- no forbidden credential references are introduced.

Remote verification is operational evidence, not a unit test. It should be recorded with command
summaries and sanitized results only.

## Open Conditions

- SSH access to `192.168.10.15` is user-approved for this slice.
- The slice assumes root-level permission to write `/etc/kolla/cloud-ui-sync-bundle` on the test
  Ansible host.
- A successful remote sync does not resolve the existing DB/MQ application-auth failures or container
  hardening failures from `docs/generated/e09-deployment-smoke-evidence.md`.
