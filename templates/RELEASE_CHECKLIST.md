# Release checklist

## Идентификация

- [ ] Git commit/tag указан.
- [ ] Frontend/backend image digest указан.
- [ ] Schema/workflow/config versions указаны.
- [ ] Release notes и known issues готовы.

## Качество

- [ ] Format/lint/typecheck.
- [ ] Unit/component/contract tests.
- [ ] Integration/E2E.
- [ ] OpenAPI compatibility.
- [ ] Migration/rollback test.
- [ ] Load/failover для P3.

## Security

- [ ] Secret scan.
- [ ] Dependency/image scan.
- [ ] SBOM связан с digest.
- [ ] Security review без unresolved critical/high.
- [ ] Session/RBAC/CSRF negative tests.
- [ ] Redaction and audit delivery.
- [ ] TLS/mTLS evidence.
- [ ] SELinux/container inspection.
- [ ] DKB delta/gaps updated.

## Deployment

- [ ] Images в approved registry.
- [ ] Kolla config reviewed.
- [ ] Migration one-shot.
- [ ] Rolling update tested.
- [ ] Rollback tested.
- [ ] Backup/precheck.
- [ ] Monitoring/alerts.
- [ ] Runbook verified on clean test environment.

## Approval

- Product owner:
- Operations:
- Security:
- DKB/compliance authority:
- Decision/date:
