#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
KOLLA_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
CONFIG_FILE="$KOLLA_DIR/kolla-build.conf.example"
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
require_var CLOUD_UI_FRONTEND_DIST_ROOT
require_var CLOUD_UI_FRONTEND_DIST_SHA256

if [ -n "${KOLLA_BUILD_CONFIG:-}" ]; then
    printf '%s\n' "KOLLA_BUILD_CONFIG override is not supported for E09.1" >&2
    exit 2
fi

if [ "$CLOUD_UI_IMAGE_TAG" = "latest" ]; then
    printf '%s\n' "CLOUD_UI_IMAGE_TAG must not be latest" >&2
    exit 2
fi

SOURCE_ROOT="$(cd "$CLOUD_UI_SOURCE_ROOT" && pwd)"
FRONTEND_DIST_ROOT="$(cd "$CLOUD_UI_FRONTEND_DIST_ROOT" && pwd)"

if [ ! -d "$SOURCE_ROOT/backend" ] || [ ! -d "$SOURCE_ROOT/frontend" ]; then
    printf '%s\n' "CLOUD_UI_SOURCE_ROOT must contain backend and frontend directories" >&2
    exit 2
fi

if ! git -C "$SOURCE_ROOT" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    printf '%s\n' "CLOUD_UI_SOURCE_ROOT must be a git checkout for source pin verification" >&2
    exit 2
fi

if ! SOURCE_PIN_COMMIT="$(git -C "$SOURCE_ROOT" rev-parse --verify "$CLOUD_UI_SOURCE_PIN^{commit}" 2>/dev/null)"; then
    printf '%s\n' "CLOUD_UI_SOURCE_PIN must resolve to a Git commit" >&2
    exit 2
fi

if ! find "$FRONTEND_DIST_ROOT" -type f -print -quit | grep -q .; then
    printf '%s\n' "CLOUD_UI_FRONTEND_DIST_ROOT must contain built frontend files" >&2
    exit 2
fi

hash_directory() {
    local directory="$1"
    (
        cd "$directory"
        find . -type f -print0 \
            | LC_ALL=C sort -z \
            | while IFS= read -r -d '' file_path; do
                shasum -a 256 "$file_path"
            done \
            | shasum -a 256 \
            | awk '{print $1}'
    )
}

ACTUAL_FRONTEND_DIST_SHA256="$(hash_directory "$FRONTEND_DIST_ROOT")"
if [ "$ACTUAL_FRONTEND_DIST_SHA256" != "$CLOUD_UI_FRONTEND_DIST_SHA256" ]; then
    printf '%s\n' "CLOUD_UI_FRONTEND_DIST_SHA256 does not match frontend dist" >&2
    exit 2
fi

SOURCE_BUILD_ROOT="$(mktemp -d "${TMPDIR:-/tmp}/cloud-ui-kolla-source.XXXXXX")"
RENDERED_CONFIG="$(mktemp "${TMPDIR:-/tmp}/cloud-ui-kolla-build.XXXXXX.conf")"
trap 'rm -rf "$SOURCE_BUILD_ROOT"; rm -f "$RENDERED_CONFIG"' EXIT

git -C "$SOURCE_ROOT" archive --format=tar "$SOURCE_PIN_COMMIT" backend \
    | tar -C "$SOURCE_BUILD_ROOT" -xf -
git -C "$SOURCE_ROOT" archive --format=tar "$SOURCE_PIN_COMMIT" frontend \
    | tar -C "$SOURCE_BUILD_ROOT" -xf -
rm -rf "$SOURCE_BUILD_ROOT/frontend/dist"
mkdir -p "$SOURCE_BUILD_ROOT/frontend/dist"
cp -a "$FRONTEND_DIST_ROOT"/. "$SOURCE_BUILD_ROOT/frontend/dist/"

awk -v backend_source="$SOURCE_BUILD_ROOT/backend" \
    -v frontend_source="$SOURCE_BUILD_ROOT/frontend" \
    -v source_pin="$SOURCE_PIN_COMMIT" '
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

if ! grep -Fx "location = $SOURCE_BUILD_ROOT/backend" "$RENDERED_CONFIG" >/dev/null; then
    printf '%s\n' "Rendered Kolla config did not point backend source at sanitized archive" >&2
    exit 2
fi

if ! grep -Fx "location = $SOURCE_BUILD_ROOT/frontend" "$RENDERED_CONFIG" >/dev/null; then
    printf '%s\n' "Rendered Kolla config did not point frontend source at sanitized archive" >&2
    exit 2
fi

REFERENCE_COUNT="$(awk -v expected="reference = $SOURCE_PIN_COMMIT" '
    $0 == expected { count++ }
    END { print count + 0 }
' "$RENDERED_CONFIG")"
if [ "$REFERENCE_COUNT" -ne 2 ]; then
    printf '%s\n' "Rendered Kolla config did not record the resolved source pin twice" >&2
    exit 2
fi

if grep -F "location = /srv/kolla/cloud-ui/sources/" "$RENDERED_CONFIG" >/dev/null; then
    printf '%s\n' "Rendered Kolla config still contains default mutable source paths" >&2
    exit 2
fi

if grep -F "reference = pinned-by-CLOUD_UI_SOURCE_PIN" "$RENDERED_CONFIG" >/dev/null; then
    printf '%s\n' "Rendered Kolla config still contains unresolved source pin placeholders" >&2
    exit 2
fi

CONFIG_FILE="$RENDERED_CONFIG"

COMMON_ARGS=(
    --config-file "$CONFIG_FILE"
    --docker-dir "$DOCKER_DIR"
    --profile cloud-ui
    --tag "$CLOUD_UI_IMAGE_TAG"
    --build-args "CLOUD_UI_SOURCE_PIN=$SOURCE_PIN_COMMIT"
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
