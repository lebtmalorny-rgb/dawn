# Актуальный реестр рисков

- Stage: E00/E02 transition
- Last updated: 2026-06-21
- Rule: запись в этом файле не является принятием риска. Риск считается сниженным только после теста, evidence и ссылки из ExecPlan/ДКБ.

## Снятые или суженные решениями риски

| ID | Риск | Текущее решение | Остаток |
|---|---|---|---|
| R-001 | Использовать Prometheus как источник inventory UI | Inventory source of truth: OpenStack APIs -> portal read model -> paginated portal API. Prometheus/Ceilometer/Gnocchi/Aodh допускаются только как telemetry enrichment. | Нужно реализовать E04 read model и доказать, что list UI не делает live fan-out. |
| R-002 | Самостоятельная эвакуация по Consul/Prometheus signals | Самостоятельный portal-side controller отложен; Masakari read/status остается first-class, а recovery path использует штатный Masakari hostmonitor Consul driver + `matrix.yaml` where enabled. | Нужен отдельный lab proof для Masakari/Consul; `processmonitor` остается diagnostic/R&D. |
| R-003 | WebSocket как преждевременная зависимость | Baseline real-time transport: SSE + HTTP commands + polling fallback. WebSocket только через ADR и load/backpressure evidence. | Проверить proxy/SSE в target HAProxy chain. |

## Блокирующие риски перед E02

| ID | Риск | Почему важен | Митигация в E02 | Evidence |
|---|---|---|---|---|
| R-010 | Test identity/federation flow не выбран | Нельзя доказать P1 login/session/RBAC без утвержденного test identity path. | Начать с deterministic mock provider, production-hard-disabled; Keystone/federation adapter оставить за feature flag до ADR-001 evidence. | Contract tests: mock нельзя включить в production profile; ADR-001 updated. |
| R-011 | Role matrix недостаточно конкретна | Backend RBAC и UI capabilities могут разойтись или стать admin-all. | Seed минимальные роли `cloud_viewer`, `cloud_operator`, `security_auditor`, `portal_admin`; deny by default; service role not assignable to human. | Negative RBAC matrix and capability snapshot tests. |
| R-012 | Session secret/key storage не определен для production | Cookie/session signing/encryption без owner и rotation не закрывает ДКБ. | В P0 использовать generated local test key; production требует Vault/SecMan reference and startup failure if missing. | Secret scan, config tests, ДКБ gap remains E08. |
| R-013 | UI route hiding mistaken for authorization | ДКБ-12 нельзя закрыть только frontend guard. | Backend policy middleware/service повторно проверяет каждый protected endpoint; frontend получает capabilities only for UX. | Direct HTTP 403 tests and UI hidden-action tests. |
| R-014 | Portal allow может обойти OpenStack deny | Portal roles сужают права, но не расширяют Keystone/OpenStack policy. | Ввести simulated OpenStack deny в E02 tests; E03 adapters preserve 403 as final denial. | Test: portal capability allow + OpenStack deny -> 403/audit. |
| R-015 | Audit baseline слишком поздно появится | E02 login/denial без audit не доказывают security gates. | В E02 добавить минимальный audit event/outbox path для auth events, без SIEM claim. | Login success/failure/logout/revoke/denial audit tests. |

## Риски inventory/read model и OpenStack API load

| ID | Риск | Текущее положение | Митигация | Stage |
|---|---|---|---|---|
| R-020 | UI перегружает OpenStack API | Стратегия описана: read model, reconciliation chunks, bounded adapters, no fan-out. Численные лимиты не утверждены. | E04/E10 должны измерить calls per UI action, p95/p99, queue depth, stale age. | E04/E10 |
| R-021 | Stale read model приведет к неверному действию | Требования требуют `observed_at`, `source_updated_at`, `sync_status`, precondition refresh. | Mutating workflows must perform freshness/precondition checks and show stale/unknown state. | E04/E06 |
| R-022 | Notification transport assumptions unreliable | ADR-003 оставляет transport/payload/permissions unknown. | Notifications accelerate only; reconciliation remains correctness authority. | E03/E04/E07 |
| R-023 | Large topology/search leaks protected resource existence | Topology/search must be capability-aware and redacted. | Backend filters nodes/edges/counts; partial counts marked as partial; no raw graph dumps. | E04/E10 |

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
| R-041 | ДКБ-22.02 mTLS scope unclear | TLS matrix exists, mTLS decisions pending. | Per-flow mTLS decision, negative certificate tests, rotation/revoke evidence. | E08/E09 |
| R-042 | ДКБ-50 full audit cannot be portal-only | Portal audit is scoped; host/libvirt/storage/IdP/SIEM sources external. | E07 creates portal audit; E12 maps external sources and gaps. | E07/E12 |
| R-043 | ДКБ-55/56 Vault does not cover all Kolla secrets | Vault product identified; endpoint/auth/rotation unknown. | Separate Vault ADR/runbook and deployment pipeline evidence. | E08/E09 |
| R-044 | ДКБ-69 conflicts with Python runtime | Backend and OpenStack services require interpreters. | Minimal runtime, SBOM/scan, non-root, formal waiver/exception. | E08/E12 |
| R-045 | ДКБ-72 storage architecture external | Portal cannot prove no hypervisor filesystem use. | Storage owner must provide Cinder/Ceph/Nova path evidence. | E12 |
| R-046 | AIO lab evidence may not transfer to HA deployment | Current lab is all-in-one; production Kolla HA behavior differs. | E09/E10 must run HA/failover/load evidence in representative environment. | E09/E10 |

## Operational hygiene risks

| ID | Риск | Текущее положение | Митигация | Stage |
|---|---|---|---|---|
| R-050 | Dirty worktree hides ownership of changes | Current E00 updates are uncommitted. | Before E02 implementation, finalize or commit E00 risk/docs patch; do not mix E02 schema/code with unrelated docs. | Now |
| R-051 | Ignored local worktrees can break scans | `.worktrees/**` previously caused secret-scan false positives. | `scripts/secret-scan.sh` excludes ignored worktrees; regression test added. | Done, keep covered |
| R-052 | Kolla prototype tests in root may not match current gate | `tests/test_e015_kolla_layout.py` targets deployment files not in current root state. | Do not use that test as E00/E02 gate unless E01.5/Kolla prototype files are restored or task requires it. | E09/E015 |

## Immediate priority order

1. Close E00 docs/risk patch with tests and review evidence.
2. Create E02 ExecPlan before code changes.
3. Implement E02.1 identity/provider contracts and negative tests first.
4. Add server-side sessions/RBAC only after deny-by-default contract is explicit.
5. Keep inventory, Prometheus and Masakari out of E02 implementation scope except for capability names and risk references.
