# Стратегия тестирования

## Принцип

Каждый этап сначала определяет наблюдаемое поведение и отрицательные сценарии, затем реализует код. Тесты не должны зависеть от production OpenStack и не должны использовать реальные секреты.

## Уровни тестов

| Уровень | Назначение | Инструменты/пример |
|---|---|---|
| Unit | Доменные правила, policy, redaction, state machines | pytest/Vitest |
| Component | API/service/repository с test DB | pytest + MariaDB profile |
| Adapter contract | Mapping и ошибки внешнего API | respx/mock HTTP fixtures |
| Integration | Backend + DB + RabbitMQ + mock services | compose/testcontainers |
| Frontend component | Таблицы, filters, capability UX | RTL/Vitest |
| E2E | Browser → API → DB/mock OpenStack | Playwright |
| Security negative | RBAC, CSRF, SSRF, injection, secret leakage | pytest/Playwright/scanners |
| Load | latency/throughput/backpressure | k6 или Locust, выбор ADR |
| Failover | crash/retry/reconciliation/HA | scripted test environment |
| Deployment | image/Kolla/upgrade/rollback | smoke/Ansible test inventory |

## Test doubles

Mock OpenStack должен:

- поддерживать Keystone, Nova, Placement и Mistral минимальные contracts;
- возвращать успешные, forbidden, not found, conflict, timeout и malformed response;
- поддерживать pagination/microversion;
- моделировать duplicate/out-of-order events;
- не содержать production payload;
- иметь versioned fixtures.

Contract fixture создается из официальной API schema или безопасно очищенного test response.

## Обязательные тесты по слоям

### Backend API

- input validation;
- error format;
- request/correlation ID;
- pagination/cursor tampering;
- stable sort;
- partial response;
- timeout/retry;
- no N+1 на критических endpoints;
- OpenAPI snapshot/compatibility.

### Auth/RBAC/session

- login success/failure;
- idle/absolute expiry;
- simultaneous sessions;
- revoke;
- CSRF;
- role/scope matrix;
- direct URL/API access;
- IDOR;
- portal allow + OpenStack deny;
- service role separation;
- audit events.

### Inventory

- full sync;
- incremental sync;
- restart from cursor;
- duplicate/out-of-order event;
- tombstone;
- stale source;
- region unavailable;
- filter/sort/page correctness;
- EXPLAIN/index evidence;
- synthetic scale dataset.

### Groups

- explicit membership;
- dynamic rule safety;
- imported membership;
- cross-scope denial;
- concurrent revision conflict;
- deleted resource behavior;
- group preview limit;
- audit.

### Workflow

- allowlist only;
- schema validation;
- target snapshot;
- idempotency same/different body;
- worker crash before/after Mistral response;
- status reconciliation;
- partial result;
- cancel/retry permissions;
- secret redaction;
- audit.

### Audit

- all mandatory fields;
- success/failure/unknown;
- timestamp/UTC;
- redaction canaries;
- delivery retry/dead-letter;
- heartbeat;
- audit.read/export separation;
- audit access is audited;
- no raw stack trace to client.

### Deployment/security

- image user/capabilities/mounts;
- no secrets in layers/history;
- SBOM generated;
- vulnerability policy;
- TLS min version/ciphers;
- mTLS negative case;
- SELinux enforcing/denials;
- registry digest;
- migration/rollback;
- unavailable dependency.

## ДКБ test matrix

В `docs/generated/dkb-test-matrix.md` каждая строка содержит:

- DKB code;
- test ID;
- preconditions;
- actor/role;
- action;
- expected UI;
- expected API outcome;
- expected audit event;
- external evidence;
- result;
- artifact link.

Особое внимание отрицательным тестам ДКБ-01/12, session tests ДКБ-20/21, TLS ДКБ-22.02/24, audit ДКБ-46–53 и image/network ДКБ-69/70/77/80.

## Quality gates

### На каждый commit/PR

- format;
- lint;
- typecheck;
- unit tests;
- secret scan;
- changed-area contract tests.

### На этап

- integration;
- E2E;
- OpenAPI compatibility;
- migration test;
- security review;
- DKB evidence update.

### Перед P2

- workflow/idempotency/recovery tests;
- SIEM delivery;
- redaction;
- real test OpenStack negative RBAC.

### Перед P3

- load;
- failover;
- TLS/mTLS;
- SBOM/vulnerability/signature;
- SELinux;
- Kolla rolling update/rollback;
- external controls review.

## Flaky tests

Flaky test не отключается без issue, owner и expiry. Retry CI не считается исправлением. Временная quarantine должна сохранять visibility и не блокировать только при утвержденном risk.

## Test data

- generated deterministic seed;
- no personal/business data;
- canary strings для leakage;
- UUIDs scoped by cloud/region;
- enough cardinality for indexes;
- cleanup idempotent.

## Evidence format

Отчеты сохраняются в `artifacts/` или CI и ссылаются из ExecPlan. В Git допускаются небольшие sanitized summaries, schemas и commands; большие логи/HTML не коммитятся без необходимости.
