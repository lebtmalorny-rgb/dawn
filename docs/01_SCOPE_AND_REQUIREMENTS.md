# Объем продукта и требования

## Функциональные требования

### FR-01. Inventory виртуальных машин

Портал предоставляет список и карточку ВМ с серверной пагинацией, фильтрацией и сортировкой. Минимальные поля: UUID, имя, project, status, power state, task state, host, hypervisor, availability zone, flavor, vCPU, RAM, image или boot volume, IP, created/updated time и источник актуальности данных.

### FR-02. Inventory гипервизоров

Портал предоставляет список и карточку гипервизоров: имя, service state, status, availability zone, aggregate, vCPU/RAM/disk capacity and usage, running VMs, disabled reason, maintenance state и связанные инциденты Masakari/Watcher.

### FR-03. Связная навигация

Из ВМ можно перейти к host, project, flavor, image, volume, сети, группе и операциям. Из host — к ВМ, aggregate, availability zone, Watcher/Masakari событиям.

### FR-04. Поиск и сохраненные представления

Поддерживаются точные и частичные фильтры, наборы фильтров, стабильная сортировка и сохраненные пользовательские представления. Фильтры транслируются в backend query; клиент не фильтрует полный набор данных.

### FR-05. Логические группы ресурсов

Пользователь с разрешением создает группы типов `vm`, `host` или `mixed`. Членство бывает:

- явным по UUID;
- динамическим по безопасному декларативному правилу;
- импортированным из tags, metadata, host aggregates или availability zones.

Группа не меняет placement автоматически. Любое изменение инфраструктуры выполняется отдельным workflow.

### FR-06. Прикладные роли и capabilities

Портал поддерживает собственные роли и permissions для страниц, групп и custom actions. Они сужают права пользователя. OpenStack policy остается обязательной второй проверкой.

### FR-07. Каталог workflow

Администратор публикует версионированное определение операции с названием, описанием, JSON Schema входа, требуемыми capabilities, target types, ссылкой на Mistral workflow и правилами отмены/повтора.

### FR-08. Запуск операции

Мутирующий запрос валидируется, авторизуется, дедуплицируется по idempotency key и возвращает `operation_id`. UI показывает состояние, этапы, время, инициатора, targets и безопасное описание ошибки.

### FR-09. First-class модуль Mistral и операций

Mistral не скрывается как техническая деталь отдельной кнопки. Портал предоставляет полноценный раздел операций:

- каталог опубликованных workflow definitions, версий, статусов публикации и risk level;
- формы запуска по JSON Schema, preview targets/preconditions/impact и approval gates;
- live tasks, operation progress, retries, cancel/abort state и child attempts;
- историю execution, correlation ID, external execution ID и связанные audit events;
- состояние Mistral API/engine/executor/event-engine как зависимость health dashboard;
- явное различие между reversible cancel, best-effort abort и необратимым partial effect.

### FR-10. First-class модуль Watcher

Watcher является самостоятельным модулем оптимизации и capacity governance, а не второстепенной linked page. UI и API должны покрывать:

- goals, strategies, audit templates, audits и continuous audits;
- action plans, actions, recommendations, statuses, history and result details;
- execution workflow через allowlisted operation catalog, включая approval, dry-run/precheck, progress, rollback/abort where applicable и post-action verification;
- риск автоматического применения рекомендаций: automatic apply по умолчанию запрещен, требует отдельной capability, policy, approval mode, bounded scope, audit evidence и rollback/abort semantics;
- связь с telemetry datasource: Ceilometer, Gnocchi, Prometheus и Aetos рассматриваются как внешние источники метрик с отдельными adapters/contracts, freshness, coverage и gap status; первый планируемый Prometheus path — `openstack-exporter` для OpenStack API metrics и `node_exporter` для host metrics;
- отображение confidence/impact, затронутых VM/hosts/aggregates/AZ, conflicting recommendations и stale telemetry warning.

### FR-11. First-class модуль Masakari

Masakari является самостоятельным HA/recovery модулем. UI и API должны покрывать:

- host failure recovery, instance HA, failover segments, segment hosts, notifications and recovery methods;
- evacuation workflows, operator approval gates, recovery progress and recovery timeline;
- hostmonitor, processmonitor and instancemonitor events, включая источник, время, confidence и correlation с Nova/compute service state;
- network-health-driven host failure recovery через штатный `masakari-hostmonitor` `monitoring_driver=consul` and `matrix.yaml`, если этот режим подтвержден в target deployment;
- явное предупреждение, что `processmonitor` в Kolla/container deployment считается R&D/diagnostic until lab proof, потому что штатная документация Masakari monitors предупреждает о рисках такого режима;
- визуализацию состояния HA по сегментам, host, instance, hypervisor, compute service and AZ;
- конфликтующие состояния: disabled compute service, host maintenance, ongoing migration/evacuation, stale notification, duplicate notification, incomplete monitor coverage;
- связь с Nova evacuate/live migration: портал показывает связь, preconditions and outcome, но mutating execution идет только через allowlisted operation/workflow and OpenStack policy;
- запрет на самостоятельную эвакуацию из портала по Consul Events или Prometheus metrics: authoritative recovery trigger должен приходить через Masakari notification/recovery workflow либо отдельный ADR with failover evidence.

### FR-12. Real-time UX и рабочие события

Портал должен поддерживать live view для:

- live tasks, operation progress, events stream, notifications, audit log tail and health status;
- статусов инстансов, гипервизоров, compute services, Neutron agents, Cinder services;
- volume operations, image tasks, orchestration stacks, load balancers, DNS zones/records, secrets metadata, bare metal nodes and background operations where modules are enabled;
- partial/stale/unknown states, включая явный источник данных, freshness и recommended operator action.

Real-time UX не должен превращаться в uncontrolled fan-out к OpenStack. Event stream ускоряет отображение, а read model/reconciliation остается источником корректности.

Consul Events API, Prometheus alerts and exporter metrics may be displayed as diagnostic/corroborating signals, but they are not durable authoritative evacuation transport for portal-initiated recovery.

### FR-13. Интеграции

Минимальный набор адаптеров:

- Keystone;
- Nova;
- Placement;
- Mistral;
- Watcher;
- Masakari.

Расширяемый набор:

- Heat;
- Neutron;
- Cinder;
- Glance;
- корпоративный SIEM;
- корпоративный Vault (SecMan).

Для модулей, не входящих в ранний PoC, contract/mocks и explicit disabled state обязательны раньше, чем UI начнет показывать production claim.

### FR-14. Аудит

Портал регистрирует вход, выход, session termination, просмотр защищенных данных, изменение ролей и групп, запуск/отмену/повтор workflow, административные изменения каталога и результат OpenStack-вызовов. Аудит доступен только уполномоченным ролям.

### FR-15. Частичные ошибки

Списковые API могут вернуть частичный результат и структурированный список недоступных источников. UI явно показывает неполноту и время последней успешной синхронизации.

### FR-16. Высокопроизводительная графика и визуализация

Портал должен проектироваться как рабочий инструмент для больших инсталляций:

- performance graphs, capacity dashboards, health dashboards and alert/problem summaries;
- topology view для сетей и dependency map между VM, ports, networks, subnets, routers, floating IP, security groups, volumes, images, hypervisors, aggregates and availability zones;
- inventory tree в стиле VMware: cloud/region/project/AZ/aggregate/hypervisor/resource group with capability-aware nodes;
- UX-модель таблиц для сотен тысяч строк: server-side pagination, keyset cursors, virtualization only for visible rows, lazy loading, controlled infinite scroll only where it does not hide stable position, fast filters, saved views and global search;
- metric aggregation, drill-down, cross-filtering, dependency graph layout, data-density controls and export limits;
- поведение при неполных правах: скрытые недоступные actions, redacted object names where needed, aggregate counts marked as partial, no inference of protected resource existence.

### FR-17. Документированное расширение

Новый resource module должен добавляться через:

- backend adapter;
- read model mapper при необходимости;
- OpenAPI endpoints;
- frontend route/module;
- capability definitions;
- audit mappings;
- contract, negative authorization и UI tests;
- запись в реестре API по ДКБ-77.

## Нефункциональные требования

### NFR-01. Безопасность

Все решения следуют `docs/10_SECURITY_DKB.md`. UI не является точкой авторизации. Секреты не попадают в браузер, Git, логи и audit payload.

### NFR-02. Масштабирование

API, frontend, worker и event consumer масштабируются горизонтально. Состояние находится в MariaDB/RabbitMQ или внешних системах. Локальный диск контейнера не является источником истины.

### NFR-03. Производительность

Численные бюджеты утверждаются в E00. До утверждения используется provisional профиль:

- 10 000 ВМ;
- 1 000 гипервизоров;
- 50 одновременных UI-пользователей;
- 1 000 000 строк прикладного audit test dataset;
- page size по умолчанию 50, максимум 200;
- p95 list API из read model не более 2 секунд в тестовом профиле;
- mutating API возвращает `operation_id` не более чем за 1 секунду без ожидания завершения workflow.

Эти числа не являются production SLA и должны быть заменены реальными.

### NFR-04. Актуальность

Каждая запись read model имеет `observed_at`, `source_updated_at` и `sync_status`. Целевая задержка утверждается отдельно. Событийная доставка не отменяет reconciliation.

Real-time delivery использует server-side correlation and aggregation. UI получает bounded event stream или adaptive polling, а не подписку на raw OpenStack notifications.

### NFR-05. Надежность

Повторная доставка события не меняет результат. Потеря события исправляется reconciliation. Повторный mutating request с тем же idempotency key не запускает вторую операцию.

### NFR-06. Совместимость

Интеграции фиксируют OpenStack API microversion, поддерживают graceful degradation и contract tests. Обновление OpenStack не должно требовать одновременного обновления frontend и backend.

### NFR-07. Наблюдаемость

Каждый HTTP request и background job имеют `request_id`/`correlation_id`. Метрики, структурированные логи и health endpoints различают liveness и readiness.

### NFR-08. Развертывание

Собираются два собственных образа. Конфигурация и secrets не baked into image. Rolling update не выполняет destructive migration.

### NFR-09. Поддерживаемость Codex

Каждый этап имеет ограниченный scope, явные тесты и документы. Код организован по доменным модулям и адаптерам, чтобы Codex мог изменять одну область без массового контекста.

## Приоритеты MoSCoW

### Must для P1

- server-side inventory;
- real backend authorization;
- session timeout и session limit;
- no token in browser;
- request correlation;
- audit собственных действий;
- HTTPS;
- negative authorization tests;
- API documentation.

### Must для P2

- resource groups;
- workflow allowlist;
- idempotency;
- operation tracking;
- Mistral integration;
- first-class Mistral operation center for approved workflows;
- first-class Watcher read/status/recommendation module with safe approved operation path;
- first-class Masakari read/status/recovery module with safe approved operation path;
- redaction;
- delivery to centralized audit test endpoint.

### Should для P2

- event-driven refresh;
- saved views;
- bulk actions;
- SSE;
- topology/dependency graph read model for enabled read-only resources;
- high-density inventory tree and dashboard UX beyond initial instance/hypervisor pages.

### Production-only

- mTLS всех утвержденных интеграций;
- corporate PKI/Vault(SecMan)/SIEM;
- Kolla HA;
- automatic Watcher recommendation apply beyond test/precheck scope;
- full Masakari monitor/HA cluster coverage and failover evidence;
- WebSocket infrastructure if bidirectional UX is justified by ADR and load tests;
- production telemetry datasource coverage for Ceilometer/Gnocchi/Prometheus/Aetos;
- image signing/SBOM policy;
- SELinux validation;
- full failover and recovery tests;
- formal DKB waivers and external evidence.
