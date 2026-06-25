# ExecPlan: E09.6 HAProxy TLS Network

## Цель и наблюдаемый результат

Оператор получает проверяемый repository-side контракт маршрутизации Cloud UI за HAProxy/TLS:
единый внешний origin обслуживает SPA и BFF/API, `/api/v1/*` направляется только в backend API,
health checks используют существующие backend readiness endpoints, а TLS, trusted proxy headers,
timeouts и management network/ACL требования зафиксированы в роли, тестах и evidence. До этой
работы роль запускала frontend/API/worker/events, но не описывала HAProxy route, TLS policy,
backend health checks, proxy headers и network flow evidence.

## Контекст и текущее состояние

- Текущий этап: `tasks/E09_KOLLA_DEPLOY.md`, единица E09.6 HAProxy/TLS/network.
- Ветка/worktree: `e09-haproxy-tls-network` at
  `/Users/dmitry/Desktop/dawn/.worktrees/e09-haproxy-tls-network`.
- `deploy/kolla/ansible/roles/cloud_ui/defaults/main.yml` already defines two images, four permanent
  Cloud UI services, one one-shot migration job and synthetic three-node process topology.
- `deploy/kolla/ansible/roles/cloud_ui/templates/cloud-ui-frontend.conf.j2` serves only the SPA on
  the frontend container port.
- `deploy/kolla/ansible/roles/cloud_ui/templates/cloud-ui-backend.env.j2` contains non-secret
  runtime config only.
- Backend exposes `/health/live`, `/health/ready`, `/api/v1/health/live` and
  `/api/v1/health/ready` in `backend/src/cloud_ui/api.py`.
- Existing E08 matrices are `docs/generated/tls-matrix.md` and
  `docs/generated/network-flow-matrix.md`. They already mark HAProxy to frontend/API flows as E09
  pending.
- Baseline in this worktree: initial `make bootstrap` failed because local `python3.11` is missing;
  `make PYTHON=python3 bootstrap` then failed because system `python3` is `3.14.0`, outside
  backend requirement `>=3.11,<3.12`. Setup succeeded with `uv sync --python 3.11 --project backend
  --extra dev` and `npm --prefix frontend ci`. Baseline `make test` passed backend
  `327 passed, 1 skipped` and frontend `35 passed`.
- Current Node is `v25.9.0` while frontend declares `>=24 <25`; `npm ci` completed with an engine
  warning. This is an environment warning, not an E09.6 behavior change.

## Scope

- Add an explicit, non-secret HAProxy route contract for Cloud UI same-origin access:
  browser/VIP -> HAProxy -> frontend for `/`, and HAProxy -> API for `/api/v1/*`.
- Add route defaults for external scheme/FQDN placeholder, public base URL, API public path,
  health check path, timeout policy, request body limit, trusted proxy header policy and
  TLS/backend TLS policy.
- Add a renderable HAProxy config fragment/template that contains no certificates, private keys,
  tokens, passwords or production inventory values.
- Keep backend TLS behind HAProxy as an explicit matrix-driven deployment decision, not a false
  production claim.
- Add tests for role defaults, template contents, negative secret checks, generated evidence and
  updated DKB/risk/matrix docs.
- Update `docs/generated/tls-matrix.md`, `docs/generated/network-flow-matrix.md`,
  `docs/generated/risk-register.md`, `docs/11_DKB_TRACEABILITY.md` and this ExecPlan.

## Non-goals

- No live Kolla-Ansible deploy, reconfigure, HAProxy reload or VIP cutover.
- No real certificates, private keys, CA bundles, credentials, production FQDNs, production URLs or
  inventory hostnames in Git.
- No browser-visible OpenStack API route and no direct JavaScript call to OpenStack APIs.
- No change to backend API semantics, OpenAPI paths, RBAC, session model, database schema or
  frontend UI.
- No claim that production PKI, mTLS, network ACLs, WAF/rate policy, revocation, rotation or
  negative certificate tests are complete.
- No E09.7 rolling update/rollback execution and no E09.8 live smoke/evidence.

## Требования и ограничения

- Browser access remains same-origin through frontend/BFF/API only; browser -> OpenStack API,
  browser -> DB/RabbitMQ/Vault/SIEM and frontend -> OpenStack DB flows remain forbidden.
- OpenStack tokens, application credentials, passwords and certificates must not be sent to the
  browser or committed to the repository.
- Backend authorization remains server-side; HAProxy/UI route visibility is not authorization.
- Mutating API requirements from prior stages remain unchanged: CSRF and idempotency are backend/API
  concerns, not HAProxy authorization shortcuts.
- HAProxy config must use safe defaults: TLS >= 1.2 at the external edge, bounded connect/client/server
  timeouts, explicit health checks, `X-Forwarded-Proto`, `X-Forwarded-For`, `X-Forwarded-Host`,
  `X-Request-ID`, security headers and request body limit.
- Backend TLS/mTLS behind HAProxy is recorded as a deployment decision tied to the TLS matrix.
- Management network and ACL evidence must remain documented as pending until a live test inventory
  proves source/destination CIDR, ports and rejection behavior.

## Связь с ДКБ

| Код | Что реализует план | Что остается внешним | Доказательство | Почему не закрыто полностью |
|---|---|---|---|---|
| ДКБ-22.02/23.02/24 | Records TLS edge policy, backend TLS decision fields, trusted proxy and per-flow TLS matrix updates. | Corporate PKI, mTLS owner decision, revocation/rotation and negative certificate tests. | HAProxy/TLS tests, `tls-matrix.md`, E09.6 evidence. | Repository config is not live PKI or mTLS proof. |
| ДКБ-65/66 | Documents management network/ACL intent and forbidden flows for Cloud UI. | Real VLAN/CIDR/firewall rules, unused-interface blocking and live reject tests. | `network-flow-matrix.md`, E09.6 evidence. | No live network ACL enforcement in this slice. |
| ДКБ-69/70 | Preserves two-image runtime and avoids secrets/certs in images/templates. | Registry digest pull, scanner/signature and ДКБ-69 waiver. | Role/template tests and secret scan. | No image build/pull/signature executed here. |
| ДКБ-76/77/80 | Adds deployment interface for route, health, timeout, headers and API/public paths. | Live HAProxy route, Kolla reconfigure idempotency and deployment API registry acceptance. | Role defaults/template tests and generated evidence. | No live Kolla reconfigure or route smoke. |
| ДКБ-82 | Documents rollback by disabling/removing route contract before live rollout. | Failed update rollback execution in test. | ExecPlan rollback section and risk register. | No live rollback execution in E09.6. |

## Milestones

1. Plan/spec written and committed.
2. RED HAProxy/TLS/network contract tests.
3. GREEN role defaults/template/config route contract.
4. Evidence, TLS/network matrix, DKB traceability and risk register updates.
5. Verification, self-review, commit and integration to `main`.

## Progress

- [x] 2026-06-25: Исследование фактического состояния. Evidence: E09 task and listed docs were read
  before design approval; role defaults/templates/tests and backend health routes inspected; baseline
  `make test` passed after Python 3.11 setup.
- [x] 2026-06-25: Контракт и тестовый double. Evidence:
  `backend/.venv/bin/python -m pytest tests/test_e09_haproxy_tls_network.py -q` failed `7 failed`
  because HAProxy defaults, template/config task, validation rules, evidence and E09 role guard updates
  are not implemented yet.
- [x] 2026-06-25: Минимальная реализация. Evidence:
  `backend/.venv/bin/python -m pytest tests/test_e09_haproxy_tls_network.py -q` passed `7 passed`
  after adding HAProxy defaults, non-secret template, config rendering, validation and evidence docs.
- [x] 2026-06-25: Отрицательные сценарии и безопасность. Evidence: E09.6 tests verify no secret
  keywords in HAProxy template, placeholder FQDN is rejected when enabled, forbidden network flows are
  documented and evidence does not claim production approval.
- [x] 2026-06-25: Интеграционные и пользовательские проверки. Evidence:
  `backend/.venv/bin/python -m pytest tests/test_e09_haproxy_tls_network.py tests/test_e09_kolla_ansible_role.py tests/test_e09_process_containers.py tests/test_e09_migration_job.py -q`
  passed `31 passed`.
- [x] 2026-06-25: Документация, evidence и review. Evidence:
  `backend/.venv/bin/python -m pytest tests -q` passed `43 passed`; `make lint`, `make typecheck`,
  `make security`, `make test` and `git diff --check` passed. Full `make test` passed backend
  `327 passed, 1 skipped` and frontend `35 passed`.

## Неожиданные открытия

- 2026-06-25: `make bootstrap` defaults to `python3.11`, which is not present on this host. Using
  `python3` creates Python `3.14.0`, which violates backend `>=3.11,<3.12`. Workaround for this
  worktree is `uv sync --python 3.11 --project backend --extra dev` with
  `UV_PROJECT_ENVIRONMENT=<worktree>/backend/.venv`.
- 2026-06-25: An early relative `UV_PROJECT_ENVIRONMENT=backend/.venv` created an ignored nested
  `backend/backend/.venv`; it was removed before baseline because `scripts/secret-scan.sh` uses
  `rg --hidden --no-ignore`.
- 2026-06-25: `npm --prefix frontend ci` succeeds but warns that local Node `v25.9.0` is outside
  frontend engine range `>=24 <25`.

## Журнал решений

- 2026-06-25: Implement repository-side HAProxy/TLS/network contract first, not live HAProxy reload.
  Alternatives: immediate live lab route or docs-only matrix update. Reason: E09.6 needs checked role
  behavior without committing certificates, production URLs or making unsafe live route changes before
  E09.7/E09.8 rollout/smoke. Consequence: live URL proof remains pending.
- 2026-06-25: Use placeholder `cloud-ui.example.invalid` for public FQDN defaults. Alternatives:
  lab IP/VIP or production-style FQDN. Reason: avoid committing production URL while keeping rendered
  route testable. Consequence: deploy inventory must override it.
- 2026-06-25: Reuse existing `/api/v1/health/ready` as API backend health check. Alternatives:
  frontend-only `/health` or root API path. Reason: backend already exposes readiness with dependency
  status and tests; frontend static SPA is checked through its own route. Consequence: live health will
  fail closed when backend dependencies are unhealthy.

## Детальный план реализации

1. Add `tests/test_e09_haproxy_tls_network.py` requiring:
   - expected HAProxy defaults exist and contain no production URLs or secret material;
   - route table maps `/` to `cloud_ui_frontend` and `/api/v1/` to `cloud_ui_api`;
   - health check paths are `/` for frontend and `/api/v1/health/ready` for API;
   - timeout/body/header/TLS policy fields exist with bounded values;
   - HAProxy template renders same-origin frontend/API backends, trusted proxy headers and security
     headers without cert/private-key content;
   - generated E09.6 evidence, TLS matrix, network matrix, DKB traceability and risk register mention
     the E09.6 scope and residual gaps.
2. Run the new test and confirm RED.
3. Update `deploy/kolla/ansible/roles/cloud_ui/defaults/main.yml` with route, TLS, timeout, header,
   ACL and health check defaults.
4. Add `deploy/kolla/ansible/roles/cloud_ui/templates/cloud-ui-haproxy.cfg.j2` as a non-secret route
   fragment/template.
5. Update `deploy/kolla/ansible/roles/cloud_ui/tasks/config.yml` or role metadata to render/publish
   the HAProxy template without invoking live Kolla HAProxy.
6. Update `deploy/kolla/ansible/roles/cloud_ui/tasks/validate.yml` with non-secret validation for
   FQDN placeholder override requirements, timeout bounds, path prefixes and backend TLS policy
   enum values.
7. Update existing E09 role tests that previously forbade `haproxy` so E09.2 guard does not block
   the now-approved E09.6 scope.
8. Add `docs/generated/e09-haproxy-tls-network.md` and update TLS/network/risk/DKB docs.
9. Run targeted and full verification.

## Миграции и совместимость

No database schema, OpenAPI, frontend route, backend API behavior or runtime command change is planned.
Existing frontend/API containers remain compatible because the route contract points to current listen
ports and existing health endpoints. Rolling update compatibility is unchanged at repository level; live
enablement must be done in E09.7 with route override, reconfigure and rollback window. Rollback before
live deployment is a Git revert of this E09.6 commit. Rollback after live deployment requires reverting
the Kolla HAProxy override and re-running `kolla-ansible reconfigure` in the test inventory.

## Проверка

Run from `/Users/dmitry/Desktop/dawn/.worktrees/e09-haproxy-tls-network`:

- `backend/.venv/bin/python -m pytest tests/test_e09_haproxy_tls_network.py -q`
- `backend/.venv/bin/python -m pytest tests/test_e09_haproxy_tls_network.py tests/test_e09_kolla_ansible_role.py tests/test_e09_process_containers.py tests/test_e09_migration_job.py -q`
- `backend/.venv/bin/python -m pytest tests -q`
- `make lint`
- `make typecheck`
- `make security`
- `make test`
- `git diff --check`

Expected final result: all commands exit 0. The first E09.6 test run must fail before implementation.

## Доказательства

- `tests/test_e09_haproxy_tls_network.py`
- `deploy/kolla/ansible/roles/cloud_ui/defaults/main.yml`
- `deploy/kolla/ansible/roles/cloud_ui/tasks/config.yml`
- `deploy/kolla/ansible/roles/cloud_ui/tasks/validate.yml`
- `deploy/kolla/ansible/roles/cloud_ui/templates/cloud-ui-haproxy.cfg.j2`
- `docs/generated/e09-haproxy-tls-network.md`
- `docs/generated/tls-matrix.md`
- `docs/generated/network-flow-matrix.md`
- `docs/generated/risk-register.md`
- `docs/11_DKB_TRACEABILITY.md`
- This ExecPlan

## Откат и восстановление

Repository rollback is `git revert` of the E09.6 commits. This slice does not mutate remote hosts,
Vault, MariaDB, RabbitMQ, registry, Kolla inventory or a live HAProxy process. If the contract has
already been used in a later live test, disable the Cloud UI HAProxy route in test inventory, re-run
Kolla reconfigure under the E09.7 rollback window and verify that the previous Horizon/OpenStack VIP
routes still answer.

## Итог и остаточные риски

Implemented E09.6 as a repository-side HAProxy/TLS/network contract. The Cloud UI role now records
same-origin route defaults, placeholder external FQDN, TLS minimum, backend TLS mode choices, trusted
proxy headers, body/timeouts/security headers, management ACL status, forbidden network flows and a
non-secret HAProxy route template. The role renders this contract to config only and does not reload a
live HAProxy process.

Residual risks: no live HAProxy route, no `https://` UI smoke, no corporate PKI scan, no mTLS owner
approval, no wrong-certificate negative test, no firewall/management ACL reject proof, no WAF/rate
policy evidence, no Kolla reconfigure/rollback execution and no production approval.
