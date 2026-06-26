# E09.8 Deployment smoke/evidence

- Stage: E09.8 Deployment smoke/evidence
- Status: partial repository evidence and read-only test-stand discovery are present; live deployment
  rows remain `pending_external_evidence`.
- Scope: `partial` `test-stand`
- Live execution status: `pending_external_evidence`

## Evidence rows

| Check | Status | Sanitized summary |
|---|---|---|
| preflight | blocked_missing_marker | Read-only discovery on 2026-06-26 confirmed the Ansible test host and `/etc/kolla/all-in-one`, but the inventory does not contain the required `cloud_ui_test_stand` marker. No live command was run. |
| two images | partial_lab_evidence | Read-only Podman discovery on `192.168.10.15` found `192.168.10.15:5000/kolla/cloud-ui-backend@sha256:8ff5287ad21048f9f249e4e28f9bd7c3a31b2d345b265a48a7ee03f46d46a822` and `192.168.10.15:5000/kolla/cloud-ui-frontend@sha256:182debc7d8c13091b29dc37cd422bf5c6a5bdf7d8b2bbff1636b578388c671cb`; signing/provenance remains pending. |
| container count | pending_external_evidence | Expected three nodes x four permanent containers = 12; no live container inventory is accepted yet. SSH auth to `192.168.10.14` failed for the current key. |
| one-shot migration | pending_external_evidence | Expected one-shot `cloud_ui_db_migrate` before rollout; live migration execution and failure/retry evidence remain pending. |
| DB/RabbitMQ | pending_external_evidence | Expected least-privilege DB/RabbitMQ access checks without secret output; production SecMan rotation proof remains pending. |
| HAProxy/TLS | pending_external_evidence | Expected same-origin UI/API health over TLS >= 1.2; corporate PKI/mTLS approval and negative certificate tests remain pending. |
| container hardening | pending_external_evidence | Expected non-root user, dropped caps, controlled mounts and SELinux labels; user/caps/mounts/SELinux proof remains pending. |
| API/UI smoke | pending_external_evidence | Expected frontend and `/api/v1/health/ready` health checks from the approved test stand only. |
| rollback | pending_external_evidence | rollback pending before full E09 acceptance; rollback execution evidence is not attached yet. |

## Read-only discovery on 2026-06-26

The following discovery was read-only and did not run `kolla-ansible reconfigure`, migration,
rollback, container stop/start or inventory writes.

| Item | Result |
|---|---|
| SSH host identity | ED25519 keys for `192.168.10.15` and `192.168.10.14` matched local known_hosts entries. |
| Ansible host | `ansible.example.local` |
| Test inventory path | `/etc/kolla/all-in-one` present on `192.168.10.15` |
| Test marker | missing: `cloud_ui_test_stand` is not present in the inventory |
| Kolla-Ansible | `20.4.1.dev5` |
| Container runtime on Ansible host | `/usr/bin/podman` |
| Cloud UI image digests on Ansible host | backend and frontend digests found in local registry refs listed above |
| All-in-one host SSH | `192.168.10.14` rejected the current key; no container inspection or smoke output was collected |

## Pending external gates

- Production approval remains pending and cannot be inferred from this partial evidence.
- Corporate PKI/mTLS approval and negative certificate evidence remain pending.
- Registry signing, provenance and approved scanner policy evidence remain pending.
- ДКБ-69 waiver remains pending because the Python backend still requires an interpreter.
- Network-owner ACL proof for management/API zones remains pending.
- Rollback execution on the approved test stand remains pending.
- The approved inventory still needs an explicit `cloud_ui_test_stand` marker before any live command
  summary can be accepted.
- SSH access to the all-in-one/container host must be restored or operator-provided sanitized
  container inspection must be attached.
- A rollback window still must be explicitly open before live reconfigure/rollback evidence can be
  accepted.

## DKB scope

- ДКБ-22.02/24: TLS and health rows are pending live test-stand evidence.
- ДКБ-42-44/77/80: network/ACL rows remain pending external proof.
- ДКБ-55/56: evidence must not contain secrets; full rotation remains external.
- ДКБ-65: SELinux/caps/mount inspection remains pending live output.
- ДКБ-69/70: image digests can be recorded; ДКБ-69 waiver remains required.
- ДКБ-82: operational lifecycle evidence remains partial until rollback is executed.
