# Kolla Mistral/Watcher/Masakari and TLS Design

## Goal

Bring the test OpenStack/Kolla environment closer to the documented target by enabling Mistral, Watcher and Masakari, enabling HTTPS/TLS on the API/Horizon VIP, and installing the build tooling needed for Kolla image work.

## Scope

Target environment:

- Ansible host: `192.168.10.15`
- OpenStack all-in-one host: `192.168.10.14`
- VIP/API: `192.168.10.250`
- Kolla-Ansible venv: `/root/venvs/kolla-epoxy`
- Correct admin OpenStack source: `/etc/kolla/admin-openrc.sh`

In scope:

- Inspect existing Kolla inventory/config without printing secrets.
- Back up Kolla config/inventory before edits.
- Install missing Kolla build tooling on the Ansible host if it is absent.
- Enable Mistral, Watcher and Masakari in Kolla config.
- Enable TLS using Kolla-supported configuration.
- Generate test-only self-signed certificates if no approved certificates exist.
- Run Kolla prechecks/reconfigure/deploy on the test inventory.
- Verify service catalog, containers and HTTPS endpoints.
- Update E00 generated docs with sanitized results.

Out of scope:

- Production deployment.
- Changing OpenStack service databases directly.
- Copying passwords, tokens, private keys or full `passwords.yml` content into the repository.
- Final DKB compliance claims.
- Building the Cloud UI application.

## Approach

All operational changes run from the Ansible host because it already contains the Kolla-Ansible venv and deployment files. Local macOS is used only for orchestration and documentation updates.

The workflow is conservative:

1. Discover the active inventory and Kolla configuration.
2. Create timestamped backups.
3. Install/verify build tooling in an isolated or existing Kolla Python environment.
4. Make minimal Kolla config changes.
5. Run prechecks.
6. Apply reconfigure/deploy on the test inventory.
7. Verify endpoints and service catalog.
8. Document facts and remaining gaps.

## TLS Policy

If existing certificates are present under `/etc/kolla/certificates`, reuse them. If not, generate a test-only self-signed CA and VIP certificate for `192.168.10.250` and local hostnames. The generated certificates are deployment artifacts on the Ansible/Kolla host and are not copied into the repository.

TLS evidence remains test-environment evidence only. Corporate PKI/mTLS evidence is still an E08/E09 production gap.

## Rollback

Rollback is file-based and deployment-based:

- Restore backed-up `/etc/kolla/globals.yml`.
- Restore any edited inventory file.
- Re-run Kolla-Ansible reconfigure.
- Keep service enablement changes reversible.
- Do not delete existing OpenStack data.

## Acceptance

- `kolla-ansible` remains available from `/root/venvs/kolla-epoxy`.
- `kolla-build` or equivalent build command is available on the Ansible host.
- Mistral, Watcher and Masakari are either present in the service catalog or a precise blocker is documented.
- Horizon/Keystone are reachable over HTTPS on `192.168.10.250`.
- No real secrets are written to local repository files.
- E00 generated docs reflect actual outcomes and remaining gaps.
