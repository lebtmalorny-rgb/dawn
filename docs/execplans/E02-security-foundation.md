# ExecPlan: E02 security foundation

## Цель и наблюдаемый результат

После E02 пользователь сможет войти через deterministic mock identity в P0, получить server-side session, увидеть только разрешенные разделы и capabilities, а прямой запрещенный API request получит `403` и audit event. Наблюдаемое поведение: browser не получает OpenStack token, session хранится на сервере, CSRF блокирует state-changing requests, backend RBAC повторно проверяет доступ независимо от UI.

До E02 в коде есть только E01 shell: FastAPI health/readiness endpoints, request ID middleware, DB/RabbitMQ probes, Alembic bootstrap and frontend readiness card. Auth/session/RBAC/audit baseline отсутствуют.

## Контекст и текущее состояние

- Repository root: `/Users/dmitry/Desktop/dawn`.
- Current branch/worktree contains uncommitted E00 docs/risk updates. `docs/generated/risk-register.md` tracks R-050: do not mix E02 schema/code with unfinalized E00 documentation.
- Backend files currently present:
  - `backend/src/cloud_ui/api.py`: FastAPI app factory, health routes and request ID middleware.
  - `backend/src/cloud_ui/config.py`: `Settings` with DB/RabbitMQ/API options.
  - `backend/src/cloud_ui/db.py`: SQLAlchemy engine/probe helper.
  - `backend/src/cloud_ui/migrations/versions/0001_schema_info.py`: initial Alembic baseline.
  - `backend/tests/test_api_health.py`, `backend/tests/test_config.py`, `backend/tests/test_db.py`, `backend/tests/test_redaction.py`.
- Frontend files currently present:
  - `frontend/src/App.tsx`: readiness UI only.
  - `frontend/src/api.ts`: readiness fetcher.
  - `frontend/src/App.test.tsx`: readiness tests.
- E02 input documents read:
  - `docs/06_AUTH_RBAC_SESSIONS.md`;
  - `docs/08_AUDIT_OBSERVABILITY.md`;
  - `docs/10_SECURITY_DKB.md`;
  - `docs/11_DKB_TRACEABILITY.md`;
  - `docs/13_TEST_STRATEGY.md`.

## Scope

- Deterministic P0 identity provider with production hard-disable.
- Server-side sessions: opaque cookie, idle expiry 900 seconds, absolute expiry, logout, revoke, simultaneous-session policy.
- CSRF for state-changing portal endpoints.
- Minimal portal RBAC: roles, permissions, bindings, scopes and deny-by-default policy service.
- Capabilities API consumed by frontend.
- Minimal audit baseline for auth/session/authorization events.
- Negative tests for direct 403, hidden UI action, CSRF, session expiry/revoke, session limit, service-role human assignment denial and portal allow + simulated OpenStack deny.
- Documentation/evidence updates for ДКБ-01-07, 12, 13, 15, 20, 21.

## Non-goals

- No production IdP/federation completion without ADR-001 owner evidence.
- No real mutating OpenStack actions.
- No inventory read model implementation; E04 owns inventory.
- No custom workflow execution; E06 owns workflow.
- No SIEM delivery claim; E07 owns external audit delivery.
- No Vault/SecMan secret lifecycle implementation; E08 owns production secret lifecycle.
- No admin UI for arbitrary policy expressions.

## Требования и ограничения

- Browser stores only opaque session cookie; no OpenStack token, application credential, password or certificate in browser storage or frontend bundle.
- Mock login is P0-only and fails startup in production profile.
- Backend authorization is mandatory for protected endpoints; frontend capabilities are UX only.
- Portal permissions may narrow OpenStack permissions, never expand them.
- Service role cannot be assigned to human subjects.
- Mutating endpoints require CSRF and, where applicable, idempotency.
- Audit events must be redacted before serialization.
- All DB schema changes use Alembic with downgrade.
- New public APIs require OpenAPI and tests.

## Связь с ДКБ

- ДКБ-01/01.01/01.03/01.04/01.05/01.06: E02 implements portal RBAC/capability checks and negative tests. It does not close host/storage/DBA access outside portal.
- ДКБ-02/02.01/02.02/02.03: E02 separates human/service roles in portal. Full SoD enforcement remains IAM/PAM evidence.
- ДКБ-03: E02 enforces portal access through server-side policy. Direct host/root/storage access remains external.
- ДКБ-04/05/07: E02 prevents service role assignment to human users and records denials. Formal non-overlap and personal admin execution remain IAM/PAM controls.
- ДКБ-12: E02 hides forbidden UI routes/actions and proves direct API 403. UI hiding alone is not accepted.
- ДКБ-13: E02 avoids password/token exposure in browser/log/audit. Host-root access to configs/secrets remains external.
- ДКБ-15: E02 supports test/mock flow only; production auth method selection remains ADR-001/IdP.
- ДКБ-20/21: E02 implements session idle timeout, expiry, revoke and simultaneous-session policy.
- ДКБ-46-53: E02 creates only auth/session/authorization audit baseline; full audit remains E07/SIEM.

## Milestones

1. Close E00/risk docs patch: run checks, review diff, keep E02 code separate.
2. Contract and test double: identity provider interface, deterministic mock provider, production-hard-disable tests.
3. Minimal server-side sessions: schema/migration, opaque cookie, login/logout/current session endpoints.
4. Session controls: idle/absolute expiry, revoke, session limit policy.
5. CSRF and security headers for state-changing portal endpoints.
6. Portal RBAC and capabilities API: deny-by-default policy service, seed roles, service-role restrictions.
7. Audit baseline for login/logout/revoke/timeout/session-limit/denial.
8. Frontend minimal login/session/capability shell and route/action guard.
9. Negative test matrix, docs, DKB evidence and self-review.

## Progress

- [x] 2026-06-21: Исследование фактического состояния E02 входа.
- [x] 2026-06-21: Risk register created for E00/E02 transition.
- [x] 2026-06-21: E02 ExecPlan created.
- [x] 2026-06-21: E00/risk docs patch verified and reviewed before E02 code. Evidence: `git diff --check`, `./scripts/secret-scan.sh`, stale-statement `rg`, `make lint`, `make typecheck`, `make test`.
- [ ] E00/risk diff committed or explicitly accepted as the E02 implementation base.
- [ ] Contract and test double.
- [ ] Minimal implementation.
- [ ] Отрицательные сценарии и безопасность.
- [ ] UI/session/capability smoke.
- [ ] Документация, evidence и review.

## Неожиданные открытия

- Current backend has no auth/session/RBAC structure, so E02 should introduce small focused modules instead of modifying a pre-existing auth layer.
- Current worktree is dirty with E00/risk docs. Starting E02 code before finalizing those changes would make review and rollback unclear.
- `tests/test_e015_kolla_layout.py` targets Kolla prototype files outside current E02 scope and must not be used as an E02 gate unless that task is explicitly resumed.

## Журнал решений

- 2026-06-21: Start E02 with deterministic mock identity and production hard-disable. Reason: ADR-001/test federation owner evidence is not complete, but P0 must remain testable.
- 2026-06-21: Minimal E02 roles are `cloud_viewer`, `cloud_operator`, `security_auditor`, `portal_admin` plus non-human `service`. Reason: enough to prove capability behavior without admin-all shortcut.
- 2026-06-21: Add audit baseline in E02, but no SIEM delivery claim. Reason: E02 acceptance requires auth events; E07 owns delivery guarantees.
- 2026-06-21: Keep inventory, Prometheus and Masakari out of E02 implementation except capability names and risk references. Reason: E02 must stay security foundation.

## Детальный план реализации

### E02.0. Finalize E00/risk patch

- Verify current docs with:
  - `git diff --check`;
  - `./scripts/secret-scan.sh`;
  - `make lint`;
  - `make typecheck`;
  - `make test`.
- Review `docs/generated/risk-register.md`, `docs/15_DECISIONS_AND_OPEN_QUESTIONS.md`, `docs/11_DKB_TRACEABILITY.md` and this ExecPlan for contradictions.
- Do not start E02 schema/code until the E00/risk diff is either committed or explicitly accepted as the base of this worktree.

### E02.1. Identity provider contracts

Create:

- `backend/src/cloud_ui/security/identity.py`: `IdentityProvider` protocol, `Subject`, `LoginRequest`, `LoginResult`, typed auth errors.
- `backend/src/cloud_ui/security/mock_identity.py`: deterministic P0 provider with fixed sanitized users and roles.
- `backend/tests/security/test_mock_identity.py`: login success/failure, disabled production profile, no password/token in result.

Modify:

- `backend/src/cloud_ui/config.py`: add `environment`, `identity_provider`, `mock_identity_enabled` and validation that mock provider is rejected for production.

### E02.2. Audit baseline model

Create:

- `backend/src/cloud_ui/security/audit.py`: in-process audit sink interface and DB-ready `AuditEvent` DTO for auth/session/RBAC events.
- `backend/tests/security/test_audit_redaction.py`: canary secret redaction and mandatory field tests.

This milestone may use a deterministic in-memory sink for unit tests. DB outbox durability can be introduced with session schema in E02.3.

### E02.3. Server-side session schema and API

Create:

- Alembic migration `backend/src/cloud_ui/migrations/versions/0002_security_foundation.py` with tables:
  - `subjects`;
  - `sessions`;
  - `session_events` or audit/outbox table if not deferred to E07;
  - `roles`;
  - `permissions`;
  - `role_bindings`.
- `backend/src/cloud_ui/security/sessions.py`: session creation, lookup, idle/absolute expiry, revoke and cookie rotation helpers.
- `backend/src/cloud_ui/security/routes.py`: `/api/v1/session/login`, `/api/v1/session/logout`, `/api/v1/session`, `/api/v1/session/active`, revoke endpoint.
- Tests for cookie flags, 900 second idle default, expiry, logout and revoke.

Modify:

- `backend/src/cloud_ui/api.py`: include security router and middleware.

### E02.4. CSRF and headers

Create:

- `backend/src/cloud_ui/security/csrf.py`: signed token or double-submit pattern tied to server session.
- Tests for missing/invalid CSRF on state-changing endpoints and acceptance on valid token.

Modify:

- `backend/src/cloud_ui/api.py`: security headers middleware for local/test mode: no-store for session endpoints, basic clickjacking/content-sniffing controls.

### E02.5. RBAC and capabilities

Create:

- `backend/src/cloud_ui/security/rbac.py`: permissions, roles, scope model, deny-by-default evaluator.
- `backend/src/cloud_ui/security/capabilities.py`: effective capability calculation and policy revision.
- Tests:
  - user without capability receives 403;
  - direct route access denied;
  - service role cannot bind to human subject;
  - portal allow plus simulated OpenStack deny remains denied;
  - capability response contains no internal policy expressions.

Modify:

- `backend/src/cloud_ui/api.py`: dependency wiring for protected endpoints.

### E02.6. Frontend session and capability shell

Create/modify:

- `frontend/src/api.ts`: session/capabilities client with runtime guards.
- `frontend/src/App.tsx`: minimal login/session state and capability-aware navigation placeholder.
- `frontend/src/App.test.tsx`: forbidden action hidden, malformed session payload safe error, login failure safe message.

Frontend must not contain hardcoded `admin means all`.

### E02.7. Evidence and docs

Update:

- `docs/generated/api-register.md`: mark E02 session/capability endpoints with implementation evidence once complete.
- `docs/generated/risk-register.md`: move E02 risks to mitigated only when tests pass.
- `docs/11_DKB_TRACEABILITY.md`: add E02 evidence references without claiming full external compliance.
- This ExecPlan progress, command results and residual risks.

## Миграции и совместимость

- Use Alembic migration with downgrade.
- Add tables without destructive changes to existing `schema_info`.
- API remains backward compatible with E01 health endpoints.
- Rolling update caveat: E02 code requiring session tables must be deployed after migration job. API must fail readiness or disable auth routes safely if migration is missing.
- Rollback: revert E02 code, run Alembic downgrade from `0002_security_foundation` to `0001_schema_info`, clear local test sessions/audit rows.

## Проверка

Required commands from `/Users/dmitry/Desktop/dawn`:

- `git diff --check` -> no whitespace errors.
- `./scripts/secret-scan.sh` -> no secret matches.
- `make lint` -> backend ruff, frontend eslint and secret scan pass.
- `make typecheck` -> backend mypy and frontend `tsc -b` pass.
- `make test` -> backend pytest and frontend vitest pass.

E02-specific tests to add and run as targeted commands while implementing:

- `cd backend && .venv/bin/python -m pytest tests/security -q`;
- `cd frontend && npm test -- --run`;
- OpenAPI smoke through `backend/tests/test_api_health.py` or a new `backend/tests/security/test_security_openapi.py`.

## Доказательства

- E02 ExecPlan with updated progress.
- Alembic migration and downgrade.
- Backend auth/session/RBAC/audit tests.
- Frontend capability/session tests.
- Secret scan output.
- DKB traceability update.
- Risk register update.
- Sanitized command summary in final report.

## Откат и восстановление

- Documentation-only E02 planning rollback: delete this file and remove links added in current patch.
- E02 implementation rollback after code starts:
  - revert E02 code files;
  - run Alembic downgrade for E02 migration in local/test DB;
  - clear test cookies/sessions;
  - keep E00 risk register unless its assumptions are invalidated.

## Итог и остаточные риски

This plan is created before E02 code starts. Remaining risks before implementation:

- E00/risk diff is still uncommitted in this worktree.
- ADR-001 production/test federation details remain incomplete.
- Vault/SecMan production key storage remains E08.
- SIEM delivery remains E07.
- IAM/PAM/SoD evidence remains external/P3.
