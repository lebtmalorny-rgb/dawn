# E04 Inventory UI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the first inventory vertical slice: schema, synthetic reconciliation, paginated API and operator UI for instances and hypervisors.

**Architecture:** Add a focused `cloud_ui.inventory` backend package with SQLAlchemy Core tables, repository/query services, cursor signing, deterministic synthetic reconciliation and FastAPI routes. Extend the existing PatternFly frontend into an authenticated operational shell that fetches only portal BFF pages, never raw OpenStack APIs or full inventory rows.

**Tech Stack:** Python 3.11, FastAPI, SQLAlchemy Core, Alembic, Pydantic, pytest, React 19, PatternFly, Vitest, TypeScript.

---

## File Structure

Create:

```text
backend/src/cloud_ui/migrations/versions/0003_inventory_read_model.py
backend/src/cloud_ui/inventory/__init__.py
backend/src/cloud_ui/inventory/models.py
backend/src/cloud_ui/inventory/schema.py
backend/src/cloud_ui/inventory/cursor.py
backend/src/cloud_ui/inventory/synthetic.py
backend/src/cloud_ui/inventory/repository.py
backend/src/cloud_ui/inventory/reconciliation.py
backend/src/cloud_ui/inventory/routes.py
backend/src/cloud_ui/inventory/scale_report.py
backend/tests/inventory/test_inventory_migration.py
backend/tests/inventory/test_cursor.py
backend/tests/inventory/test_repository.py
backend/tests/inventory/test_reconciliation.py
backend/tests/inventory/test_inventory_api.py
backend/tests/inventory/test_scale_report.py
scripts/e04_scale_report.py
docs/generated/e04-scale-report.md
```

Modify:

```text
Makefile
backend/src/cloud_ui/api.py
backend/src/cloud_ui/cli.py
backend/src/cloud_ui/config.py
backend/src/cloud_ui/security/mock_identity.py
backend/tests/test_cli.py
backend/tests/test_config.py
frontend/src/App.tsx
frontend/src/App.test.tsx
frontend/src/api.ts
frontend/src/styles.css
docs/11_DKB_TRACEABILITY.md
docs/execplans/E04-inventory-ui.md
docs/generated/api-register.md
docs/generated/integration-register.md
docs/generated/risk-register.md
```

---

### Task 1: Inventory Schema And Migration

**Files:**
- Create: `backend/src/cloud_ui/migrations/versions/0003_inventory_read_model.py`
- Create: `backend/src/cloud_ui/inventory/__init__.py`
- Create: `backend/src/cloud_ui/inventory/schema.py`
- Test: `backend/tests/inventory/test_inventory_migration.py`

- [ ] **Step 1: Write failing migration test**

Create `backend/tests/inventory/test_inventory_migration.py` with a fake Alembic op that records created
tables, dropped tables and indexes:

```python
from __future__ import annotations

import importlib
from typing import Any


class _FakeOp:
    def __init__(self) -> None:
        self.created_tables: list[str] = []
        self.dropped_tables: list[str] = []
        self.created_indexes: list[tuple[str, str, object]] = []

    def create_table(self, name: str, *columns: Any, **kwargs: Any) -> None:
        self.created_tables.append(name)

    def drop_table(self, name: str) -> None:
        self.dropped_tables.append(name)

    def create_index(self, name: str, table_name: str, columns: list[str]) -> None:
        self.created_indexes.append((name, table_name, tuple(columns)))

    def drop_index(self, name: str, table_name: str) -> None:
        pass


def test_inventory_migration_creates_and_drops_expected_tables(monkeypatch: Any) -> None:
    migration = importlib.import_module("cloud_ui.migrations.versions.0003_inventory_read_model")
    fake_op = _FakeOp()
    monkeypatch.setattr(migration, "op", fake_op)

    migration.upgrade()
    migration.downgrade()

    assert fake_op.created_tables == [
        "clouds",
        "regions",
        "inventory_sync_runs",
        "inventory_sync_cursors",
        "inventory_sync_failures",
        "instances",
        "hypervisors",
    ]
    assert fake_op.dropped_tables == [
        "hypervisors",
        "instances",
        "inventory_sync_failures",
        "inventory_sync_cursors",
        "inventory_sync_runs",
        "regions",
        "clouds",
    ]
    assert ("ix_instances_name_page", "instances", ("cloud_id", "region_id", "deleted_at", "name", "instance_id")) in fake_op.created_indexes
    assert ("ix_hypervisors_host_page", "hypervisors", ("cloud_id", "region_id", "deleted_at", "host_name", "hypervisor_id")) in fake_op.created_indexes
```

- [ ] **Step 2: Run migration test and verify RED**

Run:

```bash
cd backend && .venv/bin/python -m pytest tests/inventory/test_inventory_migration.py -q
```

Expected: import fails because `0003_inventory_read_model` does not exist.

- [ ] **Step 3: Implement migration and table metadata**

Create `backend/src/cloud_ui/inventory/__init__.py`:

```python
"""Inventory read model, reconciliation and API contracts."""
```

Create `backend/src/cloud_ui/inventory/schema.py` with `metadata = sa.MetaData()` and table objects
named `clouds`, `regions`, `inventory_sync_runs`, `inventory_sync_cursors`,
`inventory_sync_failures`, `instances`, and `hypervisors`. Use the columns from the design spec.
Use `sa.JSON()` for JSON projection fields, `sa.DateTime(timezone=True)` for UTC timestamps and
`sa.PrimaryKeyConstraint` for composite keys.

Create `backend/src/cloud_ui/migrations/versions/0003_inventory_read_model.py` with:

```python
"""create inventory read model tables"""

import sqlalchemy as sa
from alembic import op

revision = "0003_inventory_read_model"
down_revision = "0002_security_foundation"
branch_labels = None
depends_on = None
```

Implement `upgrade()` with explicit `op.create_table` calls for all seven tables and explicit
`op.create_index` calls for the indexes asserted by the test. Implement `downgrade()` by dropping
indexes first and then dropping tables in the exact reverse order asserted by the test. Do not import
runtime schema metadata into the migration.

- [ ] **Step 4: Verify GREEN**

Run:

```bash
cd backend && .venv/bin/python -m pytest tests/inventory/test_inventory_migration.py -q
```

Expected: `1 passed`.

---

### Task 2: Cursor, DTOs And Repository Queries

**Files:**
- Create: `backend/src/cloud_ui/inventory/models.py`
- Create: `backend/src/cloud_ui/inventory/cursor.py`
- Create: `backend/src/cloud_ui/inventory/repository.py`
- Modify: `backend/src/cloud_ui/config.py`
- Modify: `backend/tests/test_config.py`
- Test: `backend/tests/inventory/test_cursor.py`
- Test: `backend/tests/inventory/test_repository.py`

- [ ] **Step 1: Write failing cursor tests**

Create `backend/tests/inventory/test_cursor.py`:

```python
from cloud_ui.inventory.cursor import CursorCodec, CursorTampered


def test_cursor_round_trip_preserves_payload() -> None:
    codec = CursorCodec(signing_key="dev-inventory-cursor-key")
    payload = {
        "resource": "instances",
        "sort": "name.asc",
        "filters_hash": "abc",
        "last": {"name": "vm-0001", "id": "instance-0001"},
    }

    token = codec.encode(payload)

    assert codec.decode(token) == payload
    assert "vm-0001" not in token


def test_cursor_tampering_is_rejected() -> None:
    codec = CursorCodec(signing_key="dev-inventory-cursor-key")
    token = codec.encode({"resource": "instances", "last": {"id": "i-1"}})

    bad_token = token[:-2] + "aa"

    try:
        codec.decode(bad_token)
    except CursorTampered as exc:
        assert exc.code == "cursor_tampered"
    else:
        raise AssertionError("expected CursorTampered")
```

- [ ] **Step 2: Write failing repository tests**

Create `backend/tests/inventory/test_repository.py`. Build an in-memory SQLite engine with
`inventory.schema.metadata.create_all(engine)`, seed three instances and two hypervisors, and assert:

```python
def test_instances_are_filtered_sorted_and_keyset_paginated() -> None:
    # status=ACTIVE, sort=name.asc, limit=1 returns vm-a first and a next cursor.
    # Passing next cursor returns vm-c.
```

```python
def test_cursor_with_different_filters_is_rejected() -> None:
    # Cursor generated for status=ACTIVE cannot be reused with status=ERROR.
```

```python
def test_hypervisors_are_filtered_by_service_status_and_sorted() -> None:
    # service_status=enabled returns only enabled hosts sorted by host_name.
```

```python
def test_detail_ignores_tombstoned_rows() -> None:
    # get_instance returns None when deleted_at is not None.
```

- [ ] **Step 3: Run tests and verify RED**

Run:

```bash
cd backend && .venv/bin/python -m pytest tests/inventory/test_cursor.py tests/inventory/test_repository.py tests/test_config.py -q
```

Expected: imports fail because cursor/repository modules and settings do not exist.

- [ ] **Step 4: Implement DTOs, cursor and repository**

Add settings to `backend/src/cloud_ui/config.py`:

```python
    inventory_default_limit: int = Field(default=50, ge=1, le=200)
    inventory_max_limit: int = Field(default=200, ge=1, le=200)
    inventory_cursor_signing_key: str = Field(default="dev-inventory-cursor-key", min_length=16)
    inventory_stale_after_seconds: int = Field(default=900, ge=60)
    inventory_synthetic_instance_count: int = Field(default=10_000, ge=1)
    inventory_synthetic_hypervisor_count: int = Field(default=1_000, ge=1)
```

Extend `_CLOUD_UI_ENVIRONMENT_NAMES` in `backend/tests/test_config.py` with the matching environment
variable names and assert defaults in `test_settings_accept_dummy_dev_values`.

Create `models.py` with frozen Pydantic models:

- `InventoryWarning(code, title, detail, source)`;
- `InventoryFreshness(observed_at, last_successful_sync_at, stale_after_seconds, is_stale)`;
- `InstanceItem`;
- `HypervisorItem`;
- `InventoryPage[T]`;
- `InventorySort(field, direction)`;
- `InstanceFilters`;
- `HypervisorFilters`.

Create `cursor.py` using stdlib `base64`, `hashlib`, `hmac` and `json`. The token shape is
`base64url(json_payload).base64url(signature)`. Decode must reject malformed JSON, invalid signature
and non-object payload by raising `CursorTampered(code="cursor_tampered")`.

Create `repository.py` using SQLAlchemy Core:

- `InventoryRepository(engine, cursor_codec, default_limit, max_limit, stale_after_seconds)`;
- `list_instances(filters, sort, limit, cursor)`;
- `get_instance(cloud_id, region_id, instance_id)`;
- `list_hypervisors(filters, sort, limit, cursor)`;
- `get_hypervisor(cloud_id, region_id, hypervisor_id)`;
- `replace_instance_rows(rows)`;
- `replace_hypervisor_rows(rows)`.

The repository must:

- clamp limit to max;
- hash filters into the cursor;
- reject cursor reuse across different filters/sorts;
- apply deterministic tie-breaker by resource ID;
- return `partial=True` and warnings when sync failures exist for the cloud/region;
- compute `freshness.is_stale` from newest `observed_at` and stale threshold.

- [ ] **Step 5: Verify GREEN**

Run:

```bash
cd backend && .venv/bin/python -m pytest tests/inventory/test_cursor.py tests/inventory/test_repository.py tests/test_config.py -q
```

Expected: all selected tests pass.

---

### Task 3: Synthetic Full Reconciliation

**Files:**
- Create: `backend/src/cloud_ui/inventory/synthetic.py`
- Create: `backend/src/cloud_ui/inventory/reconciliation.py`
- Modify: `backend/src/cloud_ui/cli.py`
- Modify: `backend/tests/test_cli.py`
- Test: `backend/tests/inventory/test_reconciliation.py`

- [ ] **Step 1: Write failing reconciliation tests**

Create `backend/tests/inventory/test_reconciliation.py` with SQLite helper and tests:

```python
def test_synthetic_full_sync_populates_instances_and_hypervisors() -> None:
    # 12 instances, 3 hypervisors, chunk size 5.
    # After run: list_instances total page contains rows, sync run status is success.
```

```python
def test_full_sync_is_idempotent_for_same_seed() -> None:
    # Run twice with same seed; row counts stay 12/3 and generation advances.
```

```python
def test_partial_failure_records_failure_and_keeps_old_rows() -> None:
    # Source raises on second instance chunk; old observed rows are not tombstoned.
```

```python
def test_successful_full_sync_tombstones_missing_old_rows() -> None:
    # First run has 12 instances, second successful run has 10; two old rows get deleted_at.
```

- [ ] **Step 2: Run reconciliation tests and verify RED**

Run:

```bash
cd backend && .venv/bin/python -m pytest tests/inventory/test_reconciliation.py -q
```

Expected: imports fail because `synthetic` and `reconciliation` modules do not exist.

- [ ] **Step 3: Implement synthetic source and reconciliation service**

Create `synthetic.py`:

- `SyntheticInventorySource(instance_count, hypervisor_count, seed="e04")`;
- `iter_instances(chunk_size)`;
- `iter_hypervisors(chunk_size)`;
- deterministic IDs:
  - cloud `synthetic`;
  - region `RegionOne`;
  - instance `inst-00000001`;
  - hypervisor `hyp-0001`;
- varied `status`, `project_id`, `host_name`, `availability_zone`, flavor and capacity values.

Create `reconciliation.py`:

- `InventoryReconciler(repository, source, clock, chunk_size=500)`;
- `run_full_sync(request_id, correlation_id) -> SyncRunResult`;
- create run row before chunks;
- upsert chunks with new generation;
- update cursor after each chunk;
- on chunk error, record safe failure, mark run `partial`, and do not tombstone;
- on success, tombstone older generation rows;
- update region freshness.

Modify `cli.py`:

- add parser command `inventory-sync-synthetic`;
- implementation builds settings, DB engine, repository, synthetic source and runs full sync;
- prints `inventory synthetic sync ok: instances=<n> hypervisors=<n> status=<status>`.

Update `backend/tests/test_cli.py` to assert parser accepts the new command and that the CLI dispatch
calls a monkeypatched `run_inventory_sync_synthetic()`.

- [ ] **Step 4: Verify GREEN**

Run:

```bash
cd backend && .venv/bin/python -m pytest tests/inventory/test_reconciliation.py tests/test_cli.py -q
```

Expected: all selected tests pass.

---

### Task 4: Inventory API, Authorization And OpenAPI

**Files:**
- Create: `backend/src/cloud_ui/inventory/routes.py`
- Modify: `backend/src/cloud_ui/api.py`
- Modify: `backend/src/cloud_ui/security/mock_identity.py`
- Test: `backend/tests/inventory/test_inventory_api.py`

- [ ] **Step 1: Write failing API tests**

Create `backend/tests/inventory/test_inventory_api.py`. Use
`TestClient(create_app(readiness_check=check, security_services=security, inventory_services=test_services))`,
an in-memory repository and mock security services.

Tests:

```python
def test_instance_list_requires_session() -> None:
    response = client.get("/api/v1/instances")
    assert response.status_code == 401
```

```python
def test_auditor_without_instance_read_gets_403() -> None:
    # Login as auditor and call /instances.
    # Assert 403 forbidden and authorization.denied audit event.
```

```python
def test_instance_list_returns_page_freshness_and_cursor() -> None:
    # Login viewer, call /instances?limit=1&status=ACTIVE&sort=name.asc.
    # Assert one item, next_cursor, partial=false, freshness present.
```

```python
def test_cursor_tampering_returns_safe_400() -> None:
    # Call /instances?cursor=not-valid.
    # Assert error.code == "cursor_tampered" and request_id is present.
```

```python
def test_instance_refresh_requires_csrf_and_records_audit() -> None:
    # Login operator with instance.refresh, call POST refresh with CSRF.
    # Assert accepted status and audit action instance.refresh.requested.
```

```python
def test_hypervisor_list_and_detail_require_hypervisor_read() -> None:
    # Viewer succeeds; auditor gets 403.
```

```python
def test_openapi_contains_inventory_paths() -> None:
    schema = client.app.openapi()
    assert "/api/v1/instances" in schema["paths"]
    assert "/api/v1/hypervisors" in schema["paths"]
```

```python
def test_inventory_routes_do_not_import_openstack_http_transport() -> None:
    # Inspect backend/src/cloud_ui/inventory/routes.py text.
    # Assert "httpx" and "OpenStackHttpClient" are absent.
```

- [ ] **Step 2: Run API tests and verify RED**

Run:

```bash
cd backend && .venv/bin/python -m pytest tests/inventory/test_inventory_api.py -q
```

Expected: imports or routes fail because inventory routes are not wired.

- [ ] **Step 3: Implement inventory routes and app wiring**

Create `routes.py` with:

- Pydantic response models for list/detail/refresh/module descriptors;
- local helpers for session, capability, CSRF, trusted origin and safe error response;
- `build_inventory_router(services: InventoryServices, security: SecurityServices) -> APIRouter`.

Route behavior:

- `GET /instances`: require `instance.read`, parse allowlisted query, call repository.
- `GET /instances/{cloud_id}/{region_id}/{instance_id}`: require `instance.read`, 404 if absent.
- `POST /instances/{cloud_id}/{region_id}/{instance_id}/refresh`: require session, trusted origin,
  CSRF and `instance.refresh`; record audit action `instance.refresh.requested`; return
  `{"status": "accepted", "target": {"cloud_id": cloud_id, "region_id": region_id, "instance_id": instance_id}}`.
- `GET /hypervisors`: require `hypervisor.read`.
- `GET /hypervisors/{cloud_id}/{region_id}/{hypervisor_id}`: require `hypervisor.read`.
- `GET /inventory/modules`: require session; return capability-aware descriptors with disabled
  status for service health/topology/capacity modules.

Modify `api.py`:

- add optional `inventory_services` parameter to `create_app`;
- if no inventory services and runtime settings are available, build from `settings.database_url`;
- if tests construct app with injected readiness/security and no inventory services, use an
  unavailable service object that returns safe `503 inventory_unavailable` only when inventory
  endpoints are called.

Modify `mock_identity.py`:

- add `instance.refresh` to `cloud_operator`;
- add `instance.read`, `instance.refresh`, `hypervisor.read` to `portal_admin` so admin can test
  refresh without widening auditor.

- [ ] **Step 4: Verify GREEN**

Run:

```bash
cd backend && .venv/bin/python -m pytest tests/inventory/test_inventory_api.py tests/security/test_security_api.py -q
```

Expected: inventory API and existing security API tests pass.

---

### Task 5: Frontend Inventory Pages

**Files:**
- Modify: `frontend/src/api.ts`
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/App.test.tsx`
- Modify: `frontend/src/styles.css`

- [ ] **Step 1: Write failing frontend tests**

Extend `frontend/src/App.test.tsx` with tests:

```tsx
test("renders inventory navigation only when capabilities allow it", async () => {
  // Stub session, readiness and capabilities with instance.read only.
  // Assert "ВМ" is visible and "Гипервизоры" is absent.
});
```

```tsx
test("instances page fetches server-side page from BFF with URL filters", async () => {
  // Set window history to ?view=instances&status=ACTIVE&sort=name.asc.
  // Assert fetch called with /api/v1/instances?limit=50&status=ACTIVE&sort=name.asc.
  // Assert only returned rows are rendered.
});
```

```tsx
test("hypervisors page renders partial and stale state", async () => {
  // Stub /api/v1/hypervisors response with partial=true and freshness.is_stale=true.
  // Assert warning and stale badge text are visible.
});
```

```tsx
test("inventory pages do not store result rows in browser storage", async () => {
  // Spy on Storage.prototype.setItem while rendering a page.
  // Assert no row payload is stored.
});
```

- [ ] **Step 2: Run frontend tests and verify RED**

Run:

```bash
cd frontend && npm test -- --run src/App.test.tsx
```

Expected: tests fail because inventory APIs/pages do not exist.

- [ ] **Step 3: Extend frontend API types and validators**

Modify `api.ts`:

- add `InventoryWarning`, `InventoryFreshness`, `InstanceItem`, `HypervisorItem`,
  `InventoryPage<T>`, `InventoryModuleDescriptor`;
- add validators mirroring backend response shape;
- add functions:
  - `fetchInstances(params: URLSearchParams): Promise<InventoryPage<InstanceItem>>`;
  - `fetchHypervisors(params: URLSearchParams): Promise<InventoryPage<HypervisorItem>>`;
  - `fetchInventoryModules(): Promise<InventoryModuleDescriptor[]>`.

All functions call portal BFF paths such as `/api/v1/instances` and `/api/v1/hypervisors`, not
OpenStack URLs.

- [ ] **Step 4: Implement UI shell and pages**

Modify `App.tsx`:

- keep login/readiness behavior;
- after authentication, fetch capabilities and render navigation;
- choose active view from `window.location.search`;
- render semantic table for instances/hypervisors;
- use `URLSearchParams` for filters/sort/cursor/columns/density;
- render current `items` only;
- show loading/empty/error/partial/stale states.

Modify `styles.css` with restrained operational layout:

- full-width work area;
- compact nav;
- responsive table wrapper;
- stable cell wrapping;
- visible warning/stale badges;
- no nested cards for table content.

- [ ] **Step 5: Verify GREEN**

Run:

```bash
cd frontend && npm test -- --run src/App.test.tsx
```

Expected: frontend tests pass.

---

### Task 6: Scale Report, Disabled Descriptors And Docs

**Files:**
- Create: `backend/src/cloud_ui/inventory/scale_report.py`
- Create: `backend/tests/inventory/test_scale_report.py`
- Create: `scripts/e04_scale_report.py`
- Create: `docs/generated/e04-scale-report.md`
- Modify: `Makefile`
- Modify: docs/register files and ExecPlan

- [ ] **Step 1: Write failing scale report tests**

Create `backend/tests/inventory/test_scale_report.py`:

```python
def test_scale_report_contains_dataset_latency_and_explain_summary(tmp_path) -> None:
    report = run_synthetic_scale_report(instance_count=200, hypervisor_count=20)
    markdown = report.to_markdown()

    assert "Synthetic dataset" in markdown
    assert "instances: 200" in markdown
    assert "hypervisors: 20" in markdown
    assert "p95" in markdown
    assert "EXPLAIN" in markdown
    assert "secret" not in markdown.lower()
```

- [ ] **Step 2: Run scale test and verify RED**

Run:

```bash
cd backend && .venv/bin/python -m pytest tests/inventory/test_scale_report.py -q
```

Expected: import fails because `scale_report.py` does not exist.

- [ ] **Step 3: Implement scale report and make target**

Create `scale_report.py`:

- builds in-memory SQLite engine;
- creates inventory schema;
- runs synthetic reconciliation with requested counts;
- executes list scenarios:
  - instances default page;
  - instances filtered by status;
  - instances sorted by observed_at;
  - hypervisors default page;
  - hypervisors filtered by service_status;
- records elapsed milliseconds and p95;
- runs SQLite `EXPLAIN QUERY PLAN` for representative queries;
- returns a Markdown report with sanitized environment and findings.

Create `scripts/e04_scale_report.py`:

```python
from __future__ import annotations

from pathlib import Path

from cloud_ui.inventory.scale_report import run_synthetic_scale_report


def main() -> int:
    output = Path("docs/generated/e04-scale-report.md")
    report = run_synthetic_scale_report(instance_count=10_000, hypervisor_count=1_000)
    output.write_text(report.to_markdown(), encoding="utf-8")
    print(f"wrote {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

Modify `Makefile`:

```make
.PHONY: bootstrap format lint typecheck test test-load build up down reset smoke security

test-load:
	cd backend && .venv/bin/python ../scripts/e04_scale_report.py
```

- [ ] **Step 4: Update docs/registers**

Update:

- `docs/generated/api-register.md` with E04 endpoints and module descriptors.
- `docs/generated/integration-register.md` to mark E04 read model synthetic evidence and live smoke pending.
- `docs/generated/risk-register.md` with E04 synthetic-vs-production evidence risk.
- `docs/11_DKB_TRACEABILITY.md` with E04 DKB update.
- `docs/execplans/E04-inventory-ui.md` with completed progress and command results.

- [ ] **Step 5: Verify scale report**

Run:

```bash
cd backend && .venv/bin/python -m pytest tests/inventory/test_scale_report.py -q
make test-load
```

Expected:

- scale report test passes;
- `make test-load` writes `docs/generated/e04-scale-report.md`;
- report contains no secrets or production payload.

---

### Task 7: Final Gates, Review, Commit And Merge

**Files:**
- All E04 files

- [ ] **Step 1: Run backend E04 tests**

Run:

```bash
cd backend && .venv/bin/python -m pytest tests/inventory -q
```

Expected: all E04 backend tests pass.

- [ ] **Step 2: Run frontend tests**

Run:

```bash
cd frontend && npm test -- --run src/App.test.tsx
```

Expected: all frontend tests pass.

- [ ] **Step 3: Run final project gates**

Run:

```bash
git diff --check
./scripts/secret-scan.sh
make lint
make typecheck
make test
make test-load
```

Expected:

- `git diff --check` no output;
- secret scan no output;
- lint/typecheck/test pass;
- `make test-load` refreshes sanitized E04 scale report.

- [ ] **Step 4: Self-review**

Run:

```bash
rg -n "httpx|OpenStackHttpClient|requests" backend/src/cloud_ui/api.py backend/src/cloud_ui/inventory backend/src/cloud_ui/security
rg -n "localStorage|sessionStorage" frontend/src
git diff --stat
git diff --name-only
```

Expected:

- no route handler imports `httpx` or `OpenStackHttpClient`;
- frontend does not store inventory rows in browser storage;
- diff is limited to E04 code, tests, Makefile and docs.

- [ ] **Step 5: Commit**

Run:

```bash
git add Makefile backend/src/cloud_ui backend/tests frontend/src scripts/e04_scale_report.py docs/11_DKB_TRACEABILITY.md docs/execplans/E04-inventory-ui.md docs/generated docs/superpowers/plans/2026-06-21-e04-inventory-ui.md
git commit -m "feat: add inventory read model and UI"
```

Expected: commit succeeds.

- [ ] **Step 6: Complete branch**

Use `superpowers:finishing-a-development-branch`:

- verify tests;
- merge locally into `feature/e01-bootstrap` if continuing the current project flow;
- verify tests on merged result;
- remove E04 worktree and merged feature branch.
