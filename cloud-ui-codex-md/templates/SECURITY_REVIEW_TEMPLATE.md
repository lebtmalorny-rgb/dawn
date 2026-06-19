# Security review: <изменение/этап>

- Дата:
- Commit/image digest:
- Reviewer:
- Scope:
- Связанный ExecPlan:
- DKB codes:

## Архитектурное изменение

Кратко опишите новые data flows, trust boundaries, assets и privileges.

## Проверенные угрозы

| Угроза | Finding | Severity | Evidence | Решение |
|---|---|---|---|---|
| Auth bypass/IDOR | | | | |
| Session/CSRF/XSS | | | | |
| Secret/token leakage | | | | |
| Injection/SSRF | | | | |
| Workflow/code execution | | | | |
| Retry/idempotency | | | | |
| Audit tampering/loss | | | | |
| Container/host boundary | | | | |
| Supply chain | | | | |
| Availability/DoS | | | | |

## Findings

### <ID> <Severity> — <название>

- Путь/строка:
- Условие:
- Влияние:
- Доказательство:
- Исправление:
- Статус:
- Residual risk:

## Проверки

- [ ] Negative RBAC/IDOR.
- [ ] CSRF/session.
- [ ] Canary secret redaction.
- [ ] No credentials in browser/image/log.
- [ ] Workflow allowlist/schema.
- [ ] Retry/idempotency/lost response.
- [ ] Audit delivery/heartbeat.
- [ ] Dependency/image scan.
- [ ] SELinux/container privileges при применимости.
- [ ] DKB traceability updated.

## External controls/gaps

Что не закрывается кодом портала и кто владелец.

## Решение review

Approved / approved with conditions / blocked.

Codex не является уполномоченным лицом для финального compliance approval.
