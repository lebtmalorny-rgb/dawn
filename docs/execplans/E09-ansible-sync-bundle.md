# ExecPlan: E09 Ansible Sync Bundle

## Goal

Create a repository-side local-only export bundle for Cloud UI Kolla-Ansible artifacts.

## Scope

This slice creates tests, an exporter, local bundle evidence, documentation, traceability and a risk
row. It does not copy files to a remote host, run live mutating Kolla actions, change DB/MQ/Vault or
claim E09 deployment acceptance.

## Progress

- [x] 2026-06-26: Design approved in `docs/superpowers/specs/2026-06-26-e09-ansible-sync-bundle-design.md`.
- [x] RED contract tests.
- [x] Exporter implementation.
- [x] Evidence and traceability.
- [x] Verification and review.

## Verification

- `UV_CACHE_DIR=/tmp/dawn-uv-cache UV_PYTHON_INSTALL_DIR=/tmp/dawn-uv-python UV_PROJECT_ENVIRONMENT=/tmp/dawn-e09-sync-bundle-venv uv run --python 3.11 --project backend --extra dev pytest tests/test_e09_ansible_sync_bundle.py tests/test_e09_live_reconfigure_bundle.py tests/test_e09_kolla_ansible_role.py -q`
- `UV_CACHE_DIR=/tmp/dawn-uv-cache UV_PYTHON_INSTALL_DIR=/tmp/dawn-uv-python UV_PROJECT_ENVIRONMENT=/tmp/dawn-e09-sync-bundle-venv uv run --python 3.11 --project backend --extra dev ruff check tests/test_e09_ansible_sync_bundle.py deploy/kolla/scripts/export-ansible-bundle.py`
- `./scripts/secret-scan.sh`
- `git diff --check`

## Rollback

Revert this repository slice and remove any locally generated `/tmp/dawn-e09-ansible-sync-bundle`
directory. No remote host, registry, database, queue, Vault path or credential is changed.
