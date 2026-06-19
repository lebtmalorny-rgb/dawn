# ADR-007: Scheduler and leader strategy

- Status: proposed
- Stage: E00
- Owner required: platform/backend owner

## Context

Periodic reconciliation and cleanup require coordination across replicas. Multiple active schedulers could duplicate work or overload OpenStack APIs.

## Decision

Prefer DB lease/advisory-lock pattern for portal-owned periodic jobs unless Mistral or an external scheduler is explicitly selected. Do not use etcd for portal business coordination without separate ADR and service account/TLS evidence.

## Blockers

- MariaDB version and advisory/lease capability unknown.
- Whether external scheduler exists is unknown.
- Periodic job volume unknown.

## Consequences

- E04 can implement chunked reconciliation with safe claiming.
- E10 must test failover and thundering herd behavior.
- Celery beat with multiple active instances is not allowed without coordination.

## Verification

- Only one active leader for scheduled job.
- Leader crash releases/reassigns safely.
- Duplicate job execution is idempotent.
