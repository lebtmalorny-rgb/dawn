# ADR-003: Notification and reconciliation strategy

- Status: proposed
- Stage: E00
- Owner required: OpenStack messaging owner

## Context

Read model freshness can be accelerated by OpenStack notifications, but event ordering, transport permissions and payload stability are unknown. Polling/reconciliation remains required.

## Decision

Use reconciliation as correctness authority and notifications as acceleration. Event consumer may consume only approved notification transport or portal-owned exchange. Direct wildcard consumption of OpenStack RPC queues is forbidden.

## Blockers

- Enabled notifications unknown.
- Notification exchange/transport unknown.
- Payload versions unknown.
- Permissions model unknown.
- Freshness target unknown.
- Mistral, Watcher and Masakari are now present in the test service catalog; notification transport and payload assumptions remain blocked until verified.

## Consequences

- E04 can start with full sync and targeted refresh.
- Synthetic events are allowed for P0.
- Real notification binding requires security review and transport evidence.

## Verification

- Duplicate/out-of-order/drop event tests.
- Reconciliation repairs missed event.
- Consumer restart resumes cursor/offset safely.
- Event payload contains no secrets.
