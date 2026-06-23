# ExecPlan: E08 Session And Token Protection

## Цель и наблюдаемый результат

После этого E08.4-среза восстановленная браузерная сессия сможет безопасно получить свежий CSRF
token через BFF/API, не раскрывая OpenStack/Vault/service credentials. Mutating UI paths after page
reload остаются защищены: без cookie endpoint вернет `401`, а с валидной opaque cookie вернет только
CSRF token, subject and expiration metadata. Документация фиксирует token retention/leakage/revoke
evidence and remaining production gaps.

До этого frontend после `/api/v1/session` восстанавливал subject/capabilities, но оставлял
`csrf=null`, поэтому operation submit, audit export and group mutations fail-closed after reload. В
`docs/generated/risk-register.md` это отражено как R-034.

## Контекст и текущее состояние

- Repository root: `/Users/dmitry/Desktop/dawn/.worktrees/e08-session-token-protection`.
- Branch/worktree: `e08-session-token-protection`.
- Base commit: `e1ce6b7 Merge pull request #3 from lebtmalorny-rgb/e08-threat-model-tls`.
- Existing session implementation:
  - `backend/src/cloud_ui/security/sessions.py` creates opaque random session IDs and CSRF values
    with `secrets.token_urlsafe(32)`.
  - `backend/src/cloud_ui/security/routes.py` returns CSRF only from login response.
  - `/api/v1/session` returns only subject data.
  - `frontend/src/App.tsx` sets `csrf=null` when restoring existing session after reload.
  - `frontend/src/api.ts` has `fetchCurrentSession()` and `fetchCapabilities()` but no CSRF refresh.
- Existing DB migration `0002_security_foundation.py` contains `sessions.csrf_hash`, but current P0
  `SessionManager` is in-memory and stores raw CSRF in process memory.
- Baseline setup:
  - `make bootstrap PYTHON=/Users/dmitry/Desktop/dawn/.worktrees/e08-vault-secman-design/backend/.venv/bin/python`
    succeeded; npm warned local Node `v25.9.0` is outside declared `>=24 <25`.
  - `make lint`, `make typecheck`, `make security`, `make test` passed before implementation.

## Scope

- Add backend `GET /api/v1/session/csrf` endpoint returning a short safe CSRF bootstrap payload for
  an existing authenticated session.
- Ensure the endpoint has `no-store` cache headers via existing session middleware path.
- Ensure unauthenticated requests return safe `401` and no token-like value.
- Add backend tests for restored-session CSRF bootstrap, no OpenStack/Vault/token leakage and revoked
  session denial.
- Add frontend API helper and restore-flow integration so reload fetches CSRF after current session
  and capabilities succeed.
- Add frontend tests proving restored sessions can submit existing mutating workflow through BFF with
  refreshed CSRF, and no local/session storage secret persistence is introduced.
- Update generated session/token evidence and DKB traceability/risk register.

## Non-goals

- No production Keystone federation or token storage implementation.
- No DB-backed encrypted session repository in this slice.
- No new secrets, `.env`, openrc, `clouds.yaml` or production endpoint.
- No browser access to OpenStack, Vault, SIEM, MariaDB or RabbitMQ.
- No change to session cookie name or SameSite policy.
- No E09 Kolla deployment changes.

## Требования и ограничения

- OpenStack tokens, application credentials, Vault auth values, passwords and TLS private keys never
  enter the browser.
- CSRF token may be returned only to an authenticated same-origin browser through BFF/API and must not
  be logged or audited as raw metadata.
- Existing mutating requests must still require CSRF and trusted origin checks.
- Revoked/expired sessions must not receive CSRF.
- Responses containing session/CSRF data must use `Cache-Control: no-store`.
- Any change to sessions/secrets requires `docs/11_DKB_TRACEABILITY.md` update.

## Связь с ДКБ

- ДКБ-13/51: this slice adds leakage tests for session/CSRF bootstrap and documents that no
  OpenStack/Vault/service secrets are returned to browser or audit/log paths.
- ДКБ-20/21: session lifecycle remains one active session by default, 900-second idle timeout,
  absolute lifetime, logout and admin revoke.
- ДКБ-46-53: session restore and denial paths remain audited only where existing session-required,
  auth and revoke events apply; raw CSRF is not stored in audit metadata.
- ДКБ-55/56: session/cursor key production lifecycle remains Vault/SecMan external evidence; this
  slice does not claim production key rotation closure.

## Milestones

1. Backend RED/GREEN: CSRF bootstrap endpoint with safe payload and revoked/unauthenticated negative
   tests.
2. Frontend RED/GREEN: restored session fetches CSRF and can submit existing BFF operation path without
   local/session storage persistence.
3. Evidence docs: session/token protection artifact, risk/register/traceability updates.
4. Verification/review: targeted tests, lint/typecheck/test/integration/security and diff review.

## Progress

- [x] 2026-06-23: Baseline setup and checks passed before changes. Evidence: `make lint`,
  `make typecheck`, `make security`, `make test` passed; `make test` reported backend
  `308 passed, 1 skipped` and frontend `34 passed`.
- [x] Backend CSRF bootstrap endpoint. RED evidence: `backend/.venv/bin/python -m pytest
  backend/tests/security/test_security_api.py -q` failed with 3 expected `404` failures for
  `/api/v1/session/csrf`. GREEN evidence: same test file passed `16 passed`; combined
  `test_sessions.py` + `test_security_api.py` passed `17 passed`.
- [x] Frontend restored-session CSRF flow. RED evidence: `npm test -- src/App.test.tsx -t
  "restored session bootstraps csrf"` failed because `/api/v1/session/csrf` was not called. GREEN
  evidence: same targeted test passed, and `npm test -- src/App.test.tsx` passed `35 passed`.
- [x] Evidence docs and traceability.
- [x] Final verification and review. Evidence: `make lint`, `make typecheck`, `make test`,
  `make test-integration`, `make security` and `git diff --check` passed. `make test` reported
  backend `311 passed, 1 skipped` and frontend `35 passed`; `make test-integration` reported
  `21 passed, 1 skipped`.

## Неожиданные открытия

- 2026-06-23: The host still lacks `python3.11` on PATH; bootstrap reused the previous E08 worktree's
  Python 3.11.15 interpreter only to create this worktree's local `.venv`.
- 2026-06-23: Local Node is `v25.9.0` while frontend declares `>=24 <25`; baseline gates pass but
  release/CI should use Node 24.
- 2026-06-23: `apply_patch` defaults to the main checkout path in this environment; code/doc edits in
  this isolated worktree were applied with absolute paths after confirming the main checkout was clean.
- 2026-06-23: One existing App pagination test counted all `fetch` calls; E08.4 adds a valid
  `/api/v1/session/csrf` request, so the test was narrowed to count only `/api/v1/instances` BFF calls.

## Журнал решений

- 2026-06-23: Implement a same-origin CSRF bootstrap endpoint instead of embedding CSRF in
  `/api/v1/session`. Reason: it keeps current session response minimal while allowing restored
  sessions to opt into mutating workflows. Consequence: frontend restore flow gains one extra BFF
  request after session/capabilities success.
- 2026-06-23: Keep P0 session storage in memory and document DB/Vault lifecycle gaps. Reason:
  implementing encrypted durable sessions and key rotation is a larger persistence slice and must
  align with Vault/SecMan owners. Consequence: this slice improves restored-session behavior and
  leakage tests but does not claim production key lifecycle closure.

## Детальный план реализации

### Task 1: Backend CSRF Bootstrap

- Add response model in `backend/src/cloud_ui/security/routes.py`.
- Add `GET /session/csrf` route under existing security router.
- Use `_require_session`; return safe JSON with `csrf`, `expires_at`, and `subject`.
- Do not write CSRF token to audit metadata.
- Add tests to `backend/tests/security/test_security_api.py` or `test_sessions.py`:
  - authenticated restored session receives CSRF and can use it for logout;
  - unauthenticated request gets `401 not_authenticated`;
  - revoked session gets `401 not_authenticated`;
  - response repr does not contain OpenStack/Vault/application credential words.

### Task 2: Frontend Restore Flow

- Add `fetchCsrf()` helper and type guard in `frontend/src/api.ts`.
- Update `frontend/src/App.tsx` restore flow: after current session and capabilities succeed, fetch
  CSRF and store it in `authState.csrf`.
- Keep failure safe: if CSRF fetch fails, auth state should remain authenticated with `csrf=null` or
  error only if session/capabilities failed. Existing UI disables mutating controls when csrf is null.
- Add frontend tests in `frontend/src/App.test.tsx`:
  - restored session fetches `/api/v1/session/csrf` and then submits operation with the restored CSRF;
  - no local/session storage writes are introduced.

### Task 3: Evidence Docs

- Create `docs/generated/e08-session-token-protection.md` documenting:
  session IDs, CSRF bootstrap, browser retention, logs/audit redaction, revoke behavior, key lifecycle
  gaps and rollback.
- Update `docs/generated/risk-register.md` R-034 to mark restored-session mutation gap narrowed by
  CSRF bootstrap and keep production session persistence/key lifecycle gaps.
- Update `docs/generated/secret-inventory.md` lifecycle notes for session/cursor keys.
- Update `docs/11_DKB_TRACEABILITY.md` with E08.4 evidence and residual conditions.

### Task 4: Verification And Commit

Run:

```bash
backend/.venv/bin/python -m pytest backend/tests/security/test_sessions.py backend/tests/security/test_security_api.py -q
cd frontend && npm test -- src/App.test.tsx
make lint
make typecheck
make test
make test-integration
make security
git diff --check
```

Review diff for:

- no OpenStack/Vault/service credentials in browser response;
- no raw CSRF in audit metadata;
- mutating requests still require CSRF;
- docs do not claim production key rotation closure.

Commit:

```bash
git add backend/src/cloud_ui/security/routes.py backend/tests/security/test_security_api.py backend/tests/security/test_sessions.py frontend/src/api.ts frontend/src/App.tsx frontend/src/App.test.tsx docs/generated/e08-session-token-protection.md docs/generated/risk-register.md docs/generated/secret-inventory.md docs/11_DKB_TRACEABILITY.md docs/execplans/E08-session-token-protection.md
git commit -m "feat: add restored-session CSRF bootstrap"
```

## Миграции и совместимость

No database migration. The endpoint is additive and compatible with old frontend clients. Existing
login CSRF behavior remains unchanged. Rolling update is safe because old frontend ignores the new
endpoint and new frontend still disables mutations if the endpoint is unavailable.

## Проверка

Final verification commands are listed in Task 4. Existing live-smoke skips are acceptable only for
tests designed to skip without live configuration.

## Доказательства

- Backend session/security tests for CSRF bootstrap and denial paths.
- Frontend restore-flow tests.
- `docs/generated/e08-session-token-protection.md`.
- Updated risk register, secret inventory and DKB traceability.
- Command results recorded in this ExecPlan.

## Откат и восстановление

Revert the branch commit. No external service, database schema, remote host, queue or secret store is
changed. If rollback happens after deployment, old frontend behavior remains fail-closed with
`csrf=null` after reload.

## Итог и остаточные риски

Implemented and verified. Residual risks:

- production DB-backed encrypted sessions and key rotation remain Vault/SecMan/deployment work;
- Keystone/IdP token lifetime alignment remains ADR-001/external IAM evidence;
- host/root access to process memory and config requires E08.5/E09/E12 controls;
- local verification uses Node `v25.9.0`, outside declared frontend engine `>=24 <25`.
