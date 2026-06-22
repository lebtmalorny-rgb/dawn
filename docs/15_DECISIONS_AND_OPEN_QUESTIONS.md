# Решения, допущения и открытые вопросы

Этот файл — исходный backlog решений. E00 должен преобразовать принятые решения в ADR и заменить допущения фактами. Codex не должен придумывать ответы для внешних систем.

Актуальный рабочий реестр рисков ведется в `docs/generated/risk-register.md`. Этот файл остается backlog решений и вопросов; риск считается сниженным только после evidence в соответствующем ExecPlan.

## Зафиксированные решения

| ID | Решение |
|---|---|
| D-001 | Собственный портал сосуществует с Horizon; не требуется полная parity в PoC. |
| D-002 | BFF; browser не вызывает OpenStack API напрямую. |
| D-003 | Два custom image: frontend и backend. |
| D-004 | Backend image запускает API, worker, events и migration. |
| D-005 | MariaDB — собственные данные/read model/sessions; RabbitMQ — jobs/events. |
| D-006 | Mistral — длительные workflow. |
| D-007 | etcd не используется для business state без ADR. |
| D-008 | OpenStack service policies — окончательная авторизация. |
| D-009 | Inventory list читается из read model; events + reconciliation. |
| D-010 | Workflow только allowlisted и versioned. |
| D-011 | Production audit authoritative в SIEM; портал хранит operational projection. |
| D-012 | P0/P1/P2/P3 имеют разные security gates; P0 не считается соответствием ДКБ. |
| D-013 | Первый telemetry datasource path — Prometheus exporter stack: `openstack-exporter` для OpenStack API metrics и `node_exporter` для host metrics. Ceilometer/Gnocchi/Aetos остаются pluggable integrations. |
| D-014 | Consul используется через штатный Masakari hostmonitor `monitoring_driver=consul` and `matrix.yaml`; портал не принимает самостоятельное решение об эвакуации по Consul Events. |
| D-015 | `processmonitor` для Kolla/container deployment остается R&D/diagnostic до lab proof; first recovery slice должен опираться на hostmonitor/Consul и Masakari notification state. |
| D-016 | Первый E06 workflow — `maintenance-host-precheck@1.0.0`, dry-run only, with P0 mock as mandatory evidence and optional read-only all-in-one Mistral smoke. |
| D-017 | E06 cancel route remains fail-closed until workflow-specific Mistral cancel semantics and partial-effect evidence exist. |
| D-018 | E07 uses local/contract audit delivery in code and records Fluentd/OpenSearch all-in-one deployment as manual evidence/runbook. Production SIEM remains authoritative and external. |

## Research evidence 2026-06-21

- Masakari hostmonitor supports Consul driver and matrix-based `recovery` action: <https://docs.openstack.org/masakari-monitors/latest/hostmonitor.html>
- Masakari recovery is processed through Masakari API/engine and Nova correlation: <https://docs.openstack.org/masakari/latest/user/architecture.html>
- Masakari processmonitor warns about container/pod deployments: <https://docs.openstack.org/masakari-monitors/latest/processmonitor.html>
- Consul Events API is gossip-based and not a durable ordered recovery transport: <https://developer.hashicorp.com/consul/api-docs/event>
- Prometheus exporters selected for first path: <https://github.com/openstack-exporter/openstack-exporter> and <https://github.com/prometheus/node_exporter>

## Решения E00, которые обязательны до кода интеграции

### ADR-001. Authentication/federation flow

Нужно указать IdP, протокол, Keystone federation, callback/logout, MFA, token lifetime, session storage encryption и test flow.

### ADR-002. OpenStack client strategy

openstacksdk в bounded threadpool или async REST для конкретных API. Нужны compatibility и load evidence.

### ADR-003. Notification/reconciliation strategy

Какие notifications включены, transport/exchange, permissions, payload version, fallback polling и freshness target.

### ADR-004. Workflow publication model

GitOps или admin API, approval, versioning, rollback и связь с Mistral definition.

### ADR-005. Session concurrency policy

`deny` или `disconnect_oldest`, absolute lifetime, idle timeout, admin revoke.

### ADR-006. Package/runtime versions

Python, Node, package managers, Kolla base image, Rocky version и lock policy.

### ADR-007. Scheduler/leader

Mistral, Celery beat, DB lease или внешний scheduler. Не использовать несколько активных schedulers без coordination.

### ADR-008. Audit sink

SIEM protocol/API, delivery guarantee, retention, search integration, field mapping и heartbeat.

E07 decision: local test sink plus Fluentd HTTP payload contract are implemented for portal evidence.
OpenSearch deployment on all-in-one is documented in `docs/generated/e07-fluentd-opensearch-lab.md`
and is not automated by portal code. ADR-008 still needs the production SIEM protocol, auth/mTLS,
retention, search integration and owner acceptance.

### ADR-009. Vault (SecMan)

Secret classes, API, auth, injection, cache, rotation and break-glass.

### ADR-010. Dynamic group rule language

Allowlisted fields/operators, versioning, complexity limit, explain and security.

## Открытые вопросы продукта

- Какие функции Horizon должны остаться доступными как fallback?
- Какие действия требуются в первом mutating workflow?
- Какие Watcher goals/strategies/templates должны быть first-class в первом P2 slice?
- Разрешается ли automatic Watcher apply вообще, и если да, какие approval gates, max scope and rollback/abort policy обязательны?
- Какие Masakari recovery workflows доступны оператору: только read/approval или также controlled evacuate/live migration через approved workflow?
- Какой CSRF refresh/session bootstrap endpoint нужен, чтобы restored browser sessions could submit operations after reload?
- Должен ли operation detail/cancel быть actor-scoped like operation list or available to system/audit roles through separate capability?
- Какой уровень детализации нужен для HA timeline: host, process, instance, Nova task, operator approval and external alert?
- Нужен ли Heat в P2 или после pilot?
- Какие модули из load balancers, DNS, secrets metadata and bare metal должны войти в первый real-time UX scope?
- Требуются ли cross-project/system-scope views?
- Кто может создавать dynamic groups?
- Нужны ли shared groups между подразделениями?
- Требуется ли approval «четыре глаза» для high-risk operation?
- Какие поля audit доступны обычному operator и security auditor?
- Нужен ли экспорт CSV и какие ограничения ПДн?
- Какие locale/timezone поддерживаются?

## Открытые вопросы масштаба

- Число ВМ/host/region/project.
- Частота изменений.
- Максимальный bulk target count.
- Concurrent users/API requests.
- Audit retention/query range.
- Допустимая stale age.
- RPO/RTO.
- Network latency к OpenStack endpoints.
- Rate limits и DB connection limits.
- Live event subscriber count and burst rate.
- Topology graph node/edge limits and layout latency budget.
- Telemetry metric cardinality, retention and downsampling policy.

## Открытые вопросы инфраструктуры

- Rocky/Kolla exact supported baseline.
- Docker/Podman runtime.
- Registry product and signing.
- Existing HAProxy/TLS topology.
- Internal TLS status.
- RabbitMQ notification transport.
- SSE support through target HAProxy/proxy chain and need for WebSocket ADR.
- Prometheus datasource endpoint, retention/downsampling, label cardinality and tenant/scope filtering; Ceilometer/Gnocchi/Aetos ownership remains later decision.
- Masakari hostmonitor Consul deployment outside all-in-one: Kolla config override path, Consul ACL/TLS/token ownership, `matrix.yaml` owner, and lab evidence.
- Whether `processmonitor` is excluded from production, kept diagnostic-only, or accepted after Kolla/container lab proof.
- MariaDB backup/failover.
- Corporate CA/SCEP/NDES flow.
- SIEM/Vault endpoints.
- Production SIEM protocol for audit delivery: syslog, Fluentd HTTP, Kafka/RabbitMQ or vendor API.
- Required mTLS/client identity and authorization model for audit worker -> SIEM/Fluentd.
- Audit retention/query range and export format limits for security auditors.
- SELinux current mode/policies.
- Storage architecture по ДКБ-72.
- Management VLAN/ACL.

## Формат закрытия вопроса

При закрытии:

1. создать ADR либо запись decision log;
2. указать owner/date;
3. приложить источник/evidence;
4. обновить затронутые docs/tasks;
5. обновить DKB traceability;
6. удалить допущение только после проверки.
