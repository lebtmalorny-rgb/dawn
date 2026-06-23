# ExecPlan: E08 DKB Gaps And Waivers

## Цель и наблюдаемый результат

После E08.7 команда получает проверяемый draft gap/waiver register для требований ДКБ, которые портал
и локальный hardening не могут закрыть самостоятельно. Наблюдаемое поведение: security reviewer может
открыть `docs/generated/e08-dkb-gaps-waivers.md` и для каждого обязательного gap увидеть причину,
компенсирующие меры, owner role, review/expiry, evidence для закрытия и release gate. До этого этапа
такие gaps были распределены по risk register, traceability и отдельным E08 evidence-файлам, но не
имели единого проверяемого waiver-ready представления.

## Контекст и текущее состояние

- `tasks/E08_HARDENING.md` требует E08.7 draft gaps для ДКБ-07, 22.02, 48, 50, 55, 56, 65, 69, 72
  и других external requirements.
- `docs/10_SECURITY_DKB.md` прямо перечисляет high-risk gaps и запрещает считать formal waiver
  выполненным без внешнего approval.
- `docs/11_DKB_TRACEABILITY.md` уже содержит E08.1-E08.6 updates и полную матрицу требований.
- `docs/generated/risk-register.md` содержит риски R-040-R-045, R-047-R-049 and R-053, но не является
  waiver register.
- `backend/tests/security/test_e08_security_docs.py` and `test_e08_supply_chain.py` уже проверяют
  generated E08 evidence, поэтому E08.7 должен следовать тому же docs-contract pattern.

## Scope

- Create `docs/generated/e08-dkb-gaps-waivers.md` with one table of required DKB gaps.
- Add `backend/tests/security/test_e08_dkb_gaps.py` to enforce required codes and required fields.
- Update `docs/generated/risk-register.md` to point to the new consolidated register.
- Update `docs/11_DKB_TRACEABILITY.md` with E08.7 evidence and residual conditions.
- Keep the register as draft/security-owner input, not as approval.

## Non-goals

- No formal risk acceptance, compliance sign-off or production waiver approval.
- No live IAM, PKI, SIEM, Vault/SecMan, SELinux, storage, registry or Kolla deployment validation.
- No changes to runtime authorization, session, audit delivery, images, network or deployment code.
- No claim that ДКБ-69 is closed for Python backend or OpenStack Python services.

## Требования и ограничения

- Browser still calls only frontend/BFF; this docs-only slice must not add direct OpenStack browser
  access.
- No secrets, production endpoints, real cloud credentials or private keys may be committed.
- Each external gap must have reason, compensating controls, owner and review/expiry.
- Any authorization, session, workflow, audit, secrets or deployment compliance status change must be
  reflected in `docs/11_DKB_TRACEABILITY.md`. This slice changes compliance evidence documentation only.
- DKB-69 interpreter/shell conflict must remain explicit and must not be masked by E08.5/E08.6 local
  container evidence.

## Связь с ДКБ

| Код | Что реализует план | Что остается во внешнем контуре | Доказательство | Почему не закрыто полностью |
|---|---|---|---|---|
| ДКБ-07 | Draft service-account exception with non-interactive controls. | IAM/PAM owner approval, personal admin account enforcement and service-account review. | Gap register row + risk register reference. | Kolla/OpenStack service accounts remain necessary. |
| ДКБ-22.02 | Per-flow TLS/mTLS gaps get owner/review gate. | Corporate PKI, mTLS identity, negative cert tests. | Gap register row + existing TLS matrix. | Lab/docs evidence does not prove production PKI. |
| ДКБ-48 | Portal audit heartbeat/outbox gaps are tied to missing external monitoring controls. | FIM/auditd/IaC and missing-flow SIEM alerts. | Gap register row + E07 audit evidence. | Portal cannot prevent root from disabling host logging. |
| ДКБ-50 | Full audit source map gaps become waiver-ready. | Keystone/OpenStack, host, storage, IdP and SIEM source owner evidence. | Gap register row + audit source map. | Portal audit is only one source. |
| ДКБ-55 | Vault/SecMan portal contract gaps get production owner/gate. | Production SecMan endpoint/auth/mTLS/HA/backup approval. | Gap register row + Vault runbook/policy. | Adapter contract is not production SecMan acceptance. |
| ДКБ-56 | All-secret lifecycle gaps are consolidated. | Kolla, DB, RabbitMQ, OpenStack service secret rotation pipeline. | Gap register row + secret inventory. | Full rotation requires deployment pipeline and owner evidence. |
| ДКБ-65 | SELinux/AppArmor host evidence gap is explicit. | Rocky/Kolla SELinux enforcing labels and denial tests. | Gap register row + container hardening evidence. | Compose hardening does not prove host policy. |
| ДКБ-69 | Formal waiver for Python/interpreter conflict is required. | Approved exception and image allowlist/scanner evidence. | Gap register row + supply-chain/container evidence. | Python backend requires interpreter. |
| ДКБ-72 | Storage architecture gap is owner-scoped. | Nova/Cinder/Ceph/storage path proof and local-disk prohibition. | Gap register row + traceability reference. | Portal UI cannot prove hypervisor storage paths. |

## Milestones

1. Baseline and plan: bootstrap/test existing worktree and create this ExecPlan.
2. Contract: write failing pytest that requires mandatory DKB rows and fields.
3. Evidence: add the generated gap/waiver register and update risk/traceability docs.
4. Verification: run targeted security docs tests, lint, typecheck, full test, integration/security as relevant.
5. Review and commit: inspect diff for overclaim, leaked secret markers and missing owners.

## Progress

- [x] 2026-06-23: Исследование фактического состояния. Evidence: `make bootstrap`, `make lint`,
  `make typecheck`, `make test` passed on the new worktree before edits.
- [x] 2026-06-23: Контракт и тестовый double. Evidence: initial
  `cd backend && .venv/bin/python -m pytest tests/security/test_e08_dkb_gaps.py -q` failed with
  missing `docs/generated/e08-dkb-gaps-waivers.md`.
- [x] 2026-06-23: Минимальная реализация. Evidence: added
  `docs/generated/e08-dkb-gaps-waivers.md` and the same targeted command passed `3 passed`.
- [x] 2026-06-23: Отрицательные сценарии и безопасность. Evidence: test rejects forbidden
  `closed`/`compliant`/`approved` gap statuses and asserts ДКБ-69 remains a formal Python interpreter
  waiver, not closed.
- [x] 2026-06-23: Интеграционные и пользовательские проверки. Evidence: `make test-integration`
  passed `21 passed, 1 skipped`; this docs-only slice has no browser workflow change.
- [x] 2026-06-23: Документация, evidence и review. Evidence: `make lint`, `make typecheck`,
  `make test`, `make security` and `git diff --check` passed after documentation updates.

## Неожиданные открытия

- 2026-06-23: `apply_patch` without a worktree-prefixed path targeted the main checkout instead of
  the new worktree. Evidence: `git status --short --branch` showed untracked files in main and only
  bootstrap metadata in the worktree. The misplaced untracked files were removed from main and
  re-added under `.worktrees/e08-dkb-gaps-waivers/` before any commit.

## Журнал решений

- 2026-06-23: Use a generated Markdown register plus pytest contract, not a YAML generator.
  Alternatives: traceability-only update or structured YAML/JSON source. Reason: E08.7 needs one
  human-reviewable waiver draft and a regression guard without new generation infrastructure.
- 2026-06-23: Use owner roles, not personal names. Reason: repository cannot invent external owner
  assignments; final acceptance must come from the organization.
- 2026-06-23: Use review/expiry date `2026-09-30` for all draft gaps. Reason: it is a concrete
  short review window before P3/pilot, not a silent indefinite exception.

## Детальный план реализации

1. Create `backend/tests/security/test_e08_dkb_gaps.py`:
   - parse the first Markdown table in `docs/generated/e08-dkb-gaps-waivers.md`;
   - assert required columns: `DKB code`, `Gap status`, `Reason`, `Existing portal evidence`,
     `Compensating controls`, `Owner role`, `Review/expiry`, `Evidence required to close`,
     `Release gate`;
   - assert required rows for ДКБ-07, 22.02, 48, 50, 55, 56, 65, 69, 72;
   - assert required fields are non-empty;
   - assert ДКБ-69 row contains `formal waiver`, `Python` and `not closed`;
   - assert no row uses forbidden overclaim statuses such as `closed`, `compliant` or `approved`.
2. Run the new test and confirm it fails because the evidence file is missing.
3. Create `docs/generated/e08-dkb-gaps-waivers.md` with required rows, owner roles and review/expiry.
4. Update `docs/generated/risk-register.md` stage/last updated and external/security risks to reference
   the consolidated register.
5. Update `docs/11_DKB_TRACEABILITY.md` with an E08.7 section above the full matrix.
6. Re-run targeted tests and then the project gates.

## Миграции и совместимость

No database, API, OpenAPI, frontend or deployment runtime changes are introduced. Rolling update
compatibility is unaffected. Re-running the docs update is idempotent because it rewrites static
Markdown evidence only.

## Проверка

Run from `/Users/dmitry/Desktop/dawn/.worktrees/e08-dkb-gaps-waivers`:

- `make bootstrap PYTHON=/Users/dmitry/Desktop/dawn/backend/.venv/bin/python`
- `make lint`
- `make typecheck`
- `make test`
- `cd backend && .venv/bin/python -m pytest tests/security/test_e08_dkb_gaps.py -q`
- `cd backend && .venv/bin/python -m pytest tests/security/test_e08_security_docs.py tests/security/test_e08_supply_chain.py tests/security/test_e08_container_hardening.py tests/security/test_e08_dkb_gaps.py -q`
- `make test-integration`
- `make security`
- `git diff --check`

Expected result: all commands exit 0 after implementation. The first targeted run before evidence
creation must fail because `docs/generated/e08-dkb-gaps-waivers.md` does not exist.

## Доказательства

- `backend/tests/security/test_e08_dkb_gaps.py`
- `docs/generated/e08-dkb-gaps-waivers.md`
- `docs/generated/risk-register.md`
- `docs/11_DKB_TRACEABILITY.md`
- This ExecPlan

## Откат и восстановление

Rollback is a documentation/test revert: revert the commit or remove the new test/evidence file and
restore `docs/generated/risk-register.md`, `docs/11_DKB_TRACEABILITY.md` and this ExecPlan to the
previous commit. No runtime state, database schema, image or external service cleanup is required.

## Итог и остаточные риски

Implemented E08.7 as a docs-contract slice. The branch adds a generated gap/waiver draft with owner
roles and concrete review/expiry dates, regression tests for mandatory rows and no-overclaim statuses,
and updates risk/traceability docs.

Residual risks remain external: no IAM/PAM service-account approval, no corporate PKI/mTLS evidence,
no full SIEM source onboarding, no production SecMan acceptance or all-secret rotation, no Rocky
SELinux host proof, no formal ДКБ-69 Python interpreter waiver, no corporate registry/signing proof,
no storage path proof and no network-zone/unused-interface blocking evidence.
