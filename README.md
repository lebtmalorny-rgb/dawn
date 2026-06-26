# Cloud UI для OpenStack Epoxy 2025.1

Этот каталог — набор исходных Markdown-документов для последовательной разработки PoC и дальнейшего production-ready решения с помощью Codex.

Целевая система — расширяемый административный портал для OpenStack Epoxy 2025.1, развернутого через Kolla Build и Kolla-Ansible на Rocky Linux. Портал должен быстро отображать большие объемы данных по виртуальным машинам, гипервизорам и сервисам, поддерживать собственные группы ресурсов и прикладные роли, запускать разрешенные многошаговые операции через Mistral, предоставлять Mistral/Watcher/Masakari как first-class модули интерфейса, поддерживать real-time UX, предоставлять аудит и безопасно расширяться под новые API.

## Зафиксированное направление

Используется схема из двух собственных образов:

1. `cloud-ui-frontend` — статический React/TypeScript SPA, обслуживаемый web-сервером.
2. `cloud-ui-backend` — единый Python-образ, запускаемый в режимах `api`, `worker`, `events` и `migrate`.

В варианте с тремя control/UI-узлами ожидается 12 постоянно работающих контейнеров: по три frontend, API, worker и event consumer. Миграция БД выполняется отдельным одноразовым контейнером. Существующие MariaDB и RabbitMQ используются через отдельные БД, учетные записи, vhost, exchange и очереди. Mistral остается движком длительных пользовательских workflow. etcd не используется как бизнес-хранилище или хранилище сессий.

## Текущий статус

На 2026-06-26 активный handoff находится внутри E09.8 `Deployment smoke/evidence`.
Repository-side evidence для E09.1-E09.8 реализовано и проверено, включая Kolla image build
contract, Ansible role contracts, DB/RabbitMQ all-in-one lab provisioning, migration job contract,
process topology, HAProxy/TLS route contract, lifecycle/rollback contract и fail-closed evidence
runner.

Полная приемка E09 еще не заявлена. Остаются внешние live gates: подтвержденные image digests из
test registry, approved test inventory с marker `cloud_ui_test_stand`, 12 live containers на трех
test nodes, one-shot migration execution, HAProxy/TLS smoke, DB/RabbitMQ least-privilege checks,
container hardening/SELinux inspection и executed rollback evidence. Текущий источник handoff:
`docs/execplans/E09-deployment-smoke-evidence.md` и
`docs/generated/e09-deployment-smoke-evidence.md`.

## Как работать с комплектом

Начните с `CODEX_START.md`, затем передайте Codex только один файл этапа из `tasks/`. Для сложного этапа Codex должен создать и вести ExecPlan по правилам `PLANS.md`.

Рекомендуемый цикл:

1. Создать отдельную ветку или worktree для этапа.
2. Запустить Codex из корня репозитория с ограниченной записью только в workspace.
3. Включить Plan mode и поручить прочитать `AGENTS.md`, `PLANS.md` и выбранный файл `tasks/E*.md`.
4. Реализовать только текущий этап и его явно перечисленные единицы работы.
5. Запустить lint, typecheck, тесты, сборку и проверки безопасности, указанные в этапе.
6. Выполнить отдельный review изменений.
7. Принять этап только после сохранения проверяемых доказательств и обновления трассировки ДКБ.

Codex лучше работает с задачами, где явно заданы цель, контекст, ограничения и проверяемый результат. Поэтому каждый файл этапа имеет одинаковую структуру и может использоваться как готовое задание.

## Порядок этапов

| Этап | Результат |
|---|---|
| E00 | Проверенный baseline среды, границы, решения и открытые вопросы |
| E01 | Рабочий monorepo, два образа, локальный compose и health checks |
| E02 | Аутентификация, серверные сессии, RBAC и capability-модель |
| E03 | Типизированные адаптеры Keystone/Nova/Placement и mock-контракты |
| E04 | Read model, синхронизация, таблицы ВМ и гипервизоров |
| E05 | Пользовательские группы ВМ/хостов и управление доступом к ним |
| E06 | Каталог операций и запуск Mistral/Watcher/Masakari workflow |
| E07 | Прикладной аудит, редактирование секретов и интеграция с SIEM |
| E08 | TLS/mTLS, Vault (SecMan), image hardening, SELinux и supply chain |
| E09 | Kolla Build и Kolla-Ansible интеграция |
| E10 | Производительность, HA, отказоустойчивость и reconciliation |
| E11 | Приемка PoC, документация и воспроизводимая демонстрация |
| E12 | Production gap analysis, внешние меры и формальные исключения ДКБ |

Функциональный PoC завершается после E06. Интегрированный безопасный PoC завершается после E07. Production pilot нельзя объявлять готовым до E08–E12.

## Состав документов

- `AGENTS.md` — постоянные правила для Codex.
- `PLANS.md` — формат живого плана выполнения сложных этапов.
- `CODEX_START.md` — команды и готовые запросы для запуска работы.
- `FILE_INDEX.md` — кликабельная карта всех документов и минимального контекста для сессии.
- `docs/` — требования, архитектура, безопасность, данные, API, тесты и развертывание.
- `tasks/` — этапы, разложенные до проверяемых единиц работы.
- `templates/` — шаблоны задания, ADR, security review и release checklist.
- `backend/AGENTS.md`, `frontend/AGENTS.md`, `deploy/AGENTS.md`, `security/AGENTS.md` — локальные правила, автоматически уточняющие корневой `AGENTS.md`.

## Важное ограничение по ДКБ

Этот портал не может самостоятельно закрыть весь перечень ДКБ. Часть требований относится к корпоративному IAM, PKI, SIEM, Vault (SecMan), PAM, auditd, backup-системе, СХД, сетевой инфраструктуре и эксплуатационным регламентам. В `docs/11_DKB_TRACEABILITY.md` для каждого из 73 требований указан ответственный контур, этап и необходимое доказательство. Запрещено заявлять соответствие требованию, если реализована только UI-часть или mock-интеграция.
