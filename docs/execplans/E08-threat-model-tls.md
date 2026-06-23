# ExecPlan: E08 Threat Model And TLS Matrix

## Цель и наблюдаемый результат

Команда получает воспроизводимое security evidence для E08.1/E08.2: структурированный threat model
по фактическому коду после E07/E08 Vault slice, расширенную TLS/mTLS матрицу для всех известных flows
и автоматический тест, который проверяет обязательные строки/поля matrix. До этого threat model был
только общим разделом в `docs/10_SECURITY_DKB.md`, а `docs/generated/tls-matrix.md` оставался draft с
неполным набором полей для owner, authorization, rotation и negative test.

## Контекст и текущее состояние

- Repository root: `/Users/dmitry/Desktop/dawn/.worktrees/e08-threat-model-tls`.
- Branch/worktree: `e08-threat-model-tls`.
- Base commit: `1f2a6e0 Merge pull request #2 from lebtmalorny-rgb/e08-vault-secman-design`.
- E07 audit уже в `main`; E08 Vault/SecMan slice смержен через PR #2.
- Existing evidence:
  - `docs/generated/tls-matrix.md` содержит draft flows и lab Kolla TLS observation для VIP
    `192.168.10.250`, но не все E08 поля.
  - `docs/10_SECURITY_DKB.md` содержит общий threat model и список high-risk ДКБ gaps.
  - `docs/generated/network-flow-matrix.md` содержит flow inventory, но не per-flow TLS/mTLS
    authorization/rotation/negative test details.
  - `docs/generated/risk-register.md` фиксирует R-041 mTLS scope unclear и другие E08 gaps.
  - `backend/src/cloud_ui/secrets/*` содержит Vault/SecMan boundary from previous slice.
- Baseline setup:
  - `make bootstrap PYTHON=/Users/dmitry/Desktop/dawn/.worktrees/e08-vault-secman-design/backend/.venv/bin/python`
    succeeded; npm warned that local Node `v25.9.0` is outside declared frontend engine `>=24 <25`.
  - `make lint`, `make typecheck`, `make security`, `make test` passed before implementation.

## Scope

- Create `docs/generated/e08-threat-model.md` with assets, trust boundaries, threats, controls,
  evidence links and high residual risks.
- Expand `docs/generated/tls-matrix.md` so every required flow has minimum TLS, mTLS decision,
  CA/source, server identity check, client identity/authorization, rotation owner, negative test,
  evidence and residual gap.
- Add backend pytest coverage that validates required TLS/mTLS flows and columns are present and
  that no required E08 flow is left with empty evidence/gap cells.
- Update `docs/generated/risk-register.md`, `docs/generated/network-flow-matrix.md` and
  `docs/11_DKB_TRACEABILITY.md` to reference the new threat/TLS evidence without claiming final
  compliance.

## Non-goals

- No remote SSH, Kolla reconfiguration, certificate issuance or live TLS scan without explicit
  approval.
- No production corporate PKI, SCEP/NDES, Vault/SecMan endpoint or SIEM credential.
- No claim that lab Kolla CA or matrix documentation closes ДКБ-22.02/24.
- No new runtime dependency.
- No container hardening, SBOM/signing or SELinux host validation in this slice.
- No frontend UX change.

## Требования и ограничения

- Browser must use only frontend/BFF/API; no direct OpenStack, Vault, SIEM, DB or RabbitMQ access.
- OpenStack tokens, Vault auth material, TLS private keys and credentials must not enter browser,
  logs, audit payloads, repo, image layers or generated evidence.
- TLS/mTLS claims require test scan or explicit pending evidence. Matrix-only rows must stay marked
  as planned/pending with owner and residual gap.
- ДКБ-69 interpreter conflict must not be hidden.
- External gaps must identify owner and compensating control.
- Tests must use static sanitized docs and must not depend on production OpenStack/Vault/SIEM.

## Связь с ДКБ

- ДКБ-22.02: this plan creates per-flow mTLS decision/evidence matrix and negative-test plan. Full
  closure remains external until corporate PKI, client cert auth and live rejection tests exist.
- ДКБ-23.02/24: this plan records CA/source, hostname verification and TLS >= 1.2 evidence/gaps.
  Existing lab Kolla TLS is lab evidence only.
- ДКБ-42-44/80: network boundaries and management/API zones are mapped as threat boundaries, but
  E09 owns Kolla/network ACL evidence.
- ДКБ-46-53: audit delivery threats and SIEM protected-channel gaps are mapped; E07 portal audit
  evidence remains local/contract.
- ДКБ-55/56: Vault/SecMan threats reference the previous adapter/runbook evidence, while production
  rotation remains external.
- ДКБ-65/69/70/76/77: container, supply-chain, SELinux and unused-interface risks are listed as
  residual E08/E09/E12 gaps, not closed.

## Milestones

1. Contract test first: add failing pytest that requires TLS matrix flows/columns and threat evidence
   sections.
2. Documentation implementation: create threat model evidence and expand TLS/mTLS matrix.
3. Traceability/risk updates: link evidence from DKB traceability, risk and network flow matrix.
4. Verification and review: run targeted docs tests, lint/typecheck/test/security and diff review.

## Progress

- [x] 2026-06-23: Baseline worktree created from merged `main` and verified before changes.
  Evidence: `make lint`, `make typecheck`, `make security`, `make test` passed; `make bootstrap`
  succeeded with Node engine warning for local Node `v25.9.0`.
- [x] 2026-06-23: Contract docs tests added. Evidence: RED
  `cd backend && .venv/bin/python -m pytest tests/security/test_e08_security_docs.py -q` failed
  because `docs/generated/e08-threat-model.md` was absent and `docs/generated/tls-matrix.md` lacked
  the required E08 columns.
- [x] 2026-06-23: Threat model and TLS matrix implemented. Evidence: GREEN
  `cd backend && .venv/bin/python -m pytest tests/security/test_e08_security_docs.py -q` passed
  `3 passed in 0.00s`.
- [x] 2026-06-23: Traceability/risk/network evidence updated. Evidence:
  `docs/11_DKB_TRACEABILITY.md`, `docs/generated/risk-register.md` and
  `docs/generated/network-flow-matrix.md` now reference `docs/generated/e08-threat-model.md` and
  the expanded `docs/generated/tls-matrix.md`.
- [x] 2026-06-23: Final verification and review completed. Evidence: initial `make lint` failed only
  on Ruff import ordering in `backend/tests/security/test_e08_security_docs.py`; after
  `.venv/bin/python -m ruff check tests/security/test_e08_security_docs.py --fix`, rerun
  `make lint` passed. `make typecheck` passed with mypy `Success: no issues found in 83 source files`
  and frontend `tsc -b`; `make test` passed backend `308 passed, 1 skipped in 3.49s` and frontend
  `34 passed`; `make test-integration` passed `21 passed, 1 skipped in 0.07s`; `make security`
  passed; `git diff --check` passed.

## Неожиданные открытия

- 2026-06-23: The host has no `python3.11` binary on PATH; bootstrap used the known Python 3.11.15
  interpreter from the previous E08 worktree only to create a new local `.venv`.
- 2026-06-23: Local Node is `v25.9.0`; frontend declares `>=24 <25`. Baseline gates pass, but release
  and CI should use Node 24.
- 2026-06-23: The existing `docs/generated/tls-matrix.md` first table lacked owner, authorization,
  rotation, negative-test and residual-gap columns, so a docs-contract test can catch regressions
  that a manual markdown review would likely miss.

## Журнал решений

- 2026-06-23: Split the next E08 work into a new branch after merging PR #2. Alternative: continue
  adding commits to the Vault PR branch. Reason: Vault/SecMan slice is already reviewed/merged and
  the threat/TLS slice has a separate evidence surface. Consequence: smaller PRs and clearer rollback.
- 2026-06-23: Add tests for generated security docs rather than relying only on manual review.
  Alternative: docs-only update. Reason: E08 DoD requires observable evidence and regression guards.
  Consequence: required matrix flows/columns become enforced by CI.

## Детальный план реализации

### Task 1: Docs Contract Tests

Create `backend/tests/security/test_e08_security_docs.py` with tests that:

- parse `docs/generated/tls-matrix.md`;
- assert required columns:
  `Flow`, `Minimum TLS`, `mTLS`, `CA/source`, `Server identity check`,
  `Client identity / authorization`, `Rotation owner`, `Negative test`, `Stage`, `Evidence`,
  `Residual gap`;
- assert required flows from `docs/10_SECURITY_DKB.md` are present:
  browser -> external VIP, HAProxy -> frontend, HAProxy -> API, API/worker -> Keystone/Nova/
  Placement/Mistral/Watcher/Masakari, portal -> MariaDB, portal -> RabbitMQ, audit worker -> SIEM,
  deploy/runtime -> Vault, deploy -> registry, and telemetry/Consul rows already introduced by E06;
- assert `docs/generated/e08-threat-model.md` contains sections for assets, trust boundaries, threats,
  mitigations/evidence and high residual risks;
- assert no actual secret canary text appears in generated E08 security docs except deliberate warning
  text, using existing `DKB_CANARY` scan convention.

Run targeted test before docs changes and expect failure because `e08-threat-model.md` is absent and
`tls-matrix.md` lacks required columns.

### Task 2: Threat Model Evidence

Create `docs/generated/e08-threat-model.md` with:

- assets from auth/session, OpenStack token handling, operations, groups, audit, read model, Vault,
  MariaDB/RabbitMQ, frontend bundle, runtime images and deployment pipeline;
- trust boundaries from browser to HAProxy/frontend/API, backend to OpenStack/Mistral/Watcher/
  Masakari, DB, RabbitMQ, SIEM, Vault, registry and Rocky/Kolla host;
- threats mapped to concrete mitigations and evidence paths:
  tests, config validators, redaction tests, audit outbox tests, Vault adapter tests, matrix rows,
  risk register entries;
- high residual risks with owner and compensating control: ДКБ-07, 22.02, 48, 50, 55/56, 65, 69, 72,
  77.

### Task 3: TLS/mTLS Matrix Expansion

Rewrite `docs/generated/tls-matrix.md` table with the required columns. Keep current lab observations,
but mark lab Kolla CA as non-production evidence. For rows without live evidence, set explicit
negative test plan and residual gap, not empty cells. Add owner/rotation language without inventing
external approvals.

### Task 4: Traceability And Risk Updates

Update:

- `docs/generated/risk-register.md`: R-041 should reference the expanded matrix and remaining live
  mTLS/corporate PKI evidence; add or update high residual threat entries if needed.
- `docs/generated/network-flow-matrix.md`: align security controls/evidence pointers with the expanded
  TLS matrix and threat model.
- `docs/11_DKB_TRACEABILITY.md`: add an E08 threat/TLS update section above the full matrix and keep
  production closure gaps explicit.

### Task 5: Verification, Review And Commit

Run:

```bash
cd backend && .venv/bin/python -m pytest tests/security/test_e08_security_docs.py -q
make lint
make typecheck
make test
make test-integration
make security
git diff --check
```

Review diff for overclaims, leaked secrets, missing owners/gaps and accidental scope creep. Update
this ExecPlan with command results and residual risks, then commit:

```bash
git add backend/tests/security/test_e08_security_docs.py docs/generated/e08-threat-model.md docs/generated/tls-matrix.md docs/generated/risk-register.md docs/generated/network-flow-matrix.md docs/11_DKB_TRACEABILITY.md docs/execplans/E08-threat-model-tls.md
git commit -m "docs: add E08 threat model and TLS matrix"
```

## Миграции и совместимость

No database, API or runtime migration. The change is additive documentation and tests only. Rolling
update is unaffected.

## Проверка

Baseline already passed before implementation:

- `make lint` passed.
- `make typecheck` passed.
- `make security` passed.
- `make test` passed backend `305 passed, 1 skipped` and frontend `34 passed`.

Required final verification is listed in Task 5. `make test-integration` may include existing skips
for optional live-smoke configuration only.

## Доказательства

- `backend/tests/security/test_e08_security_docs.py`.
- `docs/generated/e08-threat-model.md`.
- Expanded `docs/generated/tls-matrix.md`.
- Updated `docs/generated/risk-register.md`.
- Updated `docs/generated/network-flow-matrix.md`.
- Updated `docs/11_DKB_TRACEABILITY.md`.
- Command results recorded in this ExecPlan.

## Откат и восстановление

Revert the single commit from this branch. No external system, remote host, certificate, Vault state,
database or queue is changed.

## Итог и остаточные риски

The E08.1/E08.2 threat/TLS slice is implemented and locally verified. The branch adds a generated
threat model, expands the TLS/mTLS matrix with per-flow owner/authorization/rotation/negative-test
and residual-gap fields, and adds a pytest guard for the generated security docs. No remote host,
certificate, Kolla configuration, Vault state, SIEM endpoint, database or queue was changed.

Residual risks:

- corporate PKI/SCEP/NDES and live mTLS remain owner-provided;
- no remote Kolla/Vault/SIEM scan was performed without explicit approval;
- network ACL/firewall evidence remains E09;
- container hardening/SBOM/signing/SELinux evidence remains later E08 slices/E09;
- local verification used Node `v25.9.0`, outside the declared frontend engine `>=24 <25`; gates
  passed, but release/CI should use Node 24;
- DKB compliance remains subject to security owner review.
