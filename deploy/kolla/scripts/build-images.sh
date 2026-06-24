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
require_var CLOUD_UI_SOURCE_ROOT

if [ "$CLOUD_UI_IMAGE_TAG" = "latest" ]; then
    printf '%s\n' "CLOUD_UI_IMAGE_TAG must not be latest" >&2
    exit 2
fi

SOURCE_ROOT="$(cd "$CLOUD_UI_SOURCE_ROOT" && pwd)"

if [ ! -d "$SOURCE_ROOT/backend" ] || [ ! -d "$SOURCE_ROOT/frontend" ]; then
    printf '%s\n' "CLOUD_UI_SOURCE_ROOT must contain backend and frontend directories" >&2
    exit 2
fi

if ! git -C "$SOURCE_ROOT" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    printf '%s\n' "CLOUD_UI_SOURCE_ROOT must be a git checkout for source pin verification" >&2
    exit 2
fi

ACTUAL_SOURCE_PIN="$(git -C "$SOURCE_ROOT" rev-parse HEAD)"
if [ "$ACTUAL_SOURCE_PIN" != "$CLOUD_UI_SOURCE_PIN" ]; then
    printf '%s\n' "CLOUD_UI_SOURCE_PIN does not match source checkout" >&2
    exit 2
fi

if ! git -C "$SOURCE_ROOT" diff --quiet; then
    printf '%s\n' "CLOUD_UI_SOURCE_ROOT has unstaged changes" >&2
    exit 2
fi

if ! git -C "$SOURCE_ROOT" diff --cached --quiet; then
    printf '%s\n' "CLOUD_UI_SOURCE_ROOT has staged changes" >&2
    exit 2
fi

RENDERED_CONFIG="$(mktemp "${TMPDIR:-/tmp}/cloud-ui-kolla-build.XXXXXX.conf")"
trap 'rm -f "$RENDERED_CONFIG"' EXIT

awk -v backend_source="$SOURCE_ROOT/backend" \
    -v frontend_source="$SOURCE_ROOT/frontend" \
    -v source_pin="$CLOUD_UI_SOURCE_PIN" '
    $0 == "location = /srv/kolla/cloud-ui/sources/backend" {
        print "location = " backend_source
        next
    }
    $0 == "location = /srv/kolla/cloud-ui/sources/frontend" {
        print "location = " frontend_source
        next
    }
    $0 == "reference = pinned-by-CLOUD_UI_SOURCE_PIN" {
        print "reference = " source_pin
        next
    }
    { print }
' "$CONFIG_FILE" > "$RENDERED_CONFIG"
CONFIG_FILE="$RENDERED_CONFIG"

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
