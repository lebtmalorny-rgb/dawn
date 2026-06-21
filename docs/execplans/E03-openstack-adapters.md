# ExecPlan: E03 OpenStack adapters

## Цель и наблюдаемый результат

После E03 backend имеет typed adapter layer для read-only Keystone, Nova и Placement. Наблюдаемое поведение: contract tests без сети получают synthetic Keystone/Nova/Placement payloads, adapters возвращают DTO, различают `401/403/404/409/429/5xx/timeout/malformed`, не логируют и не раскрывают token/header values, передают `x-request-id`/correlation headers и не требуют frontend/raw OpenStack schema.

До E03 в коде есть E01 health shell и E02 session/RBAC/audit foundation. Каталога `backend/src/cloud_ui/integrations/` нет, OpenStack adapters отсутствуют, а API register помечает Nova/Placement microversions как pending.

## Контекст и текущее состояние

- Repository root: `/Users/dmitry/Desktop/dawn`.
- Active worktree: `/Users/dmitry/Desktop/dawn/.worktrees/e03-openstack-adapters`.
- Current base commit: `ee7564f feat: complete E02 session controls`.
- Baseline verification in E03 worktree: `make test` -> backend `37 passed`, frontend `6 passed`.
- E03 input documents read:
  - `docs/02_TARGET_ARCHITECTURE.md`;
  - `docs/03_TECH_STACK.md`;
  - `docs/05_API_AND_INTEGRATIONS.md`;
  - `docs/13_TEST_STRATEGY.md`.
- Approved design spec: `docs/superpowers/specs/2026-06-21-e03-openstack-adapters-design.md`.
- Current backend dependencies place `httpx==0.28.1` under `dev`; E03 production code will import `httpx`, so `httpx` must move to runtime dependencies.

## Scope

- Shared adapter request context, typed DTO/error contracts, redaction-safe exception representation and retry classification.
- HTTP transport wrapper over `httpx.Client` with timeout, bounded retries for safe temporary read errors, correlation headers and JSON parsing.
- Keystone read-only version discovery and service catalog mapping from synthetic token-like fixtures.
- Nova read-only server list/detail, hypervisor list, compute service list and aggregate/server-group DTO mappings with fixed microversion header.
- Placement resource provider list, inventory and usage DTO mappings with fixed microversion header.
- Offline contract tests using `httpx.MockTransport`.
- Documentation and evidence updates for API/integration/risk registers.

## Non-goals

- No real credential in repo.
- No production/test Keystone authentication flow.
- No mutating OpenStack operations.
- No inventory read model or browser endpoints.
- No live fan-out path from frontend.
- No Mistral, Watcher, Masakari, telemetry, SIEM or Vault adapter implementation.
- No claim that TLS/mTLS deployment requirements are closed.

## Требования и ограничения

- Browser never sees OpenStack token, application credential or raw OpenStack schema.
- Route handlers must not call `httpx`, OpenStack SDK or raw service URLs directly.
- Endpoints come only from trusted configuration, not from browser input.
- GET calls may retry only temporary errors/timeouts; `401/403/404/409/422` are permanent.
- All adapter errors carry safe `code`, `service`, `status_code`, `request_id` and `correlation_id`.
- Error string/repr and audit/log-facing details must redact authorization/token/header values.
- Microversions are explicit settings and documented.
- Tests must pass without network access.

## Связь с ДКБ

- ДКБ-01/03/12: E03 preserves server-side authorization boundary by keeping adapters behind backend contracts; no frontend/raw OpenStack access. Evidence: contract tests and no route dependency.
- ДКБ-46/49: E03 propagates request/correlation IDs to adapter calls and typed errors. Full audit delivery remains E07/SIEM.
- ДКБ-77: E03 updates API/integration registers with Keystone/Nova/Placement versions, timeout/retry and evidence status. Technical blocking/firewall evidence remains E08/E09/P3.
- ДКБ-22.02/24: E03 can document TLS contract assumptions only. Real TLS/mTLS scans and certificate negative tests remain deployment evidence.

## Milestones

1. Shared contracts and retry policy pass unit tests.
2. HTTP transport passes offline tests for headers, retry/no-retry, timeout and malformed JSON.
3. Keystone adapter maps version/catalog and errors from synthetic fixtures.
4. Nova adapter maps read-only DTOs, pagination and microversion headers from synthetic fixtures.
5. Placement adapter maps provider/inventory/usage DTOs and temporary degradation errors.
6. Documentation/evidence updated; optional smoke is recorded as pending unless safe read-only test credential exists.
7. Full gates pass and self-review confirms no token leakage or route fan-out.

## Progress

- [x] 2026-06-21: E03 design spec created and committed. Evidence: commit `2e92243 docs: add E03 adapter design`.
- [x] 2026-06-21: Baseline in E03 worktree verified. Evidence: `make test` -> backend `37 passed`, frontend `6 passed`.
- [ ] Shared contracts and retry policy.
- [ ] HTTP transport.
- [ ] Keystone adapter.
- [ ] Nova adapter.
- [ ] Placement adapter.
- [ ] Documentation, evidence and review.

## Неожиданные открытия

- `httpx==0.28.1` is already available as a dev dependency, but production adapter code needs it as a runtime dependency.

## Журнал решений

- 2026-06-21: Use explicit `httpx` REST adapter boundary for E03. Alternative: `openstacksdk` behind thread pool. Reason: E03 acceptance emphasizes mock HTTP/service layer and offline contract tests; raw SDK auth flow is not approved yet. Consequence: E03 covers read-only contract mapping and does not claim full OpenStack SDK compatibility.
- 2026-06-21: Keep live lab smoke optional and pending by default. Alternative: use provided lab hosts immediately. Reason: no safe read-only test project credential has been proven in repo context; production/admin credentials must not be used.
- 2026-06-21: Fix Nova and Placement microversions in settings with conservative initial values, then document them. Alternative: discover dynamically in E03. Reason: task input requires fixed microversions before adapter usage.

## Детальный план реализации

Implementation plan: `docs/superpowers/plans/2026-06-21-e03-openstack-adapters.md`.

Files to create:

- `backend/src/cloud_ui/integrations/__init__.py`
- `backend/src/cloud_ui/integrations/base.py`
- `backend/src/cloud_ui/integrations/http.py`
- `backend/src/cloud_ui/integrations/openstack_config.py`
- `backend/src/cloud_ui/integrations/keystone/__init__.py`
- `backend/src/cloud_ui/integrations/keystone/adapter.py`
- `backend/src/cloud_ui/integrations/keystone/dto.py`
- `backend/src/cloud_ui/integrations/nova/__init__.py`
- `backend/src/cloud_ui/integrations/nova/adapter.py`
- `backend/src/cloud_ui/integrations/nova/dto.py`
- `backend/src/cloud_ui/integrations/placement/__init__.py`
- `backend/src/cloud_ui/integrations/placement/adapter.py`
- `backend/src/cloud_ui/integrations/placement/dto.py`
- `backend/tests/integrations/`

Files to modify:

- `backend/pyproject.toml`
- `backend/src/cloud_ui/config.py`
- `backend/tests/test_config.py`
- `docs/generated/api-register.md`
- `docs/generated/integration-register.md`
- `docs/generated/risk-register.md`
- this ExecPlan.

## Миграции и совместимость

E03 has no database migration and no public browser endpoint change. Rollback is a git revert of E03 commits. Since adapters are not yet wired into route handlers, deployment can include E03 code without changing runtime behavior except importing the new runtime `httpx` dependency.

## Проверка

Required commands from `/Users/dmitry/Desktop/dawn/.worktrees/e03-openstack-adapters`:

- `cd backend && .venv/bin/python -m pytest tests/integrations -q` -> all E03 adapter tests pass offline.
- `git diff --check` -> no whitespace errors.
- `./scripts/secret-scan.sh` -> no secret matches.
- `make lint` -> backend ruff, frontend eslint and secret scan pass.
- `make typecheck` -> backend mypy and frontend `tsc -b` pass.
- `make test` -> backend pytest and frontend vitest pass.

Optional smoke:

- Only run if a safe read-only test project credential is available outside git.
- If not available, record smoke as pending; do not use production/admin credentials.

## Доказательства

- Offline adapter contract tests.
- Error redaction tests.
- Microversion header tests.
- API/integration/risk register updates.
- Sanitized command summary in final report.

## Откат и восстановление

- Revert E03 commits.
- No DB downgrade required.
- Remove optional local-only smoke environment files if created outside git.
- Keep E02 security commits unchanged.

## Итог и остаточные риски

Pending until implementation completes:

- Real test-cloud smoke may remain pending without approved read-only credential.
- OpenStack auth/federation remains E02/P1 external evidence.
- TLS/mTLS deployment evidence remains E08/E09.
- E04 must still implement read model and avoid UI live fan-out.
