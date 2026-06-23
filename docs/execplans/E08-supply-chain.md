# ExecPlan: E08 Supply Chain

## Цель и наблюдаемый результат

После E08.6 в репозитории появляется воспроизводимый локальный supply-chain gate: base images для
двух собственных runtime images зафиксированы digest-ами, `make sbom` строит backend/frontend images
и создает sanitized SBOM/evidence summary, а тесты проверяют lockfiles, digest pinning, SBOM команду
и честное описание оставшихся registry/signing/scanner gaps. До этого slice `make sbom` отсутствовал,
Dockerfiles использовали floating base tags, а supply-chain evidence была только ожидаемым
требованием в документах.

## Контекст и текущее состояние

- Repository root: `/Users/dmitry/Desktop/dawn/.worktrees/e08-supply-chain`.
- Branch/worktree: `e08-supply-chain`.
- Base commit: `4e72caa Merge pull request #5 from lebtmalorny-rgb/e08-container-hardening`.
- `backend/pyproject.toml` already pins Python runtime and dev dependencies with exact `==`
  versions, but there is no Python lockfile and no `pip-audit` installed locally.
- `frontend/package-lock.json` exists and `npm ci` is the install path.
- `Makefile` has `security` as secret scan only and does not define `sbom`.
- `backend/Dockerfile` uses `python:3.11-slim` for builder and runtime.
- `frontend/Dockerfile` uses `node:24-alpine` for build and
  `nginxinc/nginx-unprivileged:1.27-alpine` for runtime.
- Docker SBOM plugin is available: `docker-sbom 0.6.0`, provider `syft v0.43.0`.
- `syft`, `trivy`, `grype` and `pip-audit` are not installed in the local environment.
- Baseline checks passed before changes:
  - `make bootstrap PYTHON=/Users/dmitry/Desktop/dawn/backend/.venv/bin/python` succeeded;
  - `make lint` passed;
  - `make typecheck` passed;
  - `make test` passed: backend `316 passed, 1 skipped`; frontend `35 passed`.
  - Local Node remains `v25.9.0`, outside frontend engine `>=24 <25`, but baseline gates pass.

## Scope

- Add repository tests for E08.6 supply-chain expectations.
- Pin backend and frontend Dockerfile base images by digest while preserving readable tags.
- Add `make sbom` backed by a repository script.
- Generate a small sanitized Markdown evidence file for SBOM/image digest/audit results.
- Run local dependency/image evidence commands available in this environment.
- Update DKB traceability and risk register without claiming full production supply-chain closure.

## Non-goals

- No production registry push.
- No image signing/provenance attestation implementation.
- No introduction of permanent scanner dependencies such as Trivy, Grype, Syft CLI or pip-audit
  without ADR/package policy.
- No change to runtime behavior, API contracts, RBAC, sessions, workflows, audit delivery or DB schema.
- No E09 Kolla build templates or corporate registry policy.
- No claim that ДКБ-69, ДКБ-70 or production supply-chain compliance is closed.

## Требования и ограничения

- Keep exactly two custom runtime images: backend and frontend.
- Do not add secrets, registry credentials, tokens, `.env`, `clouds.yaml`, openrc or production URLs.
- Generated evidence must be sanitized and compact enough for Git.
- Large raw SBOM/scanner output belongs in `artifacts/` or CI, not committed by default.
- `make sbom` must fail clearly when Docker or the Docker SBOM plugin is unavailable.
- Dockerfiles should retain readable image tags with immutable digest pins.
- ДКБ-69 conflict for Python interpreter remains explicit.

## Связь с ДКБ

- ДКБ-69: this plan adds digest pinning, SBOM evidence and local image inspection evidence as
  compensating controls, but does not remove the Python interpreter or inherited shell/package-manager
  components from base images.
- ДКБ-70: this plan creates local image IDs/digest evidence and an SBOM command, but does not push to
  a corporate registry, enforce immutable pull-by-digest deployment, sign images or verify provenance.
- ДКБ-76/77/80: this plan documents local supply-chain and image-source controls for portal images;
  production network/registry/firewall/Kolla evidence remains E09.

## Milestones

1. RED supply-chain tests for missing `make sbom`, floating base images and missing evidence.
2. Minimal digest pinning and `make sbom` implementation.
3. Generated evidence and DKB/risk updates.
4. Local Docker SBOM/build/audit verification.
5. Commit, push and PR.

## Progress

- [x] 2026-06-23: Baseline setup and checks passed before changes. Evidence: `make lint`,
  `make typecheck`, `make test`; backend `316 passed, 1 skipped`; frontend `35 passed`.
- [x] RED supply-chain tests. Evidence: `cd backend && .venv/bin/python -m pytest
  tests/security/test_e08_supply_chain.py -q` failed with 3 expected failures because `make sbom`,
  digest-pinned Dockerfile `FROM` lines and `docs/generated/e08-supply-chain.md` were absent.
- [x] Minimal digest pinning and SBOM command. Evidence: `make sbom` built
  `cloud-ui-backend:dev` and `cloud-ui-frontend:dev` from digest-pinned bases and wrote
  `docs/generated/e08-supply-chain.md`; targeted test then passed `4 passed`.
- [x] Evidence docs and traceability. Evidence: updated `docs/generated/risk-register.md` and
  `docs/11_DKB_TRACEABILITY.md`.
- [x] Final verification and review. Evidence: targeted E08.6 test `4 passed`; E08.5/E08.6 security
  tests `9 passed`; `make lint`, `make typecheck`, `make test`, `make test-integration`,
  `make security`, `npm --prefix frontend audit --package-lock-only --audit-level=high`,
  `make sbom`, `docker image inspect ...` and `git diff --check` passed. `make test` reported backend
  `320 passed, 1 skipped` and frontend `35 passed`; `make test-integration` reported `21 passed,
  1 skipped`; `npm audit` reported `found 0 vulnerabilities`.

## Неожиданные открытия

- 2026-06-23: Local Docker SBOM plugin is available (`docker-sbom 0.6.0`, `syft v0.43.0`), but
  standalone `syft`, `trivy`, `grype` and `pip-audit` are absent.
- 2026-06-23: Bootstrap creates `backend/src/cloud_ui.egg-info/` as an untracked editable-install
  artifact; it must not be committed.
- 2026-06-23: `docker sbom` plugin 0.6.0 fails against Docker 29 unless `DOCKER_API_VERSION=1.44`
  is set. `scripts/generate-sbom.sh` exports that value by default before invoking the plugin.

## Журнал решений

- 2026-06-23: Use Docker SBOM plugin for local SBOM evidence instead of adding a new permanent scanner
  dependency. Alternatives: add Trivy/Grype/Syft CLI now, or only document the gap. Reason: Docker
  SBOM is available locally and produces a reproducible gate without ADR-level dependency expansion.
  Consequence: vulnerability policy remains partial and scanner gaps stay explicit.
- 2026-06-23: Scope E08.6 to local images and repository evidence, not corporate registry/signing.
  Reason: E09 owns Kolla/registry deployment. Consequence: ДКБ-70 is improved but not closed.

## Детальный план реализации

### Task 1: Supply-chain tests

- Create `backend/tests/security/test_e08_supply_chain.py`.
- Assert `Makefile` declares `sbom` as a phony target and invokes `scripts/generate-sbom.sh`.
- Assert backend/frontend Dockerfile `FROM` lines use `tag@sha256:<64 hex>` pins.
- Assert frontend has `package-lock.json`.
- Assert backend runtime dependencies in `backend/pyproject.toml` use exact `==` pins.
- Assert `docs/generated/e08-supply-chain.md` records SBOM command, image digest evidence and
  residual registry/signing/scanner gaps.
- Verify RED with:
  `cd backend && .venv/bin/python -m pytest tests/security/test_e08_supply_chain.py -q`.

### Task 2: Digest pinning and SBOM command

- Modify `backend/Dockerfile`:
  - `python:3.11-slim@sha256:ae52c5bef62a6bdd42cd1e8dffef86b9cd284bde9427da79839de7a4b983e7ca`
    for builder and runtime.
- Modify `frontend/Dockerfile`:
  - `node:24-alpine@sha256:156b55f92e98ccd5ef49578a8cea0df4679826564bad1c9d4ef04462b9f0ded6`
    for build;
  - `nginxinc/nginx-unprivileged:1.27-alpine@sha256:65e3e85dbaed8ba248841d9d58a899b6197106c23cb0ff1a132b7bfe0547e4c0`
    for runtime.
- Add `scripts/generate-sbom.sh`:
  - checks Docker and `docker sbom`;
  - runs `docker sbom --format table` for `cloud-ui-backend:dev` and `cloud-ui-frontend:dev`;
  - writes a compact Markdown summary to `docs/generated/e08-supply-chain.md`;
  - records image IDs/users from `docker image inspect`;
  - records `npm audit --package-lock-only --audit-level=high` result if run separately in final
    verification;
  - lists unavailable scanner/signing/registry controls as residual gaps.
- Modify `Makefile`:
  - include `sbom` in `.PHONY`;
  - add `sbom: build` target running `./scripts/generate-sbom.sh`.

### Task 3: Evidence docs

- Update `docs/generated/risk-register.md` for E08 supply-chain status and remaining gaps.
- Update `docs/11_DKB_TRACEABILITY.md` with E08.6 evidence and limitations.
- Update this ExecPlan progress after each verification.

### Task 4: Verification and commit

Run:

```bash
cd backend && .venv/bin/python -m pytest tests/security/test_e08_supply_chain.py -q
make lint
make typecheck
make test
make test-integration
make security
npm --prefix frontend audit --package-lock-only --audit-level=high
make sbom
docker image inspect cloud-ui-backend:dev cloud-ui-frontend:dev
git diff --check
```

Review diff for:

- no secrets or production endpoints;
- no false claim that ДКБ-69/70 are closed;
- no registry/signing/provenance claim without evidence;
- no unrelated runtime/API behavior changes.

Commit:

```bash
git add Makefile backend/Dockerfile frontend/Dockerfile scripts/generate-sbom.sh \
  backend/tests/security/test_e08_supply_chain.py docs/generated/e08-supply-chain.md \
  docs/generated/risk-register.md docs/11_DKB_TRACEABILITY.md docs/execplans/E08-supply-chain.md
git commit -m "chore: add supply chain evidence gate"
```

## Миграции и совместимость

No database migration. Runtime app behavior is unchanged. Docker base digest pins are build-time
supply-chain controls; rollback restores tag-only base image resolution. Rolling update compatibility is
unchanged because no public API, schema or persisted data contract changes.

## Проверка

The final commands are listed in Task 4. Docker build/SBOM evidence is local and does not push images
to a registry. If Docker cannot pull digest-pinned bases or Docker SBOM plugin fails, record the
failure and do not claim SBOM success.

## Доказательства

- `backend/tests/security/test_e08_supply_chain.py`.
- `scripts/generate-sbom.sh`.
- `docs/generated/e08-supply-chain.md`.
- Updated `docs/generated/risk-register.md`.
- Updated `docs/11_DKB_TRACEABILITY.md`.
- Docker build/SBOM/inspect output from final verification.
  - `make sbom` built `cloud-ui-backend:dev` and `cloud-ui-frontend:dev`, then wrote
    `docs/generated/e08-supply-chain.md`;
  - backend image inspect reported `user=cloudui`, local image ID
    `sha256:8cf0d014e71be6aa2b265b7479aaffddec44a57585b968d6bfb729ad7c185c7a`;
  - frontend image inspect reported `user=101`, local image ID
    `sha256:c313d8a5199f864d0e9bf7b4a96a22d2ff1c784be9591f4bc91a73c66c7d74d2`;
  - Docker SBOM table hashes are recorded in `docs/generated/e08-supply-chain.md`.
- This ExecPlan progress log.

## Откат и восстановление

Revert the E08.6 commit. No DB schema, external registry, remote host, queue, Vault path or production
secret is changed. Rollback restores floating tag base image resolution and removes the local SBOM gate.

## Итог и остаточные риски

Implementation completed for E08.6. Residual risks:

- production registry digest policy and pull-by-digest deployment remain E09;
- image signing/provenance verification remains E08/E09 gap;
- vulnerability scanning for Python/image CVEs remains blocked until scanner tooling/policy is chosen;
- ДКБ-69 interpreter/shell/package-manager absence remains a formal waiver/gap for Python backend and
  inherited base images.
