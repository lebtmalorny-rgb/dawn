# E09.3 DB/RabbitMQ Provisioning Evidence

- Stage: E09.3 Database/RabbitMQ provisioning
- Date: 2026-06-25
- Scope: repository contract plus sanitized live all-in-one lab provisioning evidence
- Test Ansible host: 192.168.10.15
- OpenStack all-in-one host: 192.168.10.14
- Kolla inventory: /etc/kolla/all-in-one
- Secret mechanism: Vault/SecMan lab path
- Live DB/RabbitMQ mutation: executed on approved all-in-one test stand
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
| Initial Vault CLI | missing |
| Initial Vault service | inactive |
| Initial Vault listeners | none observed on `:8200` or `:8201` |
| Vault package source | `vault_package_unavailable` from the approved `dnf` package-source check |
| Official HashiCorp RPM repository | approved for lab use, but `https://rpm.releases.hashicorp.com/RHEL/hashicorp.repo` returned HTTP `404` with `x-amzn-waf-reason: geo` from the test host |
| Internal mirror candidate | `http://192.168.10.17:8080/` reachable from `192.168.10.15`; repo metadata is valid |
| Internal mirror packages | initially `terraform` only; later updated with `vault-2.0.3-1.x86_64.rpm` and refreshed metadata |
| Vault package after approved mirror install | `Vault v2.0.3` installed from `192.168.10.17:8080` |
| HashiCorp repo file | absent |
| Remote package side effect | `yum-utils` installed and `dnf-plugins-core` updated before the repository add failed |

The internal mirror became the approved reachable package source after it published the Vault RPM.
DB/MQ provisioning then proceeded with secret material stored only in Vault.

## Vault Live Evidence

| Check | Result |
|---|---|
| Package source | internal mirror `http://192.168.10.17:8080/` |
| Package signature evidence | not established in this slice; lab install used the approved internal mirror with GPG check disabled |
| Vault version | `2.0.3` |
| Service | active |
| API listener | `192.168.10.15:8200` |
| API root path | HTTP `404` expected because this is an API endpoint and `ui = false` |
| Health endpoint | `/v1/sys/health` HTTP `200` |
| Initialized | true |
| Sealed | false |
| KV engine | `kv/` enabled |
| Audit device | file audit enabled |
| Runtime secret values captured in repository | no |

The package postinstall generated its own TLS material under `/opt/vault/tls`, but the active E09
configuration uses the lab TLS files under `/etc/vault.d/tls`. The private key is not copied into the
repository or evidence.

## MariaDB Live Evidence

| Check | Result |
|---|---|
| Schema | `cloud_ui` provisioned |
| Runtime user | `cloud_ui` provisioned |
| Migration user | `cloud_ui_migration` provisioned |
| Runtime user access to `cloud_ui` | `runtime_cloud_ui_schema_ok` |
| Runtime user access to `mysql` schema | `runtime_mysql_schema_denied` |
| Application DB migration | not executed in E09.3; owned by E09.4 |

## RabbitMQ Live Evidence

| Check | Result |
|---|---|
| Vhost | `/cloud-ui` present |
| Runtime user | `cloud_ui` provisioned |
| `/cloud-ui` permissions | `^cloud-ui\\.` for configure, write and read |
| Root vhost permissions | absent for `cloud_ui` |
| Exchanges | `cloud-ui.events`, `cloud-ui.jobs`, `cloud-ui.audit`, `cloud-ui.dlx` declared durable direct |
| Queues | `cloud-ui.events`, `cloud-ui.jobs`, `cloud-ui.audit`, `cloud-ui.dead` declared durable |

RabbitMQ declaration used the management HTTP API with a temporary provisioning permission for the
Kolla `openstack` RabbitMQ user on `/cloud-ui`; that temporary permission was cleared after
declaration. Final `/cloud-ui` permissions list only `cloud_ui`.

## External Evidence Status

| Evidence | Status | Reason |
|---|---|---|
| Vault/SecMan lab service on `192.168.10.15` | completed_lab_evidence | Installed from the approved internal mirror and initialized/unsealed with KV and file audit. |
| Cloud UI DB/MQ secret material in Vault | completed_lab_evidence | Generated on the test host and stored under `kv/cloud-ui/local/*`; secret values were not printed or committed. |
| MariaDB schema `cloud_ui` | completed_lab_evidence | Created on the all-in-one MariaDB container. |
| MariaDB users `cloud_ui` and `cloud_ui_migration` | completed_lab_evidence | Created with scoped schema privileges. |
| RabbitMQ vhost `/cloud-ui` and user `cloud_ui` | completed_lab_evidence | Created on the all-in-one RabbitMQ container. |
| RabbitMQ Cloud UI exchanges and queues | completed_lab_evidence | Declared through the management API with final permissions scoped to `cloud_ui`. |
| Least-privilege DB/MQ negative checks | completed_lab_evidence | MariaDB runtime user denied `mysql`; RabbitMQ user has no root-vhost permission. |
| MariaDB HA, RabbitMQ HA/quorum, backup and rotation | pending_external_evidence | Later E09/E10 and external owner evidence. |

## DKB Impact

- ДКБ-55/56: E09.3 adds lab Vault-backed storage for Cloud UI DB/MQ material. This is lab evidence,
  not production SecMan endpoint/auth, HA, backup, auto-unseal, rotation or owner approval.
- ДКБ-76/77/80: E09.3 proves DB/MQ object boundaries and least-privilege checks in the all-in-one lab.
  Network zone, firewall, unused-interface blocking and management-zone evidence remain external
  E09/E10 proof.
- ДКБ-42-44: no new browser-to-DB/MQ path was opened by this slice. VLAN/ACL proof remains pending.
- ДКБ-69/70: unchanged by this slice; image interpreter waiver, registry digest, SBOM, scanner and
  signing evidence remain pending.
- ДКБ-82: repository rollback is a Git revert of the E09.3 commits. Live cleanup is documented for
  Vault paths, MariaDB users/schema and RabbitMQ user/vhost if explicitly approved.

## Safe Next Step

E09.3 lab DB/RabbitMQ provisioning is complete. E09.4 migration job remains a separate stage and is
not started by this evidence.
