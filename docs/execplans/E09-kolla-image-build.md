# ExecPlan: E09.1 Kolla image build

## Цель и наблюдаемый результат

E09.1 создает проверяемый repository-side контракт сборки Kolla images для портала. После изменения
оператор увидит `deploy/kolla/` с Kolla Build config, custom Dockerfile Jinja templates, build wrapper
и evidence, а тесты подтвердят, что объявлены ровно два custom image: `cloud-ui-backend` and
`cloud-ui-frontend`.

До изменения в репозитории существовал root test `tests/test_e015_kolla_layout.py`, который ожидал
`deploy/kolla/...`, но в дереве были только `deploy/AGENTS.md` and `deploy/env.example`.

## Контекст и текущее состояние

- Рабочая ветка: `e09-kolla-image-build` in `/Users/dmitry/Desktop/dawn/.worktrees/e09-kolla-image-build`.
- Базовый commit: `dda4e4f docs: add E09 image build design`.
- `backend/src/cloud_ui/cli.py` уже содержит команды `api`, `worker`, `events`, `db-upgrade` and `smoke`.
- `compose.yaml` уже использует один local backend image for API/worker/events and one frontend image.
- `backend/Dockerfile` and `frontend/Dockerfile` already pin local compose base images by digest from E08.6.
- E08 security review allows continuing into deployment evidence, but keeps registry/signing,
  SELinux, network-zone proof and the ДКБ-69 waiver as external conditions.

Baseline commands before implementation:

- `make bootstrap PYTHON=/Users/dmitry/Desktop/dawn/backend/.venv/bin/python` -> passed.
- `make lint` -> passed.
- `make typecheck` -> passed.
- `backend/.venv/bin/python -m pytest tests/test_e015_kolla_layout.py -q` -> failed with 5 failures
  because E09.1 Kolla artifacts do not exist yet.

## Scope

Included by the end of this E09.1 ExecPlan:

- Rename and scope the old root Kolla test to E09.1.
- Add Kolla Build config example for the two portal images.
- Add custom Kolla `Dockerfile.j2` templates for backend/frontend.
- Add a Bash build wrapper that requires explicit test registry, immutable tag and source pin and
  rejects `latest`.
- Add generated evidence for E09.1 in the evidence milestone, not in the minimal-artifact milestone.
- Update ДКБ traceability and risk register in the evidence milestone, not in the minimal-artifact
  milestone.

## Non-goals

- No production action.
- No SSH to test or production hosts.
- No Kolla-Ansible role deployment.
- No live registry login or push without approved test credentials.
- No image signing, vulnerability scan or SBOM against pushed registry digest in this slice.
- No DB/RabbitMQ provisioning.
- No migration job execution.
- No HAProxy/TLS reconfigure.
- No proof of 12 permanent containers.
- No SELinux host evidence.
- No rollback execution against live hosts.

## Требования и ограничения

- Exactly two portal-owned runtime images remain allowed: frontend and backend.
- API, worker, events and migration use the same backend digest with different commands.
- `latest` tag is forbidden.
- No real `clouds.yaml`, openrc, `.env`, token, password, private key, cookie, DB dump or production
  credential may be added.
- Browser trust boundary, BFF/API boundary, server-side session and workflow allowlist do not change.
- The implementation may document external registry commands, but it must not claim live registry
  evidence until the approved test environment is used.
- Official Kolla documentation supports custom non-built-in images through `--docker-dir`, profile
  selection in `kolla-build.conf`, local/git/url source sections and a custom `<name>-user` section
  for non-default users.

## Связь с ДКБ

- ДКБ-55/56: this plan stores no runtime secrets in Git. Kolla/Ansible secret references, DB/RabbitMQ
  credentials and rotation remain E09.3+ external/test deployment evidence.
- ДКБ-69: this plan creates custom image templates and preserves one backend image, but it cannot close
  the Python interpreter conflict. A formal waiver plus scanner/signing evidence remains required.
- ДКБ-70: this plan creates the test registry build/push contract and forbids `latest`. Live corporate
  test registry push, digest, SBOM, scanner and signature evidence remain pending.
- ДКБ-76/77/80: this plan documents image build interfaces. Runtime Kolla container inspection,
  disabled unused interfaces, network ACLs and management-zone proof remain E09.2-E09.8.

## Milestones

1. RED contract test exists and fails on missing E09.1 artifacts.
2. Minimal Kolla build artifacts make the repository contract test pass.
3. Evidence, DKB traceability and risk register are updated.
4. Lint, typecheck, tests, security scan and diff review pass.

## Progress

- [x] 2026-06-23: Исследование фактического состояния. Evidence: required E09 docs read; baseline
  commands above.
- [x] Контракт и RED tests.
  - 2026-06-24: RED `backend/.venv/bin/python -m pytest tests/test_e09_kolla_image_build.py -q` fails because E09.1 Kolla artifacts are absent.
- [x] Минимальная реализация.
  - 2026-06-24: Added `deploy/kolla/` build config, custom image templates, build wrapper and README.
  - 2026-06-24: `backend/.venv/bin/python -m pytest tests/test_e09_kolla_image_build.py -q`
    reports 4 passed artifact assertions and 2 expected failures for missing
    `docs/generated/e09-kolla-image-build.md`, which belongs to the evidence milestone.
  - 2026-06-24: `git diff --check` passes.
- [x] Отрицательные сценарии и безопасность.
  - 2026-06-24: Task 3 re-ran RED targeted test before evidence update:
    `backend/.venv/bin/python -m pytest tests/test_e09_kolla_image_build.py -q` -> 2 failed,
    4 passed, failing only because `docs/generated/e09-kolla-image-build.md` did not exist.
  - 2026-06-24: Evidence and risk register keep registry push, digest, SBOM, vulnerability scan,
    image signature and Kolla-Ansible deployment as `pending_external_evidence`; no live deployment,
    registry push or production action is claimed.
- [ ] Интеграционные и пользовательские проверки.
- [x] Документация, evidence и review.
  - 2026-06-24: Added `docs/generated/e09-kolla-image-build.md`.
  - 2026-06-24: Updated `docs/generated/risk-register.md` with E09 deployment risks R-056-R-058.
  - 2026-06-24: Updated `docs/11_DKB_TRACEABILITY.md` with E09.1 DKB impact and evidence links.
  - 2026-06-24: Targeted Task 3 verification:
    `backend/.venv/bin/python -m pytest tests/test_e09_kolla_image_build.py -q` -> 6 passed.
- [ ] Финальная проверка всего E09.1 набора.
  - Not complete in Task 3; full `make lint`, `make typecheck`, `make test` and `make security`
    remain outside this targeted evidence-only work item unless run later.

## Неожиданные открытия

- `tests/test_e015_kolla_layout.py` already existed and expected Kolla files that are absent from the
  current tree. It is not part of `make test`, but it is useful as a RED signal for E09.1 after
  scoping/renaming.
- The current backend CLI already has all required process commands, so E09.1 does not need new
  entrypoints.

## Журнал решений

- 2026-06-23: Start with E09.1 build contract only. Alternatives were full E09 rollout or remote-first
  registry/inventory discovery. Chosen because live registry/inventory credentials are not present and
  repository evidence can be tested without production risk.
- 2026-06-23: Use Kolla custom `--docker-dir` templates for non-built-in portal images. Reason:
  official Kolla image build documentation supports this model for external projects, source sections
  and custom users.
- 2026-06-23: Rename the legacy `E015` root test to E09.1 instead of satisfying its old lab playbook
  expectations. Reason: E09.1 scope is image build only; role/deploy/rollback playbooks belong to
  later E09 slices.
- 2026-06-24: Stage Kolla source archives inside the custom templates with `ADD
  cloud-ui-*-archive /cloud-ui-*-source` before install/copy steps. Reason: the templates must not
  depend on undocumented pre-extracted build context state.
- 2026-06-24: Copy frontend assets from the staged archive path inside the image instead of Docker
  `COPY` from the build context. Reason: the archive pin must be the source of runtime files.

## Детальный план реализации

1. Rename `tests/test_e015_kolla_layout.py` to `tests/test_e09_kolla_image_build.py`.
2. Replace the test with E09.1 assertions for required files, exactly two image sections, one backend
   image, frontend static runtime, fail-closed script and evidence status.
3. Run the targeted test and record the expected failure.
4. Minimal-artifact milestone: create `deploy/kolla/kolla-build.conf.example`.
5. Minimal-artifact milestone: create backend and frontend `Dockerfile.j2` templates.
6. Minimal-artifact milestone: create `deploy/kolla/scripts/build-images.sh` and make it executable.
7. Minimal-artifact milestone: create `deploy/kolla/README.md`.
8. Evidence milestone: create `docs/generated/e09-kolla-image-build.md`.
9. Evidence milestone: update `docs/generated/risk-register.md`.
10. Evidence milestone: update `docs/11_DKB_TRACEABILITY.md`.
11. Final verification milestone: run targeted tests and full relevant checks.
12. Final verification milestone: update this ExecPlan with command results and residual risks.

## Миграции и совместимость

No database schema or API migration is included. The build contract is backward compatible with the
existing local compose Dockerfiles because it adds Kolla-specific artifacts instead of replacing local
compose build paths.

Rolling update, migration ordering and rollback against a live Kolla deployment remain later E09
scope. This slice only documents that backend commands exist in one image and that registry artifacts
must be immutable.

## Проверка

Run from `/Users/dmitry/Desktop/dawn/.worktrees/e09-kolla-image-build`:

```bash
backend/.venv/bin/python -m pytest tests/test_e09_kolla_image_build.py -q
make lint
make typecheck
make test
make security
git diff --check
```

Expected after the evidence milestone is complete:

- targeted E09 test passes;
- backend ruff passes;
- frontend eslint passes;
- secret scan passes;
- mypy passes;
- frontend typecheck passes;
- backend and frontend tests pass;
- no whitespace errors.

Expected during the minimal-artifact milestone, before `docs/generated/e09-kolla-image-build.md`
exists: `backend/.venv/bin/python -m pytest tests/test_e09_kolla_image_build.py -q` reports only the
two evidence-document failures, while artifact assertions pass.

Review commands:

```bash
git diff --stat HEAD~1..HEAD
git diff -- deploy/kolla tests/test_e09_kolla_image_build.py docs/generated/e09-kolla-image-build.md docs/11_DKB_TRACEABILITY.md docs/generated/risk-register.md
rg -n "password|token|private key|BEGIN|latest|production approved|12 permanent containers proven" deploy/kolla docs/generated/e09-kolla-image-build.md docs/11_DKB_TRACEABILITY.md docs/generated/risk-register.md tests/test_e09_kolla_image_build.py
```

Expected: any secret-like matches are explanatory text only; no production approval or 12-container
proof is claimed.

## Доказательства

Created or updated evidence by the end of this E09.1 ExecPlan:

- `tests/test_e09_kolla_image_build.py`
- `deploy/kolla/README.md`
- `deploy/kolla/kolla-build.conf.example`
- `deploy/kolla/docker/cloud-ui-backend/Dockerfile.j2`
- `deploy/kolla/docker/cloud-ui-frontend/Dockerfile.j2`
- `deploy/kolla/scripts/build-images.sh`
- `docs/generated/e09-kolla-image-build.md`
- `docs/generated/risk-register.md`
- `docs/11_DKB_TRACEABILITY.md`
- `docs/execplans/E09-kolla-image-build.md`

## Откат и восстановление

Rollback is a Git revert of the E09.1 commit(s). No database, queue, registry, remote host, Vault path,
Kolla inventory or production credential is changed. If a live operator later runs the build wrapper
against a test registry, registry cleanup must be handled by the registry owner using the recorded tag
and digest.

## Итог и остаточные риски

Pending until implementation finishes.
