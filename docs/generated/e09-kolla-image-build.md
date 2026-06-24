# E09.1 Kolla Image Build Evidence

- Stage: E09.1 Kolla image build
- Date: 2026-06-24
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
- `CLOUD_UI_SOURCE_ROOT`
- `CLOUD_UI_FRONTEND_DIST_ROOT`
- `CLOUD_UI_FRONTEND_DIST_SHA256`

`deploy/kolla/scripts/build-images.sh` rejects `CLOUD_UI_IMAGE_TAG=latest`.
It also renders tracked backend/frontend source trees from `git archive CLOUD_UI_SOURCE_PIN`, verifies
the prebuilt frontend `dist` directory against `CLOUD_UI_FRONTEND_DIST_SHA256`, and renders a temporary
Kolla config that points backend and frontend source sections at those sanitized directories.

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
  evidence remains pending. The wrapper builds Kolla source directories from a pinned Git archive and
  separately verifies the prebuilt frontend dist hash before invoking `kolla-build`.
- ДКБ-76/77/80: deployment image interfaces are documented. Network ACLs, management-zone placement,
  disabled unused interfaces and runtime Kolla inspection remain later E09 evidence.
- ДКБ-55/56: no secrets are stored in the build contract. Secret injection and rotation remain
  deployment-pipeline evidence.

## Rollback

Revert the E09.1 commit. This slice changes only repository files and does not modify database schema,
queue state, registry contents, remote hosts, Vault paths, Kolla inventory or production credentials.
