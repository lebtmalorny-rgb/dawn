# Карта комплекта документов

Этот файл помогает человеку и Codex выбрать минимальный набор контекста для текущей работы. Не загружайте все документы в одну задачу: корневой `AGENTS.md` и файл этапа уже указывают, что необходимо прочитать.

## Точка входа

| Файл | Назначение |
|---|---|
| [README.md](README.md) | Цель решения, границы, порядок этапов и состав комплекта. |
| [AGENTS.md](AGENTS.md) | Постоянные обязательные правила для любой сессии Codex. |
| [PLANS.md](PLANS.md) | Правила создания и ведения живого ExecPlan. |
| [CODEX_START.md](CODEX_START.md) | Готовые запросы для реализации, review и security review. |
| [tasks/README.md](tasks/README.md) | Граф этапов, handoff между сессиями и уровни результата. |

## Архитектура и требования

| Файл | Назначение |
|---|---|
| [docs/00_CONTEXT.md](docs/00_CONTEXT.md) | Исходная ситуация, цели, границы ответственности и уровни P0–P3. |
| [docs/01_SCOPE_AND_REQUIREMENTS.md](docs/01_SCOPE_AND_REQUIREMENTS.md) | Функциональные и нефункциональные требования, use cases и non-goals. |
| [docs/02_TARGET_ARCHITECTURE.md](docs/02_TARGET_ARCHITECTURE.md) | Целевая BFF/read-model/event/workflow архитектура и контейнерная схема. |
| [docs/03_TECH_STACK.md](docs/03_TECH_STACK.md) | Рекомендуемый стек frontend/backend/data/CI и правила выбора зависимостей. |
| [docs/04_DOMAIN_AND_DATA.md](docs/04_DOMAIN_AND_DATA.md) | Доменные сущности, read model, группы, операции, consistency и миграции. |
| [docs/05_API_AND_INTEGRATIONS.md](docs/05_API_AND_INTEGRATIONS.md) | Контракты API и адаптеры Keystone/Nova/Placement/Mistral/Watcher/Masakari. |
| [docs/06_AUTH_RBAC_SESSIONS.md](docs/06_AUTH_RBAC_SESSIONS.md) | Аутентификация, server-side sessions, CSRF, portal RBAC и capabilities. |
| [docs/07_WORKFLOWS.md](docs/07_WORKFLOWS.md) | Каталог разрешенных операций, state machine, idempotency и Mistral. |
| [docs/08_AUDIT_OBSERVABILITY.md](docs/08_AUDIT_OBSERVABILITY.md) | Прикладной аудит, outbox, redaction, SIEM и observability. |
| [docs/09_PERFORMANCE_HA.md](docs/09_PERFORMANCE_HA.md) | Масштаб, SLO, нагрузка, HA, failover и reconciliation. |
| [docs/12_DEPLOY_ROCKY_KOLLA.md](docs/12_DEPLOY_ROCKY_KOLLA.md) | Rocky Linux, два image, Kolla Build/Kolla-Ansible и 12 контейнеров. |
| [docs/13_TEST_STRATEGY.md](docs/13_TEST_STRATEGY.md) | Пирамида тестов, mocks/contracts, безопасность, нагрузка и evidence. |
| [docs/14_DEFINITION_OF_DONE.md](docs/14_DEFINITION_OF_DONE.md) | DoD для изменения, этапа, PoC и production pilot. |
| [docs/15_DECISIONS_AND_OPEN_QUESTIONS.md](docs/15_DECISIONS_AND_OPEN_QUESTIONS.md) | Зафиксированные решения, ADR backlog и неизвестные с владельцами. |
| [docs/16_SOURCES.md](docs/16_SOURCES.md) | Происхождение требований и официальные технические источники. |

## ДКБ и безопасность

| Файл | Назначение |
|---|---|
| [docs/10_SECURITY_DKB.md](docs/10_SECURITY_DKB.md) | Security gates, threat model и девять высокорисковых требований ДКБ. |
| [docs/11_DKB_TRACEABILITY.md](docs/11_DKB_TRACEABILITY.md) | Полная трассировка 73 требований: контур, этап, gate, риск и evidence. |
| [security/AGENTS.md](security/AGENTS.md) | Дополнительные правила Codex для security-sensitive изменений. |
| [templates/SECURITY_REVIEW_TEMPLATE.md](templates/SECURITY_REVIEW_TEMPLATE.md) | Шаблон threat-driven security review. |
| [templates/DKB_EVIDENCE_TEMPLATE.md](templates/DKB_EVIDENCE_TEMPLATE.md) | Шаблон проверяемого доказательства по требованию ДКБ. |

## Этапы реализации

| Этап | Файл | Проверяемый результат |
|---|---|---|
| E00 | [tasks/E00_DISCOVERY.md](tasks/E00_DISCOVERY.md) | Проверенная среда, scope, scale profile, ADR и карта ДКБ. |
| E01 | [tasks/E01_BOOTSTRAP.md](tasks/E01_BOOTSTRAP.md) | Monorepo, два image, compose, health checks и единые команды. |
| E02 | [tasks/E02_SECURITY_FOUNDATION.md](tasks/E02_SECURITY_FOUNDATION.md) | Аутентификация, серверные сессии, RBAC и capabilities. |
| E03 | [tasks/E03_OPENSTACK_ADAPTERS.md](tasks/E03_OPENSTACK_ADAPTERS.md) | Типизированные OpenStack adapters, mocks и contract tests. |
| E04 | [tasks/E04_INVENTORY_UI.md](tasks/E04_INVENTORY_UI.md) | Read model и масштабируемые таблицы ВМ/гипервизоров. |
| E05 | [tasks/E05_RESOURCE_GROUPS.md](tasks/E05_RESOURCE_GROUPS.md) | Явные/динамические группы ВМ и хостов с ACL. |
| E06 | [tasks/E06_WORKFLOWS.md](tasks/E06_WORKFLOWS.md) | Allowlisted workflow, Mistral, operation tracking и idempotency. |
| E07 | [tasks/E07_AUDIT.md](tasks/E07_AUDIT.md) | Аудит, redaction, SIEM delivery и контроль потери потока. |
| E08 | [tasks/E08_HARDENING.md](tasks/E08_HARDENING.md) | TLS/mTLS, secrets lifecycle, image/SELinux/supply-chain hardening. |
| E09 | [tasks/E09_KOLLA_DEPLOY.md](tasks/E09_KOLLA_DEPLOY.md) | Kolla deployment: два image, 12 постоянных контейнеров и migration job. |
| E10 | [tasks/E10_SCALE_HA.md](tasks/E10_SCALE_HA.md) | Нагрузка, HA, failover, rolling update и consistency evidence. |
| E11 | [tasks/E11_ACCEPTANCE.md](tasks/E11_ACCEPTANCE.md) | Приемочные сценарии, runbooks и воспроизводимая демонстрация. |
| E12 | [tasks/E12_PRODUCTION_GAPS.md](tasks/E12_PRODUCTION_GAPS.md) | Evidence audit, внешние controls, waivers и решение о pilot. |

## Локальные инструкции Codex

| Файл | Область действия |
|---|---|
| [backend/AGENTS.md](backend/AGENTS.md) | Backend, БД, внешние адаптеры, workers и migrations. |
| [frontend/AGENTS.md](frontend/AGENTS.md) | React/TypeScript, accessibility, tables и безопасное отображение capabilities. |
| [deploy/AGENTS.md](deploy/AGENTS.md) | Images, Kolla Build, Kolla-Ansible, secrets и rollback. |
| [security/AGENTS.md](security/AGENTS.md) | Auth, sessions, workflow, audit, secret и hardening changes. |

## Шаблоны

| Файл | Назначение |
|---|---|
| [templates/TASK_TEMPLATE.md](templates/TASK_TEMPLATE.md) | Создание нового этапа или единицы работы в согласованном формате. |
| [templates/EXECPLAN_TEMPLATE.md](templates/EXECPLAN_TEMPLATE.md) | Стартовый шаблон живого плана выполнения. |
| [templates/ADR_TEMPLATE.md](templates/ADR_TEMPLATE.md) | Архитектурное решение с альтернативами и последствиями. |
| [templates/SECURITY_REVIEW_TEMPLATE.md](templates/SECURITY_REVIEW_TEMPLATE.md) | Формализованный security review. |
| [templates/RELEASE_CHECKLIST.md](templates/RELEASE_CHECKLIST.md) | Проверка release/upgrade/rollback. |
| [templates/DKB_EVIDENCE_TEMPLATE.md](templates/DKB_EVIDENCE_TEMPLATE.md) | Evidence с environment, owner, command/result, ограничениями и сроком действия. |

## Артефакты E00

| Файл | Назначение |
|---|---|
| [docs/execplans/E00-discovery-baseline.md](docs/execplans/E00-discovery-baseline.md) | Живой план и фактический результат discovery baseline. |
| [docs/generated/current-state.md](docs/generated/current-state.md) | Локальное состояние workspace, tools, target unknown и команды безопасной инвентаризации. |
| [docs/generated/poc-scope.md](docs/generated/poc-scope.md) | P0/P1/P2/P3 cutline, главные сценарии и proposed первый workflow. |
| [docs/generated/scale-profile.md](docs/generated/scale-profile.md) | Provisional scale profile и production значения, которые нужно получить у владельцев. |
| [docs/generated/integration-register.md](docs/generated/integration-register.md) | Реестр внешних интеграций, owners и текущий статус. |
| [docs/generated/api-register.md](docs/generated/api-register.md) | Черновой реестр portal/external API для ДКБ-77. |
| [docs/generated/network-flow-matrix.md](docs/generated/network-flow-matrix.md) | Planned network flows и явно запрещенные соединения. |
| [docs/generated/tls-matrix.md](docs/generated/tls-matrix.md) | Черновая TLS/mTLS matrix для E08/E09. |
| [docs/generated/secret-inventory.md](docs/generated/secret-inventory.md) | Классы секретов без значений, proposed store и lifecycle gaps. |
| [docs/generated/dkb-implementation-plan.md](docs/generated/dkb-implementation-plan.md) | План evidence по всем 73 требованиям ДКБ. |
| [docs/adr/](docs/adr/) | ADR-001..ADR-010 по обязательным решениям E00. |

## Минимальный контекст на сессию

Для E00: `AGENTS.md`, `PLANS.md`, `tasks/E00_DISCOVERY.md` и перечисленные там документы.

Для E01–E12: `AGENTS.md`, `PLANS.md`, завершенный ExecPlan предыдущего этапа, файл текущего этапа и только его раздел `Прочитать`. Локальный `AGENTS.md` будет применяться автоматически, когда Codex работает в соответствующем каталоге.
