# ADR-004: Workflow publication model

- Status: proposed
- Stage: E00
- Owner required: workflow/security owner

## Context

Portal must allow new task flows without arbitrary browser-supplied code, YAML, shell or workflow names. Mistral remains source of truth for long-running execution.

## Decision

Prefer GitOps publication for production: reviewed workflow definition, reviewed portal catalog definition, checksum/version registration, Mistral deployment, smoke test, feature flag enablement and audit evidence. P0/P1 may load definitions from repository/config.

## Blockers

- First P2 workflow not approved.
- Mistral test endpoint is present in the lab service catalog after the 2026-06-19 Kolla update, but least-privilege test credential, workflow contract and safe external effect are not approved.
- Approval and rollback owner unknown.
- Whether high-risk operations need four-eyes approval is unknown.

## Consequences

- Browser submits only `workflow_key`, version, targets and schema-validated input.
- Backend resolves Mistral workflow name server-side.
- Administrative workflow editing UI is out of PoC scope.

## Verification

- Arbitrary workflow name rejected.
- JSON Schema validation with `additionalProperties=false`.
- Idempotency tests for same/different body.
- Lost Mistral response lookup by correlation before retry.
