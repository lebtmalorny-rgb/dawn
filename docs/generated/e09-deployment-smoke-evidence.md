# E09.8 Deployment smoke/evidence

- Stage: E09.8 Deployment smoke/evidence
- Status: partial repository evidence is present; live test-stand rows are `pending_external_evidence`.
- Scope: `partial` `test-stand`
- Live execution status: `pending_external_evidence`

## Evidence rows

| Check | Status | Sanitized summary |
|---|---|---|
| preflight | pending_external_evidence | Requires explicit `cloud_ui_test_stand` marker, digest-pinned images and an open rollback window before any live command summary can be accepted. |
| two images | pending_external_evidence | Expected `cloud-ui-backend` and `cloud-ui-frontend` by sha256 digest; corporate registry signing remains pending. |
| container count | pending_external_evidence | Expected three nodes x four permanent containers = 12; no live container inventory is accepted yet. |
| one-shot migration | pending_external_evidence | Expected one-shot `cloud_ui_db_migrate` before rollout; live migration execution and failure/retry evidence remain pending. |
| DB/RabbitMQ | pending_external_evidence | Expected least-privilege DB/RabbitMQ access checks without secret output; production SecMan rotation proof remains pending. |
| HAProxy/TLS | pending_external_evidence | Expected same-origin UI/API health over TLS >= 1.2; corporate PKI/mTLS approval and negative certificate tests remain pending. |
| container hardening | pending_external_evidence | Expected non-root user, dropped caps, controlled mounts and SELinux labels; user/caps/mounts/SELinux proof remains pending. |
| API/UI smoke | pending_external_evidence | Expected frontend and `/api/v1/health/ready` health checks from the approved test stand only. |
| rollback | pending_external_evidence | rollback pending before full E09 acceptance; rollback execution evidence is not attached yet. |

## Pending external gates

- Production approval remains pending and cannot be inferred from this partial evidence.
- Corporate PKI/mTLS approval and negative certificate evidence remain pending.
- Registry signing, provenance and approved scanner policy evidence remain pending.
- ДКБ-69 waiver remains pending because the Python backend still requires an interpreter.
- Network-owner ACL proof for management/API zones remains pending.
- Rollback execution on the approved test stand remains pending.
- Read-only discovery on 2026-06-25 did not attach live evidence: SSH host identity for the provided
  test address must be confirmed, and no approved inventory path, backend/frontend image digests or
  Cloud UI/Kolla container summaries were available to record.

## DKB scope

- ДКБ-22.02/24: TLS and health rows are pending live test-stand evidence.
- ДКБ-42-44/77/80: network/ACL rows remain pending external proof.
- ДКБ-55/56: evidence must not contain secrets; full rotation remains external.
- ДКБ-65: SELinux/caps/mount inspection remains pending live output.
- ДКБ-69/70: image digests can be recorded; ДКБ-69 waiver remains required.
- ДКБ-82: operational lifecycle evidence remains partial until rollback is executed.
