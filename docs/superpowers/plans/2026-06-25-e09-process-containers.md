# E09.5 Process Containers Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a tested repository/synthetic process topology contract for twelve permanent Cloud UI containers across three control/UI nodes.

**Architecture:** Keep `cloud_ui_services` as the four-service source of truth and add a derived process topology matrix for three nodes. Publish topology facts from the Kolla role and record sanitized evidence without live deployment claims.

**Tech Stack:** Kolla-Ansible role YAML, pytest YAML contract tests, Markdown evidence.

---

### Task 1: RED Process Topology Tests

**Files:**
- Create: `tests/test_e09_process_containers.py`
- Modify: `deploy/kolla/ansible/roles/cloud_ui/defaults/main.yml`
- Modify: `deploy/kolla/ansible/roles/cloud_ui/tasks/containers.yml`

- [ ] **Step 1: Write failing topology tests**

Add tests requiring `cloud_ui_control_ui_nodes`, expected count defaults, twelve `cloud_ui_process_topology` entries and no migration job in permanent topology.

- [ ] **Step 2: Verify RED**

Run: `backend/.venv/bin/python -m pytest tests/test_e09_process_containers.py -q`
Expected: fail because the topology defaults/evidence do not exist.

- [ ] **Step 3: Implement topology defaults and facts**

Add node labels, total counts, topology list and task facts in the role.

- [ ] **Step 4: Verify GREEN**

Run: `backend/.venv/bin/python -m pytest tests/test_e09_process_containers.py -q`
Expected: topology tests pass.

### Task 2: Validation and Adjacent Contract Updates

**Files:**
- Modify: `deploy/kolla/ansible/roles/cloud_ui/tasks/validate.yml`
- Modify: `tests/test_e09_kolla_ansible_role.py`

- [ ] **Step 1: Add failing validation assertions**

Extend tests to require validation for three nodes and twelve permanent containers.

- [ ] **Step 2: Verify RED**

Run: `backend/.venv/bin/python -m pytest tests/test_e09_process_containers.py tests/test_e09_kolla_ansible_role.py -q`
Expected: fail until validation is added.

- [ ] **Step 3: Implement validation**

Add Ansible assert conditions for node count, per-node count and total count.

- [ ] **Step 4: Verify GREEN**

Run: `backend/.venv/bin/python -m pytest tests/test_e09_process_containers.py tests/test_e09_kolla_ansible_role.py -q`
Expected: tests pass.

### Task 3: Evidence and DKB Updates

**Files:**
- Create: `docs/generated/e09-process-containers.md`
- Modify: `docs/11_DKB_TRACEABILITY.md`
- Modify: `docs/generated/risk-register.md`
- Modify: `docs/execplans/E09-process-containers.md`

- [ ] **Step 1: Add failing evidence assertions**

Extend tests to require generated evidence, DKB references and live-deploy limitations.

- [ ] **Step 2: Verify RED**

Run: `backend/.venv/bin/python -m pytest tests/test_e09_process_containers.py -q`
Expected: fail until docs are written.

- [ ] **Step 3: Add evidence**

Create E09.5 evidence, update traceability, add risk row for mistaking synthetic topology for live
container proof, and keep ExecPlan current.

- [ ] **Step 4: Verify GREEN**

Run: `backend/.venv/bin/python -m pytest tests/test_e09_process_containers.py -q`
Expected: all E09.5 tests pass.

### Task 4: Final Verification and Commit

**Files:**
- Review all modified files.

- [ ] **Step 1: Run targeted tests**

Run: `backend/.venv/bin/python -m pytest tests/test_e09_process_containers.py tests/test_e09_kolla_ansible_role.py tests/test_e09_migration_job.py -q`
Expected: all selected tests pass.

- [ ] **Step 2: Run project gates**

Run: `make lint`, `make typecheck`, `make security`, `make test`, `backend/.venv/bin/python -m pytest tests -q`, `git diff --check`.
Expected: all commands exit 0.

- [ ] **Step 3: Commit**

Run: `git add ...` and `git commit -m "deploy: add E09 process topology contract"`.
Expected: one logical E09.5 implementation commit after the planning commit.
