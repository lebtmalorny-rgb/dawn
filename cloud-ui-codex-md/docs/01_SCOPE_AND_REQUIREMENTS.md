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

### FR-09. Интеграции

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

### FR-10. Аудит

Портал регистрирует вход, выход, session termination, просмотр защищенных данных, изменение ролей и групп, запуск/отмену/повтор workflow, административные изменения каталога и результат OpenStack-вызовов. Аудит доступен только уполномоченным ролям.

### FR-11. Частичные ошибки

Списковые API могут вернуть частичный результат и структурированный список недоступных источников. UI явно показывает неполноту и время последней успешной синхронизации.

### FR-12. Документированное расширение

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
- redaction;
- delivery to centralized audit test endpoint.

### Should для P2

- event-driven refresh;
- saved views;
- bulk actions;
- SSE;
- Watcher/Masakari linked views.

### Production-only

- mTLS всех утвержденных интеграций;
- corporate PKI/Vault(SecMan)/SIEM;
- Kolla HA;
- image signing/SBOM policy;
- SELinux validation;
- full failover and recovery tests;
- formal DKB waivers and external evidence.
