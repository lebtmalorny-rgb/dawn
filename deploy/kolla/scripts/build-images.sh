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
