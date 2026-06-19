# Технологический стек

Версии библиотек фиксируются lock-файлами в E01 после проверки совместимости с выбранным Kolla base image. Этот документ задает технологии и границы, но не разрешает Codex бесконтрольно обновлять major versions.

## Frontend

- React и TypeScript.
- Vite для сборки.
- React Router.
- TanStack Query для server state.
- TanStack Table для модели больших таблиц.
- PatternFly для enterprise shell, форм, accessibility и согласованного UI.
- OpenAPI-generated TypeScript types/client.
- React Hook Form и JSON Schema renderer для workflow forms.
- Vitest и React Testing Library.
- Playwright для end-to-end.
- pnpm и lockfile.

Правила:

- browser state не дублирует authoritative server state;
- page/filter/sort находятся в URL;
- таблицы используют virtualization только как дополнение к server-side pagination;
- capability checks приходят из backend;
- токены и секреты отсутствуют в JS;
- пользовательская ошибка содержит безопасный текст и correlation ID.

## Backend

- Python, версия совместима с runtime Kolla base image и фиксируется ADR.
- FastAPI.
- Pydantic.
- SQLAlchemy 2.
- Alembic.
- MariaDB driver с production-ready connection pooling.
- openstacksdk для поддерживаемой семантики OpenStack.
- httpx для явно документированных REST-интеграций и mock contract tests.
- Celery с RabbitMQ для фоновых задач портала.
- Kombu для контролируемого event consumer.
- структурированный JSON logging.
- OpenTelemetry или Prometheus-compatible metrics.
- pytest, pytest-asyncio, respx и testcontainers/compose profile.
- Ruff и mypy.
- uv для воспроизводимого developer workflow либо эквивалент, зафиксированный ADR.

### Async и openstacksdk

FastAPI endpoint может быть async, но sync openstacksdk нельзя вызывать напрямую в event loop. Адаптер должен:

- выполнять sync-вызовы в ограниченном thread pool; либо
- использовать проверенный async REST adapter для конкретного API.

Выбор фиксируется ADR и нагрузочным тестом. Не переписывать все OpenStack API на raw HTTP без необходимости.

## Data

- Собственная БД/schema `cloud_ui`.
- Alembic migrations.
- UUID/ULID для внутренних operation IDs.
- UTC timestamps.
- JSON только для ограниченных расширяемых attributes; поля фильтрации и join хранятся в типизированных колонках.
- Full-text/поисковая система не добавляется до доказанной необходимости. Сначала используются индексы MariaDB и нормализованные фильтры.

## Messaging

- Отдельный RabbitMQ vhost `/cloud-ui`.
- Отдельные users для producer/consumer при необходимости.
- Очереди с explicit durability, dead-letter exchange и ограниченной политикой retry.
- Message payload versioning.
- Idempotent consumers.
- Никаких чувствительных токенов в сообщении; используется reference на server-side credential/session context либо service integration identity.

## Workflow

- Mistral — источник истины длительного execution.
- Каталог портала содержит только утвержденные mappings и схемы.
- Watcher, Masakari и Heat вызываются через Mistral либо отдельные адаптеры, если операция не является длительной.
- Celery не реализует сложную orchestration state machine.

## Reverse proxy и frontend serving

- Production routing через существующий HAProxy Kolla.
- Frontend image содержит только runtime static server и compiled assets.
- `/api` проксируется к backend API на том же origin.
- Security headers: HSTS в production, CSP, X-Content-Type-Options, Referrer-Policy, frame restrictions.
- TLS termination и при необходимости backend TLS задаются deployment-контуром.

## Container и supply chain

- Multi-stage build.
- Отдельные build и runtime слои.
- Runtime без compiler и package manager, когда это возможно.
- Non-root user.
- Read-only root filesystem, writable tmp/cache как отдельные mount.
- Drop capabilities.
- SBOM через Syft или эквивалент.
- Vulnerability scan через Trivy/Grype или корпоративный scanner.
- Image signing и admission policy — production-контур.
- Требование отсутствия Python interpreter в backend несовместимо с выбранным runtime и требует формального исключения ДКБ-69.

## Почему не добавляется Redis

В исходной среде уже есть MariaDB и RabbitMQ. Для PoC server-side сессии, idempotency, operations и rate counters реализуются без нового stateful-компонента. Redis добавляется только после измерения bottleneck и ADR.

## Почему etcd не используется

etcd относится к control plane и не является общим приложенческим KV-store. Связывать доступность портала с внутренним etcd OpenStack без необходимости рискованно. Для leader election сначала рассматривается DB advisory/lease pattern; любое использование etcd требует отдельного service account, namespace, TLS и ADR.
