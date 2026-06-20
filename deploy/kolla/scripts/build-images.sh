#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"

KOLLA_BUILD="${KOLLA_BUILD:-kolla-build}"
KOLLA_CONFIG="${KOLLA_CONFIG:-${repo_root}/deploy/kolla/kolla-build.conf.example}"
KOLLA_DOCKER_DIR="${KOLLA_DOCKER_DIR:-${repo_root}/deploy/kolla/docker}"
KOLLA_LOGS_DIR="${KOLLA_LOGS_DIR:-/tmp/dawn-kolla-build/logs}"
KOLLA_WORK_DIR="${KOLLA_WORK_DIR:-/tmp/dawn-kolla-build/work}"
CLOUD_UI_REGISTRY="${CLOUD_UI_REGISTRY:-192.168.10.15:5000}"
CLOUD_UI_TAG="${CLOUD_UI_TAG:-2025.1-rocky-9}"
CLOUD_UI_SOURCE="${CLOUD_UI_SOURCE:-/opt/dawn/source}"
CLOUD_UI_IMAGES_REGEX="${CLOUD_UI_IMAGES_REGEX:-^cloud-ui-(backend|frontend)$}"

if [ ! -d "${CLOUD_UI_SOURCE}" ]; then
  printf 'source directory not found: %s\n' "${CLOUD_UI_SOURCE}" >&2
  printf 'sync this repository to the build host first, for example /opt/dawn/source\n' >&2
  exit 2
fi

if [ ! -d "${CLOUD_UI_SOURCE}/frontend/dist" ]; then
  printf 'frontend/dist not found under %s; run npm ci && npm run build before kolla-build\n' "${CLOUD_UI_SOURCE}" >&2
  exit 2
fi

mkdir -p "${KOLLA_LOGS_DIR}" "${KOLLA_WORK_DIR}"

exec "${KOLLA_BUILD}" \
  --config-file "${KOLLA_CONFIG}" \
  --docker-dir "${KOLLA_DOCKER_DIR}" \
  --logs-dir "${KOLLA_LOGS_DIR}" \
  --work-dir "${KOLLA_WORK_DIR}" \
  --registry "${CLOUD_UI_REGISTRY}" \
  --tag "${CLOUD_UI_TAG}" \
  --push \
  "${CLOUD_UI_IMAGES_REGEX}"
