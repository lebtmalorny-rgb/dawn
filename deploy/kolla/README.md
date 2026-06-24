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
