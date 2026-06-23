# Актуальный реестр рисков

- Stage: E08 Vault/SecMan evidence
- Last updated: 2026-06-22
- Rule: запись в этом файле не является принятием риска. Риск считается сниженным только после теста, evidence и ссылки из ExecPlan/ДКБ.

## Снятые или суженные решениями риски

| ID | Риск | Текущее решение | Остаток |
|---|---|---|---|
| R-001 | Использовать Prometheus как источник inventory UI | Inventory source of truth: OpenStack APIs -> portal read model -> paginated portal API. Prometheus/Ceilometer/Gnocchi/Aodh допускаются только как telemetry enrichment. | E04 реализует read model/API/UI и synthetic scale evidence без live fan-out; production MariaDB/live OpenStack/HA evidence остаются E09/E10/P3. |
| R-002 | Самостоятельная эвакуация по Consul/Prometheus signals | Самостоятельный portal-side controller отложен; Masakari read/status остается first-class, а recovery path использует штатный Masakari hostmonitor Consul driver + `matrix.yaml` where enabled. | Нужен отдельный lab proof для Masakari/Consul; `processmonitor` остается diagnostic/R&D. |
| R-003 | WebSocket как преждевременная зависимость | Baseline real-time transport: SSE + HTTP commands + polling fallback. WebSocket только через ADR и load/backpressure evidence. | Проверить proxy/SSE в target HAProxy chain. |

## Блокирующие риски перед E02

| ID | Риск | Почему важен | Митигация в E02 | Evidence |
|---|---|---|---|---|
| R-010 | Test identity/federation flow не выбран | Нельзя доказать P1 login/session/RBAC без утвержденного test identity path. | E02 реализует deterministic mock provider, production-hard-disable; Keystone/federation adapter остается за feature flag до ADR-001 evidence. | `backend/tests/security/test_mock_identity.py`, `backend/tests/test_config.py`. Остаток: ADR-001/test federation не закрыт. |
| R-011 | Role matrix недостаточно конкретна | Backend RBAC и UI capabilities могут разойтись или стать admin-all. | E02 seed roles: `cloud_viewer`, `cloud_operator`, `security_auditor`, `portal_admin`; deny by default; service role not assignable to human. | `docs/06_AUTH_RBAC_SESSIONS.md` P0 matrix, `backend/tests/security/test_security_api.py`, frontend capability test. |
| R-012 | Session secret/key storage не определен для production | Cookie/session signing/encryption без owner и rotation не закрывает ДКБ. | E02 uses opaque random session IDs and server-side P0 records; production persistence/key lifecycle remains Vault/SecMan E08. | `backend/tests/security/test_sessions.py`, `./scripts/secret-scan.sh`. Остаток: DB-backed encrypted session context and rotation. |
| R-013 | UI route hiding mistaken for authorization | ДКБ-12 нельзя закрыть только frontend guard. | E02 backend policy service повторно проверяет protected endpoints; frontend получает capabilities only for UX. | Direct request/403 tests, `audit reader` mutating denial and `session.manage` tests in `backend/tests/security/test_security_api.py`; hidden action test in `frontend/src/App.test.tsx`. |
| R-014 | Portal allow может обойти OpenStack deny | Portal roles сужают права, но не расширяют Keystone/OpenStack policy. | E02 adds simulated OpenStack deny contract; E03 adapters must preserve real OpenStack 403 as final denial. | `test_portal_allow_does_not_override_simulated_openstack_deny` -> `403 openstack_forbidden` and audit event. |
| R-015 | Audit baseline слишком поздно появится | E02 login/denial без audit не доказывают security gates. | E02 records in-process sanitized audit events for auth/session/revoke/origin/authorization, without SIEM delivery claim. | `backend/tests/security/test_audit.py`, `backend/tests/security/test_security_api.py`. Остаток: durable outbox/SIEM E07. |

## Риски inventory/read model и OpenStack API load

| ID | Риск | Текущее положение | Митигация | Stage |
|---|---|---|---|---|
| R-020 | UI перегружает OpenStack API | E04 list/detail APIs read only from the portal read model. `docs/generated/e04-scale-report.md` records 10 000 synthetic instances / 1 000 hypervisors, page limit 200, SQL max 5 and p95 below the provisional 2 s budget on local SQLite. | Repeat evidence on production-like MariaDB/HA with live adapter call counts, queue depth, stale age and p95/p99 in E09/E10. | E04/E10 |
| R-021 | Stale read model приведет к неверному действию | E04 API/UI expose freshness, stale/partial warnings and sync status; frontend refresh affordance is intentionally inert until the mutating frontend CSRF/idempotency flow is complete. | Future mutating workflows must perform freshness/precondition checks before Nova/Mistral actions and audit the result. | E04/E06 |
| R-022 | Notification transport assumptions unreliable | ADR-003 оставляет transport/payload/permissions unknown; E04 does not bind to real notifications. | Notifications accelerate only; full reconciliation remains correctness authority until E07 contract and security evidence exist. | E03/E04/E07 |
| R-023 | Large topology/search leaks protected resource existence | E04 exposes future topology/capacity/service-health modules only as disabled descriptors with capability metadata. | Implement backend scope filtering, redaction and partial counts before enabling real topology/search endpoints. | E04/E10 |

## Resource group risks

| ID | Риск | Текущее положение | Митигация | Stage |
|---|---|---|---|---|
| R-024 | P0 group ownership mistaken for production IAM/SoD evidence | E05 uses trusted mock subject `scope_type/scope_id` for project-scoped VM groups and system-like admin paths for host/mixed groups. | Production federation/Keystone/IAM mapping must replace P0 mock scope and provide SoD evidence before pilot. | E05/E08/E12 |
| R-025 | Dynamic group DSL becomes arbitrary query/code path | E05 compiler accepts only allowlisted JSON AST fields/operators, bounded depth and scalar values; no SQL/Jinja/Python/regex. | Add new fields only with schema/tests/index evidence and update ADR-010/risk register. | E05+ |
| R-026 | Frontend group mutation controls lack CSRF on restored sessions | `/api/v1/session` does not return CSRF; E05 frontend exposes typed mutation wrappers but visible UI is list/detail/search/preview/filter only. | Add explicit CSRF refresh/session bootstrap contract before enabling create/update/add/remove controls after page reload. | E05/E06 |
| R-027 | Member idempotency model reused for destructive workflows | E05 stores HMAC key binding and request hash, including no-op add/remove, but same-key/same-payload replay is re-evaluated instead of served from a stored response snapshot. | Future destructive operations must store response/result snapshots or use operation table semantics before retry is allowed. | E05/E06 |
| R-028 | Host group semantics overstate project ownership | Hypervisors are not project-owned in the read model; P0 host/mixed group management requires admin/system-like capability. | Keep host group mutations admin-only until a formal ownership/approval model exists. | E05/E06 |

## Operations/workflow risks

| ID | Риск | Текущее положение | Митигация | Stage |
|---|---|---|---|---|
| R-029 | P0 Mistral mock mistaken for production workflow safety | E06 proves durable operation/idempotency/outbox, worker duplicate-prevention and UI through `InMemoryMistralAdapter`. Optional all-in-one smoke is read-only workflow lookup and creates no execution. | Do not claim mutating production safety until approved test workflow, service identity, SIEM delivery, OpenStack policy evidence and rollback/cancel evidence exist. | E06/E08 |
| R-033 | Cancel UI implies guaranteed abort | E06 exposes cancel route shape but backend returns `409 operation_not_cancelable` until Mistral state/cancel semantics are proven. | Keep cancel fail-closed; enable only per workflow definition/state with tests for partial effects and audit. | E06+ |
| R-034 | Restored browser session cannot submit operation after reload | `/api/v1/session` does not return CSRF. Frontend disables operation submit unless login response provided in-memory CSRF. | Add explicit CSRF refresh/session bootstrap endpoint before relying on restored-session mutation UX. | E06/E08 |
| R-035 | Watcher/Masakari P0 placeholders overstate live integration | E06 P0 endpoints expose first-class status/risk/conflict markers but do not call live Watcher/Masakari adapters. | Add typed live adapters, contract fixtures and lab evidence before claiming service integration. | E06/E10 |
| R-036 | Operation list leaks cross-scope data | E06 list endpoint filters by actor subject and session scope and uses signed cursor. Detail endpoint still relies on `operation.read` policy only. | Add operation ownership/scope checks to detail/cancel before shared operations or cross-operator views are enabled. | E06/E08 |

## Telemetry and recovery signal risks

| ID | Риск | Текущее положение | Митигация | Stage |
|---|---|---|---|---|
| R-030 | Prometheus exporter load on OpenStack APIs | Prometheus is optional enrichment; not inventory authority. `openstack-exporter` can still add API pressure. | If enabled: service include/exclude, cache TTL, scrape timeout, low-cardinality labels, backend fixed queries. | E10/P3 |
| R-031 | Telemetry datasource ownership unclear | Prometheus path selected for first telemetry option; Ceilometer/Gnocchi/Aodh remain alternatives if deployed. | Record endpoint, retention, downsampling, label policy and RBAC model before UI uses metrics. | E10/P3 |
| R-032 | Raw PromQL or metric labels leak scope | Browser must not access Prometheus directly. | Portal backend exposes allowlisted aggregate endpoints only, with capability/scope filtering. | E10 |

## External/security/compliance risks

| ID | Риск | Текущее положение | Митигация | Stage |
|---|---|---|---|---|
| R-040 | ДКБ-07 service accounts conflict | Human access can use IdP; OpenStack/Kolla service accounts remain necessary. | Formal service-account exception, non-interactive controls, SIEM/audit evidence. | E12 |
| R-041 | ДКБ-22.02 mTLS scope unclear | TLS matrix exists; E08 adds Vault server TLS contract, adapter CA verification tests and lab runbook, but mTLS decisions remain pending. | Per-flow mTLS decision, production PKI evidence, negative certificate tests, rotation/revoke evidence. | E08/E09 |
| R-042 | ДКБ-50 full audit cannot be portal-only | Portal audit is scoped; host/libvirt/storage/IdP/SIEM sources external. | E07 creates portal audit; E12 maps external sources and gaps. | E07/E12 |
| R-043 | ДКБ-55/56 Vault does not cover all Kolla secrets | E08 defines the portal Vault/SecMan contract, synthetic lab paths and `192.168.10.15` runbook; production SecMan endpoint/auth and full Kolla/service secret rotation remain open. | Separate Vault ADR/runbook execution, deployment pipeline integration and rotation/revoke evidence for Kolla, MariaDB, RabbitMQ and OpenStack service secrets. | E08/E09 |
| R-044 | ДКБ-69 conflicts with Python runtime | Backend and OpenStack services require interpreters. | Minimal runtime, SBOM/scan, non-root, formal waiver/exception. | E08/E12 |
| R-045 | ДКБ-72 storage architecture external | Portal cannot prove no hypervisor filesystem use. | Storage owner must provide Cinder/Ceph/Nova path evidence. | E12 |
| R-046 | AIO lab evidence may not transfer to HA deployment | Current lab is all-in-one; production Kolla HA behavior differs. | E09/E10 must run HA/failover/load evidence in representative environment. | E09/E10 |
| R-047 | E07 local audit sink mistaken for production SIEM | E07 proves durable portal audit, local delivery and Fluentd HTTP payload shape, not production SIEM retention or protected channel. | Keep ADR-008 open; require SIEM endpoint/auth/mTLS/retention evidence before pilot. | E07/E08 |
| R-048 | Fluentd running without OpenSearch/central logging | All-in-one has Kolla `fluentd` container, but `enable_central_logging`, `enable_opensearch` and `enable_opensearch_dashboards` are `"no"`. | Treat Fluentd/OpenSearch deployment as manual runbook/evidence only; do not claim current OpenSearch delivery. | E07/E09 |
| R-049 | Portal audit source map overstates full ДКБ-50 coverage | Portal covers its own actions; Keystone/Nova/Neutron/Glance/Cinder/Mistral/Watcher/Masakari, host/container, storage, IdP and monitoring sources are external. | Maintain `docs/generated/audit-source-map.md`; require external owner evidence for full ДКБ-50. | E07/E12 |

## E03 adapter contract risks

| ID | Риск | Текущее положение | Митигация | Stage |
|---|---|---|---|---|
| R-060 | Adapter contract drift from real OpenStack | E03 uses sanitized fixtures and fixed microversions; optional live smoke is pending without approved read-only credential. | Keep fixtures versioned, run smoke only with safe test credential, update microversions deliberately. | E03/E04 |
| R-061 | Token/header leakage in adapter errors | E03 errors redact details and tests assert sensitive values do not appear in repr. | Continue canary tests for future auth adapter and audit/log sinks. | E03 |

## Operational hygiene risks

| ID | Риск | Текущее положение | Митигация | Stage |
|---|---|---|---|---|
| R-050 | Dirty worktree hides ownership of changes | E00 risk/docs patch was finalized before E02 code. | E02 worktree is based on commit `23f6b6f docs: align realtime ops requirements`; schema/code changes are separate. | Done |
| R-051 | Ignored local worktrees can break scans | `.worktrees/**` previously caused secret-scan false positives. | `scripts/secret-scan.sh` excludes ignored worktrees; regression test added. | Done, keep covered |
| R-052 | Kolla prototype tests in root may not match current gate | `tests/test_e015_kolla_layout.py` targets deployment files not in current root state. | Do not use that test as E00/E02 gate unless E01.5/Kolla prototype files are restored or task requires it. | E09/E015 |

## Immediate priority order

1. Finish E07 final verification and keep local/contract audit delivery separate from production SIEM evidence.
2. Keep ADR-001/test federation, ADR-008 production SIEM, Vault/SecMan, IAM/PAM/SoD and host audit evidence as explicit external gaps.
3. Do not treat E06 P0 mock, read-only Mistral smoke or E07 local audit sink as proof of production mutating workflow safety.
