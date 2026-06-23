# E08 threat model review

- Stage: E08.1
- Status: generated evidence after E07 audit and E08 Vault/SecMan slices.
- Rule: this file maps portal risks to implemented controls and pending external evidence. It is not
  a compliance approval.

## Assets

| Asset | Why it matters | Current controls/evidence |
|---|---|---|
| User identity and server-side session | Portal actions must stay tied to the authenticated human and scope. | `backend/tests/security/test_sessions.py`, `backend/tests/security/test_security_api.py`, server-side cookie, CSRF and idle timeout. |
| OpenStack token/application credential | Token leakage would bypass browser/BFF boundary. | Browser receives no OpenStack token; E03 adapter errors redact headers/details; service credential lifecycle remains in `docs/generated/secret-inventory.md`. |
| Workflow catalog and operation input | Arbitrary workflow/code execution is the highest mutating-PoC risk. | E06 allowlist, bounded JSON Schema, idempotency and target snapshot tests in `backend/tests/operations`. |
| Resource groups and read model | Stale or cross-scope data can drive unsafe operations. | E04/E05 server-side pagination, group scope checks and freshness markers. |
| Audit outbox and audit search | Audit loss or disclosure weakens ДКБ-46-53 evidence. | E07 durable audit repository/outbox, local sink, Fluentd HTTP contract, heartbeat and redaction tests. |
| Vault/SecMan secret paths | Secret store access must be server-side and policy-limited. | E08 `SecretProvider`, Vault adapter/readiness tests and `docs/generated/e08-vault-policy.hcl`. |
| MariaDB and RabbitMQ portal state | Sessions, operations, read model and audit delivery must not share OpenStack DB/RPC queues. | Separate portal schema/vhost requirement in `docs/12_DEPLOY_ROCKY_KOLLA.md` and `docs/generated/network-flow-matrix.md`. |
| Frontend bundle and browser storage | Browser is the least trusted runtime. | Frontend calls only portal API, storage spy tests check no session/token persistence in `localStorage`/`sessionStorage`. |
| Runtime images and registry | Supply-chain compromise can bypass application controls. | Pending E08/E09 SBOM, image scan, signing and registry evidence; ДКБ-69 interpreter conflict remains explicit. |
| Deployment credentials and TLS private keys | Host/root access can expose all service credentials. | No real secrets in Git; Vault/SecMan and PKI owners remain external controls. |

## Trust Boundaries

| Boundary | Trusted side | Untrusted or less trusted side | Required controls |
|---|---|---|---|
| browser -> HAProxy/frontend/API | portal frontend/API and session store | browser, extensions, user network | HTTPS, HttpOnly cookie, CSRF, CSP/security headers, no OpenStack/Vault/SIEM direct calls. |
| HAProxy -> frontend/API containers | Kolla/portal management network | external/user network | same-origin routing, trusted proxy headers, backend ACL/TLS by matrix. |
| API/worker -> Keystone/Nova/Placement/Mistral/Watcher/Masakari | portal backend and allowlisted adapters | OpenStack APIs and policy engines | TLS, timeout/retry, typed errors, Keystone/service policy remains final authority. |
| API/worker/events -> MariaDB/RabbitMQ | portal runtime identity | DB/broker backend zone | dedicated schema/vhost/user, TLS by matrix, no OpenStack service DB/RPC consumption. |
| Audit worker -> SIEM | portal audit outbox and worker | external SIEM transport | sanitized payload, heartbeat, retry/dead-letter, protected TLS/mTLS channel pending owner evidence. |
| Deploy/runtime -> Vault (SecMan) | backend/deploy identities | secret management service | server-side `SecretProvider`, policy-limited paths, CA verification, no secret values in evidence. |
| Deploy -> registry | CI/deploy pipeline | registry/supply-chain system | TLS, digest pinning, SBOM/scan/signing pending. |
| container -> Rocky/Kolla host | container process | host root, kernel, runtime socket | non-root, drop caps, read-only FS, no socket/host root mounts, SELinux evidence pending. |
| monitoring/recovery signals -> operations | portal worker and operator approval | telemetry/exporter/Consul data | no automatic evacuation from Prometheus/Consul Events; Masakari/Nova state remains authoritative. |

## Threats, Controls And Evidence

| Threat | Control | Evidence | Residual gap |
|---|---|---|---|
| Token or secret leakage to browser | BFF boundary, server-side session, no OpenStack/Vault direct browser access, no local/session storage for tokens. | `backend/tests/security/test_security_api.py`, `frontend/src/App.test.tsx`, `backend/tests/secrets/test_vault_adapter.py`. | Production service credential injection and browser CSP validation remain E08/E09. |
| CSRF against mutating endpoints | SameSite cookie, CSRF token and origin checks. | `backend/tests/security/test_sessions.py`, `backend/tests/security/test_security_api.py`. | Restored browser sessions still need explicit CSRF refresh before frontend mutation controls expand. |
| IDOR or privilege escalation | Backend policy checks, scope checks, OpenStack policy final denial. | E02/E04/E05/E06 backend negative tests; `docs/11_DKB_TRACEABILITY.md`. | Production federation/IAM/SoD and real OpenStack negative RBAC evidence remain external. |
| Arbitrary workflow or code execution | Server-side workflow allowlist, versioned schema, no browser-provided workflow name. | `backend/tests/operations/test_operation_api.py`, `backend/tests/operations/test_operation_worker.py`. | Approved live Mistral mutating workflow and rollback/cancel semantics pending. |
| Duplicate destructive operation | Idempotency key, request hash and durable operation table. | E05/E06 idempotency tests. | Future destructive workflows need stored response/result replay semantics where applicable. |
| SSRF through endpoint input | Service endpoints come from trusted config/service catalog, not user-provided URLs. | E03 adapter contracts and architecture invariant. | Full endpoint allowlist and firewall evidence remain E08/E09. |
| Audit tampering/loss | Durable outbox, retry/dead-letter, heartbeat and audit access logging. | `backend/tests/audit/*`, `docs/generated/audit-source-map.md`. | Root can still disable host/container logs without FIM/auditd/SIEM missing-flow alerts. |
| Audit or error data leaks secrets | Central redaction, safe error responses, no raw request bodies in audit. | `backend/tests/audit/test_audit_redaction.py`, `backend/tests/secrets/test_vault_adapter.py`, `scripts/secret-scan.sh`. | Production service logs and SIEM pipeline must preserve redaction and protected full-error access. |
| Event or telemetry poisoning causes unsafe recovery | No portal-side recovery controller; Masakari/Nova authoritative path and approval gates. | E06 Watcher/Masakari P0 status/risk markers, `docs/generated/risk-register.md`. | Live Masakari/Consul/Watcher evidence and conflict handling remain E10/P3. |
| Stale read model drives unsafe action | Freshness/status exposed; operation target snapshot frozen at acceptance. | E04 reconciliation tests and E06 group target snapshot tests. | Live reconciliation lag budget and precondition checks need E09/E10 evidence. |
| Container breakout or image compromise | Non-root/minimal/read-only/caps/SBOM/signing requirements documented. | `docs/10_SECURITY_DKB.md`, `docs/12_DEPLOY_ROCKY_KOLLA.md`. | E08.5/E08.6/E09 must inspect real images; ДКБ-69 interpreter conflict remains unresolved. |
| Weak TLS or unauthenticated integration | Per-flow TLS/mTLS matrix with negative-test plan. | `docs/generated/tls-matrix.md`. | Corporate PKI, mTLS authorization and live rejection tests remain owner-provided. |

## High Residual Risks

| Code | Risk | Owner | Compensating control until closed | Evidence needed |
|---|---|---|---|---|
| ДКБ-07 | Necessary OpenStack/Kolla service accounts conflict with a broad ban on local technical accounts. | IAM/platform owner | Non-interactive service accounts, least privilege, no human shared admin use, SIEM/PAM audit. | Formal service-account exception and IAM/PAM evidence. |
| ДКБ-22.02 | Strict mTLS for every integration has no single global switch. | PKI/platform/SIEM/Vault owners | TLS everywhere, service-specific auth, firewall allowlists and per-flow owner decisions. | Corporate PKI, client cert auth and negative certificate tests per required flow. |
| ДКБ-48 | Host root can disable or tamper with audit forwarding. | Security/platform owner | Audit heartbeat, FIM/auditd, immutable IaC and missing-flow alerting. | Host/container auditd/FIM and SIEM alert evidence. |
| ДКБ-50 | Portal audit cannot cover every OpenStack, host, storage and IdP event. | SIEM/OpenStack/platform/storage owners | Portal audit source map separates implemented and external sources. | CADF/notifications/host/libvirt/storage/IdP source onboarding evidence. |
| ДКБ-55/56 | Vault adapter does not rotate every Kolla/OpenStack/MariaDB/RabbitMQ secret. | Vault/platform/OpenStack owners | Portal secrets use `SecretProvider`; Kolla/service rotations remain deployment pipeline work. | Approved SecMan endpoint/auth, issue/rotate/revoke runbooks and live evidence. |
| ДКБ-65 | SELinux/AppArmor depends on Rocky/Kolla host policy and labels. | Platform/security owner | Do not claim closure from package presence; keep host validation as blocker. | SELinux enforcing status, container labels/profiles and denial tests. |
| ДКБ-69 | Backend and OpenStack services require Python interpreter; full no-interpreter rule conflicts. | Product/security owner | Minimal runtime, remove compilers/package managers, non-root, SBOM/scan, formal waiver. | Image inspection, vulnerability policy and approved exception. |
| ДКБ-72 | Portal cannot prove VM disks avoid hypervisor filesystem paths. | Storage/OpenStack owner | Keep storage claim external; require boot-from-volume/Ceph/Cinder architecture. | Nova/Cinder/Ceph path and storage policy evidence. |
| ДКБ-77 | Documentation alone does not block unused APIs/interfaces. | Platform/OpenStack owner | API/register documentation plus firewall/policy deny plan. | Kolla service endpoint, firewall and policy blocking evidence. |
