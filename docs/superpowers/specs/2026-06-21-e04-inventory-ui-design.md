# E04 Inventory Read Model And UI Design

## Context

E04 starts from E03 commit `4537e6a feat: add OpenStack adapter contracts`.
The baseline in `/Users/dmitry/Desktop/dawn/.worktrees/e04-inventory-ui` is clean:

- `make test` -> backend `58 passed`, frontend `6 passed`.

The current codebase has:

- FastAPI app assembly in `backend/src/cloud_ui/api.py`;
- E02 security/session/capability services in `backend/src/cloud_ui/security/`;
- E03 Keystone/Nova/Placement adapter contracts in `backend/src/cloud_ui/integrations/`;
- Alembic migrations `0001_schema_info` and `0002_security_foundation`;
- a compact PatternFly frontend in `frontend/src/App.tsx`.

## Goal

Build the first inventory vertical slice: operators can open VM and hypervisor pages, use
server-side filters, stable sorting and cursor pagination, and see freshness, stale and partial
state. Backend list/detail requests read from MariaDB read model and must not fan out to
OpenStack per page request.

## Scope

### Included

- Inventory read-model schema for clouds, regions, instances, hypervisors, sync runs, cursors
  and failures.
- Deterministic synthetic reconciliation using the provisional scale profile:
  10,000 instances and 1,000 hypervisors.
- Chunked full reconciliation with generation, cursor state, retry/failure recording and
  tombstone after successful run completion.
- Minimal targeted refresh contract path with authorization, CSRF and audit, but without
  mutating Nova or starting Mistral.
- Read-only API:
  - `GET /api/v1/instances`;
  - `GET /api/v1/instances/{cloud_id}/{region_id}/{instance_id}`;
  - `POST /api/v1/instances/{cloud_id}/{region_id}/{instance_id}/refresh`;
  - `GET /api/v1/hypervisors`;
  - `GET /api/v1/hypervisors/{cloud_id}/{region_id}/{hypervisor_id}`.
- Server-side limit, signed cursor, typed filter allowlist, stable sort, freshness and partial
  warnings.
- Capability checks for `instance.read`, `instance.refresh` and `hypervisor.read`.
- Frontend pages for instances and hypervisors with URL-controlled filters, sort and page cursor.
- UI states for loading, empty, error, partial and stale data.
- Saved-view-ready state shape: URL stores filters/sort/columns/density, but no result rows.
- Synthetic scale report with query timing and `EXPLAIN` summaries.
- Feature-flagged disabled descriptors for compute services, Neutron agents, Cinder services,
  image tasks, topology and capacity summary.
- Documentation and DKB/API register updates.

### Excluded

- Dynamic groups and group preview.
- Mistral workflow execution.
- Mutating Nova actions.
- Real OpenStack notification binding.
- Production/live credential usage.
- Full compute-service, Neutron, Cinder, Glance, topology or capacity modules.
- New persistent infrastructure dependency such as Redis.

## Architecture

E04 adds a new `cloud_ui.inventory` package separate from E03 adapters. The package owns
read-model DTOs, SQLAlchemy table metadata or focused query helpers, reconciliation services,
cursor signing and API response models. Route handlers call inventory services and repositories;
they do not import `httpx`, OpenStack service URLs or raw adapter clients.

The first reconciliation implementation is synthetic/offline. This gives deterministic tests and
load evidence without test-cloud credentials. The service interface remains compatible with
future Nova/Placement-backed reconciliation: later code can replace the synthetic source with
E03 adapters without changing list API or frontend contracts.

The frontend remains a utilitarian PatternFly application. E04 extends it into an operational
shell with navigation and two dense table views. It avoids marketing layout and card nesting; page
sections are full-width work areas, and tables render current page rows only.

## Data Model

### `clouds`

Stores connected cloud deployments. E04 can seed one synthetic cloud but keeps keys
multi-cloud-ready.

Required fields:

- `cloud_id` primary key;
- `display_name`;
- `enabled`;
- `created_at`;
- `updated_at`;
- `last_sync_at`.

### `regions`

Stores region metadata and sync freshness.

Required fields:

- `cloud_id`;
- `region_id`;
- `display_name`;
- `enabled`;
- `last_successful_sync_at`;
- `last_attempted_sync_at`;
- `sync_status`;
- primary key `(cloud_id, region_id)`.

### `instances`

Projection of Nova servers, not source of truth.

Required fields:

- `cloud_id`, `region_id`, `instance_id`;
- `name`, `project_id`, `user_id`;
- `status`, `power_state`, `task_state`, `vm_state`;
- `host_name`, `hypervisor_id`, `availability_zone`;
- `flavor_id`, `vcpus`, `ram_mb`, `disk_gb`;
- `image_id`, `boot_volume_id`, `addresses_json`;
- `source_created_at`, `source_updated_at`, `observed_at`;
- `sync_generation`, `sync_status`, `deleted_at`;
- `change_hash`;
- primary key `(cloud_id, region_id, instance_id)`.

Initial indexes target the accepted query cases:

- list by name: `(cloud_id, region_id, deleted_at, name, instance_id)`;
- list/filter by project and status: `(cloud_id, region_id, deleted_at, project_id, status, instance_id)`;
- list/filter by host and status: `(cloud_id, region_id, deleted_at, host_name, status, instance_id)`;
- stale/freshness scans: `(cloud_id, region_id, observed_at)`.

### `hypervisors`

Projection of Nova hypervisors and compute service health.

Required fields:

- `cloud_id`, `region_id`, `hypervisor_id`;
- `host_name`, `service_id`, `service_status`, `service_state`;
- `hypervisor_type`, `hypervisor_version`;
- `availability_zone`, `aggregates_json`;
- `vcpus_total`, `vcpus_used`, `ram_mb_total`, `ram_mb_used`, `disk_gb_total`, `disk_gb_used`;
- `running_vms`, `disabled_reason`, `maintenance_status`;
- `observed_at`, `sync_generation`, `sync_status`, `deleted_at`;
- `change_hash`;
- primary key `(cloud_id, region_id, hypervisor_id)`.

Initial indexes:

- `(cloud_id, region_id, deleted_at, host_name, hypervisor_id)`;
- `(cloud_id, region_id, deleted_at, service_status, service_state, hypervisor_id)`;
- `(cloud_id, region_id, availability_zone, hypervisor_id)`;
- `(cloud_id, region_id, observed_at)`.

### Sync tables

`inventory_sync_runs` records full/targeted runs, generation, status, counts, request ID and
correlation ID.

`inventory_sync_cursors` records per-resource sync cursor, generation and retry state.

`inventory_sync_failures` records safe failure summaries by run/source/chunk. It must not contain
tokens, raw request bodies or secret-bearing headers.

## Reconciliation

Full reconciliation proceeds by resource type and chunk:

1. Create `inventory_sync_runs` row with status `running` and a new generation.
2. Read deterministic source chunks.
3. Upsert instances/hypervisors with current generation and `observed_at`.
4. Persist cursor progress after each chunk.
5. On recoverable chunk failure, record `inventory_sync_failures`, mark run `partial` and keep
   already-valid old rows.
6. Only after a successful full scan, tombstone rows from older generations that were not observed.
7. Mark region freshness and run status.

The operation is idempotent: re-running the same synthetic seed converges to the same read model.
Partial failure never deletes previously correct data.

Targeted refresh in E04 is a protected contract path. It records audit and returns an accepted
status for the future operation path, but it does not call Nova mutation APIs or Mistral.

## API Contract

List endpoints accept:

- `limit`: default 50, maximum 200;
- `cursor`: signed opaque cursor;
- allowlisted filters;
- allowlisted sort key and direction.

Instance filters:

- `status`;
- `project_id`;
- `host_name`;
- `availability_zone`;
- `q` for bounded partial name match.

Instance sorts:

- `name`;
- `status`;
- `observed_at`;
- `source_updated_at`;
- tie-breaker `instance_id`.

Hypervisor filters:

- `service_status`;
- `service_state`;
- `availability_zone`;
- `q` for bounded partial host match.

Hypervisor sorts:

- `host_name`;
- `service_status`;
- `observed_at`;
- tie-breaker `hypervisor_id`.

Responses contain:

- `items`;
- `next_cursor`;
- `partial`;
- `warnings`;
- `freshness`;
- `limit`;
- `sort`.

Cursor tampering returns a safe `400` error with a machine-readable code and request ID.

Authorization:

- instance list/detail require `instance.read`;
- instance refresh requires `instance.refresh` plus CSRF and trusted origin;
- hypervisor list/detail require `hypervisor.read`.

## Frontend Contract

The frontend adds inventory navigation inside the authenticated shell:

- `ВМ` appears if `instance.read` is present;
- `Гипервизоры` appears if `hypervisor.read` is present;
- disabled descriptor modules are not rendered as broken links.

Tables use URL state:

- `?view=instances&status=ACTIVE&sort=name.asc&cursor=...&density=compact`;
- no result rows are stored in URL, localStorage or sessionStorage;
- page transitions replace only the current page rows.

Visible states:

- loading spinner;
- empty state for zero rows;
- safe error alert;
- partial warning alert with source/failure summary;
- stale badge based on freshness;
- disabled refresh action if capability is missing.

The UI does not perform client-side filtering over a full inventory. Tests assert that only the
requested page is rendered and that no code path accumulates all rows.

## E04.8 Disabled Descriptor Contract

Compute services, Neutron agents, Cinder services, image tasks, topology and capacity are represented
as disabled module descriptors:

- stable key;
- display title;
- required capability;
- status `disabled`;
- reason;
- future endpoint path.

The frontend uses descriptors to avoid broken links. The backend may expose descriptors through
capabilities or a small inventory module metadata endpoint if needed by implementation; it must not
claim those integrations are enabled.

## Testing

### Backend

- Alembic upgrade/downgrade test for inventory schema.
- Repository tests for filter/sort/page correctness.
- Cursor signing tests, including tampering rejection.
- Reconciliation tests for full sync, idempotent rerun, partial failure, cursor resume and tombstone.
- API tests for capability enforcement, detail lookup, validation, partial warnings and refresh audit.
- Negative tests for no route handler importing E03 `httpx` transport.

### Frontend

- Navigation shows inventory links only with capabilities.
- Instances and hypervisors pages fetch BFF endpoints, not OpenStack.
- Filters/sort/cursor round-trip through URL.
- Partial/stale/error/empty states render safely.
- Large page fixture renders current page only and does not store rows in browser storage.

### Load Evidence

- Deterministic script or pytest test seeds 10,000 instances and 1,000 hypervisors.
- Query timing captures p95 for accepted list scenarios.
- `EXPLAIN` output is summarized in `docs/generated/e04-scale-report.md`.
- If provisional p95 budget is missed, the report records a finding and likely index/query fix.

## Documentation And DKB

E04 updates:

- `docs/generated/api-register.md`;
- `docs/generated/integration-register.md`;
- `docs/generated/risk-register.md`;
- `docs/11_DKB_TRACEABILITY.md`;
- this stage ExecPlan.

Touched DKB requirements:

- ДКБ-01/03/12: inventory scope and backend authorization;
- ДКБ-46/49: request/correlation/freshness events;
- ДКБ-60: data foundation for future groups only, no group implementation claim;
- ДКБ-77/82: API and operational documentation.

## Risks And Open Questions

- Real test-cloud smoke remains pending unless an approved read-only test credential is provided
  outside git.
- Provisional freshness target is not yet owner-approved. E04 will expose freshness values and
  use documented stale thresholds only for UI indication.
- Synthetic SQLite-style performance is not production MariaDB evidence. E04 report is provisional
  and must be repeated in representative deployment for P3.
- Targeted refresh is a protected contract stub; actual Nova refresh and operation tracking
  need later integration.
- Service health/topology/capacity modules remain disabled descriptors in E04.

## Rollback

Rollback is a git revert of E04 commits. The database migration includes downgrade that drops E04
inventory tables. Since E04 adds public API endpoints and frontend navigation, rolling deployment
must run migration before enabling E04 routes in production-like environments.
