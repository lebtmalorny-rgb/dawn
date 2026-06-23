# E08.4 Session And Token Protection Evidence

- Stage: E08.4
- Date: 2026-06-23
- Scope: restored browser session CSRF bootstrap through the portal BFF/API
- Rule: this artifact contains no real cookie, CSRF value, OpenStack token, Vault token, password,
  private key or production endpoint.

## Observable behavior

An already authenticated browser that still has the opaque `cloud_ui_session` cookie can call
`GET /api/v1/session/csrf` through the portal BFF/API. The response contains only:

- `subject`: portal subject metadata already available from `/api/v1/session`;
- `csrf`: the anti-CSRF value for the current server-side session;
- `expires_at`: the absolute server-side session expiry timestamp.

The endpoint uses the existing session-required path. If the cookie is missing, unknown, revoked or
expired, the response is a safe `401` error and no CSRF field is returned. The middleware classifies
all `/api/v1/session*` responses as sensitive and sets `Cache-Control: no-store`.

## Browser retention

The frontend still does not store session identifiers, CSRF values or OpenStack credentials in
`localStorage` or `sessionStorage`. On initial load it:

1. Reads `/api/v1/session`.
2. Reads `/api/v1/capabilities`.
3. Reads `/api/v1/session/csrf`.
4. Keeps the CSRF value only in React state.

If CSRF bootstrap fails after session and capabilities succeed, the UI remains authenticated with
`csrf=null`; mutating controls stay fail-closed because existing submit/export/group paths require a
non-null CSRF value before calling the BFF/API.

## Leakage and audit controls

The CSRF bootstrap endpoint does not return OpenStack tokens, application credentials, Vault auth
values, passwords, TLS private keys or service credentials. It also does not write the raw CSRF value
to audit metadata. Existing denial paths still record sanitized `session.required`,
`session.timeout`, `csrf.denied`, logout and revoke events.

Mutating requests are unchanged:

- backend endpoints still require the server-side session;
- CSRF verification still uses the `x-csrf-token` header;
- trusted `Origin` checks still run for state-changing security routes;
- backend authorization remains the enforcement point; frontend capabilities are UX only.

## Evidence

- `backend/tests/security/test_security_api.py`
  - `test_restored_session_can_bootstrap_csrf_without_secret_leakage`
  - `test_csrf_bootstrap_denies_request_without_session`
  - `test_csrf_bootstrap_denies_revoked_session`
- `frontend/src/App.test.tsx`
  - `restored session bootstraps csrf before submitting host precheck`

These tests prove restored-session mutation for the existing operation submit path, safe unauthenticated
and revoked-session denial, no raw CSRF in audit metadata, no OpenStack/Vault/password/private-key words
in the CSRF payload and no browser storage write.

## Residual gaps

- P0 sessions are still in-memory records; DB-backed encrypted session storage remains future work.
- Session key issue, rotation, revoke, cache TTL and break-glass ownership remain Vault/SecMan and
  deployment pipeline work.
- Keystone/IdP token lifetime alignment remains ADR-001/external IAM evidence.
- Host/root access to backend process memory and runtime config requires host hardening, PAM/FIM and
  E09/E12 evidence.
- Production mTLS/PKI, Kolla secret rotation and live Vault/SecMan ownership are not closed by this
  CSRF bootstrap slice.

## Rollback

Revert the E08.4 branch commit. No database schema, external service, queue, Vault path, Kolla
configuration or production secret is changed. After rollback, restored browser sessions return to the
previous fail-closed behavior with `csrf=null` after page reload.
