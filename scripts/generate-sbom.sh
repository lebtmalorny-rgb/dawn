#!/usr/bin/env bash
set -euo pipefail

output_path="${SBOM_OUTPUT:-docs/generated/e08-supply-chain.md}"
backend_image="${BACKEND_IMAGE:-cloud-ui-backend:dev}"
frontend_image="${FRONTEND_IMAGE:-cloud-ui-frontend:dev}"
export DOCKER_API_VERSION="${DOCKER_API_VERSION:-1.44}"

require_command() {
  if ! command -v "$1" >/dev/null 2>&1; then
    printf 'required command not found: %s\n' "$1" >&2
    exit 1
  fi
}

sbom_digest() {
  if command -v sha256sum >/dev/null 2>&1; then
    sha256sum "$1" | awk '{print $1}'
    return
  fi
  if command -v shasum >/dev/null 2>&1; then
    shasum -a 256 "$1" | awk '{print $1}'
    return
  fi
  printf 'required command not found: sha256sum or shasum\n' >&2
  exit 1
}

sbom_line_count() {
  wc -l < "$1" | tr -d '[:space:]'
}

image_inspect_line() {
  local image="$1"
  docker image inspect "$image" \
    --format 'tags={{json .RepoTags}} user={{.Config.User}} cmd={{json .Config.Cmd}} id={{.Id}}'
}

write_image_section() {
  local image="$1"
  local sbom_file="$2"
  local inspect_line="$3"
  local digest
  local lines

  digest="$(sbom_digest "$sbom_file")"
  lines="$(sbom_line_count "$sbom_file")"

  {
    printf '### `%s`\n\n' "$image"
    printf -- '- Image inspect: `%s`.\n' "$inspect_line"
    printf -- '- Docker SBOM command: `docker sbom --format table %s`.\n' "$image"
    printf -- '- SBOM table line count: `%s`.\n' "$lines"
    printf -- '- SBOM table SHA-256: `%s`.\n\n' "$digest"
  } >> "$output_path"
}

require_command docker
require_command awk

if ! docker sbom version >/dev/null 2>&1; then
  printf 'docker sbom plugin is required for make sbom\n' >&2
  exit 1
fi

tmp_dir="$(mktemp -d)"
trap 'rm -rf "$tmp_dir"' EXIT

backend_sbom="$tmp_dir/backend-sbom.txt"
frontend_sbom="$tmp_dir/frontend-sbom.txt"

docker sbom --format table "$backend_image" > "$backend_sbom"
docker sbom --format table "$frontend_image" > "$frontend_sbom"

backend_inspect="$(image_inspect_line "$backend_image")"
frontend_inspect="$(image_inspect_line "$frontend_image")"
sbom_version="$(docker sbom version | tr '\n' '; ' | sed 's/[; ][; ]*$//')"

mkdir -p "$(dirname "$output_path")"
{
  printf '# E08.6 Supply Chain Evidence\n\n'
  printf -- '- Stage: E08.6\n'
  printf -- '- Date: %s\n' "$(date -u '+%Y-%m-%d')"
  printf -- '- Scope: local backend/frontend portal images built from this repository\n'
  printf -- '- Rule: this artifact contains no registry credential, private key, token or production endpoint.\n\n'
  printf '## Tooling\n\n'
  printf -- '- Docker SBOM plugin: `%s`.\n' "$sbom_version"
  printf -- '- Standalone `syft`, `trivy`, `grype` and `pip-audit` are not required by this local gate.\n\n'
  printf '## Base Image Pins\n\n'
  printf -- '- Backend: `python:3.11-slim@sha256:ae52c5bef62a6bdd42cd1e8dffef86b9cd284bde9427da79839de7a4b983e7ca`.\n'
  printf -- '- Frontend build: `node:24-alpine@sha256:156b55f92e98ccd5ef49578a8cea0df4679826564bad1c9d4ef04462b9f0ded6`.\n'
  printf -- '- Frontend runtime: `nginxinc/nginx-unprivileged:1.27-alpine@sha256:65e3e85dbaed8ba248841d9d58a899b6197106c23cb0ff1a132b7bfe0547e4c0`.\n\n'
  printf '## Docker SBOM Summary\n\n'
} > "$output_path"

write_image_section "$backend_image" "$backend_sbom" "$backend_inspect"
write_image_section "$frontend_image" "$frontend_sbom" "$frontend_inspect"

{
  printf '## Dependency Lock Evidence\n\n'
  printf -- '- Frontend install path uses `frontend/package-lock.json` with `npm ci`.\n'
  printf -- '- Backend runtime and dev dependencies in `backend/pyproject.toml` are exact `==` pins.\n'
  printf -- '- Python transitive lock and Python CVE audit remain pending until a package-policy decision chooses a lock/audit tool.\n\n'
  printf '## Residual Gaps\n\n'
  printf -- '- ДКБ-69: Python backend still requires an interpreter, and inherited base images may contain shell or package-manager components. This local SBOM gate does not claim full no-interpreter/no-shell compliance.\n'
  printf -- '- ДКБ-70: this slice does not claim corporate registry push, immutable production pull-by-digest, image signing or provenance verification.\n'
  printf -- '- Vulnerability policy: npm audit is verified separately in the E08.6 command log; full image/Python CVE scanner policy remains an external/tooling gap.\n'
  printf -- '- License inventory is not enforced in this slice because no approved license policy or scanner has been selected.\n\n'
  printf '## Rollback\n\n'
  printf 'Revert the E08.6 commit. No database schema, external registry, remote host, Vault path, queue or production secret is changed.\n'
} >> "$output_path"

printf 'Wrote %s\n' "$output_path"
