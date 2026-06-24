# ExecPlan: E09.2 Kolla-Ansible role skeleton

## Цель и наблюдаемый результат

E09.2 добавляет проверяемый repository-side Kolla-Ansible role skeleton для Cloud UI. После изменения
оператор увидит `deploy/kolla/ansible/roles/cloud_ui` with defaults, validation tasks, config
templates, handler names and container definition data for `cloud_ui_frontend`, `cloud_ui_api`,
`cloud_ui_worker` and `cloud_ui_events`.

До изменения в репозитории есть E09.1 Kolla Build artifacts under `deploy/kolla/`, but no Cloud UI
Kolla-Ansible role structure or tests for the role skeleton.

## Контекст и текущее состояние

- Рабочая ветка: `e09-ansible-role-skeleton`.
- Worktree: `/Users/dmitry/Desktop/dawn/.worktrees/e09-ansible-role-skeleton`.
- Base commit: `a8ce44a docs: record E09 final verification`.
- E09.1 already created:
  - `deploy/kolla/kolla-build.conf.example`;
  - `deploy/kolla/docker/cloud-ui-backend/Dockerfile.j2`;
  - `deploy/kolla/docker/cloud-ui-frontend/Dockerfile.j2`;
  - `deploy/kolla/scripts/build-images.sh`;
  - `tests/test_e09_kolla_image_build.py`;
  - `docs/generated/e09-kolla-image-build.md`.
- `deploy/AGENTS.md` requires test inventory only, no production hostnames or credentials, and no
  weakening of SELinux, TLS, firewall or container permissions.
- Bootstrap for this worktree completed with
  `make bootstrap PYTHON=/Users/dmitry/Desktop/dawn/backend/.venv/bin/python`; npm reported 0
  vulnerabilities and an EBADENGINE warning because local Node is `v25.9.0` while the frontend expects
  `>=24 <25`.
- Baseline targeted checks:
  - `backend/.venv/bin/python -m pytest tests/test_e09_kolla_image_build.py -q` -> 6 passed.
  - `bash -n deploy/kolla/scripts/build-images.sh` -> passed.

## Scope

Included in E09.2:

- create `deploy/kolla/ansible/roles/cloud_ui`;
- add defaults for enable flags, image names, digest/tag placeholders, service groups, ports, config
  paths and container hardening dimensions;
- add validation, config and container-definition task files;
- add non-secret backend/frontend config templates;
- add handler names without live restart implementation;
- add static contract tests;
- add generated E09.2 evidence, risk register update and DKB traceability update.

## Non-goals

- No Kolla-Ansible execution against hosts.
- No test or production inventory.
- No registry push, digest, SBOM, vulnerability scan or image signature.
- No DB/RabbitMQ provisioning.
- No migration job execution.
- No HAProxy/TLS configuration.
- No SELinux host proof.
- No live 12-container proof.
- No rolling update or rollback execution.
- No production action.

## Требования и ограничения

- Preserve exactly two portal-owned images: `cloud-ui-frontend` and `cloud-ui-backend`.
- API, worker and events must use the same backend image with different commands.
- Do not use `latest`.
- Do not store `clouds.yaml`, openrc, `.env`, tokens, private keys, cookies, DB dumps, registry
  credentials or production URLs.
- Role files must not claim DB/MQ, migration, HAProxy/TLS, SELinux, rollback or live deployment proof.
- Runtime secrets, Vault/SecMan integration and rotation remain later E09 work.
- The browser trust boundary, BFF/API boundary, server-side sessions and workflow allowlist do not
  change in this slice.

## Связь с ДКБ

- ДКБ-22.02/23.02/24: this plan creates no TLS/mTLS runtime configuration. Evidence remains external
  to E09.6 and later test-stand scans.
- ДКБ-42-44/76/77/80: this plan describes role placement and container interfaces, but does not prove
  runtime network ACLs, disabled unused interfaces or management-zone placement.
- ДКБ-55/56: this plan stores no runtime secret values. Vault/SecMan references, DB/MQ credentials and
  rotation evidence remain E09.3+.
- ДКБ-65: this plan keeps container hardening dimensions in defaults, but SELinux label evidence
  requires Rocky/Kolla host inspection.
- ДКБ-69/70: this plan preserves two image names and forbids `latest`; full closure still requires
  registry digest, SBOM, scanner, signing and formal Python interpreter waiver evidence.
- ДКБ-82: rollback remains later E09.7 evidence; this plan only records rollback-by-git for repository
  artifacts.

## Milestones

1. RED contract test exists and fails because E09.2 role files are absent.
2. Minimal role skeleton makes structural role assertions pass while evidence remains absent.
3. Generated evidence, risk register and DKB traceability make E09.2 contract tests pass.
4. Full relevant gates and review pass; residual external evidence remains explicit.

## Progress

- [x] 2026-06-24: AGENTS.md, tasks/E09_KOLLA_DEPLOY.md, docs/12_DEPLOY_ROCKY_KOLLA.md,
  docs/09_PERFORMANCE_HA.md, docs/10_SECURITY_DKB.md, docs/generated/e08-security-review.md and
  deploy/AGENTS.md read.
- [x] 2026-06-24: Existing `deploy/kolla` and root E09.1 tests inspected.
- [x] 2026-06-24: E09.2 design approved and committed in
  `docs/superpowers/specs/2026-06-24-e09-ansible-role-skeleton-design.md`.
- [x] 2026-06-24: Worktree bootstrapped. Baseline targeted E09.1 test and shell syntax checks passed.
- [ ] Contract and RED tests.
- [ ] Minimal role skeleton.
- [ ] Evidence, DKB traceability and risk register.
- [ ] Final verification and review.

## Неожиданные открытия

- New worktrees do not contain `backend/.venv` or `frontend/node_modules`; bootstrap is required before
  running tests in the isolated workspace.
- `make bootstrap` succeeds in the worktree, but local Node version is newer than the frontend
  package engine range. This is a warning only in the current environment and did not block bootstrap.

## Журнал решений

- 2026-06-24: Scope E09.2 to repository-side role skeleton only. Alternatives were full role plus live
  single-node smoke or generic scaffold. Chosen because test inventory, image digests and deployment
  secrets are not available, and a generic scaffold would not prove Cloud UI invariants.
- 2026-06-24: Use role path `deploy/kolla/ansible/roles/cloud_ui`. Reason: it keeps deployment
  artifacts colocated with E09.1 Kolla Build files without introducing a production inventory.
- 2026-06-24: Use static contract tests instead of Ansible execution. Reason: E09.2 must be
  reproducible without a test stand and must not imply live deploy evidence.

## Детальный план реализации

The detailed TDD implementation plan is
`docs/superpowers/plans/2026-06-24-e09-ansible-role-skeleton.md`.

Implementation order:

1. Add `tests/test_e09_kolla_ansible_role.py` and verify RED failure.
2. Add `deploy/kolla/ansible/README.md`.
3. Add `deploy/kolla/ansible/roles/cloud_ui/defaults/main.yml`.
4. Add task files: `main.yml`, `validate.yml`, `config.yml`, `containers.yml`.
5. Add `handlers/main.yml`.
6. Add templates: `cloud-ui-backend.env.j2`, `cloud-ui-frontend.conf.j2`.
7. Add `docs/generated/e09-kolla-ansible-role.md`.
8. Update `deploy/kolla/README.md`, `docs/generated/risk-register.md` and
   `docs/11_DKB_TRACEABILITY.md`.
9. Run final gates and record exact results here.

## Миграции и совместимость

No database schema or API migration is included. The role skeleton is additive and does not replace
E09.1 image build artifacts or local compose files. Rolling update, one-shot migration ordering and
rollback against live Kolla deployments remain E09.4-E09.8.

If a later E09 slice executes this role on a test stand, it must use reviewed inventory, approved
image digests and a secret delivery mechanism. Re-running this repository-only slice is idempotent
because it only changes tracked files.

## Проверка

Run from `/Users/dmitry/Desktop/dawn/.worktrees/e09-ansible-role-skeleton`:

```bash
backend/.venv/bin/python -m pytest tests/test_e09_kolla_ansible_role.py -q
backend/.venv/bin/python -m pytest tests/test_e09_kolla_image_build.py tests/test_e09_kolla_ansible_role.py -q
cd backend && .venv/bin/python -m ruff check ../tests/test_e09_kolla_ansible_role.py
make lint
make typecheck
make test
make security
git diff --check
rg -n "password|token|private key|BEGIN|latest|production approved|12 live containers proven" deploy/kolla docs/generated/e09-kolla-ansible-role.md docs/11_DKB_TRACEABILITY.md docs/generated/risk-register.md tests/test_e09_kolla_ansible_role.py
```

Expected final results:

- E09.2 targeted test passes.
- Combined E09.1/E09.2 tests pass.
- Ruff, frontend lint, mypy and TypeScript checks pass.
- Full backend and frontend tests pass.
- Secret scan passes.
- Diff check passes.
- Self-review grep finds only explanatory text, negative assertions or existing traceability
  references, not secrets or production approval claims.

## Доказательства

Evidence created or updated by this plan:

- `tests/test_e09_kolla_ansible_role.py`;
- `deploy/kolla/ansible/README.md`;
- `deploy/kolla/ansible/roles/cloud_ui/defaults/main.yml`;
- `deploy/kolla/ansible/roles/cloud_ui/tasks/*.yml`;
- `deploy/kolla/ansible/roles/cloud_ui/handlers/main.yml`;
- `deploy/kolla/ansible/roles/cloud_ui/templates/*.j2`;
- `docs/generated/e09-kolla-ansible-role.md`;
- `docs/generated/risk-register.md`;
- `docs/11_DKB_TRACEABILITY.md`;
- this ExecPlan.

## Откат и восстановление

Rollback is a Git revert of the E09.2 commits. No database, queue, registry, remote host, Vault path,
Kolla inventory or production credential is changed. If later live E09 slices consume this role, their
own rollback procedures must handle host config and container state.

## Итог и остаточные риски

To be completed after implementation. Expected residual risks:

- no live Kolla-Ansible syntax/render on a test inventory;
- no test registry digest/SBOM/scan/signing;
- no DB/RabbitMQ provisioning;
- no one-shot migration execution;
- no HAProxy/TLS proof;
- no SELinux host proof;
- no 12 live container proof;
- no rollback/reconfigure proof.
