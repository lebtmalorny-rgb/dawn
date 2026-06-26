# E09 Ansible Sync Bundle Design

## Goal

Create a repository-side export bundle for safely preparing an approved E09 test Ansible host with
the Cloud UI Kolla-Ansible artifacts. The bundle must make the current repository role/playbook
portable without touching a remote host, running live Kolla actions, or storing inventory/secrets.

## Context

E09 live evidence showed that the approved all-in-one test stand already has Cloud UI containers, but
the repository `cloud_ui` custom role/config was not found on the Ansible host. The same evidence also
showed DB/MQ runtime authentication drift and blocked backend readiness. A live reconfigure would be
premature until the Ansible host can be prepared from a reproducible, sanitized artifact and the
runtime secret inputs are supplied externally.

## Scope

The slice creates a local bundle/export mechanism only. It includes:

- `deploy/kolla/ansible/roles/cloud_ui`;
- `deploy/kolla/ansible/playbooks/cloud-ui-preflight.yml`;
- `deploy/kolla/ansible/examples/cloud-ui-vars.yml.example`;
- a generated manifest with relative paths, file sizes and SHA256 checksums;
- generated evidence documenting bundle contents, checks and remaining live blockers.

The slice does not include:

- real Kolla inventory;
- runtime secret values, DB/MQ URLs, SSH data, tokens, private keys, `.env`, `clouds.yaml` or openrc;
- remote copy to `192.168.10.15`;
- `kolla-ansible` execution;
- container changes, migration, rollback, DB/MQ provisioning or HAProxy changes.

## Approach

Add a small Python exporter under `deploy/kolla/scripts/` that copies an allowlisted set of files into
a local output directory and writes `manifest.json`. The exporter validates that every bundled path is
inside the allowlist, rejects symlink escapes, scans bundled text for secret-like values and live
mutating command patterns, and writes a sanitized evidence Markdown file under `docs/generated/`.

The output directory should be caller-provided and may be under `/tmp` or another build directory.
Generated evidence must stay under `docs/generated/`. This keeps the artifact reproducible while
preventing accidental commits of host-specific values.

## Bundle Contract

The manifest records:

- bundle schema version;
- source commit SHA;
- generated UTC timestamp;
- each file path relative to the bundle root;
- SHA256 checksum and byte size for each file;
- operator notes for `ANSIBLE_ROLES_PATH=roles` or equivalent role path configuration.

The bundle root layout is:

```text
roles/cloud_ui/...
playbooks/cloud-ui-preflight.yml
examples/cloud-ui-vars.yml.example
manifest.json
```

The exporter intentionally does not create a tarball in this slice. Directory output is easier to
inspect in tests and avoids archive-path traversal concerns. A later remote-sync slice can package or
copy the directory after separate approval.

## Safety Rules

The exporter fails before writing evidence when:

- a source path is missing;
- an allowlisted path resolves outside the repository;
- a source file is a symlink;
- a bundled text file contains credential URLs, private-key markers, static tokens/password-looking
  assignments, `clouds.yaml`, openrc or `.env` references;
- a bundled file contains executable live mutating Kolla command patterns;
- evidence output is outside `docs/generated/` or escapes through a symlink.

The example vars file remains placeholder-only and may contain environment lookup expressions for
`CLOUD_UI_DATABASE_URL` and `CLOUD_UI_RABBITMQ_URL`; those are references, not runtime secret values.

## Documentation And Traceability

Update:

- `deploy/kolla/ansible/README.md` with a short operator note that the export bundle is local-only and
  must be copied to a test host only in a separately approved step;
- `docs/generated/e09-ansible-sync-bundle.md` with manifest summary and remaining blockers;
- `docs/11_DKB_TRACEABILITY.md` with a scoped E09 update;
- `docs/generated/risk-register.md` with a new risk row that the bundle could be mistaken for live
  deployment or secret remediation.

The docs must keep live reconfigure, 12-container inspection, DB/MQ auth remediation, HAProxy/TLS,
SELinux and rollback as pending external evidence.

## Testing

Add contract tests that verify:

- the exporter exists and accepts a safe temporary output directory;
- the produced bundle contains only the allowlisted paths;
- `manifest.json` checksums match file contents;
- generated evidence is under `docs/generated/` and includes no secret-like values;
- symlink/source escape and evidence path escape are rejected;
- injected credential URLs, private-key markers and live mutating command patterns are rejected;
- docs record local-only scope, DKB impact and remaining external evidence.

Existing E09 role/preflight tests remain the baseline for source artifact correctness.

## Rollback

Rollback is a Git revert of this slice. It creates no remote state, no database changes, no queue
changes, no Vault paths and no production or test-stand mutation.
