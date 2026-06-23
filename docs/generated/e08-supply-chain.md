# E08.6 Supply Chain Evidence

- Stage: E08.6
- Date: 2026-06-23
- Scope: local backend/frontend portal images built from this repository
- Rule: this artifact contains no registry credential, private key, token or production endpoint.

## Tooling

- Docker SBOM plugin: `Application:        docker-sbom (0.6.0);Provider:           syft (v0.43.0);GitCommit:          741c56e0db8c65d853f18e0a9b23287d33b30e05;GitDescription:     v0.6.0;Platform:           darwin/arm64`.
- Standalone `syft`, `trivy`, `grype` and `pip-audit` are not required by this local gate.

## Base Image Pins

- Backend: `python:3.11-slim@sha256:ae52c5bef62a6bdd42cd1e8dffef86b9cd284bde9427da79839de7a4b983e7ca`.
- Frontend build: `node:24-alpine@sha256:156b55f92e98ccd5ef49578a8cea0df4679826564bad1c9d4ef04462b9f0ded6`.
- Frontend runtime: `nginxinc/nginx-unprivileged:1.27-alpine@sha256:65e3e85dbaed8ba248841d9d58a899b6197106c23cb0ff1a132b7bfe0547e4c0`.

## Docker SBOM Summary

### `cloud-ui-backend:dev`

- Image inspect: `tags=["cloud-ui-backend:dev"] user=cloudui cmd=["cloud-ui","api"] id=sha256:8cf0d014e71be6aa2b265b7479aaffddec44a57585b968d6bfb729ad7c185c7a`.
- Docker SBOM command: `docker sbom --format table cloud-ui-backend:dev`.
- SBOM table line count: `137`.
- SBOM table SHA-256: `be82bb0329907bd0697e15ae790f53275a04d6a3e4c5b97273c82e5f9d36c6ee`.

### `cloud-ui-frontend:dev`

- Image inspect: `tags=["cloud-ui-frontend:dev"] user=101 cmd=["nginx","-g","daemon off;"] id=sha256:c313d8a5199f864d0e9bf7b4a96a22d2ff1c784be9591f4bc91a73c66c7d74d2`.
- Docker SBOM command: `docker sbom --format table cloud-ui-frontend:dev`.
- SBOM table line count: `69`.
- SBOM table SHA-256: `b328635eefb4957612f3b9d546eb4b777b5b92d8a0f6c2222d42485ac488da29`.

## Dependency Lock Evidence

- Frontend install path uses `frontend/package-lock.json` with `npm ci`.
- Backend runtime and dev dependencies in `backend/pyproject.toml` are exact `==` pins.
- Python transitive lock and Python CVE audit remain pending until a package-policy decision chooses a lock/audit tool.

## Residual Gaps

- ДКБ-69: Python backend still requires an interpreter, and inherited base images may contain shell or package-manager components. This local SBOM gate does not claim full no-interpreter/no-shell compliance.
- ДКБ-70: this slice does not claim corporate registry push, immutable production pull-by-digest, image signing or provenance verification.
- Vulnerability policy: npm audit is verified separately in the E08.6 command log; full image/Python CVE scanner policy remains an external/tooling gap.
- License inventory is not enforced in this slice because no approved license policy or scanner has been selected.

## Rollback

Revert the E08.6 commit. No database schema, external registry, remote host, Vault path, queue or production secret is changed.
