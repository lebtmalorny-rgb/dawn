# ADR-002: OpenStack client strategy

- Status: proposed
- Stage: E00
- Owner required: backend/OpenStack owner

## Context

FastAPI endpoints may be async. `openstacksdk` is generally synchronous and must not block the event loop directly. Raw REST clients increase maintenance cost and contract drift risk.

## Decision

Use typed adapter interfaces. Prefer `openstacksdk` behind a bounded thread pool for supported APIs unless a specific API requires an explicit `httpx` REST adapter. Every adapter must expose DTOs, typed errors, timeout, bounded concurrency, metrics, correlation ID and mock/contract tests.

## Blockers

- Target Python version unknown.
- Kolla base image unknown.
- Approved Nova/Placement microversions unknown.
- Test cloud availability unknown.

## Consequences

- Route handlers cannot call SDK directly.
- E03 creates deterministic mocks before real adapters.
- Any async REST exception must be justified by API contract and load evidence.

## Verification

- Adapter tests run without network.
- Event loop is not blocked by sync SDK calls.
- 401/403/404/409/429/5xx/timeout/malformed payload mapping tests.
- Optional read-only smoke against test cloud when available.
