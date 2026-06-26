# Запуск работы в Codex

## Базовый режим

Работайте из корня Git-репозитория. Для локальной разработки используйте профиль разрешений с записью только в workspace. Сетевой доступ включайте только для явно нужных доменов и не предоставляйте доступ к production management network.

Перед первой реализацией создайте отдельную ветку или worktree. Не запускайте параллельные сессии Codex на одних и тех же файлах.

## Первый запрос: этап E00

Откройте Codex, включите Plan mode и передайте:

> Прочитай полностью `AGENTS.md`, `PLANS.md`, `README.md` и `tasks/E00_DISCOVERY.md`. Осмотри фактическое состояние репозитория. Создай ExecPlan по `PLANS.md` и выполни только этап E00. Не создавай прикладной код, пока не зафиксированы границы, решения, scale profile, внешние зависимости и карта ДКБ. Не используй production credentials. В конце выполни self-review и выдай отчет в формате `AGENTS.md`.

## Запрос для следующего этапа

Замените имя файла этапа:

> Прочитай `AGENTS.md`, `PLANS.md`, завершенный ExecPlan предыдущего этапа и `tasks/E01_BOOTSTRAP.md`. Проверь входные критерии. Создай или актуализируй ExecPlan и выполни только текущий этап по единицам работы. После каждой единицы запускай релевантные тесты. Не переходи к следующему этапу. Обнови документацию и трассировку ДКБ, затем выполни self-review.

## Запрос для продолжения E09.8

Используйте этот запрос, если нужно продолжить с текущего handoff, а не начинать E10:

> Прочитай `AGENTS.md`, `PLANS.md`, `tasks/E09_KOLLA_DEPLOY.md`,
> `docs/execplans/E09-deployment-smoke-evidence.md` и
> `docs/generated/e09-deployment-smoke-evidence.md`. Перепроверь рабочее дерево и релевантные
> E09 tests. Не начинай E10. Продолжай только E09.8 live smoke/evidence: используй approved test
> inventory с marker `cloud_ui_test_stand`, backend/frontend images только по `@sha256`, открытый
> rollback window и подтвержденную SSH host identity. Не коммить inventory, credentials, private keys,
> cookies, токены или production URLs. Обновляй только sanitized evidence и явно оставляй
> `pending_external_evidence`, если live proof не получен.

## Запрос на review

После реализации используйте отдельный проход:

> Проведи строгий review незакоммиченных изменений относительно требований текущего этапа, `AGENTS.md`, архитектурных инвариантов и ДКБ. Ищи обходы backend-авторизации, утечки токенов/секретов, некорректные retries, отсутствие idempotency, небезопасные миграции, загрузку полного inventory, несогласованность OpenAPI и отсутствие отрицательных тестов. Сначала перечисли findings по критичности с точными файлами и строками. Затем исправь подтвержденные проблемы и повторно запусти проверки.

## Запрос на security review

> Прочитай `security/AGENTS.md`, `docs/10_SECURITY_DKB.md`, `docs/11_DKB_TRACEABILITY.md` и изменения текущего этапа. Выполни threat-driven review. Не считай UI-скрытие авторизацией и не заявляй закрытие внешних требований. Проверь секреты, сессии, CSRF, SSRF, injection, workflow allowlist, audit redaction, container privileges и supply chain. Сохрани результат по `templates/SECURITY_REVIEW_TEMPLATE.md`.

## Правило размера задачи

Одна сессия должна выполнять один этап либо одну явно обозначенную единицу работы внутри этапа. Когда этап состоит более чем из четырех независимых изменений, сначала поручите Codex завершить только первую единицу и обновить ExecPlan. Следующая сессия продолжает по тому же плану.

## Разрешенный автономный выбор

Codex может самостоятельно:

- выбирать внутреннюю структуру небольшого модуля;
- добавлять тестовые fixtures и mocks;
- исправлять lint/typecheck в изменяемой области;
- выбирать безопасный fallback, не расширяющий права;
- документировать неизвестную внешнюю интеграцию через interface и mock.

Codex не должен самостоятельно:

- менять production OpenStack policy;
- запускать Kolla-Ansible на production inventory;
- выполнять destructive migration;
- добавлять реальные secrets;
- подключаться к OpenStack service DB;
- ослаблять TLS, RBAC, SELinux или container isolation ради прохождения теста;
- объявлять соответствие ДКБ без доказательств.

## Официальные рекомендации Codex

Документы построены вокруг четырех частей хорошего задания: цель, контекст, ограничения и проверяемое условие завершения. Для сложной работы используется Plan mode и живой `PLANS.md`; постоянные правила находятся в коротком `AGENTS.md`, а локальные уточнения — в подкаталогах.

Источники:

- https://developers.openai.com/codex/learn/best-practices
- https://developers.openai.com/codex/guides/agents-md
- https://developers.openai.com/codex/permissions
- https://developers.openai.com/cookbook/articles/codex_exec_plans
