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
export CLOUD_UI_SOURCE_PIN='<git-sha>'
export CLOUD_UI_SOURCE_ROOT='/path/to/cloud-ui-git-checkout'
export CLOUD_UI_FRONTEND_DIST_ROOT='/path/to/prebuilt/frontend-dist'
export CLOUD_UI_FRONTEND_DIST_SHA256='<directory-sha256>'
```

The tag `latest` is rejected by `scripts/build-images.sh`. The wrapper renders temporary source
directories from `git archive CLOUD_UI_SOURCE_PIN` for tracked backend/frontend files, verifies the
prebuilt frontend `dist` directory against `CLOUD_UI_FRONTEND_DIST_SHA256`, copies that verified dist
into the temporary frontend source tree, then renders a temporary Kolla config that points the backend
and frontend source sections at those sanitized directories. `KOLLA_BUILD_CONFIG` and
`KOLLA_DOCKER_DIR` overrides are not supported in E09.1; the wrapper always starts from the checked-in
`kolla-build.conf.example` and `deploy/kolla/docker`, then validates the rendered source paths and
resolved commit before invoking `kolla-build`.

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

Kolla Build turns each source section into an archive named after the image source section, so the
templates intentionally use `ADD cloud-ui-backend-archive` and `ADD cloud-ui-frontend-archive`.

## Security Rules

- Do not store registry credentials, scanner tokens, signing keys, Kolla passwords or production URLs
  in this directory.
- Backend `api`, `worker`, `events`, `db-upgrade` and `smoke` run from the same
  `cloud-ui-backend` image.
- The frontend image serves prebuilt static assets and does not carry the frontend build toolchain.
- ДКБ-69 remains open for the Python backend interpreter unless a formal waiver is approved.
