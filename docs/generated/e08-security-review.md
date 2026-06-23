# Security review: E08 hardening

- Date: 2026-06-23
- Commit/image digest: repository commit `6983fbb`; local image evidence is recorded in `docs/generated/e08-supply-chain.md`
- Reviewer: Codex automated review, not a formal security-owner approval
- Scope: E08 portal-owned hardening evidence from threat/TLS, Vault/SecMan, session/token protection, container hardening, supply chain and DKB gap/waiver slices
- Related ExecPlan: `docs/execplans/E08-security-review.md`
- DKB codes: ДКБ-07, 13, 22.02, 23.02, 24, 25, 42-44, 46-53, 55, 56, 65, 69, 70, 76, 77, 80
- Unresolved critical/high findings: 0

## Архитектурное изменение

E08 did not add a new browser trust boundary or direct OpenStack browser integration. The portal still
uses a BFF/API boundary, server-side sessions, backend capability checks, allowlisted workflows and
backend-only OpenStack/Vault/SIEM integration paths. E08 added evidence and controls around restored
session CSRF bootstrap, Vault/SecMan adapter contracts, TLS/mTLS planning, local container hardening,
local SBOM generation and explicit external DKB gaps.

The main remaining boundary is not inside the portal code. It is the deployment and external-control
boundary: IAM/PAM, corporate PKI/mTLS, SIEM source onboarding, production SecMan, Rocky SELinux,
corporate registry/signing, storage architecture and network zoning are still owner-provided evidence.
ДКБ-69 remains not closed because the Python backend requires an interpreter and needs a formal waiver.

## Проверенные угрозы

| Угроза | Finding | Severity | Evidence | Решение |
|---|---|---|---|---|
| Auth bypass/IDOR | Backend capability/scope checks are covered for security, inventory, groups and operations; frontend capabilities are UX only. | None | `backend/tests/security/test_security_api.py`, `backend/tests/groups/test_group_api.py`, `backend/tests/operations/test_operation_api.py`, `frontend/src/App.test.tsx` | No E08 code change required. Production IAM/SoD remains external. |
| Session/CSRF/XSS | Restored sessions can bootstrap CSRF through BFF/API; missing/revoked sessions fail closed; browser storage tests prevent session/token persistence. | None | `docs/generated/e08-session-token-protection.md`, `backend/tests/security/test_security_api.py`, `frontend/src/App.test.tsx` | Keep CSP/security headers as E09 deployment evidence. |
| Secret/token leakage | No OpenStack/Vault tokens are returned to browser; audit sanitizer and secret-scan canaries are covered. | None | `backend/tests/audit/test_audit_redaction.py`, `backend/tests/secrets/test_vault_adapter.py`, `scripts/secret-scan.sh`, `docs/generated/secret-inventory.md` | Production service logs and SIEM redaction remain external controls. |
| Injection/SSRF | Review did not find eval/exec/shell execution paths or user-provided integration endpoints. Dynamic group rules and OpenStack adapters use allowlisted contracts. | None | `backend/tests/groups/test_group_rules.py`, E03 adapter tests, review grep for `eval`, `exec`, `shell=True`, `os.system` | Keep endpoint allowlist/firewall evidence for E09. |
| Workflow/code execution | Workflow execution uses server-side catalog and schema; browser cannot submit arbitrary Mistral workflow names. | None | `backend/src/cloud_ui/operations/catalog.py`, `backend/tests/operations/test_workflow_catalog.py`, `backend/tests/operations/test_operation_api.py` | Live mutating workflow approval remains external/P2 gate. |
| Retry/idempotency | Operation idempotency, target snapshot and Mistral lost-response lookup are covered for the P0 workflow. | None | `backend/tests/operations/test_operation_api.py`, `backend/tests/operations/test_operation_worker.py` | Future destructive workflows need per-workflow replay/rollback evidence. |
| Audit tampering/loss | Portal audit outbox, retry/dead-letter and heartbeat are implemented; host/root log tampering remains external. | Medium external condition | `docs/generated/audit-source-map.md`, `backend/tests/audit/test_delivery_worker.py`, `backend/tests/audit/test_heartbeat.py` | Keep ДКБ-48/50 in `docs/generated/e08-dkb-gaps-waivers.md`. |
| Container/host boundary | Local portal app containers are non-root/read-only/cap-dropped/no-new-privileges; SELinux host proof remains external. | Medium external condition | `docs/generated/e08-container-hardening.md`, `backend/tests/security/test_e08_container_hardening.py`, `compose.yaml` | Require E09 Rocky/Kolla SELinux labels and denial evidence. |
| Supply chain | Dockerfiles pin base image digests and local SBOM is generated; full image/Python CVE scanner, signing and corporate registry evidence are not present. | Medium external/tooling condition | `docs/generated/e08-supply-chain.md`, `backend/tests/security/test_e08_supply_chain.py`, `Makefile` `sbom` target | Keep ДКБ-69/70 conditions before production pilot. |
| Availability/DoS | P0 tests cover operation state transitions and audit retry; production HA/load/failover is outside E08. | Medium external condition | `make test`, `make test-integration`, `docs/12_DEPLOY_ROCKY_KOLLA.md` | E09/E10 must provide HA/failover/load evidence. |

## Findings

### E08-SR-001 Medium — External controls remain required before production claims

- Path/line: `docs/generated/e08-dkb-gaps-waivers.md`
- Condition: E08 has explicit gaps for IAM/PAM, PKI/mTLS, SIEM, SecMan, SELinux, registry/signing,
  storage and network controls.
- Impact: Treating E08 local evidence as production compliance would overstate the security posture.
- Evidence: `docs/generated/e08-dkb-gaps-waivers.md`, `docs/generated/risk-register.md`
- Fix: Keep these rows as release gates until the named owner roles provide evidence.
- Status: Open external condition, not an unresolved portal Critical/High finding.
- Residual risk: P3/production pilot remains blocked until owner evidence or formal waiver exists.

### E08-SR-002 Medium — ДКБ-69 interpreter conflict requires formal waiver

- Path/line: `backend/Dockerfile`, `docs/generated/e08-supply-chain.md`, `docs/generated/e08-dkb-gaps-waivers.md`
- Condition: The backend runtime is Python-based and therefore contains a Python interpreter.
- Impact: ДКБ-69 cannot be marked closed by digest pins, non-root runtime or local SBOM alone.
- Evidence: `backend/tests/security/test_e08_supply_chain.py`, `docs/generated/e08-supply-chain.md`,
  `docs/generated/e08-dkb-gaps-waivers.md`
- Fix: Obtain formal waiver for Python interpreter and any retained shell components; add scanner and
  approved image allowlist evidence.
- Status: Open formal waiver condition, not closed.
- Residual risk: Blocks any claim that ДКБ-69 is fully met.

### E08-SR-003 Low — Local compose contains dummy dev credentials

- Path/line: `compose.yaml`
- Condition: Local MariaDB/RabbitMQ defaults use dummy `cloud_ui_dev` values.
- Impact: Acceptable for local PoC, but would be unsafe if copied into production deployment.
- Evidence: `scripts/secret-scan.sh` allowlist behavior, `docs/12_DEPLOY_ROCKY_KOLLA.md`,
  `docs/generated/secret-inventory.md`
- Fix: Keep production deployment on secret references and Vault/SecMan/Kolla secret mechanisms.
- Status: Accepted for local PoC only.
- Residual risk: E09 must prove production secret injection without `.env` or Git-stored values.

## Проверки

- [x] Negative RBAC/IDOR.
- [x] CSRF/session.
- [x] Canary secret redaction.
- [x] No credentials in browser/image/log.
- [x] Workflow allowlist/schema.
- [x] Retry/idempotency/lost response.
- [x] Audit delivery/heartbeat.
- [x] Dependency/image scan.
- [x] SELinux/container privileges.
- [x] DKB traceability updated.

Reviewed evidence index:

- `docs/generated/e08-threat-model.md`
- `docs/generated/tls-matrix.md`
- `docs/generated/e08-vault-lab-runbook.md`
- `docs/generated/e08-session-token-protection.md`
- `docs/generated/e08-container-hardening.md`
- `docs/generated/e08-supply-chain.md`
- `docs/generated/e08-dkb-gaps-waivers.md`
- `docs/generated/risk-register.md`

Evidence commands for this review are recorded in `docs/execplans/E08-security-review.md`. The
dependency/image scan checkbox means the E08 local evidence was evaluated: npm audit reported no
frontend vulnerabilities during bootstrap, `make security` runs the repository secret scan, and
`docs/generated/e08-supply-chain.md` records local Docker SBOM evidence. Full image/Python CVE scanner,
license policy, registry and signing evidence remain external/tooling conditions.

## External controls/gaps

- IAM/PAM: formal service-account exception and access review for ДКБ-07.
- PKI/mTLS: corporate CA, mTLS authorization and negative certificate tests for ДКБ-22.02/24/25.
- SIEM: production source onboarding, protected ingest, retention and missing-flow alerts for ДКБ-46-53.
- SecMan: production Vault endpoint/auth, HA, backup and all-secret rotation for ДКБ-55/56.
- SELinux: Rocky/Kolla enforcing mode, labels and denial evidence for ДКБ-65.
- registry/signing: corporate registry, pull-by-digest, signature/provenance and scanner policy for ДКБ-69/70.
- storage: Nova/Cinder/Ceph path proof and local hypervisor filesystem prohibition for ДКБ-72.
- network: management zone, firewall/ACL and unused-interface blocking evidence for ДКБ-42-44/77/80.

## Решение review

Decision: Approved with conditions for continuing the portal-owned E08 hardening candidate into the
next deployment-evidence stage. This is not production approval and not a ДКБ compliance conclusion.
Codex is not the final compliance approval authority.

Conditions:

- Do not enable production destructive workflows without approved live workflow, IAM/PAM, SIEM,
  SecMan and rollback evidence.
- Do not claim ДКБ-69 closure without a formal Python interpreter waiver and image policy evidence.
- Do not claim production TLS/mTLS, SIEM, SecMan, SELinux, registry/signing, storage or network-zone
  compliance until owner evidence is attached and `docs/11_DKB_TRACEABILITY.md` is updated.
