# E01 — Bootstrap monorepo и воспроизводимая локальная среда

## Пользовательский результат

Разработчик на Rocky Linux клонирует репозиторий, запускает одну команду и получает frontend, API, worker/event process, MariaDB/RabbitMQ test profile и health page. Codex может запускать все проверки сам.

## Входные критерии

- E00 принят.
- ADR runtime/package versions имеет статус accepted.
- Нет blocker на локальный container runtime.

## Прочитать

- завершенный ExecPlan E00;
- `docs/02_TARGET_ARCHITECTURE.md`;
- `docs/03_TECH_STACK.md`;
- `docs/12_DEPLOY_ROCKY_KOLLA.md`;
- `docs/13_TEST_STRATEGY.md`.

## Единицы работы

### E01.1. Структура

Создать monorepo:

    backend/
    frontend/
    deploy/
    tests/
    docs/execplans/
    docs/adr/
    artifacts/
    compose.yaml
    Makefile

Сохранить вложенные `AGENTS.md`.

### E01.2. Backend skeleton

Создать backend package с командами:

    cloud-ui api
    cloud-ui worker
    cloud-ui events
    cloud-ui db-upgrade

Добавить liveness/readiness, config loading, JSON logs, request ID и typed settings. API не должен автоматически мигрировать БД.

### E01.3. Frontend skeleton

Создать shell, route `/`, health/status view, API client и error boundary. Не реализовывать OpenStack UI.

### E01.4. Data/messaging profile

Compose поднимает локальные MariaDB и RabbitMQ с dummy credentials. Backend имеет отдельную schema/vhost. Добавить Alembic initial migration только для технической таблицы schema version/health при необходимости.

### E01.5. Два image

Создать multi-stage Dockerfiles:

- frontend runtime;
- backend runtime.

Backend image один для всех процессов. Контейнеры non-root, имеют health checks и не содержат secrets.

### E01.6. Единые команды

Реализовать минимум:

    make bootstrap
    make format
    make lint
    make typecheck
    make test
    make build
    make up
    make down
    make smoke

### E01.7. CI baseline

Добавить CI-neutral scripts или pipeline текущей системы: lint, typecheck, unit, build, secret scan. Не привязывать production deploy.

## Acceptance

- `make up` запускает локальный stack.
- UI доступен и показывает API readiness.
- `make smoke` проверяет frontend/API/DB/RabbitMQ.
- API, worker и events используют один backend image.
- Ровно два custom image.
- Миграция запускается отдельно.
- Все обязательные команды работают.
- Containers non-root.
- `.gitignore` исключает credentials.
- unit tests проходят без сети.

## Негативные проверки

- API не стартует с отсутствующей обязательной config и выдает безопасную ошибку.
- Readiness меняется при недоступной DB/RabbitMQ, liveness остается корректным.
- В image history и frontend assets нет dummy secret.
- Backend не пишет config values в лог.

## Затронутые ДКБ

- ДКБ-69/70: только baseline image/registry design, не полное закрытие.
- ДКБ-77/82: начало API и технической документации.
- ДКБ-46: structured logging baseline.

## Не делать

- auth/RBAC;
- OpenStack integration;
- inventory;
- Mistral workflow;
- production Kolla role.

## Итоговый запрос Codex

> Реализуй только E01. Сначала минимальный end-to-end health slice, затем quality commands и images. Не добавляй OpenStack credential и не создавай третий runtime image.
