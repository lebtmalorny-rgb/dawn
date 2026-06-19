# ADR-009: Vault (SecMan) integration

- Status: proposed
- Stage: E00
- Owner required: Vault/platform owner

## Context

ДКБ-55/56 require secret management and rotation. SecMan is HashiCorp Vault in this environment. Barbican/Vault does not automatically cover all Kolla/service/deployment secrets.

## Decision

Separate OpenStack key manager concerns from deployment/application secret lifecycle. Portal implements a Vault interface and test adapter; production integration requires approved auth method, secret classes, injection, rotation, revoke and audit procedure.

## Blockers

- Vault endpoint, auth method, namespace/path policy and audit integration are unknown.
- Secret classes and owners not fully approved.
- Kolla/Ansible secret rotation process unknown.

## Consequences

- No real Vault token in Git/image/env file.
- E08 must create lifecycle inventory and rotation runbook.
- ДКБ-56 remains gap until all secret classes are covered.

## Verification

- Secret lookup contract test with dummy values.
- Retry/redaction tests.
- No token/secret in browser/log/message/image layers.
- Rotation runbook evidence before P3.
