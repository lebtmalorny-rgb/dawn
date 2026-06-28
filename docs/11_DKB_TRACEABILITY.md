# Трассировка требований ДКБ

Источник — предоставленный файл `анализ ДКБ.xlsx`, лист `Матрица`, 73 строки требований. Эта Markdown-матрица добавляет ответственный контур, этап реализации и gate PoC. Исходная оценка не является формальным заключением о соответствии.

## Сводка исходной оценки

- Реализуемо штатно/настройкой: 19.
- Реализуемо при интеграции/архитектуре: 21.
- Частично / внешние меры: 30.
- Пробел / конфликт: 2.
- Нужна детализация: 1.

## Правила использования

- Столбец `Gate` указывает самый ранний уровень, на котором требование должно быть проверено: P1 — интегрированный read-only PoC, P2 — mutating PoC, P3 — production pilot/внешний контур.
- Статус `P3/внешний контур` не означает, что требование неважно для PoC; он означает, что портал сам не может создать достаточное доказательство.
- При изменении реализации обновляются столбцы этапа/evidence и сохраняется ссылка на фактический test report/config/ADR.
- Требование считается закрытым только после review владельцем безопасности; Codex не присваивает финальный статус соответствия.

## Обновление требований 2026-06-21: E02 security foundation

E02 добавляет портальные доказательства для auth/session/RBAC, но не закрывает внешний IAM/PAM/SIEM/PKI контур:

- ДКБ-01/01.01/01.03/01.04/01.05/01.06: портал получил deny-by-default `PolicyService`, P0 role matrix (`cloud_viewer`, `cloud_operator`, `security_auditor`, `portal_admin`) и capability API. Доказательства: `backend/tests/security/test_security_api.py`, `frontend/src/App.test.tsx`, `docs/06_AUTH_RBAC_SESSIONS.md`.
- ДКБ-02/02.01/02.02/02.03: E02 разделяет human/service subject types и запрещает назначение `service` роли human subject. Доказательство: `test_role_binding_denies_service_role_for_human_subject`.
- ДКБ-03/12: frontend скрывает недоступные действия по capabilities, а backend повторно проверяет прямой request. Доказательство: direct request получает `401/403`, UI capability test скрывает `role.manage` action.
- ДКБ-13: login/session responses не содержат OpenStack token/application credential; frontend не пишет session data в `localStorage`/`sessionStorage`; audit metadata редактируется до хранения. Доказательства: `test_mock_identity_authenticates_known_operator_without_browser_secrets`, frontend storage spy, `backend/tests/security/test_audit.py`.
- ДКБ-15: production mock identity hard-disabled через config validation. Это только P0/test evidence; production federation/auth-policy selection остается за ADR-001 и внешним IdP.
- ДКБ-20/21: E02 реализует opaque server-side session cookie, idle timeout 900 seconds, absolute lifetime, logout/admin revoke, CSRF и trusted `Origin` для mutating endpoints, а также default simultaneous-session policy `deny`. Доказательства: `backend/tests/security/test_sessions.py`, `test_session_limit_deny_policy_blocks_second_login`, `test_admin_lists_and_revokes_active_sessions_with_audit_event`, `test_csrf_rejects_state_changing_request`, `test_mutating_endpoint_rejects_untrusted_origin_before_csrf`.
- ДКБ-46-53: E02 создает только baseline audit events для login success/failure, logout, revoke, timeout, session limit, CSRF/origin/authorization/OpenStack denial. Durable outbox, SIEM delivery, heartbeat and full OpenStack/host audit coverage remain E07/P3.
- ДКБ-04/05/07 не закрыты E02. Портальные доказательства сужают риск misuse service-role, но непересечение административных ролей, персональный запуск админских действий, исключения для local/service accounts и PAM-аудит требуют доказательств владельца корпоративного IAM/PAM.

## Обновление требований 2026-06-21: Mistral/Watcher/Masakari и real-time UX

Новый блок требований расширяет будущие evidence, но не меняет текущий статус соответствия:

- ДКБ-01/03/12: first-class модули Mistral, Watcher, Masakari, topology, health dashboards and event streams требуют capability matrix, backend 403 and negative UI/API tests. UI redaction при неполных правах не считается авторизацией без server-side enforcement.
- ДКБ-46–53: operation progress, real-time stream access, Watcher recommendation/apply/abort, Masakari recovery approval and notification views add audit event types and SIEM mapping obligations. Raw OpenStack notifications are not sufficient portal audit evidence.
- ДКБ-66: Masakari visualization, recovery timeline and Nova evacuate/live migration correlation are future HA/failover evidence, but full claim still requires E10 controlled failover and external Kolla/storage/network evidence.
- ДКБ-77/82: API register and user/operator documentation must include event stream, polling fallback, Watcher, Masakari, telemetry datasource, topology/capacity/search interfaces and disabled-interface controls.
- ДКБ-72: topology or Masakari/Nova recovery visualization does not prove storage architecture; storage path evidence remains external/P3.
- Research decision: Consul is treated through Masakari hostmonitor `monitoring_driver=consul` and `matrix.yaml`; Consul Events and Prometheus exporter metrics are diagnostic/corroborating signals, not standalone authoritative recovery triggers.
- Current risk register for E00/E02 transition is `docs/generated/risk-register.md`; it tracks open risks separately from formal ДКБ status and does not claim compliance.

## Обновление требований 2026-06-21: E03 OpenStack adapters

E03 добавляет только backend adapter contracts для read-only Keystone, Nova и Placement. Изменение не добавляет browser endpoints, не передает OpenStack token/application credential в UI и не меняет session/RBAC model:

- ДКБ-01/03/12: adapters находятся за backend boundary; frontend не получает raw OpenStack schema и не вызывает OpenStack API напрямую. Доказательства: `backend/tests/integrations/test_keystone_adapter.py`, `backend/tests/integrations/test_nova_adapter.py`, `backend/tests/integrations/test_placement_adapter.py`.
- ДКБ-46/49/51: adapter errors несут `request_id`/`correlation_id` и редактируют `authorization`/`token` details до `repr`/log-facing представления. Доказательства: `backend/tests/integrations/test_base.py`, `backend/tests/integrations/test_http.py`, `backend/tests/test_redaction.py`.
- ДКБ-77/82: API и integration registers обновлены для Keystone/Nova/Placement с microversions `2.96`/`1.39`, timeout/retry contract и статусом offline evidence. Техническое блокирование неиспользуемых API, firewall/ACL, TLS/mTLS и production PKI остаются E08/E09/P3.

## Обновление требований 2026-06-21: E04 Inventory read model и UI

E04 добавляет первый пользовательский inventory slice через portal read model. Браузер по-прежнему обращается только к frontend/BFF, не получает OpenStack token/application credential и не вызывает OpenStack API напрямую:

- ДКБ-01/03/12: backend проверяет capabilities `instance.read`, `hypervisor.read` и `instance.refresh` на list/detail/refresh endpoints, а frontend использует capabilities только для навигации и действий. Доказательства: `backend/tests/inventory/test_inventory_api.py`, `frontend/src/App.test.tsx`.
- ДКБ-46/49: reconciliation сохраняет sync/freshness/partial state, а protected refresh contract требует CSRF + `Idempotency-Key`, возвращает `operation_id` и пишет sanitized audit event `instance.refresh.requested`. Durable audit outbox/SIEM delivery остаются E07/P3. Доказательства: `backend/tests/inventory/test_reconciliation.py`, `backend/tests/inventory/test_inventory_api.py`.
- ДКБ-60: read model содержит project/flavor/host/availability-zone projections, которые создают базу для будущих групп, но E04 не реализует dynamic groups или group CRUD.
- ДКБ-77/82: `docs/generated/api-register.md`, `docs/generated/integration-register.md`, `docs/generated/risk-register.md` и `docs/generated/e04-scale-report.md` фиксируют реализованные `/api/v1/instances`, `/api/v1/hypervisors`, `/api/v1/inventory/modules`, disabled module descriptors и synthetic scale evidence. Техническое блокирование unused OpenStack/API interfaces, production MariaDB/HA evidence и safe live Nova comparison остаются E08/E09/E10/P3.

## Обновление требований 2026-06-22: E05 Resource groups

E05 добавляет portal-owned resource groups, explicit membership, safe dynamic preview, group-aware
inventory filters and frontend read/search/preview UX. Это не OpenStack placement side effect:
группы не изменяют Nova server groups, host aggregates или Placement.

- ДКБ-60: реализованы `/api/v1/groups*`, project-scoped VM groups, explicit VM/host membership,
  dynamic preview с bounded limit/explain и inventory `group_id` filter. Доказательства:
  `backend/tests/groups/test_group_api.py`, `backend/tests/groups/test_group_repository.py`,
  `backend/tests/groups/test_group_rules.py`, `backend/tests/inventory/test_inventory_api.py`,
  `frontend/src/App.test.tsx`.
- ДКБ-01/03/12: backend повторно проверяет `group.read`/`group.manage`, owner/scope и inventory read
  capability; direct IDOR и cross-project member add получают `403/404`, stale update получает `409`.
  UI uses capabilities only for navigation/actions and does not call OpenStack APIs directly.
- ДКБ-46/49/50.10/51: group create/update/delete/member/preview success and denial paths create
  sanitized portal audit events. Raw `idempotency-key` is not stored in audit metadata; only HMAC key
  hashes/request hashes are persisted for member mutation binding. Durable SIEM delivery remains E07.
- ДКБ-77/82: API, integration and risk registers document `/api/v1/groups*`, `group_id` inventory
  filters, disabled/future semantics and residual P0 limits.

Residual conditions: P0 mock scope is not IAM/SoD production evidence; host group ownership is
admin/system-like only; frontend exposes mutation API wrappers but not create/update/add/remove
controls until restored sessions have a CSRF refresh path; same-key/same-payload member replay is
not a stored-response idempotency model for future destructive workflows.

## Обновление требований 2026-06-22: E06 Operations workflow catalog

E06 добавляет operations-first pipeline: workflow catalog, durable operations/idempotency/outbox,
Mistral adapter mock, worker dispatch, operation UI, P0 Watcher/Masakari read/status modules and
optional read-only all-in-one Mistral smoke.

- ДКБ-01/03/12: backend проверяет `operation.read` and `workflow.execute.maintenance-host` for
  operation submit/list/detail/cancel paths; frontend uses capabilities only for visibility. Direct
  submit without execute capability gets `403`. Доказательства: `backend/tests/operations/test_operation_api.py`,
  `frontend/src/App.test.tsx`.
- ДКБ-46/49/51/52: operation accepted/denied paths create sanitized audit metadata and operation
  timeline events. Raw idempotency keys and browser-supplied workflow names are not stored or exposed.
  Durable SIEM delivery remains E07/P3. Доказательства: `backend/tests/operations/test_operation_api.py`,
  `backend/tests/operations/test_operation_worker.py`, `backend/tests/operations/test_mistral_mock.py`.
- ДКБ-60: E06 consumes E05 groups as operation targets by expanding explicit host groups into concrete
  host snapshots with source group revision. Later membership changes do not change accepted operation
  targets. Доказательство: `test_submit_group_target_expands_and_freezes_member_snapshot`.
- ДКБ-77/82: API/integration/risk registers now document operation APIs, Mistral/Watcher/Masakari
  read/status modules, disabled mutation paths and optional P2 smoke. Technical blocking of unused
  OpenStack endpoints/firewall/policy remains E08/E09/E12.

Residual conditions: default Mistral evidence is P0 mock; P2 smoke is read-only lookup; production
workflow safety, SIEM delivery, IAM/PAM/SoD, Vault identities and HA/failover evidence remain external
gates.

## Обновление требований 2026-06-22: E07 прикладной аудит

E07 добавляет portal-owned audit delivery/search path and generated evidence without claiming full
infrastructure audit compliance:

- ДКБ-46/47: портал пишет нормализованные события в durable outbox and доставляет их в
  `LocalTestAuditSink`; `FluentdHttpAuditSink` проверяет JSON payload contract with `tag`, `time` and
  sanitized `record`. Production SIEM endpoint, protected mTLS/auth channel, retention and SIEM owner
  review remain external. Доказательства: `backend/tests/audit/test_sinks.py`,
  `backend/tests/audit/test_delivery_worker.py`, `docs/generated/e07-fluentd-opensearch-lab.md`.
- ДКБ-48: heartbeat, queue depth, oldest pending age, retry/dead-letter and recovery states are
  implemented for portal audit delivery. This does not prevent root from disabling host/container
  logging; FIM/auditd/IaC and SIEM missing-flow alerting remain external evidence.
- ДКБ-49/49.01-49.08: mandatory portal fields are normalized and documented in
  `docs/generated/audit-event-schema.json` and `docs/generated/audit-action-dictionary.md`.
  Доказательства: `backend/tests/audit/test_models.py`, `backend/tests/audit/test_taxonomy.py`.
- ДКБ-50/50.x: `docs/generated/audit-source-map.md` separates `implemented_by_portal`,
  `lab_contract_only`, `external_required` and `not_in_scope` sources. Portal audit does not close
  Keystone/Nova/Neutron/Glance/Cinder/Mistral/Watcher/Masakari, host/container, storage, IdP or
  monitoring audit coverage.
- ДКБ-51: recursive sanitizer covers stored audit projection, delivery payload and API/frontend
  response canaries. Доказательства: `backend/tests/audit/test_audit_redaction.py`,
  `backend/tests/audit/test_sinks.py`, `backend/tests/audit/test_audit_api.py`,
  `frontend/src/App.test.tsx`.
- ДКБ-52: audit responses expose safe error codes and request/correlation IDs; full internal error text
  must remain in protected sanitized service logs and be correlated externally. E07 does not expose raw
  stack traces in audit API/UI.
- ДКБ-53: `audit.read` and `audit.export` are separate capabilities, audit access is itself audited,
  and the frontend uses backend capabilities only for UX. Direct DB/log/index access remains an
  external PAM/DB/SIEM control. Доказательства: `backend/tests/audit/test_audit_api.py`,
  `frontend/src/App.test.tsx`.

## Обновление требований 2026-06-22: E08 Vault/SecMan

E08 добавляет контракт Vault/SecMan для портальных секретов и generated evidence для lab deployment,
не заявляя production-закрытие SecMan/PKI:

- ДКБ-22.02/24: для Vault зафиксирован server TLS contract, CA verification на уровне adapter tests и
  lab runbook для постоянного Vault на Ansible host `192.168.10.15`. mTLS остается решением владельца
  контура; lab CA не считается corporate PKI evidence.
- ДКБ-13/51: `SecretProvider`/Vault adapter and readiness tests проверяют typed safe errors and
  redaction, а evidence/runbook запрещают сохранять root token, unseal keys, client token, private keys
  or real secret values.
- ДКБ-55: добавлены portal Vault/SecMan path contract, policy artifact
  `docs/generated/e08-vault-policy.hcl`, local/test adapter contract and lab runbook. Production
  SecMan endpoint/auth method still requires owner approval and live evidence.
- ДКБ-56: secret inventory теперь разделяет lifecycle для portal session, cursor, OpenStack, SIEM and
  Vault auth classes. Full Kolla/service secret rotation for MariaDB, RabbitMQ, OpenStack service
  credentials, certificates and deploy pipeline remains open.

Residual gaps: corporate PKI, mTLS, HA Vault topology, backup/restore, auto-unseal/HSM, break-glass,
production endpoint/auth and Kolla/service rotation are not closed by E08 Task 4 documentation.

## Обновление требований 2026-06-23: E08 threat model и TLS/mTLS matrix

E08.1/E08.2 добавляют структурированное security evidence без заявления production-закрытия:

- ДКБ-22.02/23.02/24: `docs/generated/tls-matrix.md` теперь фиксирует per-flow TLS/mTLS decision,
  CA/source, server identity check, client identity/authorization, rotation owner, negative test,
  evidence and residual gap. Lab Kolla TLS evidence for VIP `192.168.10.250` remains lab-only and
  does not replace corporate PKI, SCEP/NDES, mTLS authorization or production negative-certificate
  tests.
- ДКБ-42-44/80: `docs/generated/e08-threat-model.md` and
  `docs/generated/network-flow-matrix.md` map trust boundaries and forbidden flows. Network/VLAN/ACL
  proof remains E09/external evidence.
- ДКБ-46-53: audit delivery threats now point to E07 portal audit evidence and explicitly keep SIEM
  protected-channel mTLS/auth/retention and host audit/FIM as external controls.
- ДКБ-55/56: the threat model references the E08 Vault/SecMan adapter/runbook evidence while keeping
  full Kolla/OpenStack/MariaDB/RabbitMQ secret rotation as an E09/deployment-pipeline gap.
- ДКБ-65/69/70/76/77: high residual risks are listed with owner and compensating controls. ДКБ-69 is
  still a conflict for Python backend/OpenStack runtime and is not hidden by matrix documentation.

Evidence: `backend/tests/security/test_e08_security_docs.py`, `docs/generated/e08-threat-model.md`,
`docs/generated/tls-matrix.md`, `docs/generated/risk-register.md`,
`docs/generated/network-flow-matrix.md` and ExecPlan `docs/execplans/E08-threat-model-tls.md`.

## Обновление требований 2026-06-23: E08 session/token protection

E08.4 добавляет безопасный CSRF bootstrap для восстановленной server-side browser session без
заявления production-закрытия durable session storage или Vault rotation:

- ДКБ-13/51: `GET /api/v1/session/csrf` возвращает только subject, CSRF and expiration для
  authenticated BFF/API session. Тесты проверяют, что payload не содержит OpenStack/Vault/password/
  private-key indicators, raw CSRF не пишется в audit metadata, а frontend не сохраняет CSRF/session
  data в `localStorage` или `sessionStorage`.
- ДКБ-20/21: logout/revoke/timeout semantics remain server-side. Missing, revoked or expired sessions
  do not receive CSRF and return safe `401`; restored valid sessions can submit the existing operation
  path only after receiving the CSRF value.
- ДКБ-46-53: denial paths keep using sanitized session/audit events; the bootstrap endpoint itself does
  not add a raw-token audit event. SIEM delivery, host audit and full external source coverage remain
  E07/E12 evidence, not closed by this slice.
- ДКБ-55/56: session/cursor key lifecycle still depends on Vault/SecMan ownership, rotation and
  deployment evidence. E08.4 documents CSRF as a per-session runtime value, not a long-lived
  Vault-managed secret.

Evidence: `backend/tests/security/test_security_api.py`,
`frontend/src/App.test.tsx`, `docs/generated/e08-session-token-protection.md`,
`docs/generated/risk-register.md`, `docs/generated/secret-inventory.md` and ExecPlan
`docs/execplans/E08-session-token-protection.md`.

## Обновление требований 2026-06-23: E08 container hardening

E08.5 добавляет проверяемые controls для portal-owned app containers in local compose, не заявляя
полное production-закрытие образов или SELinux:

- ДКБ-65: `compose.yaml` теперь задает read-only root filesystem, dropped capabilities,
  `no-new-privileges` and controlled tmpfs paths для `api`, `worker`, `events`, `frontend`. Rocky
  SELinux enforcing mode, labels and denial evidence остаются E09/external host proof.
- ДКБ-69: backend/frontend Dockerfile tests фиксируют build/runtime separation and non-root runtime
  evidence. Python backend still requires an interpreter, and inherited base images may still contain
  shell/package-manager components; this remains a formal waiver/gap, not a closed requirement.
- ДКБ-70: this slice does not push images to a corporate registry and does not create digest/signing
  evidence. Registry and provenance proof remain E08.6/E09.
- ДКБ-76/77/80: app containers no longer expose default writable root/capability posture in local
  compose, and tests reject Docker/Podman socket or host-root mounts. Full Kolla network/container
  runtime evidence remains E09.

Evidence: `backend/tests/security/test_e08_container_hardening.py`,
`compose.yaml`, `backend/Dockerfile`, `frontend/Dockerfile`,
`docs/generated/e08-container-hardening.md`, `docs/generated/risk-register.md` and ExecPlan
`docs/execplans/E08-container-hardening.md`.

## Обновление требований 2026-06-23: E08 supply chain

E08.6 добавляет локальный reproducible supply-chain gate для двух portal-owned images без заявления
production registry/signing compliance:

- ДКБ-69: `backend/Dockerfile` and `frontend/Dockerfile` now pin base images by digest, and
  `make sbom` records local Docker SBOM summaries for `cloud-ui-backend:dev` and
  `cloud-ui-frontend:dev`. Python backend still requires an interpreter, and inherited base images may
  contain shell/package-manager components; this remains a formal waiver/gap.
- ДКБ-70: `make sbom` builds local images and records local image IDs plus SBOM table SHA-256 values.
  This is not corporate registry push, production pull-by-digest enforcement, image signing or
  provenance verification. Those controls remain E09/external supply-chain evidence.
- ДКБ-76/77/80: local image source and SBOM evidence now has repository tests. Full Kolla build,
  registry ACL/network and deployment digest evidence remains E09.

Evidence: `backend/tests/security/test_e08_supply_chain.py`, `Makefile`,
`scripts/generate-sbom.sh`, `backend/Dockerfile`, `frontend/Dockerfile`,
`docs/generated/e08-supply-chain.md`, `docs/generated/risk-register.md` and ExecPlan
`docs/execplans/E08-supply-chain.md`.

## Обновление требований 2026-06-23: E08 DKB gaps/waivers

E08.7 добавляет consolidated draft gap/waiver register without claiming approval or compliance closure:

- ДКБ-07: service-account conflict вынесен в `formal_waiver_required` with IAM/PAM owner role,
  review/expiry and compensating controls. Human federation can remain the target path, but Kolla,
  OpenStack, OS and integration service accounts require a formal exception and non-interactive
  controls.
- ДКБ-22.02: TLS/mTLS matrix evidence is linked to a production PKI/mTLS gap. Corporate CA,
  certificate rotation, client identity authorization and negative certificate tests remain external.
- ДКБ-48/50: portal audit evidence remains scoped to portal-owned events. Host/container/libvirt/
  network/storage/IdP/OpenStack audit sources, SIEM missing-flow alerts and protected SIEM retention
  remain external evidence.
- ДКБ-55/56: Vault/SecMan adapter contract, policy artifact and lab runbook are not production
  SecMan acceptance. Full Kolla, MariaDB, RabbitMQ, OpenStack service, SIEM, PKI and portal secret
  issue/rotation/revoke evidence remains required.
- ДКБ-65: local compose hardening does not prove Rocky SELinux/AppArmor enforcing labels, denials or
  host policy. These remain E09/external deployment evidence.
- ДКБ-69/70: local container hardening, digest pins and SBOM narrow supply-chain risk but do not close
  the Python interpreter/shell conflict, corporate registry, signature, scanner and provenance
  requirements. ДКБ-69 explicitly remains not closed and requires a formal waiver for Python backend.
- ДКБ-72/77/80: storage path, unused-interface blocking and management-zone placement require storage,
  Kolla/firewall/policy and network owner evidence. Repository documentation alone is not enough.

Evidence: `backend/tests/security/test_e08_dkb_gaps.py`,
`docs/generated/e08-dkb-gaps-waivers.md`, `docs/generated/risk-register.md` and ExecPlan
`docs/execplans/E08-dkb-gaps-waivers.md`.

## Обновление требований 2026-06-23: E08 security review

E08.8 добавляет итоговый automated security review по `templates/SECURITY_REVIEW_TEMPLATE.md` without
formal compliance approval:

- Review decision is `Approved with conditions` for the portal-owned E08 hardening candidate, with
  `Unresolved critical/high findings: 0` for the reviewed local code/docs scope.
- ДКБ-13/51: review verifies no browser OpenStack/Vault token exposure, restored-session CSRF behavior,
  canary redaction, secret scan and secret inventory evidence.
- ДКБ-22.02/24/25: review keeps TLS/mTLS as matrix evidence plus external PKI/mTLS owner conditions;
  no production protected-channel claim is made.
- ДКБ-46-53: review accepts portal audit evidence for local scope and keeps SIEM/source onboarding,
  host/container audit, retention and missing-flow alerts external.
- ДКБ-55/56: review keeps Vault/SecMan adapter evidence separate from production SecMan acceptance and
  all-secret rotation.
- ДКБ-65/69/70/77/80: review verifies local container/supply-chain evidence and keeps SELinux,
  formal ДКБ-69 waiver, corporate registry/signing, network-zone and unused-interface blocking as
  external/deployment gates.

Evidence: `backend/tests/security/test_e08_security_review.py`,
`docs/generated/e08-security-review.md`, `docs/generated/risk-register.md` and ExecPlan
`docs/execplans/E08-security-review.md`.

## Обновление требований 2026-06-24: E09.1 Kolla image build

E09.1 добавляет repository-side Kolla Build contract для двух portal-owned images без заявления live
registry/deployment compliance:

- ДКБ-69: `deploy/kolla/docker/cloud-ui-backend/Dockerfile.j2` and
  `deploy/kolla/docker/cloud-ui-frontend/Dockerfile.j2` define custom Kolla image templates and
  keep one backend image for API, worker, events, migration and smoke commands. Python backend still
  requires an interpreter; formal waiver and approved scanner/signing evidence remain required.
- ДКБ-70: `deploy/kolla/scripts/build-images.sh` requires explicit test registry, immutable tag and
  source pin, rejects `latest`, and provides the push-by-registry contract. Actual corporate test
  registry push, digest, SBOM, scanner and signature evidence remain pending external evidence.
  The wrapper builds Kolla source directories from a pinned Git archive and separately verifies the
  prebuilt frontend dist hash, rejects custom Kolla config/template overrides, and validates rendered
  source paths before invoking `kolla-build`.
- ДКБ-76/77/80: `deploy/kolla/README.md` documents image build interfaces and non-goals. Runtime
  Kolla-Ansible container inspection, network ACLs, management-zone placement, disabled unused
  interfaces, HAProxy/TLS and rollback proof remain E09.2-E09.8.
- ДКБ-55/56: the build contract stores no runtime secrets. Kolla/Ansible secret references, DB/RabbitMQ
  credentials and rotation proof remain later deployment evidence.

Evidence: `tests/test_e09_kolla_image_build.py`, `deploy/kolla/README.md`,
`deploy/kolla/kolla-build.conf.example`, `deploy/kolla/scripts/build-images.sh`,
`docs/generated/e09-kolla-image-build.md` and ExecPlan `docs/execplans/E09-kolla-image-build.md`.

## Обновление требований 2026-06-24: E09.2 Kolla-Ansible role skeleton

E09.2 добавляет repository-side Kolla-Ansible role skeleton для Cloud UI без заявления live
deployment compliance:

- ДКБ-69: `deploy/kolla/ansible/roles/cloud_ui/defaults/main.yml` keeps exactly two portal-owned
  image names and maps `cloud_ui_api`, `cloud_ui_worker` and `cloud_ui_events` to `cloud-ui-backend`.
  Python backend still requires an interpreter; formal waiver, scanner and signing evidence remain
  required.
- ДКБ-70: role defaults include tag/digest placeholders and validation rejects `latest`. Corporate
  registry push, pull-by-digest enforcement, SBOM, vulnerability scan and signature evidence remain
  pending external evidence.
- ДКБ-76/77/80: `deploy/kolla/ansible/roles/cloud_ui` records service groups, ports, config roots,
  volumes and hardening dimensions for later Kolla-Ansible integration. It does not prove runtime
  network ACLs, management-zone placement, unused-interface blocking, HAProxy/TLS or live container
  inspection.
- ДКБ-55/56: E09.2 templates contain only non-secret config. Kolla secret delivery, DB/RabbitMQ
  credentials and rotation proof remain later deployment evidence.
- ДКБ-82: rollback for this slice is Git revert only. Live Kolla reconfigure/rollback proof remains
  later E09 evidence.

Evidence: `tests/test_e09_kolla_ansible_role.py`, `deploy/kolla/ansible/README.md`,
`deploy/kolla/ansible/roles/cloud_ui/*`, `docs/generated/e09-kolla-ansible-role.md`,
`docs/generated/risk-register.md` and ExecPlan `docs/execplans/E09-kolla-ansible-role.md`.

E09 runtime-secret injection update: the `cloud_ui` role now declares empty
`cloud_ui_database_url`/`cloud_ui_rabbitmq_url` inputs, documents their Vault/SecMan lab paths in
`cloud_ui_secret_references`, validates that these URLs are supplied when `cloud_ui_enabled=true`,
and renders `CLOUD_UI_DATABASE_URL`/`CLOUD_UI_RABBITMQ_URL` with `no_log: true`. This narrows the
live readiness 503 root cause to runtime secret delivery/principal drift without committing any
runtime secret value. It does not close full ДКБ-55/56 rotation/owner evidence.

## Обновление требований 2026-06-25: E09.3 DB/RabbitMQ provisioning

E09.3 добавляет repository-side contract and sanitized all-in-one lab evidence для one-time Cloud UI
MariaDB/RabbitMQ provisioning:

- ДКБ-55/56: `deploy/kolla/ansible/roles/cloud_ui_provisioning` фиксирует Vault/SecMan lab path
  `kv/cloud-ui/local/*`, отдельные Cloud UI DB/MQ principals and `no_log` task shape. Lab Vault
  `2.0.3` installed from approved internal mirror `192.168.10.17:8080`, initialized/unsealed on
  `192.168.10.15`, with KV and file audit enabled. Cloud UI DB/MQ secrets were generated on the test
  host and stored in Vault without committing or printing secret values. Package signature evidence
  for that mirror was not established in this slice, so the lab install does not close production
  supply-chain controls. Production SecMan endpoint, HA, backup, auto-unseal, rotation and owner
  approval remain external.
- ДКБ-42-44/76/77/80: lab MariaDB schema/users and RabbitMQ vhost/user/exchanges/queues were created
  with least-privilege checks: DB runtime user denied `mysql`; RabbitMQ `cloud_ui` has only
  `/cloud-ui` permissions matching `^cloud-ui\\.` and no root-vhost permission. Network/VLAN/ACL,
  management-zone placement, unused-interface blocking and HA evidence remain external E09/E10 proof.
- Auth boundary clarification: Keystone service users/service tokens authorize OpenStack API and
  service-to-service calls. MariaDB sessions and RabbitMQ broker sessions are authenticated by their
  own DB/MQ principals and deployment secrets. `oslo.messaging` defines the messaging transport, but
  with RabbitMQ it still uses broker credentials, vhost permissions and TLS from the transport URL.
  DB/MQ `Access denied`/`ACCESS_REFUSED` readiness failures are therefore not Keystone RBAC failures.
- ДКБ-69/70/82: E09.3 не меняет image build, registry, scanner/signing or full rollback proof.
  Repository rollback is Git revert; live cleanup requires explicit approval for Vault paths,
  MariaDB users/schema and RabbitMQ user/vhost.

Evidence: `tests/test_e09_db_rabbitmq_provisioning.py`,
`docs/generated/e09-db-rabbitmq-provisioning.md`, `docs/generated/risk-register.md` and ExecPlan
`docs/execplans/E09-db-rabbitmq-provisioning.md`.

## Обновление требований 2026-06-25: E09.4 Migration job

E09.4 добавляет repository-side contract для one-shot DB migration job без live schema mutation:

- ДКБ-55/56: `cloud_ui_db_migrate` uses the existing backend image and the explicit
  `cloud-ui db-upgrade` command. Migration secret material remains tied to the E09.3 Vault-backed
  migration credential and is not stored in Git. CLI success output is sanitized and does not print
  database URL or credentials.
- ДКБ-69/70: the migration job preserves the two-image contract and does not introduce a third
  migration image. Registry digest pull, scanner, signing, package provenance and the ДКБ-69 Python
  interpreter waiver remain pending external evidence.
- ДКБ-76/77/80/82: role metadata records one-shot semantics, precheck command, required lock and
  rollback-window requirement. `API auto migration` is disabled; live migration execution remains pending.
  No Kolla deploy/reconfigure or three-node rollout proof is claimed by this slice.

Evidence: `tests/test_e09_migration_job.py`, `docs/generated/e09-migration-job.md`,
`docs/generated/risk-register.md` and ExecPlan `docs/execplans/E09-migration-job.md`.

## Обновление требований 2026-06-25: E09.5 Process containers

E09.5 adds synthetic repository topology evidence for the permanent Cloud UI process layout:

- ДКБ-69/70: `cloud_ui_process_topology` preserves the two-image contract: `cloud-ui-frontend` for
  frontend and `cloud-ui-backend` for API, worker and events. Registry digest pull, scanner,
  signature/provenance evidence and the ДКБ-69 Python interpreter waiver remain pending.
- ДКБ-76/77/80: the role records 3 control/UI nodes and 12 permanent containers as synthetic
  repository topology. `cloud_ui_db_migrate` remains a separate one-shot job. live container inspection remains pending;
  no Kolla deploy/reconfigure, HAProxy/TLS or network ACL proof is claimed by this slice.
- ДКБ-82: rollback is repository-only by Git revert. Live rolling update and failed-update rollback
  remain later E09 evidence.

Evidence: `tests/test_e09_process_containers.py`, `docs/generated/e09-process-containers.md`,
`docs/generated/risk-register.md` and ExecPlan `docs/execplans/E09-process-containers.md`.

## Обновление требований 2026-06-25: E09.6 HAProxy/TLS/network

E09.6 добавляет repository-side HAProxy/TLS/network contract для Cloud UI same-origin route:

- ДКБ-22.02/23.02/24: роль фиксирует внешний `https` route, TLS minimum `TLSv1.2`, backend TLS mode
  decision (`internal_http`, `backend_tls`, `backend_mtls`) and trusted proxy headers. Corporate PKI,
  mTLS authorization, revocation/rotation and negative certificate tests remain pending external
  evidence.
- ДКБ-65/66: `docs/generated/network-flow-matrix.md` records Cloud UI same-origin route and forbidden
  browser/frontend flows. Management CIDR/VLAN/firewall ACL proof remains pending external evidence.
- ДКБ-69/70: HAProxy template stores no certificate/key material, passwords, tokens, `.env` or
  production inventory values. Registry digest pull, scanner/signature and ДКБ-69 waiver remain
  external gates.
- ДКБ-76/77/80/82: route, health check, timeout, body limit, security headers and public path
  deployment interface are tested. This is not a live HAProxy deployment, Kolla reconfigure, route
  smoke, rollback execution or production approval.

Evidence: `tests/test_e09_haproxy_tls_network.py`,
`docs/generated/e09-haproxy-tls-network.md`, `docs/generated/tls-matrix.md`,
`docs/generated/network-flow-matrix.md`, `docs/generated/risk-register.md` and ExecPlan
`docs/execplans/E09-haproxy-tls-network.md`.

## Обновление требований 2026-06-25: E09.7 Reconfigure/upgrade/rollback

E09.7 добавляет repository-side lifecycle contract для Cloud UI Kolla deployment без live
`kolla-ansible` запуска:

- ДКБ-55/56: lifecycle keeps secrets out of Git and references the existing deployment-secret boundary.
  Full Kolla/OpenStack/MariaDB/RabbitMQ/SIEM/PKI secret rotation remains external evidence.
- ДКБ-69/70: lifecycle requires image pull by digest before rollout and preserves the two-image
  contract. Live registry digest pull, scanner/signature/SBOM and the ДКБ-69 Python interpreter waiver
  remain pending.
- ДКБ-76/77/80: clean deploy/reconfigure, rolling upgrade, failed update rollback and disable/uninstall
  phases are documented for test-inventory execution. Firewall/ACL, management-zone scan and disabled
  unused-interface proof remain external.
- ДКБ-82: operational lifecycle and rollback path are documented. This is not a live Kolla
  reconfigure, idempotency run, rolling update, failed rollback execution or production approval.

Evidence: `tests/test_e09_reconfigure_rollback.py`,
`docs/generated/e09-reconfigure-rollback.md`, `docs/generated/risk-register.md` and ExecPlan
`docs/execplans/E09-reconfigure-rollback.md`.

## Обновление требований 2026-06-25: E09.8 Deployment smoke/evidence

E09.8 adds a fail-closed evidence runner for approved test-stand deployment smoke:

- ДКБ-22.02/24: TLS and health evidence can be recorded from the test stand. Corporate PKI/mTLS
  approval and negative certificate tests remain external.
- ДКБ-42-44/77/80: container count, management network and ACL evidence can be attached only after
  sanitized test-stand output is collected.
- ДКБ-55/56: the runner rejects or redacts secret-like output and stores no credentials in Git.
  Full secret rotation and revoke evidence remain external.
- ДКБ-65: container user/capability/mount/SELinux inspection is represented as live evidence rows.
- ДКБ-69/70: digest-pinned image evidence is required, but ДКБ-69 remains open without the Python
  interpreter waiver and image policy evidence.
- ДКБ-82: deployment smoke evidence improves operational proof; full E09 acceptance still requires
  executed rollback evidence.

Evidence: `tests/test_e09_deployment_smoke_evidence.py`,
`deploy/kolla/scripts/collect-e09-evidence.py`,
`docs/generated/e09-deployment-smoke-evidence.md`,
`docs/generated/risk-register.md` and ExecPlan
`docs/execplans/E09-deployment-smoke-evidence.md`.

Обновление live evidence 2026-06-28: на утвержденном all-in-one test stand Cloud UI развернут
из digest-pinned backend/frontend образов через ограниченный Ansible/Docker lab script. Зафиксированы
четыре live контейнера (`frontend`, `api`, `worker`, `events`), успешный `cloud-ui db-upgrade`,
API readiness HTTP 200 с DB/RabbitMQ `reachable`, frontend HTTP 200 и frontend BFF route
`/api/v1/session` HTTP 401 без раскрытия сессии. Sanitized Docker inspect подтвердил non-root
`cloudui`, read-only root filesystem, `cap_drop=["ALL"]` и `no-new-privileges` для всех четырех
контейнеров. Runtime env, credentials and full inspect files are not committed.

This narrows, but does not close, the affected requirements:

- ДКБ-55/56: lab DB/MQ runtime access now works without committing secret values. Full SecMan/Kolla
  rotation, revoke, owner approval and production secret lifecycle evidence remain open.
- ДКБ-65: container user/cap/read-only-rootfs evidence is now available for one all-in-one test node.
  SELinux label and host policy evidence remain open.
- ДКБ-69/70: digest pull/deploy evidence exists for the test registry. ДКБ-69 remains a formal
  Python interpreter/shell waiver gap; corporate registry signing, scanner/SBOM and provenance remain
  open.
- ДКБ-76/77/80: live evidence is limited to one Docker `cloud-ui` network and direct test ports.
  Three-node topology, management VLAN, firewall/ACL and unused-interface blocking remain open.
- ДКБ-82: rollback snapshot and smoke evidence exist for the all-in-one lab. Full Kolla-Ansible
  reconfigure, rolling update and failed-update rollback acceptance remain open.

Обновление live evidence 2026-06-28, AIO role path: текущий all-in-one UI переведен с bounded
manual Docker script на Kolla-Ansible-side role path. `deploy/kolla/ansible` был синхронизирован на
Ansible host в `/etc/kolla/cloud-ui-sync-bundle`, preflight playbook прошел с `ok=10 changed=0
failed=0`, затем `playbooks/cloud-ui-aio-reconfigure.yml` был выполнен через Kolla inventory
`/etc/kolla/all-in-one` и Kolla virtualenv с итогом `openstack-aio : ok=35 changed=6 failed=0
skipped=1`. Повторный прогон с `cloud_ui_aio_run_migration=false` подтвердил idempotency:
`openstack-aio : ok=34 changed=0 failed=0 skipped=2`. После роли API readiness вернул HTTP 200,
frontend `/api/v1/session` через frontend вернул HTTP 401, а sanitized inspect снова подтвердил
`cloudui`, read-only rootfs, `cap_drop=["ALL"]` и `no-new-privileges`.

This further narrows, but still does not close, the affected requirements:

- ДКБ-55/56: role tasks accept DB/MQ runtime URLs only from runtime vars and secret-referencing tasks
  use `no_log: true`; full SecMan/Kolla rotation and revoke evidence remain open.
- ДКБ-65: the all-in-one role path preserves non-root/read-only/cap-drop runtime evidence; SELinux
  label and host policy evidence remain open.
- ДКБ-69/70: the role converged digest-pinned test-registry images. Formal ДКБ-69 waiver,
  corporate registry signing/scanner/provenance evidence remain open.
- ДКБ-76/77/80: evidence is still direct-port AIO on Docker network `cloud-ui`; HAProxy/VIP/TLS,
  management VLAN, firewall/ACL and unused-interface blocking remain open.
- ДКБ-82: AIO role reconfigure and idempotency evidence now exist, but upstream Kolla
  `site.yml`/tag integration, three-node rolling update and failed-update rollback acceptance remain
  open.

Обновление live evidence 2026-06-28, AIO Kolla CLI path: добавлен и выполнен bounded wrapper
`deploy/kolla/scripts/run-cloud-ui-aio-kolla.py`, который строит allowlisted запуск
`kolla-ansible reconfigure -p <cloud-ui-aio-playbook> -t cloud-ui` для текущего all-in-one пути.
Wrapper rejects production-looking inventories, non-digest image inputs and a closed rollback window,
and it does not read or print DB/MQ runtime URL values. Kolla CLI preflight completed with
`localhost : ok=10 changed=0 failed=0`; Kolla CLI `reconfigure-no-migration` completed with
`openstack-aio : ok=34 changed=0 failed=0 skipped=2`. Post-run smoke returned API readiness HTTP 200,
frontend HTTP 200 and frontend `/api/v1/session` HTTP 401; sanitized inspect confirmed `cloudui`,
read-only rootfs, `cap_drop=["ALL"]` and `no-new-privileges`. This narrows ДКБ-82 from direct
`ansible-playbook` evidence to Kolla CLI custom-playbook evidence, but still does not close upstream
Kolla `site.yml` service integration, three-node rolling update or failed-update rollback acceptance.

## E09 live reconfigure preflight bundle

Обновление требований 2026-06-26: E09 live reconfigure preflight bundle is preflight only. It
validates repository-side inputs for an approved test-stand preparation path while live
deploy/reconfigure evidence remains
`pending_external_evidence`. The slice does not create a production action or E09 acceptance claim.

For ДКБ-55/56, the bundle validates runtime DB/MQ inputs supplied from the approved secret mechanism
without committing any runtime secret value. Rotation, owner approval and SecMan evidence remain open
until the approved external run provides sanitized proof.

For ДКБ-65/69/70/76/77/80/82, this slice creates no live container, registry, network, SELinux or
rollback proof. It adds operator documentation and a preflight validation bundle only; live Kolla
run evidence, registry digest proof, management-zone/API proof, host hardening inspection and rollback
execution evidence remain pending.

Evidence paths:

- `tests/test_e09_live_reconfigure_bundle.py`
- `deploy/kolla/ansible/playbooks/cloud-ui-preflight.yml`
- `deploy/kolla/ansible/examples/cloud-ui-vars.yml.example`
- `docs/generated/e09-live-reconfigure-bundle.md`

## E09 Ansible sync bundle

Обновление требований 2026-06-26: E09 Ansible sync bundle is local-only and prepares a reproducible
operator artifact for a later, separately approved test-host sync. Remote sync, live reconfigure,
DB/MQ auth remediation, 12-container inspection, HAProxy/TLS, SELinux and rollback remain
`pending_external_evidence`.

For ДКБ-55/56, the exporter rejects runtime secret value material and does not include inventory,
DB/MQ URLs, SSH data, tokens, private keys, `.env`, `clouds.yaml` or openrc. Secret delivery and
rotation remain external evidence.

For ДКБ-65/69/70/76/77/80/82, this slice creates a checksum manifest and operator documentation only.
It does not prove live container hardening, registry pull-by-digest, management-zone ACLs, live
deployment, rollback or ДКБ-69 waiver closure.

Evidence paths:

- `tests/test_e09_ansible_sync_bundle.py`
- `deploy/kolla/scripts/export-ansible-bundle.py`
- `docs/generated/e09-ansible-sync-bundle.md`

## Полная матрица

| Код | Требование | Исходная оценка | Контур ответственности | Этап | Gate | Рекомендуемая реализация/проверка | Остаточный риск/условие | Доказательство |
|---|---|---|---|---|---|---|---|---|
| ДКБ-01 | Ролевая модель должна соответствовать принципу наименьших привилегий; механизм управления правами доступа должен покрывать функции, объекты и данные системы. | Реализуемо при интеграции/архитектуре (3/4) | Портал + Keystone + корпоративный IAM | E02 | P1 | Keystone RBAC, system/domain/project scopes, default roles admin/member/reader/manager/service; политики oslo.policy по сервисам; проектирование кастомных ролей под функциональные позиции. | Неполное покрытие действий вне API: host CLI, libvirt, storage backend, DB/root-доступ. | Ролевая матрица; policy/capability tests; отрицательные UI/API tests; session/CSRF tests; audit login/denial. |
| ДКБ-01.01 | Предоставление пользователям минимально необходимых прав для выполнения функциональных обязанностей. | Реализуемо штатно/настройкой (4/4) | Портал + Keystone + корпоративный IAM | E02 | P1 | Назначение ролей Keystone на минимальном scope; отдельные группы IdP/LDAP; запрет admin там, где достаточно reader/member/manager. | Нужна ревизия policy.yaml каждого сервиса и тестирование негативных сценариев. | Ролевая матрица; policy/capability tests; отрицательные UI/API tests; session/CSRF tests; audit login/denial. |
| ДКБ-01.02 | Архитектура БД должна быть такова, чтобы права пользователей в БД не превышали прав пользователей в прикладной системе. | Частично / внешние меры (2/4) | Портал + Keystone + корпоративный IAM | E02 | P2 | Пользователи OpenStack не получают прямой доступ к БД; БД обслуживается сервисными DB-аккаунтами. Ограничить DB-аккаунты по сервисам; доступ DBA/root оформлять отдельно. | Администратор БД или root на контроллере обходит прикладной RBAC; нужен PAM/sudo/auditd/разделение обязанностей. | Ролевая матрица; policy/capability tests; отрицательные UI/API tests; session/CSRF tests; audit login/denial. |
| ДКБ-01.03 | Механизм распределения прав доступа должен охватывать все операции пользователей над объектами системы и операции над объектами системы. | Частично / внешние меры (2/4) | Портал + Keystone + корпоративный IAM | E02 | P2 | API-операции покрыть Keystone/oslo.policy и сервисными policy-файлами; операции на узлах, libvirt, storage и backup покрыть ОС/RBAC/SIEM. | Полнота требования зависит от запрета прямого доступа к хостам и backend-хранилищам. | Ролевая матрица; policy/capability tests; отрицательные UI/API tests; session/CSRF tests; audit login/denial. |
| ДКБ-01.04 | Механизм разграничения прав доступа должен быть реализован на основе ролей. | Реализуемо штатно/настройкой (4/4) | Портал + Keystone + корпоративный IAM | E02 | P1 | Keystone RBAC + роли OpenStack; политики сервисов через oslo.policy. | Для нестандартных ролей нужна поддерживаемая policy-модель и регресс-тесты после обновлений. | Ролевая матрица; policy/capability tests; отрицательные UI/API tests; session/CSRF tests; audit login/denial. |
| ДКБ-01.05 | Роли должны быть разработаны на основе функциональной позиции пользователя с учетом минимальных полномочий и иерархии. | Реализуемо при интеграции/архитектуре (3/4) | Портал + Keystone + корпоративный IAM | E02 | P1 | Разработать проектную ролевую матрицу: Cloud Operator, Security Auditor, Tenant Admin, Network Admin, Image Admin, Backup Operator и т.п.; маппинг групп IdP на роли Keystone. | Риск role creep; требуется периодическая переаттестация прав. | Ролевая матрица; policy/capability tests; отрицательные UI/API tests; session/CSRF tests; audit login/denial. |
| ДКБ-01.06 | Ролевая модель должна охватывать и определять доступ к данным, хранимым и обрабатываемым в системе. | Частично / внешние меры (2/4) | Портал + Keystone + корпоративный IAM | E02 | P2 | RBAC OpenStack покрывает доступ к cloud-ресурсам: projects, instances, volumes, images, networks. Данные внутри ВМ, на backup/SIEM/СХД и прямой host-root доступ требуют внешних controls. | Нужно явно определить границу ответственности OpenStack vs guest OS/storage/backup. | Ролевая матрица; policy/capability tests; отрицательные UI/API tests; session/CSRF tests; audit login/denial. |
| ДКБ-02 | Ролевая модель должна состоять из непересекающихся подмножеств: административные, технологические, внутренние роли. | Реализуемо при интеграции/архитектуре (3/4) | Портал + Keystone + корпоративный IAM | E02 | P1 | Реализовать группы/домены в IdP + роли Keystone; разделить human-admin, service/service role, internal tenant users. | В Keystone нет полноценного SoD-движка для запрета всех конфликтующих сочетаний ролей. | Ролевая матрица; policy/capability tests; отрицательные UI/API tests; session/CSRF tests; audit login/denial. |
| ДКБ-02.01 | Административные роли назначаются ИТ-персоналу организации. | Реализуемо штатно/настройкой (4/4) | Портал + Keystone + корпоративный IAM | E02 | P1 | System/domain scoped admin/manager/reader; группы IdP для ИТ-персонала. | Нужен процесс согласования и переаттестации. | Ролевая матрица; policy/capability tests; отрицательные UI/API tests; session/CSRF tests; audit login/denial. |
| ДКБ-02.02 | Технологические роли назначаются технологическим пользователям системы. | Реализуемо штатно/настройкой (4/4) | Портал + Keystone + корпоративный IAM | E02 | P1 | Использовать role service для service-to-service вызовов; отдельные service users/projects; запрет admin для сервисов без необходимости. | Полностью отказаться от сервисных учетных записей нельзя. | Ролевая матрица; policy/capability tests; отрицательные UI/API tests; session/CSRF tests; audit login/denial. |
| ДКБ-02.03 | Внутренние роли назначаются пользователям организации/дочерних компаний для доступа из внутреннего сегмента сети. | Реализуемо при интеграции/архитектуре (3/4) | Портал + Keystone + корпоративный IAM | E02 | P1 | Маппинг LDAP/AD/OIDC/SAML групп на Keystone; сетевые ACL/VPN/VLAN для внутреннего сегмента; Horizon/API доступ через внутренний VIP. | OpenStack не определяет корпоративную сетевую принадлежность без внешних сетевых controls. | Ролевая матрица; policy/capability tests; отрицательные UI/API tests; session/CSRF tests; audit login/denial. |
| ДКБ-03 | Любой доступ, включая доступ к данным и его актуализация, должен осуществляться на основании ролевых моделей. | Частично / внешние меры (2/4) | Портал + Keystone + корпоративный IAM | E02 | P2 | Запретить прямой доступ к DB/storage/API backend; всё пользовательское администрирование вести через Keystone/Horizon/API; host-level доступ через PAM/sudo/audit. | Доступ root/DBA/storage-admin потенциально вне OpenStack RBAC. | Ролевая матрица; policy/capability tests; отрицательные UI/API tests; session/CSRF tests; audit login/denial. |
| ДКБ-04 | Не должно быть совмещения ролей администратора ПВ с любыми другими ролями. | Частично / внешние меры (2/4) | Портал + Keystone + корпоративный IAM | E02 | P2 | Реализовать SoD в корпоративном IAM: запрет конфликтующих групп, отдельные персональные admin-аккаунты, регулярные проверки role assignment. | Без IAM-политики пользователь может получить несколько ролей. | Ролевая матрица; policy/capability tests; отрицательные UI/API tests; session/CSRF tests; audit login/denial. |
| ДКБ-05 | Запуск любых скриптов администраторами должен производиться только под персонифицированной учетной записью. | Частично / внешние меры (2/4) | Портал + Keystone + корпоративный IAM | E02 | P2 | CLI/OpenStackClient запускать с персональными federated/LDAP accounts; для root-команд — bastion, sudo, auditd, session recording; запрет shared admin. | Ansible/Kolla и root-доступ на узлах требуют отдельного процесса и журналирования. | Ролевая матрица; policy/capability tests; отрицательные UI/API tests; session/CSRF tests; audit login/denial. |
| ДКБ-06 | Доступ предоставляется только в рамках роли из централизованного сервиса управления доступом после аутентификации. | Реализуемо при интеграции/архитектуре (3/4) | Портал + Keystone + корпоративный IAM | E02 | P1 | Keystone federation с корпоративным IdP через SAML/OIDC или LDAP backend; роли назначать группам, не локальным пользователям. | Локальный bootstrap/admin и service users должны быть ограничены и исключены из human access. | Ролевая матрица; policy/capability tests; отрицательные UI/API tests; session/CSRF tests; audit login/denial. |
| ДКБ-07 | Использование локальных технологических учетных записей для задач пользователей и администраторов запрещено. | Частично / внешние меры (2/4) | Портал + Keystone + корпоративный IAM | E02 | P2 | Human access — только IdP/LDAP/federation. Service accounts Keystone и OS/container users оставить как технологические, но запретить интерактивное использование и журналировать. | Формально требование может потребовать исключений для service users и системных аккаунтов ОС. | Ролевая матрица; policy/capability tests; отрицательные UI/API tests; session/CSRF tests; audit login/denial. |
| ДКБ-12 | UI пользователя/администратора не должен отображать элементы, на работу с которыми у него нет прав. | Реализуемо штатно/настройкой (4/4) | Портал + Keystone + корпоративный IAM | E02 | P1 | Horizon policy files + policy checks; синхронизировать политики Horizon с policy.yaml сервисов; провести UI negative tests. | UI-скрытие не заменяет серверную проверку RBAC на API. | Ролевая матрица; policy/capability tests; отрицательные UI/API tests; session/CSRF tests; audit login/denial. |
| ДКБ-13 | Исключить доступ администратора к паролям и другим конфиденциальным данным пользователей. | Частично / внешние меры (2/4) | Портал + Keystone + корпоративный IAM | E02 | P2 | Пароли пользователей не должны храниться/выводиться в открытом виде; federation предпочтительнее LDAP bind. Секреты сервисов — в Vault/Barbican, доступ root ограничить. | Root/оператор на контроллере может получить конфиги/логи/дампы, если нет host hardening и secrets management. | Ролевая матрица; policy/capability tests; отрицательные UI/API tests; session/CSRF tests; audit login/denial. |
| ДКБ-15 | Функция выбора одной из политик аутентификации администратора в системе управления виртуальной инфраструктурой. | Реализуемо при интеграции/архитектуре (3/4) | Портал + Keystone + корпоративный IAM | E02 | P1 | Настроить Keystone auth methods: password/federated OIDC/SAML, LDAP, mTLS/OAuth2 для интеграций; админ-доступ через IdP policy/MFA. | Единого UI-переключателя 'политик аутентификации' в OpenStack обычно нет; выбор реализуется конфигурацией Keystone/IdP. | Ролевая матрица; policy/capability tests; отрицательные UI/API tests; session/CSRF tests; audit login/denial. |
| ДКБ-17 | Монопольный доступ к файловым ресурсам ВМ. | Частично / внешние меры (2/4) | Nova/libvirt + СХД + гостевая ОС | E12 | P3/внешний контур | Tenant isolation через projects/RBAC, libvirt+sVirt/SELinux, Ceph/RBD/Cinder ACL; запрет прямого доступа tenant/admin к backing files; шифрование volumes/guest data. | Host root/storage admin может читать backing storage без доп. мер; 'монопольность' зависит от СХД и шифрования. | Gap/waiver; внешний контроль и утвержденное доказательство владельца контура. |
| ДКБ-18 | Разграничение доступа к резервным копиям конфигурации менеджера виртуальных машин. | Частично / внешние меры (2/4) | Backup-система + IAM/PAM | E12 | P3/внешний контур | Backup OpenStack/Kolla конфигов, БД и inventory хранить в корпоративной backup-системе с отдельными ролями; шифровать; аудит доступа. | Без внешней backup-системы и RBAC на хранилище требование не закрывается. | Gap/waiver; внешний контроль и утвержденное доказательство владельца контура. |
| ДКБ-20 | Ограничение числа параллельных сеансов доступа. | Реализуемо штатно/настройкой (4/4) | Портал + Keystone + корпоративный IAM | E02 | P1 | Для Horizon использовать SIMULTANEOUS_SESSIONS='disconnect' или 'deny'. Для API — token lifetime, IdP session policy, OAuth/OIDC controls. | API-токены и CLI-сессии требуют отдельной политики в Keystone/IdP. | Ролевая матрица; policy/capability tests; отрицательные UI/API tests; session/CSRF tests; audit login/denial. |
| ДКБ-21 | Блокирование сеанса пользователя при неактивности по истечении 15 минут. | Реализуемо штатно/настройкой (4/4) | Портал + Keystone + корпоративный IAM | E02 | P1 | Horizon SESSION_TIMEOUT=900; согласовать Keystone token expiration и IdP idle timeout. | Консоли ВМ, CLI и external IdP могут иметь отдельные timeout settings. | Ролевая матрица; policy/capability tests; отрицательные UI/API tests; session/CSRF tests; audit login/denial. |
| ДКБ-22.02 | Для внешних интеграций: строгая взаимная аутентификация и авторизация сторон при сетевом взаимодействии через mTLS v1.2; исключить неаутентифицированные/неавторизованные соединения. | Частично / внешние меры (2/4) | Портал/Kolla + PKI/IdP + сеть | E08/E09 | P2 | Включить TLS external/internal/backend в Kolla-Ansible; использовать корпоративный CA; для внешних интеграций — API gateway/HAProxy/Apache client cert verification, Keystone OAuth2 mTLS, firewall allowlists. | Строгий mTLS 'для всех соединений' не включается одной настройкой и требует per-integration дизайна, сертификатной авторизации и тестов отказа. | TLS/mTLS matrix and scans; Vault contract/rotation runbook; SBOM/scan; image/SELinux/network evidence. |
| ДКБ-23.02 | Интеграция с корпоративным УЦ и использование сертификатов организации, включая выпуск по SCEP/NDES, для внешних интеграций. | Реализуемо при интеграции/архитектуре (3/4) | Портал/Kolla + PKI/IdP + сеть | E08/E09 | P2 | Использовать сертификаты корпоративного CA в Kolla TLS; доверенный CA раскатать в контейнеры; выпуск через корпоративные SCEP/NDES/PKI процессы вне OpenStack. | SCEP/NDES issuance не является штатной функцией OpenStack; это задача PKI-контура. | TLS/mTLS matrix and scans; Vault contract/rotation runbook; SBOM/scan; image/SELinux/network evidence. |
| ДКБ-24 | Доступ к UI должен быть реализован с использованием https c TLS не ниже 1.2. | Реализуемо штатно/настройкой (4/4) | Портал/Kolla + PKI/IdP + сеть | E08/E09 | P1 | Включить external TLS для Horizon/API VIP; профиль HAProxy modern/intermediate; запрет TLS <1.2 и слабых шифров. | Нужно проверить фактические cipher suites сканером. | TLS/mTLS matrix and scans; Vault contract/rotation runbook; SBOM/scan; image/SELinux/network evidence. |
| ДКБ-25 | Полноценное функционирование компонентов ПВ без использования NTLM. | Реализуемо штатно/настройкой (4/4) | Портал/Kolla + PKI/IdP + сеть | E08/E09 | P1 | OpenStack использует Keystone tokens, SAML/OIDC/LDAP, TLS; не требует NTLM. При AD-интеграции использовать LDAPS/Kerberos/OIDC/SAML, запретить NTLM на IdP. | Риск появляется только при внешней AD/Windows-интеграции. | TLS/mTLS matrix and scans; Vault contract/rotation runbook; SBOM/scan; image/SELinux/network evidence. |
| ДКБ-42 | Интерфейсы управления должны быть выделены в отдельную VLAN сеть. | Реализуемо при интеграции/архитектуре (3/4) | Kolla + Rocky + сетевая инфраструктура | E09 | P3/внешний контур | Проектировать отдельный management/API VLAN: api_interface, internal VIP, DB/RabbitMQ/SSH management; firewall east-west. | Требование закрывается архитектурой сети, а не только OpenStack-конфигом. | Kolla inventory/config; network/VIP/ACL evidence; container inspection; registry digest. |
| ДКБ-43 | Управляющие сервисы должны быть изолированы от хостовой сети. | Частично / внешние меры (2/4) | Kolla + Rocky + сетевая инфраструктура | E09 | P3/внешний контур | Изоляция management/control-plane трафика отдельными interfaces/VLAN/security groups/firewalls; контейнерные namespaces; запрет bind на публичные интерфейсы. | Полная изоляция от host network физически невозможна для части сервисов; нужна сегментация и host firewall. | Kolla inventory/config; network/VIP/ACL evidence; container inspection; registry digest. |
| ДКБ-44 | Для взаимодействия сервисов должны использоваться виртуальные сети на уровне виртуализации и контейнеризации, если применимо. | Реализуемо при интеграции/архитектуре (3/4) | Kolla + Rocky + сетевая инфраструктура | E09 | P3/внешний контур | Разнести internal API, tunnel/tenant, storage, external/provider, management сети; для контейнеров Kolla использовать заданные interfaces/VIPs и backend TLS. | Нужна физическая/VLAN/overlay-схема и проверка маршрутизации. | Kolla inventory/config; network/VIP/ACL evidence; container inspection; registry digest. |
| ДКБ-46 | Возможность передачи логов и событий безопасности во внешние системы. | Реализуемо штатно/настройкой (4/4) | Портал + OpenStack + SIEM + ОС/гипервизор | E07 | P1 | oslo.log syslog/json; keystonemiddleware audit notifications to log/messaging; Kolla logging pipeline/SIEM integration. | Нужна нормализация событий по требованиям SIEM. | Audit schema/mapping; redaction tests; SIEM delivery/heartbeat; access tests; samples success/failure. |
| ДКБ-47 | Передача событий аудита компонентов ПВ в централизованный сервис аудита по Syslog и/или брокеру сообщений с защищенным авторизованным соединением. | Реализуемо при интеграции/архитектуре (3/4) | Портал + OpenStack + SIEM + ОС/гипервизор | E07 | P2 | Включить CADF/audit middleware; направить notifications в RabbitMQ/Kafka/лог; настроить TLS/авторизацию broker/syslog-ng/rsyslog. | Защищенность/авторизация канала зависят от брокера/rsyslog и PKI. | Audit schema/mapping; redaction tests; SIEM delivery/heartbeat; access tests; samples success/failure. |
| ДКБ-48 | Запрет отключения передачи событий в централизованный сервис аудита либо фиксация отключения в журнале. | Частично / внешние меры (2/4) | Портал + OpenStack + SIEM + ОС/гипервизор | E07 | P3/внешний контур | IaC/Ansible enforcement, immutable configs, file integrity monitoring, auditd на изменение конфигов и systemd/container stop, мониторинг отсутствия потока логов. | Root на контроллере может отключить агент/логирование; нужна внешняя фиксация и SIEM heartbeat. | Audit schema/mapping; redaction tests; SIEM delivery/heartbeat; access tests; samples success/failure. |
| ДКБ-49 | Каждое событие аудита должно содержать минимальные атрибуты: дата/время, пользователь, действие, событие, результат, ресурс. | Реализуемо при интеграции/архитектуре (3/4) | Портал + OpenStack + SIEM + ОС/гипервизор | E07 | P1 | Использовать CADF notifications и audit middleware; настроить формат логов с request_id/user_identity; описать маппинг полей CADF к требованиям. | Не все обычные service logs являются CADF; для полного покрытия нужен event enrichment. | Audit schema/mapping; redaction tests; SIEM delivery/heartbeat; access tests; samples success/failure. |
| ДКБ-49.01 | Дата и время события с точностью до секунды. | Реализуемо штатно/настройкой (4/4) | Портал + OpenStack + SIEM + ОС/гипервизор | E07 | P1 | CADF timestamp + синхронизация времени NTP/PTP; в логах использовать ISO timestamp. | Требуется централизованная синхронизация времени и проверка timezone. | Audit schema/mapping; redaction tests; SIEM delivery/heartbeat; access tests; samples success/failure. |
| ДКБ-49.02 | Идентификатор пользователя. | Реализуемо штатно/настройкой (4/4) | Портал + OpenStack + SIEM + ОС/гипервизор | E07 | P1 | CADF initiator.id/name; oslo.log user_identity/request context. | Для service-to-service нужно различать human user и service role. | Audit schema/mapping; redaction tests; SIEM delivery/heartbeat; access tests; samples success/failure. |
| ДКБ-49.03 | Идентификатор действия, приведшего к событию. | Реализуемо штатно/настройкой (4/4) | Портал + OpenStack + SIEM + ОС/гипервизор | E07 | P1 | CADF action/event_type и request_id; маппинг к справочнику действий. | Нужен справочник событий для аудиторов. | Audit schema/mapping; redaction tests; SIEM delivery/heartbeat; access tests; samples success/failure. |
| ДКБ-49.04 | Наименование события. | Реализуемо штатно/настройкой (4/4) | Портал + OpenStack + SIEM + ОС/гипервизор | E07 | P1 | event_type/name в notification/audit log; нормализация в SIEM. | Для разных сервисов названия событий отличаются. | Audit schema/mapping; redaction tests; SIEM delivery/heartbeat; access tests; samples success/failure. |
| ДКБ-49.05 | Результат события: успешный/неуспешный. | Реализуемо штатно/настройкой (4/4) | Портал + OpenStack + SIEM + ОС/гипервизор | E07 | P1 | CADF outcome и HTTP status/result; собирать failure events. | Проверить отрицательные сценарии по всем API. | Audit schema/mapping; redaction tests; SIEM delivery/heartbeat; access tests; samples success/failure. |
| ДКБ-49.08 | Идентификатор/адрес/название данных, системного компонента или ресурса, на которые повлияло событие. | Реализуемо при интеграции/архитектуре (3/4) | Портал + OpenStack + SIEM + ОС/гипервизор | E07 | P1 | CADF target/resource + service-specific IDs: project_id, instance_id, volume_id, image_id, network_id; enrichment в SIEM. | Иногда требуется дополнение логов данными из API/catalog. | Audit schema/mapping; redaction tests; SIEM delivery/heartbeat; access tests; samples success/failure. |
| ДКБ-50 | Список событий аудита должен включать действия пользователей, администраторов, изменения настроек, недоступность компонентов, операции с ВМ/сетями/образами и компонентами виртуализации. | Частично / внешние меры (2/4) | Портал + OpenStack + SIEM + ОС/гипервизор | E07 | P3/внешний контур | CADF/audit middleware для API; Keystone notifications для IAM; Nova/Neutron/Glance/Cinder notifications; host auditd/systemd/libvirt logs; monitoring events в SIEM. | Наиболее рискованный блок: потребуется комплексная схема аудита beyond OpenStack. | Audit schema/mapping; redaction tests; SIEM delivery/heartbeat; access tests; samples success/failure. |
| ДКБ-50.01 | Создание/изменение/удаление пользователей и их прав доступа администратором. | Реализуемо штатно/настройкой (4/4) | Портал + OpenStack + SIEM + ОС/гипервизор | E07 | P3/внешний контур | Keystone CADF/basic notifications на users/groups/role assignments. | Если users в external IdP, события должны приходить из IdP/IAM. | Audit schema/mapping; redaction tests; SIEM delivery/heartbeat; access tests; samples success/failure. |
| ДКБ-50.02 | Аутентификация и авторизация пользователей ВМ и пользователей системы: успешная/неуспешная. | Частично / внешние меры (2/4) | Портал + OpenStack + SIEM + ОС/гипервизор | E07 | P3/внешний контур | Keystone auth events для пользователей OpenStack; VM guest auth — агент/логирование внутри ВМ или централизованный AD/Linux audit. | Требуется уточнить, входят ли пользователи ВМ в периметр ПВ. | Audit schema/mapping; redaction tests; SIEM delivery/heartbeat; access tests; samples success/failure. |
| ДКБ-50.03 | Изменение параметров и системных настроек системы. | Частично / внешние меры (2/4) | Портал + OpenStack + SIEM + ОС/гипервизор | E07 | P3/внешний контур | API-configurable settings фиксировать через OpenStack audit; файловые конфиги Kolla/Ansible/systemd — через git/IaC/auditd/FIM. | Root/admin на узле может менять конфиги вне API. | Audit schema/mapping; redaction tests; SIEM delivery/heartbeat; access tests; samples success/failure. |
| ДКБ-50.04 | Список действий администраторов системы. | Частично / внешние меры (2/4) | Портал + OpenStack + SIEM + ОС/гипервизор | E07 | P3/внешний контур | Admin API actions через CADF; host-level actions через sudo logs, auditd, session recording, Ansible logs. | Нужно исключить shared accounts. | Audit schema/mapping; redaction tests; SIEM delivery/heartbeat; access tests; samples success/failure. |
| ДКБ-50.06 | Доступ к компонентам сервиса/системы. | Частично / внешние меры (2/4) | Портал + OpenStack + SIEM + ОС/гипервизор | E07 | P3/внешний контур | API access logs + service auth logs + SSH/PAM/auditd + network device logs. | Нужна корреляция request_id/source IP/user. | Audit schema/mapping; redaction tests; SIEM delivery/heartbeat; access tests; samples success/failure. |
| ДКБ-50.07 | Случаи недоступности компонентов сервисов/систем, включая централизованный сервис аудита. | Частично / внешние меры (2/4) | Портал + OpenStack + SIEM + ОС/гипервизор | E07 | P3/внешний контур | Prometheus/Zabbix/Icinga/Monasca + SIEM alerts; heartbeat лог-агентов; RabbitMQ/DB/API health checks. | Если audit service down, само событие должно уйти альтернативным каналом. | Audit schema/mapping; redaction tests; SIEM delivery/heartbeat; access tests; samples success/failure. |
| ДКБ-50.08 | Использование и изменение механизмов идентификации и аутентификации. | Реализуемо при интеграции/архитектуре (3/4) | Портал + OpenStack + SIEM + ОС/гипервизор | E07 | P3/внешний контур | Keystone events для federation mappings, users, groups, application credentials; IdP audit для MFA/policies. | Полнота зависит от IdP/IAM. | Audit schema/mapping; redaction tests; SIEM delivery/heartbeat; access tests; samples success/failure. |
| ДКБ-50.10 | Создание и удаление объектов системного уровня. | Реализуемо при интеграции/архитектуре (3/4) | Портал + OpenStack + SIEM + ОС/гипервизор | E07 | P3/внешний контур | Nova/Neutron/Glance/Cinder/Keystone notifications; audit middleware на API endpoints. | Нужна проверка по каждому сервису и API extension. | Audit schema/mapping; redaction tests; SIEM delivery/heartbeat; access tests; samples success/failure. |
| ДКБ-50.11 | Изменение параметров настроек виртуальных сетевых сегментов средствами гипервизора. | Реализуемо при интеграции/архитектуре (3/4) | Портал + OpenStack + SIEM + ОС/гипервизор | E07 | P3/внешний контур | Neutron API audit + OVS/OVN/libvirt/network logs; запрет прямых изменений на compute/network nodes. | Изменения через ovs-vsctl/ip link вне Neutron не видны как OpenStack audit event. | Audit schema/mapping; redaction tests; SIEM delivery/heartbeat; access tests; samples success/failure. |
| ДКБ-50.12 | Создание/удаление, запуск/остановка ВМ. | Реализуемо при интеграции/архитектуре (3/4) | Портал + OpenStack + SIEM + ОС/гипервизор | E07 | P3/внешний контур | Nova API/audit notifications; correlate instance_id, project_id, user_id. | Прямые virsh/libvirt действия на гипервизоре требуют host audit. | Audit schema/mapping; redaction tests; SIEM delivery/heartbeat; access tests; samples success/failure. |
| ДКБ-50.13 | Создание, изменение, копирование, удаление базовых образов ВМ. | Реализуемо при интеграции/архитектуре (3/4) | Портал + OpenStack + SIEM + ОС/гипервизор | E07 | P3/внешний контур | Glance API audit/notifications; storage backend audit; ограничить image import/copy/delete ролями. | Нужны политики Glance и контроль доступа к хранилищу образов. | Audit schema/mapping; redaction tests; SIEM delivery/heartbeat; access tests; samples success/failure. |
| ДКБ-50.14 | Копирование текущих образов ВМ. | Частично / внешние меры (2/4) | Портал + OpenStack + SIEM + ОС/гипервизор | E07 | P3/внешний контур | Snapshot/copy через Nova/Cinder/Glance audit; прямое копирование файлов/томов на backend запретить и логировать отдельно. | Высокий риск обхода через storage admin/root. | Audit schema/mapping; redaction tests; SIEM delivery/heartbeat; access tests; samples success/failure. |
| ДКБ-50.15 | Изменение прав логического доступа к серверным компонентам виртуализации. | Частично / внешние меры (2/4) | Портал + OpenStack + SIEM + ОС/гипервизор | E07 | P3/внешний контур | Keystone role assignments/policy changes audit + OS/PAM/sudo audit для host/service access. | Нужно формально разделить OpenStack logical access и host logical access. | Audit schema/mapping; redaction tests; SIEM delivery/heartbeat; access tests; samples success/failure. |
| ДКБ-50.16 | Изменение параметров настроек серверных компонентов виртуализации. | Частично / внешние меры (2/4) | Портал + OpenStack + SIEM + ОС/гипервизор | E07 | P3/внешний контур | Контроль изменений Kolla/Ansible inventory, service configs, libvirt/qemu configs через GitOps/FIM/auditd + SIEM. | Требует внешней системы управления конфигурациями. | Audit schema/mapping; redaction tests; SIEM delivery/heartbeat; access tests; samples success/failure. |
| ДКБ-50.17 | Запуск/остановка ПО серверных компонентов виртуализации. | Частично / внешние меры (2/4) | Портал + OpenStack + SIEM + ОС/гипервизор | E07 | P3/внешний контур | systemd/docker/podman/auditd logs, Ansible logs, SIEM; запрет прямого restart без change request. | OpenStack API audit не фиксирует все systemctl/docker operations. | Audit schema/mapping; redaction tests; SIEM delivery/heartbeat; access tests; samples success/failure. |
| ДКБ-50.19 | Копирование текущих образов ВМ. | Частично / внешние меры (2/4) | Портал + OpenStack + SIEM + ОС/гипервизор | E07 | P3/внешний контур | То же, что ДКБ-50.14: контролируемые snapshot/copy операции через API; storage-level copy через отдельный audit/backup control. | Нужен контроль на уровне СХД. | Audit schema/mapping; redaction tests; SIEM delivery/heartbeat; access tests; samples success/failure. |
| ДКБ-51 | Не допускается передача в событиях аудита паролей пользователей, бизнес-данных и персональных данных. | Реализуемо при интеграции/архитектуре (3/4) | Портал + OpenStack + SIEM + ОС/гипервизор | E07 | P1 | Отключить debug в production; log masking/sanitization; CADF payload без секретов; SIEM фильтры; запрет логирования request bodies с секретами. | Ошибочные debug/exception logs могут раскрыть данные — нужны тесты на утечки. | Audit schema/mapping; redaction tests; SIEM delivery/heartbeat; access tests; samples success/failure. |
| ДКБ-52 | При ошибках в событиях аудита должен фиксироваться полный текст сообщения об ошибке, включая системные сообщения. | Частично / внешние меры (2/4) | Портал + OpenStack + SIEM + ОС/гипервизор | E07 | P1 | Собирать service logs с exception/error text; в audit-события добавлять error status/message where available; SIEM link на request_id. | Баланс с ДКБ-51: полный текст ошибки не должен раскрывать секреты/ПДн. | Audit schema/mapping; redaction tests; SIEM delivery/heartbeat; access tests; samples success/failure. |
| ДКБ-53 | Доступ к данным аудита предоставляется только уполномоченным пользователям и только через прикладной уровень. | Частично / внешние меры (2/4) | Портал + OpenStack + SIEM + ОС/гипервизор | E07 | P1 | Хранить аудит в централизованной системе с RBAC; запрет прямого доступа к log files/broker/index; аудит чтения логов. | Локальные файлы логов на контроллерах доступны root без дополнительных мер. | Audit schema/mapping; redaction tests; SIEM delivery/heartbeat; access tests; samples success/failure. |
| ДКБ-55 | Интеграция с системой управления секретами организации на базе Hashicorp Vault. | Частично / внешние меры (2/4) | Vault (SecMan) + Kolla/Ansible + портал | E08/E09 | P2 | Barbican Vault secret store для cloud/user secrets; отдельная интеграция Kolla/Ansible/passwords с Vault; PKI и rotation workflows. | Barbican Vault не решает хранение всех service passwords Kolla и имеет ограничения multitenancy. | TLS/mTLS matrix and scans; Vault contract/rotation runbook; SBOM/scan; image/SELinux/network evidence. |
| ДКБ-56 | Все секреты ТУЗ, интеграционные и сервисные секреты должны храниться в SecMan, то есть Vault в этой среде, и ротироваться по требованиям безопасности. | Пробел / конфликт с требованием (1/4) | Vault (SecMan) + Kolla/Ansible + портал | E08/E09 | P2 | Нужны внешние playbooks: генерация/получение секретов из Vault, ротация passwords/certs/tokens, rolling restart, контроль старых секретов. Barbican использовать только как OpenStack key manager. | Сильный gap: требуется доработка deployment pipeline и регламент ротации. | TLS/mTLS matrix and scans; Vault contract/rotation runbook; SBOM/scan; image/SELinux/network evidence. |
| ДКБ-60 | Поддержка группировки ВМ, объединение ВМ разных конфигураций в одну логическую группу. | Реализуемо штатно/настройкой (4/4) | Портал + Nova | E05/E06 | P2 | Portal-owned logical groups: project-scoped VM groups, explicit membership, bounded dynamic preview and inventory `group_id` filters. E06 operation submit expands explicit host groups into concrete target snapshots before acceptance. No automatic placement/Nova aggregate side effect. | P0 не реализует shared groups, tag/imported membership и frontend create/add controls; host groups require admin/system-like policy; snapshot evidence does not prove production governance. | `backend/tests/groups/test_group_api.py`, `backend/tests/groups/test_group_repository.py`, `backend/tests/groups/test_group_rules.py`, `backend/tests/inventory/test_inventory_api.py`, `backend/tests/operations/test_operation_api.py`, `frontend/src/App.test.tsx`, ExecPlans E05/E06. |
| ДКБ-62 | Производитель должен выпускать плановые и внеплановые обновления ПВ для устранения уязвимостей и соответствия требованиям КБ. | Частично / внешние меры (2/4) | Поставщик/эксплуатация + release pipeline | E12 | P3/внешний контур | Для upstream OpenStack — использовать stable/2025.1 releases/security patches; для закупочного требования нужен vendor/SLA, advisory process, регламент emergency updates. | Upstream community не равна коммерческому SLA производителя. | Gap/waiver; внешний контроль и утвержденное доказательство владельца контура. |
| ДКБ-65 | Разработка и включение профилей SELinux или AppArmor в зависимости от ОС гипервизора. | Частично / внешние меры (2/4) | Rocky SELinux/sVirt + Kolla | E08/E09 | P3/внешний контур | Использовать SELinux+sVirt для KVM/libvirt; включить дистрибутивные OpenStack SELinux policies; для AppArmor/Kolla — разработать/подключить профили контейнеров и QEMU. | Требование 'разработка и включение' не закрывается чистым upstream OpenStack; зависит от ОС/дистрибутива. | TLS/mTLS matrix and scans; Vault contract/rotation runbook; SBOM/scan; image/SELinux/network evidence. |
| ДКБ-66 | Высокая доступность Active-Active или Active-Passive по всем ключевым компонентам АС; автоматическое переключение на резерв. | Реализуемо при интеграции/архитектуре (3/4) | Kolla/OpenStack HA + СХД/сеть | E10 | P3/внешний контур | Kolla-Ansible HA: HAProxy+Keepalived VIP, несколько controllers, MariaDB/RabbitMQ quorum, redundant API/backends; проверить каждый сервис и stateful-компонент. | Некоторые компоненты требуют отдельной HA-схемы и тестов failover; storage HA вне OpenStack. | Load, failover, recovery and consistency reports. |
| ДКБ-69 | Образы контейнеров должны содержать минимально необходимый набор компонентов; не допускаются компиляторы, интерпретаторы и командные оболочки. | Пробел / конфликт с требованием (1/4) | Kolla Build + registry + supply chain | E08/E09 | P3/внешний контур | Требуется собственная hardened image baseline: удаление лишних пакетов, vulnerability scanning, SBOM, allowlist; при этом многие OpenStack services — Python-приложения, интерпретатор необходим. | Запрет интерпретаторов конфликтует с Python-сервисами OpenStack; нужен формальный waiver/исключение или глубокая переработка образов. | TLS/mTLS matrix and scans; Vault contract/rotation runbook; SBOM/scan; image/SELinux/network evidence. |
| ДКБ-70 | Образы контейнеров должны находиться в централизованном репозитории организации. | Реализуемо штатно/настройкой (4/4) | Kolla Build + registry + supply chain | E08/E09 | P2 | Собирать/сканировать Kolla images и push в корпоративный registry; настроить Kolla-Ansible на pull из него. | Нужно управление доверенными базовыми образами и подписью/сканированием. | TLS/mTLS matrix and scans; Vault contract/rotation runbook; SBOM/scan; image/SELinux/network evidence. |
| ДКБ-72 | Не допускается использование файловой системы гипервизоров виртуальными машинами. | Частично / внешние меры (2/4) | Nova/Cinder/Ceph/СХД | E12 | P3/внешний контур | Запретить local file-backed ephemeral disks; использовать boot-from-volume/Cinder/Ceph RBD/remote storage; ограничить instances_path; проверить live migration/snapshot paths. | В vanilla Nova VM disks могут размещаться в /var/lib/nova/instances; полное выполнение требует архитектуры storage. | Gap/waiver; внешний контроль и утвержденное доказательство владельца контура. |
| ДКБ-76 | Система контейнеризации в ПВ должна соответствовать требованиям, если применимо. | Нужна детализация (0/4) | Kolla Build + registry + supply chain | E08/E09 | P3/внешний контур | В файле указано только заглавное требование без под-требований. Для оценки нужны критерии: runtime, registry, image hardening, network policies, secrets, audit, privileged mode и т.д. | Запросить полный блок ДКБ-76.x. | TLS/mTLS matrix and scans; Vault contract/rotation runbook; SBOM/scan; image/SELinux/network evidence. |
| ДКБ-77 | Использование любых API и интерфейсов продукта должно быть описано; неиспользуемые API и интерфейсы должны быть заблокированы. | Реализуемо при интеграции/архитектуре (3/4) | Портал + OpenStack/Kolla + firewall | E08/E09 | P1 | Документировать включенные OpenStack services/endpoints/API versions; отключить ненужные сервисы/endpoints в Kolla; firewall; policy deny для неиспользуемых операций. | Нужен конкретный перечень включенных компонентов и техническое блокирование портов/API; E07 docs describe portal-level audit/operation endpoints and disabled mutation paths but do not implement firewall/policy blocking. | E07 `docs/generated/api-register.md`, `docs/generated/integration-register.md`, `docs/generated/risk-register.md`, `docs/generated/audit-source-map.md`, `docs/generated/e07-fluentd-opensearch-lab.md`, E06 `docs/generated/e06-mistral-smoke.md`, disabled descriptors; TLS/mTLS matrix and scans; Vault contract/rotation runbook; SBOM/scan; image/SELinux/network evidence. |
| ДКБ-80 | Размещение интерфейсов управления компонентами ПВ в отдельной сетевой зоне. | Реализуемо при интеграции/архитектуре (3/4) | Kolla + Rocky + сетевая инфраструктура | E09 | P3/внешний контур | Аналог ДКБ-42: отдельная management zone/VLAN, internal VIP, firewall, bastion-only admin access. | Нужно подтверждение сетевой схемой и ACL. | Kolla inventory/config; network/VIP/ACL evidence; container inspection; registry digest. |
| ДКБ-82 | Наличие технической и эксплуатационной документации на продукт. | Реализуемо штатно/настройкой (4/4) | Команда продукта + эксплуатация | E11 | P1 | Использовать официальную документацию OpenStack 2025.1/Kolla-Ansible/Nova/Keystone/Neutron/Barbican; дополнить эксплуатационными регламентами конкретного deployment. | Внутренние runbooks, схемы и регламенты эксплуатации нужно разработать для конкретной инсталляции. | E04 scale report and generated registers; техническая/эксплуатационная документация; приемочный протокол. |

## Непринимаемые упрощения

- Закрывать ДКБ-12 только скрытием кнопки без backend 403.
- Закрывать ДКБ-50 только журналом действий портала.
- Закрывать ДКБ-55/56 наличием Barbican без lifecycle всех Kolla/service secrets.
- Закрывать ДКБ-65 наличием SELinux package без enforcing и тестов.
- Закрывать ДКБ-69 удалением compiler, игнорируя наличие необходимого Python interpreter/shell.
- Закрывать ДКБ-72 настройкой UI без проверки storage paths Nova/Cinder/Ceph.
- Закрывать ДКБ-77 одной документацией без firewall/policy/disabled endpoints.
