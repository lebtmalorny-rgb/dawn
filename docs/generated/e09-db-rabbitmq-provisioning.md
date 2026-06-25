# E09.3 DB/RabbitMQ Provisioning Evidence

- Stage: E09.3 Database/RabbitMQ provisioning
- Date: 2026-06-25
- Scope: repository contract plus sanitized test-stand precheck for Cloud UI MariaDB/RabbitMQ provisioning
- Test Ansible host: 192.168.10.15
- OpenStack all-in-one host: 192.168.10.14
- Kolla inventory: /etc/kolla/all-in-one
- Secret mechanism: Vault/SecMan lab path
- Live DB/RabbitMQ mutation: not executed
- Production action: none

## Repository Contract

The one-time provisioning role is located at `deploy/kolla/ansible/roles/cloud_ui_provisioning`.

It keeps DB/MQ setup separate from the permanent E09.2 service role and defines only non-secret
object names and secret references:

| Object | Scoped value |
|---|---|
| MariaDB schema | `cloud_ui` |
| MariaDB runtime user | `cloud_ui` |
| MariaDB migration user | `cloud_ui_migration` |
| RabbitMQ vhost | `/cloud-ui` |
| RabbitMQ user | `cloud_ui` |
| Vault/SecMan lab path | `kv/cloud-ui/local/*` |

The role tasks are fail-closed around the Cloud UI object names and use `no_log: true` for Vault,
MariaDB and RabbitMQ tasks. No runtime secret value, Kolla secret file, registry credential or
production inventory was added to the repository.

## Remote Precheck Evidence

Read-only checks were run against the approved test Ansible host before any DB/RabbitMQ mutation.

| Check | Result |
|---|---|
| SSH target hostname | `ansible.example.local` |
| Kolla-Ansible binary | `/root/venvs/kolla-epoxy/bin/kolla-ansible` present |
| Kolla inventory | `/etc/kolla/all-in-one` present |
| Vault CLI | missing |
| Vault service | inactive |
| Vault listeners | none observed on `:8200` or `:8201` |
| Vault package source | `vault_package_unavailable` from the approved `dnf` package-source check |

The plan requires stopping when the selected test host has no approved Vault package source. DB/MQ
provisioning was therefore not attempted.

## External Evidence Status

| Evidence | Status | Reason |
|---|---|---|
| Vault/SecMan lab service on `192.168.10.15` | pending_external_evidence | The approved package-source check did not expose a Vault package. |
| Cloud UI DB/MQ secret material in Vault | pending_external_evidence | Requires the lab Vault service or another approved SecMan mechanism. |
| MariaDB schema `cloud_ui` | pending_external_evidence | Not created because the protected secret mechanism is unavailable. |
| MariaDB users `cloud_ui` and `cloud_ui_migration` | pending_external_evidence | Not created because DB credentials must come from the protected secret mechanism. |
| RabbitMQ vhost `/cloud-ui` and user `cloud_ui` | pending_external_evidence | Not created because MQ credentials must come from the protected secret mechanism. |
| RabbitMQ Cloud UI exchanges and queues | pending_external_evidence | Requires the live MQ provisioning step and approved declaration tooling. |
| Least-privilege DB/MQ negative checks | pending_external_evidence | Requires successful live DB/MQ provisioning first. |
| MariaDB HA, RabbitMQ HA/quorum, backup and rotation | pending_external_evidence | Later E09/E10 and external owner evidence. |

## DKB Impact

- ДКБ-55/56: E09.3 adds the repository-side Vault/SecMan path contract for Cloud UI DB/MQ material,
  but the selected test host does not yet provide an approved lab Vault package source. Full secret
  storage, rotation, production SecMan endpoint/auth and owner approval remain open.
- ДКБ-76/77/80: E09.3 documents the DB/MQ interface boundaries for Cloud UI. Network zone, firewall,
  unused-interface blocking and management-zone evidence remain external E09/E10 proof.
- ДКБ-42-44: no new browser, DB or MQ network path was opened by this slice. VLAN/ACL proof remains
  pending.
- ДКБ-69/70: unchanged by this slice; image interpreter waiver, registry digest, SBOM, scanner and
  signing evidence remain pending.
- ДКБ-82: repository rollback is a Git revert of the E09.3 commits. No live DB/MQ cleanup is required
  because live provisioning stopped before mutation.

## Safe Next Step

Provide an approved Vault/SecMan package source or a pre-installed approved lab Vault on
`192.168.10.15`, then rerun the E09.3 remote bootstrap steps before attempting MariaDB/RabbitMQ
provisioning.
