# ADR-008: Audit sink

- Status: proposed
- Stage: E00
- Owner required: SIEM/security owner

## Context

Portal stores operational audit projection, but authoritative long-term audit must be external SIEM or equivalent protected audit system.

## Decision

Implement audit sink interface and test sink first. Production SIEM protocol, field mapping, retention, auth, TLS/mTLS and heartbeat are owner-provided before E07/E08 integration claims.

## Blockers

- SIEM product/API/protocol unknown.
- Retention and field classification unknown.
- Search integration unknown.
- Delivery acknowledgement model unknown.

## Consequences

- Portal audit table is not claimed immutable SIEM.
- Delivery failure must create durable backlog and alert.
- Direct SIEM index/broker access by users is not acceptable application access.

## Verification

- Mandatory field schema tests.
- Redaction canary tests across all sinks.
- Delivery success/failure/retry/dead-letter tests.
- Heartbeat and audit access tests.
