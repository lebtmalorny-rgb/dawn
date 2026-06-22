# Безопасность и требования ДКБ

## Принцип доказуемости

Код, конфигурация, тест и внешний контроль различаются. Для каждого требования ДКБ должно быть понятно:

- какой контур отвечает;
- что реализует портал;
- что реализует OpenStack/Kolla;
- что требуется от IAM/PKI/SIEM/Vault(SecMan)/PAM/СХД;
- каким артефактом доказано выполнение;
- какое ограничение или исключение остается.

Mock, комментарий или скрытая UI-кнопка не являются доказательством.

## Обязательные security gates

### До интегрированного read-only PoC

- HTTPS не ниже TLS 1.2;
- реальная или эквивалентная тестовая federation identity;
- server-side session;
- idle timeout 15 минут;
- simultaneous session policy;
- backend RBAC;
- отрицательные UI/API tests;
- token absent from browser/log;
- audit login/access/denial;
- documented APIs;
- test project with least privilege.

### До mutating PoC

- workflow allowlist;
- JSON Schema input;
- idempotency;
- target scope checks;
- operation audit;
- secret redaction;
- SIEM test delivery;
- safe retry/cancel semantics;
- no arbitrary scripts/templates;
- security review.

E06 P0 implements the first mutating-PoC foundation through `maintenance-host-precheck`: server-side
allowlist, bounded JSON Schema subset, CSRF/idempotency, target snapshot, operation audit, safe
Mistral retry lookup and disabled arbitrary workflow names. The default evidence uses a strict mock;
the optional all-in-one Mistral smoke is read-only workflow lookup and does not prove production
mutating workflow safety. SIEM delivery, production IAM/PAM/SoD, Vault-backed service identities and
formal security review remain required before production pilot.

E07 adds the portal audit foundation needed for mutating-PoC evidence: normalized audit schema,
central sanitizer, durable outbox, local test sink, Fluentd HTTP payload contract, retry/dead-letter,
heartbeat, audit read/export separation and audited audit access. This is local/contract evidence.
Production SIEM credentials, mTLS/auth, retention, OpenStack CADF/notification collection and
host-level FIM/auditd remain external controls before pilot.

### До production pilot

- corporate PKI and mTLS matrix;
- Vault (SecMan) integration and rotation runbook;
- management network/VLAN and firewall evidence;
- Kolla HA;
- registry, scan, SBOM, signing policy;
- SELinux validation;
- external audit source integration;
- PAM/auditd/FIM;
- backup/storage controls;
- failover/load reports;
- formal DKB gap/waiver approval.

## Высокие риски из исходной матрицы

| Код | Риск | Решение/позиция |
|---|---|---|
| ДКБ-07 | Полный запрет локальных технологических УЗ конфликтует с service users OpenStack | Human access только через IdP; service accounts остаются non-interactive, least privilege и auditable. Требуется формальное разграничение. |
| ДКБ-22.02 | Строгий mTLS для всех интеграций не включается одной настройкой | Создать per-integration matrix: endpoint, client/server identity, CA, authorization, renewal и failure tests. |
| ДКБ-48 | Root может отключить передачу аудита | Внешний FIM/auditd, immutable/IaC config, SIEM heartbeat и alert отсутствия потока. Портал сам root не блокирует. |
| ДКБ-50 | Полный перечень аудита выходит за OpenStack API | Объединить CADF, notifications, host/container/libvirt/network/storage/IdP/monitoring events в SIEM. |
| ДКБ-55 | Barbican/Vault не покрывает все secrets Kolla | Разделить OpenStack key manager и deployment secrets; интеграция Kolla/Ansible с корпоративным Vault (SecMan) выполняется отдельно. |
| ДКБ-56 | Все secrets и rotation отсутствуют из коробки | Нужен внешний lifecycle: issue, distribute, rolling rotation, revoke, verify and evidence. |
| ДКБ-65 | SELinux/AppArmor зависит от ОС и образов | Rocky: SELinux enforcing, sVirt/libvirt и tested container labels/profiles. Не заявлять закрытие без host evidence. |
| ДКБ-69 | Запрет интерпретаторов/shell конфликтует с Python OpenStack/portal backend | Минимизировать runtime, удалить compiler/package manager, non-root, scan/SBOM; получить формальное исключение для необходимого interpreter. |
| ДКБ-72 | Vanilla Nova допускает local instance files | Требуется storage architecture boot-from-volume/Cinder/Ceph RBD и проверка всех paths. Портал не закрывает это требование. |

## Threat model

### Активы

- user identity/session;
- OpenStack token;
- workflow permission;
- group membership;
- operation input;
- audit integrity;
- read model integrity;
- deployment secrets;
- registry images;
- availability control plane.

### Границы доверия

- browser ↔ HAProxy;
- HAProxy ↔ frontend/API;
- API ↔ IdP/Keystone/OpenStack;
- API/worker ↔ MariaDB/RabbitMQ;
- worker ↔ Mistral;
- audit worker ↔ SIEM;
- deployment ↔ Vault/registry;
- container ↔ Rocky host.

### Основные угрозы и controls

| Угроза | Controls |
|---|---|
| Кража token через XSS | token не в browser, CSP, escaping, dependency scan |
| CSRF | SameSite + CSRF token + origin checks |
| IDOR | server-side scope/target authorization |
| Privilege escalation | portal capability + OpenStack policy + negative tests |
| Arbitrary workflow/code execution | allowlist, versioned schema, no free-form code |
| Duplicate destructive action | idempotency, external correlation, reconciliation |
| SSRF | trusted endpoint config, URL allowlist, no user endpoint |
| Secret leakage | redaction, no debug, canary tests, Vault references |
| Audit tampering/loss | outbox, protected external sink, heartbeat, FIM |
| Event poisoning | dedicated credentials/queues, schema validation, idempotency |
| Real-time stream data leakage | server-side session auth, scope/capability filtering, field redaction, resumable cursors tied to policy revision |
| Unsafe automatic optimization/recovery | automatic Watcher apply disabled by default, Masakari recovery via authoritative notification/workflow path, approval gates, risk level, bounded target scope, rollback/abort policy, full audit |
| HA recovery conflicts | Masakari/Nova state reconciliation, operator approval for evacuation/recovery, conflict markers, no bypass of Nova policy |
| SQL injection | ORM/bound parameters, filter allowlist |
| Supply-chain compromise | lockfiles, SBOM, scan, registry/signing |
| Container breakout | non-root, drop caps, SELinux, read-only FS, no socket |
| Stale data causes unsafe action | freshness/precondition checks and targeted refresh |
| Shared admin credential | user context/delegation, service identity separation |
| Cursor tampering | signed operation/inventory cursors and safe `400 cursor_tampered` response |

## Secrets

Классы secrets:

- human/OpenStack session tokens;
- service application credentials;
- MariaDB/RabbitMQ passwords;
- TLS private keys;
- session encryption/signing keys;
- operation/inventory cursor signing keys;
- SIEM/Vault credentials;
- Mistral/OpenStack integration identities.

Для каждого класса E08 фиксирует owner, store, delivery, rotation, revoke, audit и emergency procedure. `.env` допустим только для локального P0 с dummy values и не коммитится.

## TLS/mTLS matrix

В `docs/generated/tls-matrix.md` должны быть строки:

- browser → external VIP;
- HAProxy → frontend/API;
- API/worker → Keystone/Nova/etc.;
- portal → MariaDB;
- portal → RabbitMQ;
- portal → Mistral/Watcher/Masakari;
- portal → SIEM;
- deployment → Vault;
- image pull → registry.

Для каждой строки: minimum TLS, mTLS yes/no, CA, certificate identity, hostname verification, authorization, rotation и negative test.

## Image hardening

- trusted base image;
- pinned digest;
- multi-stage;
- no build tools in runtime;
- minimal packages;
- non-root;
- read-only FS;
- capabilities dropped;
- health command without sensitive output;
- SBOM;
- vulnerability policy;
- image signature;
- registry retention;
- no secrets in layers/history.

Отсутствие shell/interpreter фиксируется отдельно по каждому image. Для backend ожидается исключение.

## Security evidence

Артефакты не должны содержать secrets. Минимум:

- role matrix;
- policy/negative test report;
- session tests;
- TLS scan;
- mTLS failure test;
- redaction test;
- audit delivery test;
- SBOM and vulnerability report;
- image configuration inspection;
- SELinux status/denial test;
- Kolla network/ACL evidence;
- failover report;
- DKB traceability update;
- approved waivers/gaps.
