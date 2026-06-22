# E05 Resource Groups Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build project-scoped portal resource groups with explicit membership, safe dynamic preview and group-aware inventory filtering.

**Architecture:** Add a new `cloud_ui.groups` backend package for portal-owned group data, rule validation and API routes. Keep OpenStack inventory projections in `cloud_ui.inventory`; inventory only receives a narrow `group_id` filter integration after backend group access checks.

**Tech Stack:** Python 3.11, FastAPI, SQLAlchemy Core, Alembic, Pydantic, pytest, React 19, PatternFly, TypeScript, Vitest.

---

## File Structure

Create:

```text
backend/src/cloud_ui/migrations/versions/0004_resource_groups.py
backend/src/cloud_ui/groups/__init__.py
backend/src/cloud_ui/groups/models.py
backend/src/cloud_ui/groups/schema.py
backend/src/cloud_ui/groups/repository.py
backend/src/cloud_ui/groups/rules.py
backend/src/cloud_ui/groups/routes.py
backend/tests/groups/test_group_migration.py
backend/tests/groups/test_group_repository.py
backend/tests/groups/test_group_rules.py
backend/tests/groups/test_group_api.py
frontend/src/groups.ts
```

Modify:

```text
backend/src/cloud_ui/api.py
backend/src/cloud_ui/inventory/models.py
backend/src/cloud_ui/inventory/repository.py
backend/src/cloud_ui/inventory/routes.py
backend/src/cloud_ui/security/identity.py
backend/src/cloud_ui/security/mock_identity.py
backend/src/cloud_ui/security/routes.py
backend/tests/inventory/test_inventory_api.py
backend/tests/inventory/test_repository.py
backend/tests/security/test_mock_identity.py
backend/tests/security/test_security_api.py
frontend/src/App.tsx
frontend/src/App.test.tsx
frontend/src/api.ts
frontend/src/styles.css
docs/04_DOMAIN_AND_DATA.md
docs/05_API_AND_INTEGRATIONS.md
docs/06_AUTH_RBAC_SESSIONS.md
docs/11_DKB_TRACEABILITY.md
docs/generated/api-register.md
docs/generated/integration-register.md
docs/generated/risk-register.md
docs/execplans/E05-resource-groups.md
```

---

### Task 1: P0 Project Scope And Capabilities

**Files:**
- Modify: `backend/src/cloud_ui/security/identity.py`
- Modify: `backend/src/cloud_ui/security/mock_identity.py`
- Modify: `backend/src/cloud_ui/security/routes.py`
- Modify: `backend/tests/security/test_mock_identity.py`
- Modify: `backend/tests/security/test_security_api.py`

- [ ] **Step 1: Write failing scope tests**

Add assertions to `backend/tests/security/test_mock_identity.py`:

```python
def test_operator_has_project_scope_and_group_manage() -> None:
    provider = build_mock_identity_provider()

    result = provider.authenticate(LoginRequest(login="operator", credential="operator-code"))

    assert result.subject.scope_type == "project"
    assert result.subject.scope_id == "project-a"
    assert "group.manage" in result.subject.capabilities
```

Add assertions to `backend/tests/security/test_security_api.py` in the existing capabilities test:

```python
assert capabilities["scope"] == {"type": "project", "id": "project-a"}
assert "group.manage" in capabilities["capabilities"]
```

- [ ] **Step 2: Verify RED**

Run:

```bash
cd backend && .venv/bin/python -m pytest tests/security/test_mock_identity.py tests/security/test_security_api.py -q
```

Expected: failures mention missing `scope_type`/`scope_id` or missing `group.manage`.

- [ ] **Step 3: Implement P0 scope fields**

Update `Subject` in `backend/src/cloud_ui/security/identity.py`:

```python
    scope_type: Literal["project", "system"] = "system"
    scope_id: str | None = None
```

Update mock identities:

- viewer: `scope_type="project"`, `scope_id="project-a"`, capabilities include `group.read`.
- operator: `scope_type="project"`, `scope_id="project-a"`, capabilities include `group.read`, `group.manage`.
- auditor: `scope_type="system"`, `scope_id=None`, no group capabilities.
- admin: `scope_type="system"`, `scope_id=None`, capabilities include `group.read`, `group.manage`.

Update `capabilities()` in `backend/src/cloud_ui/security/routes.py` to return:

```python
scope={"type": session.subject.scope_type, "id": session.subject.scope_id}
```

- [ ] **Step 4: Verify GREEN and commit**

Run:

```bash
cd backend && .venv/bin/python -m pytest tests/security/test_mock_identity.py tests/security/test_security_api.py -q
cd backend && .venv/bin/python -m mypy src
```

Expected: security tests pass and mypy reports no issues.

Commit:

```bash
git add backend/src/cloud_ui/security backend/tests/security
git commit -m "feat: add project scope to mock subjects"
```

---

### Task 2: Resource Group Schema And Migration

**Files:**
- Create: `backend/src/cloud_ui/migrations/versions/0004_resource_groups.py`
- Create: `backend/src/cloud_ui/groups/__init__.py`
- Create: `backend/src/cloud_ui/groups/schema.py`
- Test: `backend/tests/groups/test_group_migration.py`

- [ ] **Step 1: Write failing migration test**

Create `backend/tests/groups/test_group_migration.py`:

```python
from __future__ import annotations

import importlib
from typing import Any


class _FakeOp:
    def __init__(self) -> None:
        self.created_tables: list[str] = []
        self.dropped_tables: list[str] = []
        self.created_indexes: list[tuple[str, str, tuple[str, ...]]] = []
        self.operations: list[tuple[str, str]] = []

    def create_table(self, name: str, *columns: Any, **kwargs: Any) -> None:
        self.created_tables.append(name)
        self.operations.append(("create_table", name))

    def drop_table(self, name: str) -> None:
        self.dropped_tables.append(name)
        self.operations.append(("drop_table", name))

    def create_index(self, name: str, table_name: str, columns: list[str]) -> None:
        self.created_indexes.append((name, table_name, tuple(columns)))
        self.operations.append(("create_index", name))

    def drop_index(self, name: str, table_name: str) -> None:
        self.operations.append(("drop_index", name))


def test_group_migration_creates_tables_indexes_and_reversible_order(monkeypatch: Any) -> None:
    migration = importlib.import_module("cloud_ui.migrations.versions.0004_resource_groups")
    fake_op = _FakeOp()
    monkeypatch.setattr(migration, "op", fake_op)

    migration.upgrade()
    migration.downgrade()

    assert fake_op.created_tables == [
        "resource_groups",
        "resource_group_members",
        "resource_group_revisions",
    ]
    assert fake_op.dropped_tables == [
        "resource_group_revisions",
        "resource_group_members",
        "resource_groups",
    ]
    assert (
        "ix_resource_groups_owner_scope_name",
        "resource_groups",
        ("owner_subject_id", "scope_type", "scope_id", "deleted_at", "name", "group_id"),
    ) in fake_op.created_indexes
    assert (
        "ix_resource_group_members_group_page",
        "resource_group_members",
        ("group_id", "added_at", "resource_type", "cloud_id", "region_id", "resource_id"),
    ) in fake_op.created_indexes
```

- [ ] **Step 2: Verify RED**

Run:

```bash
cd backend && .venv/bin/python -m pytest tests/groups/test_group_migration.py -q
```

Expected: import fails because `0004_resource_groups` does not exist.

- [ ] **Step 3: Implement migration and metadata**

Create `backend/src/cloud_ui/groups/__init__.py`:

```python
"""Portal-owned resource group domain."""
```

Create `backend/src/cloud_ui/groups/schema.py` with `metadata = sa.MetaData()` and three SQLAlchemy
Core tables matching the spec:

- `resource_groups`
- `resource_group_members`
- `resource_group_revisions`

Create `backend/src/cloud_ui/migrations/versions/0004_resource_groups.py` with revision
`0004_resource_groups`, `down_revision = "0003_inventory_read_model"`, explicit `op.create_table`
calls and explicit index creation. Use `sa.JSON()` for `rule_body_json` and `change_json`,
`sa.DateTime(timezone=True)` for timestamps, and foreign keys from members/revisions to
`resource_groups.group_id` with `ondelete="CASCADE"`.

- [ ] **Step 4: Verify GREEN and commit**

Run:

```bash
cd backend && .venv/bin/python -m pytest tests/groups/test_group_migration.py tests/inventory/test_inventory_migration.py -q
cd backend && .venv/bin/python -m ruff check src tests
```

Expected: migration tests pass and Ruff reports no issues.

Commit:

```bash
git add backend/src/cloud_ui/groups backend/src/cloud_ui/migrations/versions/0004_resource_groups.py backend/tests/groups/test_group_migration.py
git commit -m "feat: add resource group schema"
```

---

### Task 3: Group Repository And Explicit Membership

**Files:**
- Create: `backend/src/cloud_ui/groups/models.py`
- Create: `backend/src/cloud_ui/groups/repository.py`
- Test: `backend/tests/groups/test_group_repository.py`

- [ ] **Step 1: Write failing repository tests**

Create tests for these behaviors in `backend/tests/groups/test_group_repository.py`:

```python
def test_group_crud_soft_delete_and_revision_conflict(repository: GroupRepository) -> None:
    created = repository.create_group(
        actor_id="mock-user-operator",
        scope_type="project",
        scope_id="project-a",
        name="prod-vms",
        description="Production VMs",
        resource_type="vm",
        membership_mode="explicit",
    )

    updated = repository.update_group(
        group_id=created.group_id,
        actor_id="mock-user-operator",
        expected_revision=created.revision,
        name="prod-vms-renamed",
        description="Renamed",
    )

    assert updated.revision == created.revision + 1
    with pytest.raises(GroupRevisionConflict):
        repository.update_group(
            group_id=created.group_id,
            actor_id="mock-user-operator",
            expected_revision=created.revision,
            name="stale",
            description="stale",
        )

    repository.delete_group(group_id=created.group_id, actor_id="mock-user-operator")
    assert repository.get_group(created.group_id) is None
```

```python
def test_membership_add_remove_is_idempotent(repository: GroupRepository) -> None:
    group = repository.create_group(
        actor_id="mock-user-operator",
        scope_type="project",
        scope_id="project-a",
        name="tenant-a",
        description=None,
        resource_type="vm",
        membership_mode="explicit",
    )

    first = repository.add_member(
        group_id=group.group_id,
        resource_type="vm",
        cloud_id="dev-cloud",
        region_id="RegionOne",
        resource_id="instance-0001",
        source="explicit",
        actor_id="mock-user-operator",
    )
    second = repository.add_member(
        group_id=group.group_id,
        resource_type="vm",
        cloud_id="dev-cloud",
        region_id="RegionOne",
        resource_id="instance-0001",
        source="explicit",
        actor_id="mock-user-operator",
    )

    assert first == second
    assert [member.resource_id for member in repository.list_members(group.group_id, limit=50)] == [
        "instance-0001"
    ]

    repository.remove_member(
        group_id=group.group_id,
        resource_type="vm",
        cloud_id="dev-cloud",
        region_id="RegionOne",
        resource_id="instance-0001",
    )
    repository.remove_member(
        group_id=group.group_id,
        resource_type="vm",
        cloud_id="dev-cloud",
        region_id="RegionOne",
        resource_id="instance-0001",
    )
    assert repository.list_members(group.group_id, limit=50) == []
```

- [ ] **Step 2: Verify RED**

Run:

```bash
cd backend && .venv/bin/python -m pytest tests/groups/test_group_repository.py -q
```

Expected: import fails because group repository classes do not exist.

- [ ] **Step 3: Implement repository**

Create frozen Pydantic models in `groups/models.py`: `ResourceGroup`, `GroupMember`,
`GroupCreate`, `GroupUpdate`, `GroupPage`, `GroupRevisionConflict`, `GroupNotFound`.

Create `GroupRepository` in `groups/repository.py` with methods:

- `create_group(...) -> ResourceGroup`
- `get_group(group_id: str) -> ResourceGroup | None`
- `list_groups(actor_id: str, scope_type: str, scope_id: str | None, include_admin: bool, limit: int) -> list[ResourceGroup]`
- `update_group(... expected_revision: int, ...) -> ResourceGroup`
- `delete_group(group_id: str, actor_id: str) -> None`
- `add_member(...) -> GroupMember`
- `remove_member(...) -> None`
- `list_members(group_id: str, limit: int) -> list[GroupMember]`

Use SQLAlchemy Core statements and explicit transaction boundaries. Soft-delete groups by setting
`deleted_at`. Increment `revision` for group update/delete and for membership add/remove that changes
state.

- [ ] **Step 4: Verify GREEN and commit**

Run:

```bash
cd backend && .venv/bin/python -m pytest tests/groups/test_group_repository.py -q
cd backend && .venv/bin/python -m mypy src
```

Expected: repository tests pass and mypy reports no issues.

Commit:

```bash
git add backend/src/cloud_ui/groups backend/tests/groups/test_group_repository.py
git commit -m "feat: add resource group repository"
```

---

### Task 4: Safe Dynamic Rule Compiler

**Files:**
- Create: `backend/src/cloud_ui/groups/rules.py`
- Test: `backend/tests/groups/test_group_rules.py`

- [ ] **Step 1: Write failing rule tests**

Create `backend/tests/groups/test_group_rules.py` with tests named:

- `test_valid_vm_rule_compiles_to_project_scoped_conditions`
- `test_unknown_field_operator_and_extra_properties_are_rejected`
- `test_depth_node_and_in_value_limits_are_enforced`
- `test_host_rule_uses_host_allowlist_only`

Use this assertion shape:

```python
compiler = GroupRuleCompiler()
compiled = compiler.compile(
    resource_type="vm",
    scope_type="project",
    scope_id="project-a",
    rule={
        "all": [
            {"field": "project_id", "op": "eq", "value": "project-a"},
            {"field": "status", "op": "in", "value": ["ACTIVE", "SHUTOFF"]},
        ]
    },
)

assert compiled.explain == [
    "project_id eq project-a",
    "status in 2 values",
]
assert str(compiled.condition.compile(compile_kwargs={"literal_binds": True}))
```

- [ ] **Step 2: Verify RED**

Run:

```bash
cd backend && .venv/bin/python -m pytest tests/groups/test_group_rules.py -q
```

Expected: import fails because `cloud_ui.groups.rules` does not exist.

- [ ] **Step 3: Implement compiler**

Create:

- `GroupRuleError(code: str)`
- `CompiledGroupRule(condition: sa.ColumnElement[bool], explain: list[str])`
- `GroupRuleCompiler(max_depth=4, max_nodes=32, max_in_values=20)`

Allowed VM fields map to `schema.instances` columns:

```python
project_id, status, host_name, availability_zone, flavor_id
```

Allowed host fields map to `schema.hypervisors` columns:

```python
host_name, service_status, service_state, availability_zone, maintenance_status
```

Accepted node shapes are exactly one of:

- `{"all": [node, ...]}`
- `{"any": [node, ...]}`
- `{"not": node}`
- `{"field": str, "op": str, "value": scalar_or_list}`

Reject any extra keys. Operators: `eq`, `in`, `prefix`, `exists`. Use bound SQLAlchemy operations,
never string-concatenated SQL. For VM project groups always add `instances.project_id == scope_id`.

- [ ] **Step 4: Verify GREEN and commit**

Run:

```bash
cd backend && .venv/bin/python -m pytest tests/groups/test_group_rules.py -q
cd backend && .venv/bin/python -m ruff check src tests
```

Expected: rule tests pass and Ruff reports no issues.

Commit:

```bash
git add backend/src/cloud_ui/groups/rules.py backend/tests/groups/test_group_rules.py
git commit -m "feat: add safe group rule compiler"
```

---

### Task 5: Group API, Authorization And Audit

**Files:**
- Create: `backend/src/cloud_ui/groups/routes.py`
- Modify: `backend/src/cloud_ui/api.py`
- Test: `backend/tests/groups/test_group_api.py`

- [ ] **Step 1: Write failing API tests**

Create tests for:

- operator creates a VM group and receives `revision=1`;
- stale `PATCH` revision returns `409`;
- auditor without `group.read` receives `403` and an audit denial;
- missing CSRF on create returns `403`;
- adding a VM from another project is denied;
- adding a deleted/missing resource returns safe error;
- membership add with same idempotency key returns stable result;
- preview returns bounded items and explain;
- arbitrary rule field/operator returns `400`.

Use existing `backend/tests/inventory/test_inventory_api.py` login/test-client style.

- [ ] **Step 2: Verify RED**

Run:

```bash
cd backend && .venv/bin/python -m pytest tests/groups/test_group_api.py -q
```

Expected: route imports or endpoint calls fail because group routes are not wired.

- [ ] **Step 3: Implement routes**

Create `GroupServices(repository: GroupRepository | None, inventory_repository: InventoryRepository | None)` and `build_group_router(services, security)`. Wire it in `create_app()` after security and before inventory routes.

Implement response models:

- `GroupResponse`
- `GroupListResponse`
- `GroupMemberResponse`
- `GroupMembersResponse`
- `GroupPreviewResponse`
- `RuleValidationResponse`

Route behavior:

- require session for all endpoints;
- require `group.read` for read/preview;
- require `group.manage` for create/update/delete/member changes;
- require trusted origin + CSRF for all mutating endpoints;
- require `idempotency-key` for member add/remove;
- record audit with actions `group.create`, `group.update`, `group.delete`, `group.member.add`,
  `group.member.remove`, `group.preview`, `authorization.denied`;
- validate VM membership by reading E04 instance detail and comparing `project_id` with group scope;
- validate host membership only for system/admin-like subjects.

- [ ] **Step 4: Verify GREEN and commit**

Run:

```bash
cd backend && .venv/bin/python -m pytest tests/groups/test_group_api.py tests/security/test_security_api.py -q
cd backend && .venv/bin/python -m mypy src
```

Expected: group/security API tests pass and mypy reports no issues.

Commit:

```bash
git add backend/src/cloud_ui/api.py backend/src/cloud_ui/groups backend/tests/groups/test_group_api.py
git commit -m "feat: add resource group API"
```

---

### Task 6: Group-Aware Inventory Filters

**Files:**
- Modify: `backend/src/cloud_ui/inventory/models.py`
- Modify: `backend/src/cloud_ui/inventory/repository.py`
- Modify: `backend/src/cloud_ui/inventory/routes.py`
- Modify: `backend/tests/inventory/test_repository.py`
- Modify: `backend/tests/inventory/test_inventory_api.py`

- [ ] **Step 1: Write failing inventory tests**

Add repository tests proving `InstanceFilters(group_id=...)` and `HypervisorFilters(group_id=...)`
join `resource_group_members` and keep stable pagination. Add API tests proving:

- authorized `GET /api/v1/instances?group_id=...` returns only group members;
- unauthorized group filter returns `403`;
- cursor created for one `group_id` is rejected for a different `group_id`.

- [ ] **Step 2: Verify RED**

Run:

```bash
cd backend && .venv/bin/python -m pytest tests/inventory/test_repository.py tests/inventory/test_inventory_api.py -q
```

Expected: filters reject unsupported `group_id` or models do not accept the field.

- [ ] **Step 3: Implement inventory integration**

Add `group_id: str | None = None` to `InstanceFilters` and `HypervisorFilters`. In repository
condition builders, when `group_id` is present, join/exists against `groups.schema.resource_group_members`
matching group id, resource type, cloud id, region id and resource id. In routes, accept `group_id`
query param, include it in allowed params and call the group access check before listing inventory.

- [ ] **Step 4: Verify GREEN and commit**

Run:

```bash
cd backend && .venv/bin/python -m pytest tests/groups/test_group_api.py tests/inventory/test_repository.py tests/inventory/test_inventory_api.py -q
cd backend && .venv/bin/python -m ruff check src tests
```

Expected: targeted tests pass and Ruff reports no issues.

Commit:

```bash
git add backend/src/cloud_ui/inventory backend/tests/inventory backend/tests/groups/test_group_api.py
git commit -m "feat: filter inventory by resource group"
```

---

### Task 7: Frontend Group UX

**Files:**
- Create: `frontend/src/groups.ts`
- Modify: `frontend/src/api.ts`
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/App.test.tsx`
- Modify: `frontend/src/styles.css`

- [ ] **Step 1: Write failing frontend tests**

Add Vitest/RTL tests for:

- `Группы` nav is shown for `group.read`;
- group list renders loading/empty/error states;
- group detail shows owner/scope/revision;
- member picker calls paginated inventory API and does not request a full dataset;
- dynamic preview renders validation errors and bounded preview rows;
- inventory group filter round-trips through URL.

- [ ] **Step 2: Verify RED**

Run:

```bash
cd frontend && npm test -- --run src/App.test.tsx
```

Expected: tests fail because group UI and API helpers do not exist.

- [ ] **Step 3: Implement frontend helpers and UI**

Add group types and runtime validators to `frontend/src/api.ts` or `frontend/src/groups.ts`:

- `ResourceGroup`
- `GroupMember`
- `GroupListResponse`
- `GroupPreviewResponse`
- `fetchGroups`
- `fetchGroup`
- `createGroup`
- `updateGroup`
- `fetchGroupMembers`
- `addGroupMember`
- `removeGroupMember`
- `previewGroupRule`

Extend `App.tsx` with a `groups` view, forms using controlled React state, server-side member
search via current inventory fetch helpers, and `group_id` URL controls on inventory pages. Keep
refresh/CSRF/idempotency handling aligned with backend contracts.

- [ ] **Step 4: Verify GREEN and commit**

Run:

```bash
cd frontend && npm test -- --run src/App.test.tsx
cd frontend && npm run typecheck
cd frontend && npm run lint
```

Expected: frontend tests, typecheck and lint pass.

Commit:

```bash
git add frontend/src
git commit -m "feat: add resource group frontend"
```

---

### Task 8: Documentation, Evidence And Final Gates

**Files:**
- Modify: `docs/04_DOMAIN_AND_DATA.md`
- Modify: `docs/05_API_AND_INTEGRATIONS.md`
- Modify: `docs/06_AUTH_RBAC_SESSIONS.md`
- Modify: `docs/11_DKB_TRACEABILITY.md`
- Modify: `docs/generated/api-register.md`
- Modify: `docs/generated/integration-register.md`
- Modify: `docs/generated/risk-register.md`
- Modify: `docs/execplans/E05-resource-groups.md`

- [ ] **Step 1: Update docs**

Document group schema, API endpoints, scope rules, DSL limits, host-group limitation, DKB mapping and
residual risks. Register the new `/api/v1/groups*` endpoints and the `group_id` inventory filter.

- [ ] **Step 2: Run final gates**

Run:

```bash
make lint
make typecheck
make test
make security
git diff --check HEAD
```

Expected: all commands pass. If `make test-load` is updated for E05 group filters, run:

```bash
make test-load
```

Expected: sanitized report records success and no query count regression.

- [ ] **Step 3: Update ExecPlan progress**

Record final command results, commit ids, residual risks and rollback notes in
`docs/execplans/E05-resource-groups.md`.

- [ ] **Step 4: Commit documentation**

Run:

```bash
git add docs
git commit -m "docs: update E05 resource group evidence"
```
