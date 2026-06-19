# ADR-001: Authentication and federation flow

- Status: proposed
- Stage: E00
- Owner required: IAM/OpenStack security owner

## Context

Production flow must use corporate IdP and Keystone federation or an approved equivalent. Browser receives only an opaque portal session cookie. P0 may use deterministic mock identity, but production config must hard-disable it.

## Decision

Use server-side portal sessions backed by Keystone-scoped identity context. Human identity source is corporate IdP. Keystone and OpenStack service policies remain final authorization for OpenStack operations.

## Blockers

- IdP product/protocol unknown.
- Keystone federation mapping unknown.
- MFA/session lifetime policy unknown.
- Logout/callback behavior unknown.
- Session token encryption key lifecycle pending ADR-009.

## Consequences

- E02 may implement mock provider and interface first.
- P1 cannot claim integrated identity until test federation/equivalent flow is verified.
- No shared service-admin credential may execute user actions without separate delegation/impersonation ADR.

## Verification

- Login success/failure tests.
- Token absent from browser/storage/log/audit.
- Backend 403 for direct unauthorized request.
- Portal allow plus simulated OpenStack deny remains denied.
