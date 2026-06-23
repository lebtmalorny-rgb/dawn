# ExecPlan: E08 Security Review

## Цель и наблюдаемый результат

После E08.8 команда получает воспроизводимый security review report для E08 hardening candidate.
Наблюдаемое поведение: reviewer может открыть `docs/generated/e08-security-review.md` и увидеть scope,
проверенные угрозы из `templates/SECURITY_REVIEW_TEMPLATE.md`, evidence links, findings, external
gaps and a release decision. До этого E08 имел отдельные evidence-файлы по threat model, Vault,
session protection, container hardening, supply chain and gaps, но не имел единого review decision.

## Контекст и текущее состояние

- `tasks/E08_HARDENING.md` требует E08.8 security review через
  `templates/SECURITY_REVIEW_TEMPLATE.md` and says critical/high findings must be fixed or block
  release.
- `docs/generated/e08-dkb-gaps-waivers.md` already records external gaps and formal waiver drafts.
- Current `main` is commit `6983fbb docs: add E08 DKB gap waiver register`.
- Baseline in this worktree passed `make bootstrap`, `make lint`, `make typecheck` and `make test`
  before E08.8 edits.

## Scope

- Add `backend/tests/security/test_e08_security_review.py` contract for the generated review report.
- Add `docs/generated/e08-security-review.md` following the repository template.
- Update `docs/11_DKB_TRACEABILITY.md` with E08.8 evidence.
- Update `docs/generated/risk-register.md` if review decision adds or clarifies residual risk.
- Record findings and decision without claiming formal compliance approval.

## Non-goals

- No production compliance approval or human security-owner sign-off.
- No live corporate PKI, SIEM, SecMan, SELinux, registry, storage or network validation.
- No runtime code change unless the review finds a concrete critical/high defect that can be fixed in
  this slice.
- No start of E09 Kolla/deployment work.

## Требования и ограничения

- Use the template headings and threat categories from `templates/SECURITY_REVIEW_TEMPLATE.md`.
- Critical/high findings either must be fixed in this branch or the review decision must be `Blocked`.
- DKB-69 Python interpreter/shell conflict remains explicit and cannot be marked closed.
- The report must not contain secrets, production URLs with credentials, tokens, private keys or real
  cloud configuration.
- This docs-only review does not change API, database schema or rolling-update behavior.

## Связь с ДКБ

| Код | Что реализует этот план | Что остается внешним | Доказательство | Почему не закрыто полностью |
|---|---|---|---|---|
| ДКБ-07 | Review verifies service-account gap is explicit. | IAM/PAM approval and service-account policy. | Security review report and gap register. | Portal cannot eliminate OpenStack/Kolla service accounts. |
| ДКБ-13/51 | Review verifies secret/token leakage evidence and redaction tests. | Host/root and external SIEM redaction controls. | Security review report and existing tests. | Production logs/SIEM are external. |
| ДКБ-22.02/24/25 | Review verifies TLS/mTLS matrix and external PKI gaps. | Corporate PKI/mTLS scan and owner acceptance. | Security review report and TLS matrix. | Lab/docs evidence is not production PKI evidence. |
| ДКБ-46-53 | Review verifies portal audit evidence and external source gaps. | Full SIEM source onboarding and retention. | Security review report and audit source map. | Portal audit is not full platform audit. |
| ДКБ-55/56 | Review verifies Vault/SecMan evidence and all-secret lifecycle gaps. | Production SecMan, HA, backup and rotation. | Security review report and secret inventory. | Adapter contract is not production acceptance. |
| ДКБ-65/69/70/76/77/80 | Review verifies container/supply-chain/network gaps. | SELinux host proof, formal ДКБ-69 waiver, registry/signing and network blocking. | Security review report, hardening and SBOM evidence. | E09/E12 external evidence remains required. |

## Milestones

1. Baseline and plan.
2. RED contract for generated security review.
3. Review evidence: inspect docs/tests/config and write report.
4. Verification: targeted test, E08 security docs tests, lint, typecheck, full tests, integration,
   security scan and diff checks.
5. Diff review, commit and integration handling.

## Progress

- [x] 2026-06-23: Исследование фактического состояния. Evidence: `make bootstrap`, `make lint`,
  `make typecheck`, `make test` passed before E08.8 edits.
- [x] 2026-06-23: Контракт и тестовый double. Evidence:
  `cd backend && .venv/bin/python -m pytest tests/security/test_e08_security_review.py -q` failed
  with missing `docs/generated/e08-security-review.md`.
- [x] 2026-06-23: Минимальная реализация. Evidence: added
  `docs/generated/e08-security-review.md`; targeted test passed `3 passed`.
- [x] 2026-06-23: Отрицательные сценарии и безопасность. Evidence: review test rejects overclaim
  phrases, requires `Unresolved critical/high findings: 0`, ДКБ-69 `not closed`, and external gaps.
- [x] 2026-06-23: Интеграционные и пользовательские проверки. Evidence: `make test` passed backend
  `326 passed, 1 skipped` and frontend `35 passed`; `make test-integration` passed
  `21 passed, 1 skipped`.
- [x] 2026-06-23: Документация, evidence и review. Evidence: E08.8 report, risk register and
  traceability were updated; `make lint`, `make typecheck`, `make security` and `git diff --check`
  passed.

## Неожиданные открытия

- 2026-06-23: The review found no unresolved portal-owned Critical/High defect for P2 scope, but
  several high-impact production controls remain external conditions. Evidence:
  `docs/generated/e08-security-review.md`.

## Журнал решений

- 2026-06-23: Generate a Markdown review report plus pytest contract. Alternatives: untested report
  only, or a machine-readable YAML registry. Reason: E08.8 needs human-readable evidence and a
  regression guard without adding a new generator.
- 2026-06-23: Use `Approved with conditions` only if no unresolved critical/high finding is found.
  Reason: E08 still has external gaps and cannot be marked fully approved/compliant by Codex.

## Детальный план реализации

1. Add `backend/tests/security/test_e08_security_review.py`.
2. Run it and confirm RED because `docs/generated/e08-security-review.md` is missing.
3. Review E08 evidence: `docs/generated/e08-threat-model.md`, `tls-matrix.md`,
   `e08-vault-*`, `e08-session-token-protection.md`, `e08-container-hardening.md`,
   `e08-supply-chain.md`, `e08-dkb-gaps-waivers.md`, `risk-register.md`, relevant security tests,
   Dockerfiles, `compose.yaml`, `Makefile` and `scripts/generate-sbom.sh`.
4. Add `docs/generated/e08-security-review.md` using the template categories and explicit findings.
5. Update traceability/risk register if the review decision adds evidence or clarifies residual risk.
6. Run all verification commands and update this ExecPlan with actual results.

## Миграции и совместимость

No database, OpenAPI, frontend runtime or deployment runtime changes are planned. Rolling update
compatibility is unaffected. Rollback is a documentation/test revert.

## Проверка

Run from `/Users/dmitry/Desktop/dawn/.worktrees/e08-security-review`:

- `cd backend && .venv/bin/python -m pytest tests/security/test_e08_security_review.py -q`
- `cd backend && .venv/bin/python -m pytest tests/security/test_e08_security_review.py tests/security/test_e08_security_docs.py tests/security/test_e08_supply_chain.py tests/security/test_e08_container_hardening.py tests/security/test_e08_dkb_gaps.py -q`
- `make lint`
- `make typecheck`
- `make test`
- `make test-integration`
- `make security`
- `git diff --check`

Expected final result: all commands exit 0. Initial targeted test must fail before report creation.

## Доказательства

- `backend/tests/security/test_e08_security_review.py`
- `docs/generated/e08-security-review.md`
- `docs/11_DKB_TRACEABILITY.md`
- `docs/generated/risk-register.md` if updated
- This ExecPlan

## Откат и восстановление

Revert the E08.8 commit or remove the new review test/report and restore traceability/risk files to
the previous commit. No runtime cleanup is required.

## Итог и остаточные риски

Implemented E08.8 as a tested security review evidence slice. The generated review follows the
template categories, records `Unresolved critical/high findings: 0` for the reviewed portal-owned
local scope, and sets the decision to `Approved with conditions`.

Residual risks remain external and must not be treated as closed: IAM/PAM service-account exception,
corporate PKI/mTLS, production SIEM source onboarding and retention, production SecMan and all-secret
rotation, Rocky SELinux proof, formal ДКБ-69 Python interpreter waiver, corporate registry/signing,
storage path proof and management-zone/unused-interface blocking evidence.
