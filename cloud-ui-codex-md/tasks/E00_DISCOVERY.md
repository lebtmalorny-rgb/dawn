# E00 — Discovery, baseline и архитектурные решения

## Пользовательский результат

Команда получает проверенный документ о фактической среде, согласованные границы PoC, scale profile, архитектурные решения и карту внешних зависимостей. После этапа Codex может писать код без скрытых предположений.

## Входные критерии

- Доступен этот набор Markdown-файлов.
- Известно, что целевая платформа — OpenStack Epoxy 2025.1, Kolla Build/Kolla-Ansible и Rocky Linux.
- Production credentials Codex не предоставляются.

## Прочитать

- `docs/00_CONTEXT.md`
- `docs/01_SCOPE_AND_REQUIREMENTS.md`
- `docs/02_TARGET_ARCHITECTURE.md`
- `docs/10_SECURITY_DKB.md`
- `docs/11_DKB_TRACEABILITY.md`
- `docs/15_DECISIONS_AND_OPEN_QUESTIONS.md`

## Ограничения

- Не писать прикладной frontend/backend.
- Не подключаться к production.
- Не заменять неизвестные факты «разумными» значениями без пометки.
- Не заявлять закрытие ДКБ.
- Все собираемые примеры должны быть sanitized.

## Единицы работы

### E00.1. Осмотр репозитория и среды

Создать `docs/generated/current-state.md`:

- существующие файлы/репозитории;
- версии доступных tools;
- Rocky/Kolla baseline;
- доступные test endpoints без secrets;
- существующие CI/registry;
- включенные OpenStack services;
- текущая схема TLS/network;
- доступность MariaDB/RabbitMQ/Mistral/Watcher/Masakari;
- какие данные подтверждены, а какие неизвестны.

Если среда недоступна, описать точные команды безопасной инвентаризации для оператора и оставить result pending.

### E00.2. Scope и use cases

Создать `docs/generated/poc-scope.md`:

- P0/P1/P2 cutline;
- три главных пользовательских сценария;
- первый mutating workflow;
- non-goals;
- owners;
- критерии демонстрации.

### E00.3. Scale profile

Создать `docs/generated/scale-profile.md` с production и provisional значениями:

- resources;
- users;
- change/event rate;
- latency/freshness;
- RPO/RTO;
- test dataset.

Не оставлять число без источника или пометки assumption.

### E00.4. ADR

Создать минимум ADR для:

- authentication/federation;
- OpenStack client async strategy;
- notification/reconciliation;
- workflow publication;
- session policy;
- runtime/package versions;
- scheduler/leader;
- audit sink;
- Vault (SecMan);
- dynamic group rules.

Необязательно принимать все решения: ADR может иметь статус `proposed` и перечислять blocker.

### E00.5. Карта интеграций

Создать:

- `docs/generated/integration-register.md`;
- `docs/generated/api-register.md`;
- `docs/generated/network-flow-matrix.md`;
- `docs/generated/tls-matrix.md`;
- `docs/generated/secret-inventory.md`.

Значения, содержащие credential, заменяются reference/owner.

### E00.6. План ДКБ

Создать `docs/generated/dkb-implementation-plan.md`:

- требования P1/P2/P3;
- owner контур;
- evidence;
- gaps/waivers;
- review authority.

Использовать все 73 строки из traceability.

## Acceptance

- Все неизвестные перечислены, а не замаскированы.
- Есть конкретный PoC cutline.
- Есть scale profile.
- Каждое архитектурное решение имеет ADR либо явно назначенный blocker.
- Реестры API/network/TLS/secrets созданы.
- Для всех 73 ДКБ есть owner и этап.
- В Git нет secrets.
- Выполнен review документов на противоречия.

## Проверки

- проверить внутренние ссылки Markdown;
- проверить отсутствие строк, похожих на token/password/private key;
- проверить, что каждое `unknown` имеет owner или способ получения;
- проверить, что ни один документ не утверждает production compliance.

## Затронутые ДКБ

Все требования — на уровне классификации и планирования, без изменения статуса соответствия.

## Итоговый запрос Codex

> Выполни E00 как исследовательский и документирующий этап. Создай ExecPlan. Не создавай приложение. Факты отделяй от допущений, а внешние требования — от ответственности портала. Заверши этап только после полной карты 73 требований ДКБ.
