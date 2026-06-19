# PoC scope

- Stage: E00
- Status: proposed cutline pending owner review

## Delivery levels

| Level | Scope | Compliance position |
|---|---|---|
| P0 local functional PoC | Mock identity/OpenStack/SIEM, local DB/RabbitMQ, health, inventory, groups and mock workflow | Not DKB evidence |
| P1 integrated read-only PoC | Test identity/federation or equivalent, HTTPS, server-side session, RBAC, read model against test OpenStack, portal audit | Evidence for portal-scoped P1 controls only |
| P2 integrated mutating PoC | Allowlisted Mistral workflow in test project, idempotency, operation tracking, SIEM test delivery, redaction, negative authorization | Evidence for portal-scoped workflow/audit controls only |
| P3 production pilot | Kolla deployment, PKI/SIEM/Vault(SecMan)/registry/network/HA/storage evidence, load/failover/rollback, approved gaps | Requires E08-E12 and human approval |

## P0 cutline

Included:

- monorepo skeleton;
- two images: frontend/backend;
- local compose profile;
- mock auth;
- server-side sessions in local mode;
- mock Keystone/Nova/Placement/Mistral;
- read model for synthetic instances and hypervisors;
- group CRUD and dynamic preview;
- mock operation tracking;
- portal audit index and redaction tests.

Excluded:

- production credentials;
- real OpenStack mutation;
- production Kolla deployment;
- formal DKB compliance claim.

## P1 cutline

Included:

- test identity or federation flow;
- HTTPS in test;
- server-side session and session limit;
- backend RBAC and negative tests;
- real read-only OpenStack inventory against test project/cloud;
- no token in browser/log/audit;
- request/correlation ID;
- partial/stale indication;
- documented APIs and DKB evidence for portal-scoped controls.

Excluded:

- destructive OpenStack actions;
- full infrastructure audit;
- production PKI/SIEM/Vault(SecMan) claims.

## P2 cutline

Included:

- one allowlisted Mistral workflow in isolated test scope;
- `Idempotency-Key`;
- operation state machine and durable outbox;
- target snapshot from explicit/group selection;
- cancel/retry semantics only if definition allows;
- SIEM/test sink delivery;
- redaction canary tests;
- security review.

Proposed first workflow:

- `cloud_ui.test.maintenance_precheck.v1`
- Target: test project instance or host reference.
- External effects: Mistral execution and portal operation/audit only unless a test owner approves a harmless OpenStack mutation.
- Purpose: prove catalog/schema/auth/idempotency/status/audit before any risky operation.

This workflow remains proposed until E00/E06 owners approve exact target and external effect. Current test cloud does not expose Mistral, Watcher or Masakari in the service catalog, so E06 real workflow integration is blocked unless Mistral is enabled or the PoC uses a strict P0 mock/test substitute.

## Three primary user scenarios

1. Operator filters instances by project/status/host, opens an instance, sees linked hypervisor and freshness status.
2. Operator creates an explicit VM/host group, previews a safe dynamic rule and filters inventory by the group.
3. Operator launches an approved test workflow for selected target/group, receives `operation_id`, monitors state and confirms redacted audit event.

## Owners required before P1/P2

| Area | Needed decision/evidence |
|---|---|
| IAM/IdP | test identity/federation flow, session policy, MFA position |
| OpenStack admin | test project, read-only credentials, service catalog, microversions |
| Workflow owner | first allowlisted Mistral workflow and safe test target |
| Security owner | role matrix, DKB evidence review authority |
| SIEM owner | test sink protocol and retention expectations |
| Platform owner | Kolla/Rocky/container/runtime baseline |
