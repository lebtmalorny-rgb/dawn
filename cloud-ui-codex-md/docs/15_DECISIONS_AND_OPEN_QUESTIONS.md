# Решения, допущения и открытые вопросы

Этот файл — исходный backlog решений. E00 должен преобразовать принятые решения в ADR и заменить допущения фактами. Codex не должен придумывать ответы для внешних систем.

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

### ADR-009. Vault (SecMan)

Secret classes, API, auth, injection, cache, rotation and break-glass.

### ADR-010. Dynamic group rule language

Allowlisted fields/operators, versioning, complexity limit, explain and security.

## Открытые вопросы продукта

- Какие функции Horizon должны остаться доступными как fallback?
- Какие действия требуются в первом mutating workflow?
- Нужен ли Heat в P2 или после pilot?
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

## Открытые вопросы инфраструктуры

- Rocky/Kolla exact supported baseline.
- Docker/Podman runtime.
- Registry product and signing.
- Existing HAProxy/TLS topology.
- Internal TLS status.
- RabbitMQ notification transport.
- MariaDB backup/failover.
- Corporate CA/SCEP/NDES flow.
- SIEM/Vault endpoints.
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
