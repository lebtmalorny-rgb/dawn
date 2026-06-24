# E09 Kolla Image Build Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the repository-side E09.1 Kolla image build contract for exactly two portal images without claiming live registry or deployment evidence.

**Architecture:** Add Kolla custom docker templates under `deploy/kolla/docker`, an example `kolla-build.conf`, a fail-closed build script, generated evidence, DKB/risk updates and tests. The tests validate static repository artifacts and explicitly keep registry push, signing, scanner, SELinux host proof and rollout evidence pending until a test environment is provided.

**Tech Stack:** Python pytest for repository contract tests, Bash for the operator build script, Kolla Build custom `--docker-dir` Jinja Dockerfile templates, Markdown evidence.

---

## File Structure

- Rename and modify: `tests/test_e015_kolla_layout.py` -> `tests/test_e09_kolla_image_build.py`
  - Responsibility: E09.1 repository contract tests for Kolla image build artifacts.
- Create: `deploy/kolla/README.md`
  - Responsibility: operator runbook for dry-run/list/build/push-by-digest evidence flow.
- Create: `deploy/kolla/kolla-build.conf.example`
  - Responsibility: example Kolla Build config for the two portal custom images and `cloudui` user.
- Create: `deploy/kolla/docker/cloud-ui-backend/Dockerfile.j2`
  - Responsibility: backend custom image template, one image for API/worker/events/migration/smoke commands.
- Create: `deploy/kolla/docker/cloud-ui-frontend/Dockerfile.j2`
  - Responsibility: frontend custom image template using prebuilt static assets without Node/npm runtime.
- Create: `deploy/kolla/scripts/build-images.sh`
  - Responsibility: fail-closed operator wrapper around `kolla-build`.
- Create: `docs/generated/e09-kolla-image-build.md`
  - Responsibility: generated-style evidence for E09.1 scope, commands, pending external evidence and DKB impact.
- Modify: `docs/generated/risk-register.md`
  - Responsibility: add E09 image build risks and mitigations.
- Modify: `docs/11_DKB_TRACEABILITY.md`
  - Responsibility: trace E09.1 evidence to affected DKB controls without claiming closure.
- Modify during execution: `docs/execplans/E09-kolla-image-build.md`
  - Responsibility: living project ExecPlan, progress, commands, results and residual risks.

## Task 1: RED Test Contract

**Files:**
- Rename: `tests/test_e015_kolla_layout.py` -> `tests/test_e09_kolla_image_build.py`
- Modify: `tests/test_e09_kolla_image_build.py`

- [ ] **Step 1: Rename the outdated root Kolla test**

Run:

```bash
git mv tests/test_e015_kolla_layout.py tests/test_e09_kolla_image_build.py
```

Expected: Git records a rename. No content change yet.

- [ ] **Step 2: Replace the test file with the E09.1 contract**

Write exactly this file content:

```python
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CUSTOM_IMAGES = {"cloud-ui-backend", "cloud-ui-frontend"}


def read_text(relative_path: str) -> str:
    return (ROOT / relative_path).read_text(encoding="utf-8")


def test_kolla_image_build_files_exist() -> None:
    expected_paths = [
        "deploy/kolla/README.md",
        "deploy/kolla/kolla-build.conf.example",
        "deploy/kolla/docker/cloud-ui-backend/Dockerfile.j2",
        "deploy/kolla/docker/cloud-ui-frontend/Dockerfile.j2",
        "deploy/kolla/scripts/build-images.sh",
        "docs/generated/e09-kolla-image-build.md",
    ]

    for relative_path in expected_paths:
        assert (ROOT / relative_path).exists(), relative_path


def test_kolla_build_config_declares_exactly_two_custom_images() -> None:
    config = read_text("deploy/kolla/kolla-build.conf.example")

    assert "engine = podman" in config
    assert "base = rocky" in config
    assert "base_tag = 9" in config
    assert "openstack_release = 2025.1" in config
    assert "profile = cloud-ui" in config
    assert "cloud-ui = cloud-ui-backend,cloud-ui-frontend" in config
    assert "[cloudui-user]" in config
    assert "uid = 42424" in config
    assert "gid = 42424" in config

    image_sections = set(
        re.findall(r"^\[(cloud-ui-(?:backend|frontend))\]$", config, re.MULTILINE)
    )
    assert image_sections == CUSTOM_IMAGES
    assert "latest" not in config.lower()


def test_backend_template_keeps_one_backend_image_for_all_commands() -> None:
    template = read_text("deploy/kolla/docker/cloud-ui-backend/Dockerfile.j2")

    for expected in [
        "FROM {{ namespace }}/{{ image_prefix }}openstack-base:{{ tag }}",
        "ARG CLOUD_UI_SOURCE_PIN",
        "ADD cloud-ui-backend-archive /cloud-ui-backend-source",
        "cloud-ui-backend-source",
        "{{ macros.configure_user(name='cloudui') }}",
        "org.opencontainers.image.title=\"cloud-ui-backend\"",
        "cloud-ui api",
        "cloud-ui worker",
        "cloud-ui events",
        "cloud-ui db-upgrade",
        "cloud-ui smoke",
    ]:
        assert expected in template

    for forbidden in [
        "name=\"cloud-ui-api\"",
        "name=\"cloud-ui-worker\"",
        "name=\"cloud-ui-events\"",
        "cloud-ui-api-source",
        "cloud-ui-worker-source",
        "cloud-ui-events-source",
    ]:
        assert forbidden not in template


def test_frontend_template_uses_prebuilt_dist_without_node_runtime() -> None:
    template = read_text("deploy/kolla/docker/cloud-ui-frontend/Dockerfile.j2")

    for expected in [
        "FROM {{ namespace }}/{{ image_prefix }}base:{{ tag }}",
        "ARG CLOUD_UI_SOURCE_PIN",
        "ADD cloud-ui-frontend-archive /cloud-ui-frontend-source",
        "cloud-ui-frontend-source/frontend/dist",
        "{{ macros.configure_user(name='cloudui') }}",
        "org.opencontainers.image.title=\"cloud-ui-frontend\"",
        "nginx",
    ]:
        assert expected in template

    normalized_template = template.lower()
    assert "node" not in normalized_template
    assert "npm" not in normalized_template


def test_build_script_requires_test_registry_pin_and_rejects_latest() -> None:
    script = read_text("deploy/kolla/scripts/build-images.sh")

    for expected in [
        "require_var CLOUD_UI_TEST_REGISTRY",
        "require_var CLOUD_UI_IMAGE_TAG",
        "require_var CLOUD_UI_SOURCE_PIN",
        "CLOUD_UI_IMAGE_TAG must not be latest",
        "--config-file \"$CONFIG_FILE\"",
        "--docker-dir \"$DOCKER_DIR\"",
        "--profile cloud-ui",
        "--tag \"$CLOUD_UI_IMAGE_TAG\"",
        "--build-args \"CLOUD_UI_SOURCE_PIN=$CLOUD_UI_SOURCE_PIN\"",
        "--registry \"$CLOUD_UI_TEST_REGISTRY\"",
        "--push",
        "cloud-ui-backend",
        "cloud-ui-frontend",
    ]:
        assert expected in script

    assert "example.com" not in script
    assert "password" not in script.lower()
    assert "token" not in script.lower()


def test_e09_evidence_records_scope_and_pending_external_proofs() -> None:
    evidence = read_text("docs/generated/e09-kolla-image-build.md")

    for expected in [
        "Stage: E09.1 Kolla image build",
        "Exactly two custom images",
        "cloud-ui-backend",
        "cloud-ui-frontend",
        "pending_external_evidence",
        "corporate test registry push",
        "vulnerability scan",
        "image signature",
        "ДКБ-69",
        "ДКБ-70",
    ]:
        assert expected in evidence

    assert "12 permanent containers proven" not in evidence
    assert "production approved" not in evidence.lower()
```

- [ ] **Step 3: Run the RED test**

Run:

```bash
backend/.venv/bin/python -m pytest tests/test_e09_kolla_image_build.py -q
```

Expected: FAIL because `deploy/kolla/...` and `docs/generated/e09-kolla-image-build.md` do not exist yet.

- [ ] **Step 4: Update ExecPlan progress**

In `docs/execplans/E09-kolla-image-build.md`, mark "Контракт и RED tests" in progress and record the failing command:

```markdown
- 2026-06-23: RED `backend/.venv/bin/python -m pytest tests/test_e09_kolla_image_build.py -q` fails because E09.1 Kolla artifacts are absent.
```

## Task 2: Minimal Kolla Build Artifacts

**Files:**
- Create: `deploy/kolla/README.md`
- Create: `deploy/kolla/kolla-build.conf.example`
- Create: `deploy/kolla/docker/cloud-ui-backend/Dockerfile.j2`
- Create: `deploy/kolla/docker/cloud-ui-frontend/Dockerfile.j2`
- Create: `deploy/kolla/scripts/build-images.sh`

- [ ] **Step 1: Create `deploy/kolla/kolla-build.conf.example`**

Write:

```ini
[DEFAULT]
engine = podman
base = rocky
base_tag = 9
openstack_release = 2025.1
tag = 2025.1-rocky-9
profile = cloud-ui
namespace = cloud-ui-test
image_prefix =
maintainer = Cloud UI Platform Team <platform@example.invalid>

[profiles]
cloud-ui = cloud-ui-backend,cloud-ui-frontend

[cloud-ui-backend]
type = local
location = /srv/kolla/cloud-ui/sources/backend
reference = pinned-by-CLOUD_UI_SOURCE_PIN

[cloud-ui-frontend]
type = local
location = /srv/kolla/cloud-ui/sources/frontend
reference = pinned-by-CLOUD_UI_SOURCE_PIN

[cloudui-user]
uid = 42424
gid = 42424
```

- [ ] **Step 2: Create backend custom Dockerfile template**

Write `deploy/kolla/docker/cloud-ui-backend/Dockerfile.j2`:

```jinja
FROM {{ namespace }}/{{ image_prefix }}openstack-base:{{ tag }}

ARG CLOUD_UI_SOURCE_PIN=unrecorded

{% block labels %}
LABEL maintainer="{{ maintainer }}" name="{{ image_name }}" build-date="{{ build_date }}" \
      org.opencontainers.image.title="cloud-ui-backend" \
      org.opencontainers.image.description="Cloud UI backend runtime for API, worker, events, migration and smoke commands" \
      org.opencontainers.image.revision="${CLOUD_UI_SOURCE_PIN}"
{% endblock %}

{% import "macros.j2" as macros with context %}

{{ macros.configure_user(name='cloudui') }}

ADD cloud-ui-backend-archive /cloud-ui-backend-source

RUN ln -s cloud-ui-backend-source/* /cloud-ui-backend \
    && {{ macros.install_pip(['/cloud-ui-backend'] | customizable("pip_packages")) }} \
    && mkdir -p /etc/cloud-ui /var/log/kolla/cloud-ui \
    && chown -R cloudui: /etc/cloud-ui /var/log/kolla/cloud-ui

USER cloudui
EXPOSE 8080

# Supported commands:
# - cloud-ui api
# - cloud-ui worker
# - cloud-ui events
# - cloud-ui db-upgrade
# - cloud-ui smoke
CMD ["cloud-ui", "api"]

{% block footer %}{% endblock %}
```

- [ ] **Step 3: Create frontend custom Dockerfile template**

Write `deploy/kolla/docker/cloud-ui-frontend/Dockerfile.j2`:

```jinja
FROM {{ namespace }}/{{ image_prefix }}base:{{ tag }}

ARG CLOUD_UI_SOURCE_PIN=unrecorded

{% block labels %}
LABEL maintainer="{{ maintainer }}" name="{{ image_name }}" build-date="{{ build_date }}" \
      org.opencontainers.image.title="cloud-ui-frontend" \
      org.opencontainers.image.description="Cloud UI static frontend runtime" \
      org.opencontainers.image.revision="${CLOUD_UI_SOURCE_PIN}"
{% endblock %}

{% import "macros.j2" as macros with context %}

{{ macros.configure_user(name='cloudui') }}
{{ macros.install_packages(['nginx']) }}

ADD cloud-ui-frontend-archive /cloud-ui-frontend-source

COPY cloud-ui-frontend-source/frontend/dist /usr/share/nginx/html
COPY cloud-ui-frontend-source/frontend/nginx.conf /etc/nginx/nginx.conf

RUN mkdir -p /var/cache/nginx /var/run /var/log/kolla/cloud-ui-frontend \
    && chown -R cloudui: /usr/share/nginx/html /var/cache/nginx /var/run /var/log/kolla/cloud-ui-frontend

USER cloudui
EXPOSE 8080
CMD ["nginx", "-g", "daemon off;"]

{% block footer %}{% endblock %}
```

- [ ] **Step 4: Create the fail-closed build wrapper**

Write `deploy/kolla/scripts/build-images.sh`:

```bash
#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
KOLLA_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
CONFIG_FILE="${KOLLA_BUILD_CONFIG:-$KOLLA_DIR/kolla-build.conf.example}"
DOCKER_DIR="${KOLLA_DOCKER_DIR:-$KOLLA_DIR/docker}"
ACTION="${1:-build}"

require_var() {
    local name="$1"
    if [ -z "${!name:-}" ]; then
        printf '%s\n' "Missing required environment variable: $name" >&2
        exit 2
    fi
}

require_var CLOUD_UI_TEST_REGISTRY
require_var CLOUD_UI_IMAGE_TAG
require_var CLOUD_UI_SOURCE_PIN

if [ "$CLOUD_UI_IMAGE_TAG" = "latest" ]; then
    printf '%s\n' "CLOUD_UI_IMAGE_TAG must not be latest" >&2
    exit 2
fi

COMMON_ARGS=(
    --config-file "$CONFIG_FILE"
    --docker-dir "$DOCKER_DIR"
    --profile cloud-ui
    --tag "$CLOUD_UI_IMAGE_TAG"
    --build-args "CLOUD_UI_SOURCE_PIN=$CLOUD_UI_SOURCE_PIN"
)

case "$ACTION" in
    list)
        kolla-build "${COMMON_ARGS[@]}" --list-images
        ;;
    build)
        kolla-build "${COMMON_ARGS[@]}"
        ;;
    push)
        kolla-build "${COMMON_ARGS[@]}" --registry "$CLOUD_UI_TEST_REGISTRY" --push
        ;;
    *)
        printf '%s\n' "Usage: $0 [list|build|push]" >&2
        exit 2
        ;;
esac

printf '%s\n' "E09.1 Kolla image action complete for cloud-ui-backend and cloud-ui-frontend"
```

Then make it executable:

```bash
chmod +x deploy/kolla/scripts/build-images.sh
```

- [ ] **Step 5: Create the operator README**

Write `deploy/kolla/README.md`:

```markdown
# Cloud UI Kolla Image Build

This directory is the E09.1 repository contract for building the two portal-owned Kolla images:

- `cloud-ui-backend`;
- `cloud-ui-frontend`.

It follows the Kolla custom template flow: `kolla-build.conf.example` defines a `cloud-ui` profile,
and `deploy/kolla/docker` is passed to `kolla-build` with `--docker-dir`.

## Scope

This slice creates build artifacts only. It does not deploy Kolla-Ansible, create DB or RabbitMQ
users, configure HAProxy/TLS, prove SELinux labels, push to a live registry, sign images or prove the
three-node 12-container topology.

## Required Operator Inputs

Set these only in the test build environment:

```bash
export CLOUD_UI_TEST_REGISTRY='registry.test.example.invalid/cloud-ui'
export CLOUD_UI_IMAGE_TAG='2025.1-rocky-9-<git-sha>'
export CLOUD_UI_SOURCE_PIN='<git-sha-or-source-archive-sha256>'
```

The tag `latest` is rejected by `scripts/build-images.sh`.

## Commands

List the custom images visible to Kolla:

```bash
deploy/kolla/scripts/build-images.sh list
```

Build the images:

```bash
deploy/kolla/scripts/build-images.sh build
```

Push to the approved test registry:

```bash
deploy/kolla/scripts/build-images.sh push
```

Record image digests, SBOM, vulnerability scan and signature evidence in
`docs/generated/e09-kolla-image-build.md` after the live test registry flow is executed.

## Security Rules

- Do not store registry credentials, scanner tokens, signing keys, Kolla passwords or production URLs
  in this directory.
- Backend `api`, `worker`, `events`, `db-upgrade` and `smoke` run from the same
  `cloud-ui-backend` image.
- The frontend image serves prebuilt static assets and does not carry the frontend build toolchain.
- ДКБ-69 remains open for the Python backend interpreter unless a formal waiver is approved.
```

- [ ] **Step 6: Run the targeted tests**

Run:

```bash
backend/.venv/bin/python -m pytest tests/test_e09_kolla_image_build.py -q
```

Expected: still FAIL because generated evidence and docs traceability are not complete yet, or PASS if Task 3 was completed before this check.

## Task 3: Evidence, Traceability and Risk Register

**Files:**
- Create: `docs/generated/e09-kolla-image-build.md`
- Modify: `docs/generated/risk-register.md`
- Modify: `docs/11_DKB_TRACEABILITY.md`
- Modify: `docs/execplans/E09-kolla-image-build.md`

- [ ] **Step 1: Create generated E09.1 evidence**

Write `docs/generated/e09-kolla-image-build.md`:

```markdown
# E09.1 Kolla Image Build Evidence

- Stage: E09.1 Kolla image build
- Date: 2026-06-23
- Scope: repository-side Kolla Build contract for portal custom images
- Live deployment: not executed in this slice
- Production action: none

## Image Contract

Exactly two custom images are declared:

| Image | Runtime purpose | Source |
|---|---|---|
| `cloud-ui-backend` | `cloud-ui api`, `cloud-ui worker`, `cloud-ui events`, `cloud-ui db-upgrade`, `cloud-ui smoke` | `deploy/kolla/docker/cloud-ui-backend/Dockerfile.j2` |
| `cloud-ui-frontend` | static frontend served by nginx | `deploy/kolla/docker/cloud-ui-frontend/Dockerfile.j2` |

No separate `cloud-ui-api`, `cloud-ui-worker` or `cloud-ui-events` image is declared.

## Reproducible Build Inputs

Required operator inputs:

- `CLOUD_UI_TEST_REGISTRY`
- `CLOUD_UI_IMAGE_TAG`
- `CLOUD_UI_SOURCE_PIN`

`deploy/kolla/scripts/build-images.sh` rejects `CLOUD_UI_IMAGE_TAG=latest`.

## Commands

```bash
deploy/kolla/scripts/build-images.sh list
deploy/kolla/scripts/build-images.sh build
deploy/kolla/scripts/build-images.sh push
```

The `push` command is only for an approved corporate test registry. It was not executed in this
repository-only slice.

## External Evidence Status

| Evidence | Status | Reason |
|---|---|---|
| corporate test registry push | pending_external_evidence | Requires approved test registry credentials and network access. |
| image digest from registry | pending_external_evidence | Requires completed push and registry inspection. |
| SBOM tied to pushed digest | pending_external_evidence | Requires approved SBOM tool against the pushed digest. |
| vulnerability scan | pending_external_evidence | Requires approved scanner and policy threshold. |
| image signature | pending_external_evidence | Requires approved signing key and verification policy. |
| Kolla-Ansible deployment | pending_external_evidence | E09.2-E09.8 own role, rollout, HAProxy/TLS, rollback and smoke. |

## DKB Impact

- ДКБ-69: image minimization contract is improved, but the Python backend still requires an interpreter.
  This is not closed without a formal waiver and approved scanner/signing evidence.
- ДКБ-70: the repository now has a corporate test registry build/push contract, but live registry
  evidence remains pending.
- ДКБ-76/77/80: deployment image interfaces are documented. Network ACLs, management-zone placement,
  disabled unused interfaces and runtime Kolla inspection remain later E09 evidence.
- ДКБ-55/56: no secrets are stored in the build contract. Secret injection and rotation remain
  deployment-pipeline evidence.

## Rollback

Revert the E09.1 commit. This slice changes only repository files and does not modify database schema,
queue state, registry contents, remote hosts, Vault paths, Kolla inventory or production credentials.
```

- [ ] **Step 2: Append risk register rows**

In `docs/generated/risk-register.md`, add a section before "Immediate priority order":

```markdown
## E09 Kolla deployment risks

| ID | Риск | Текущее положение | Митигация | Stage |
|---|---|---|---|---|
| R-056 | E09.1 build contract mistaken for live registry proof | E09.1 creates Kolla Build config/templates/script/evidence for two images only. No registry push, digest, signing or vulnerability scanner was executed in this slice. | Keep registry/SBOM/scan/signature rows as `pending_external_evidence` until an approved corporate test registry flow is executed and recorded. | E09 |
| R-057 | Custom backend processes split into multiple images | E09.1 tests enforce one `cloud-ui-backend` image for API, worker, events, `db-upgrade` and `smoke`. | Keep Kolla role definitions in E09.2-E09.5 pointing to one backend digest with different commands. | E09 |
| R-058 | Kolla custom image syntax drifts from supported flow | E09.1 uses Kolla `--docker-dir`, profile and custom user section patterns from upstream Kolla image-build documentation. | Run `deploy/kolla/scripts/build-images.sh list` in the approved Kolla 2025.1 test build environment before claiming live build readiness. | E09 |
```

- [ ] **Step 3: Add DKB traceability update**

In `docs/11_DKB_TRACEABILITY.md`, add this section before `## Полная матрица`:

```markdown
## Обновление требований 2026-06-23: E09.1 Kolla image build

E09.1 добавляет repository-side Kolla Build contract для двух portal-owned images без заявления live
registry/deployment compliance:

- ДКБ-69: `deploy/kolla/docker/cloud-ui-backend/Dockerfile.j2` and
  `deploy/kolla/docker/cloud-ui-frontend/Dockerfile.j2` define custom Kolla image templates and
  keep one backend image for API, worker, events, migration and smoke commands. Python backend still
  requires an interpreter; formal waiver and approved scanner/signing evidence remain required.
- ДКБ-70: `deploy/kolla/scripts/build-images.sh` requires explicit test registry, immutable tag and
  source pin, rejects `latest`, and provides the push-by-registry contract. Actual corporate test
  registry push, digest, SBOM, scanner and signature evidence remain pending external evidence.
- ДКБ-76/77/80: `deploy/kolla/README.md` documents image build interfaces and non-goals. Runtime
  Kolla-Ansible container inspection, network ACLs, management-zone placement, disabled unused
  interfaces, HAProxy/TLS and rollback proof remain E09.2-E09.8.
- ДКБ-55/56: the build contract stores no runtime secrets. Kolla/Ansible secret references, DB/RabbitMQ
  credentials and rotation proof remain later deployment evidence.

Evidence: `tests/test_e09_kolla_image_build.py`, `deploy/kolla/README.md`,
`deploy/kolla/kolla-build.conf.example`, `deploy/kolla/scripts/build-images.sh`,
`docs/generated/e09-kolla-image-build.md` and ExecPlan `docs/execplans/E09-kolla-image-build.md`.
```

- [ ] **Step 4: Update ExecPlan with completed evidence task**

Record the created evidence, traceability and risk-register changes in `docs/execplans/E09-kolla-image-build.md`.

- [ ] **Step 5: Run targeted tests**

Run:

```bash
backend/.venv/bin/python -m pytest tests/test_e09_kolla_image_build.py -q
```

Expected: `6 passed`.

- [ ] **Step 6: Commit E09.1 implementation artifacts**

Run:

```bash
git add tests/test_e09_kolla_image_build.py deploy/kolla docs/generated/e09-kolla-image-build.md docs/generated/risk-register.md docs/11_DKB_TRACEABILITY.md docs/execplans/E09-kolla-image-build.md
git commit -m "docs: add E09 Kolla image build contract"
```

Expected: one commit with tests, deploy artifacts and evidence.

## Task 4: Final Verification and Review

**Files:**
- Modify: `docs/execplans/E09-kolla-image-build.md`

- [ ] **Step 1: Run repository verification**

Run these commands from `/Users/dmitry/Desktop/dawn/.worktrees/e09-kolla-image-build`:

```bash
backend/.venv/bin/python -m pytest tests/test_e09_kolla_image_build.py -q
make lint
make typecheck
make test
make security
git diff --check
```

Expected:

- targeted test reports `6 passed`;
- `make lint` reports backend ruff, frontend eslint and secret scan passing;
- `make typecheck` reports mypy and frontend typecheck passing;
- `make test` reports backend and frontend tests passing;
- `make security` reports secret scan passing;
- `git diff --check` exits `0`.

- [ ] **Step 2: Self-review deployment/security diff**

Run:

```bash
git diff --stat HEAD~1..HEAD
git diff -- deploy/kolla tests/test_e09_kolla_image_build.py docs/generated/e09-kolla-image-build.md docs/11_DKB_TRACEABILITY.md docs/generated/risk-register.md
rg -n "password|token|private key|BEGIN|latest|production approved|12 permanent containers proven" deploy/kolla docs/generated/e09-kolla-image-build.md docs/11_DKB_TRACEABILITY.md docs/generated/risk-register.md tests/test_e09_kolla_image_build.py
```

Expected:

- diff only contains E09.1 files;
- any `token`/`password` hits are explanatory text, not values;
- `latest` appears only in the explicit rejection rule or explanatory prohibition;
- no production approval or 12-container proof is claimed.

- [ ] **Step 3: Update ExecPlan final command log**

In `docs/execplans/E09-kolla-image-build.md`, record each command from Task 4 Step 1 and its result.

- [ ] **Step 4: Commit ExecPlan final update**

Run:

```bash
git add docs/execplans/E09-kolla-image-build.md
git commit -m "docs: record E09 image build verification"
```

Expected: a second commit recording final verification evidence.

- [ ] **Step 5: Report branch status**

Run:

```bash
git status --short --branch
git log --oneline -3
```

Expected: clean branch `e09-kolla-image-build` ahead of `main` by E09.1 implementation commits.

## References Checked for This Plan

- Local task: `tasks/E09_KOLLA_DEPLOY.md`.
- Local deployment requirements: `docs/12_DEPLOY_ROCKY_KOLLA.md`.
- Local HA requirements: `docs/09_PERFORMANCE_HA.md`.
- Local security requirements: `docs/10_SECURITY_DKB.md`.
- E08 security review: `docs/generated/e08-security-review.md`.
- Official Kolla image build documentation: https://docs.openstack.org/kolla/latest/admin/image-building.html
