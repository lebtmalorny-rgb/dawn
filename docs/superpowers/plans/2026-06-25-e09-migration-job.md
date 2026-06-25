# E09.4 Migration Job Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a tested repository-side one-shot Kolla migration job contract for `cloud-ui db-upgrade`.

**Architecture:** Reuse the existing backend image and CLI command. The Kolla role defines a separate
`cloud_ui_db_migrate` job and execution policy, keeps it out of permanent service definitions, and
records evidence that live execution is pending.

**Tech Stack:** Python 3.11, pytest, YAML contract tests, Kolla-Ansible role defaults/tasks, Alembic CLI.

---

### Task 1: Migration Job Contract Tests

**Files:**
- Create: `tests/test_e09_migration_job.py`
- Modify: `deploy/kolla/ansible/roles/cloud_ui/defaults/main.yml`
- Modify: `deploy/kolla/ansible/roles/cloud_ui/tasks/main.yml`
- Create: `deploy/kolla/ansible/roles/cloud_ui/tasks/migration.yml`

- [ ] **Step 1: Write failing tests**

Add tests that load the role YAML and require `cloud_ui_migration_job`, `cloud_ui_migration_execution_policy`, `migration.yml`, and `docs/generated/e09-migration-job.md`.

- [ ] **Step 2: Verify RED**

Run: `backend/.venv/bin/python -m pytest tests/test_e09_migration_job.py -q`
Expected: fail because the test file or required migration artifacts are missing.

- [ ] **Step 3: Implement role contract**

Add migration defaults and `migration.yml`. Insert `migration.yml` in `tasks/main.yml` after
`config.yml` and before `containers.yml`.

- [ ] **Step 4: Verify GREEN**

Run: `backend/.venv/bin/python -m pytest tests/test_e09_migration_job.py -q`
Expected: migration contract tests pass.

### Task 2: Backend CLI Safety Tests

**Files:**
- Modify: `tests/test_e09_migration_job.py`
- Modify: `backend/src/cloud_ui/cli.py`

- [ ] **Step 1: Write failing tests**

Add tests that monkeypatch Alembic command functions and assert `main(["api"])` does not call
`upgrade`, while `main(["db-upgrade"])` does call `upgrade`.

- [ ] **Step 2: Verify RED**

Run: `backend/.venv/bin/python -m pytest tests/test_e09_migration_job.py -q`
Expected: fail on the missing precheck or logging behavior added by the test.

- [ ] **Step 3: Implement minimal CLI behavior**

Keep API startup separate from migration execution. If the tests require CLI output, print a sanitized
success line after Alembic upgrade without database URL or credentials.

- [ ] **Step 4: Verify GREEN**

Run: `backend/.venv/bin/python -m pytest tests/test_e09_migration_job.py -q`
Expected: all E09.4 tests pass.

### Task 3: Evidence and Traceability

**Files:**
- Create: `docs/generated/e09-migration-job.md`
- Modify: `docs/11_DKB_TRACEABILITY.md`
- Modify: `docs/generated/risk-register.md`
- Modify: `docs/execplans/E09-migration-job.md`

- [ ] **Step 1: Write failing evidence assertions**

Extend `tests/test_e09_migration_job.py` to require stage name, one-shot semantics, no live execution
claim, DKB rows and remaining risks.

- [ ] **Step 2: Verify RED**

Run: `backend/.venv/bin/python -m pytest tests/test_e09_migration_job.py -q`
Expected: fail until generated evidence and traceability are updated.

- [ ] **Step 3: Add evidence**

Write sanitized evidence, update DKB traceability and add a risk-register row for mistaking repository
contract for live migration proof.

- [ ] **Step 4: Verify GREEN**

Run: `backend/.venv/bin/python -m pytest tests/test_e09_migration_job.py -q`
Expected: all E09.4 tests pass.

### Task 4: Final Verification

**Files:**
- Review all modified files.

- [ ] **Step 1: Run targeted tests**

Run: `backend/.venv/bin/python -m pytest tests/test_e09_migration_job.py tests/test_e09_kolla_ansible_role.py tests/test_e09_db_rabbitmq_provisioning.py -q`
Expected: all selected tests pass.

- [ ] **Step 2: Run gates**

Run: `make lint`, `make typecheck`, `make security`, `make test`, `git diff --check`.
Expected: all commands exit 0.

- [ ] **Step 3: Commit**

Run: `git add ...` and `git commit -m "deploy: add E09 migration job contract"`.
Expected: one logical E09.4 commit on branch `e09-migration-job`.
