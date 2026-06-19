# ADR-005: Session concurrency policy

- Status: proposed-default
- Stage: E00
- Owner required: security owner

## Context

ДКБ-20 requires limiting parallel access sessions. Policy must be explicit and testable.

## Decision

Default proposed policy: `deny` new login when simultaneous UI session limit is reached. Idle timeout default is 900 seconds. Absolute lifetime remains owner decision. Admin revoke is required.

## Open decision

Security owner may replace `deny` with `disconnect_oldest` before E02 if operationally preferred.

## Consequences

- E02 must make policy configurable.
- Session limit event is audited.
- CLI/OpenStack token sessions remain outside portal session registry and require IdP/Keystone policy.

## Verification

- Login denied or oldest disconnected according to configured policy.
- Idle timeout and revoke tests.
- Session rotation after login/elevation.
- Audit events for login/logout/timeout/revoke/session-limit.
