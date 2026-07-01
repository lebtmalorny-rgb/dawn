# UI object workspace design

## Status

Approved direction as of 2026-06-29. This is a design/specification artifact only. It does not
change frontend code, backend API, OpenStack state, deployment state or DKB compliance status.

## Goal

While the test stand is unavailable, improve the product-facing UI track by defining the next
offline implementation slice: a vSphere-informed object workspace for virtual machines and
hypervisors. The slice should make the future administration surface visible and testable without
pretending that unavailable backend contracts, telemetry, diagnostics or mutating operations exist.

The observable result of the later implementation should be:

- VM and hypervisor workspaces with top-level `Summary`, `Monitor`, `Configure`, `Permissions` and
  related-resource tabs, plus type-specific secondary navigation inside `Monitor`;
- action menus that show required host/VM functions as `enabled`, `disabled`, `pending` or
  `blocked`;
- multi-object action context for several VMs or hypervisors, including allowed, denied, stale and
  blocked target counts;
- explicit placeholder states for metrics and diagnostics when backend datasource contracts are not
  enabled;
- tests proving the UI does not call OpenStack, telemetry or host endpoints directly and does not
  store tokens or secrets in browser storage.

## Context

Existing design documents already establish the direction:

- `docs/superpowers/specs/2026-06-25-vsphere-like-admin-console-design.md`;
- `docs/superpowers/specs/2026-06-26-ui-ux-dkb-horizon-vsphere-design.md`;
- `docs/generated/ui-shell-horizon-parity.md`.

The current frontend already has:

- `frontend/src/shell/CloudShell.tsx`;
- `frontend/src/shell/TopChrome.tsx`;
- `frontend/src/shell/ObjectNavigator.tsx`;
- `frontend/src/shell/BottomWorkPanel.tsx`;
- static navigation and Horizon parity registries.

The current limitation is that the shell is still mostly list/view oriented. VM and hypervisor detail
surfaces do not yet expose the full administration model described by the requirements.

Additional vSphere screenshot review on 2026-07-01 refined the object workspace requirements:

- the primary object tabs should stay coarse-grained, while detailed monitor pages live in a local
  secondary side navigation;
- performance time-series and current utilization/capacity bars are different surfaces, not the same
  chart with different data;
- event and task views are dense operator tables with per-column filtering, expandable rows, managed
  columns and bounded page-size controls;
- global warnings and object issue strips are first-class status regions, not incidental card content.

## Scope

This design covers the next offline UI slice only:

- frontend route/component model for VM and hypervisor object workspaces;
- UI state model for actions, metrics, diagnostics and multi-target precheck previews;
- mock/fixture data used only for frontend component tests and visual verification;
- documentation and regression tests for disabled/pending states and security boundaries.

No live OpenStack, Prometheus, host console, SSH, Kolla, Mistral mutation or production identity flow is
introduced by this slice.

## Non-goals

- No live metrics collection.
- No diagnostic bundle generation.
- No VM create/delete/power/snapshot/migration execution.
- No hypervisor reboot, shutdown, maintenance, NTP, network adapter or user-management execution.
- No VM console proxy implementation.
- No browser access to OpenStack, Prometheus, Consul, host management APIs or shell endpoints.
- No new permanent runtime dependency.

## Product Model

### Workspace navigation model

The object workspace should keep two levels of navigation:

- top-level object tabs for stable work areas: `Summary`, `Monitor`, `Configure`, `Permissions` and
  resource-specific relationship tabs such as `VMs`, `Networks`, `Volumes`, `Snapshots` or
  `Updates`;
- secondary navigation inside a selected top-level tab for dense object-local pages such as
  `Performance Overview`, `Utilization`, `Tasks`, `Events` and health/status pages.

This keeps the object header and action model stable while avoiding a long, flat tab row. The
secondary navigation is resource-type-specific: VM and hypervisor monitor pages do not have to expose
identical entries.

The object header should show the resource type icon, object name, warning/health marker, compact
quick actions and a single `Actions` menu. Object-level warnings should also appear as issue strips
near the top of `Summary` or the relevant monitor page, with issue-scoped actions rendered as
pending/disabled/blocked unless backend contracts exist.

### Hypervisor workspace

The hypervisor object workspace should expose these top-level tabs:

- `Summary`: host identity, service status/state, hypervisor type/version, AZ, aggregates,
  running VM count, issue strip, capacity summary, related objects, maintenance/disabled reason and
  freshness.
- `Monitor`: secondary navigation for host health, time-series, utilization, allocation, tasks and
  events.
- `Configure`: pending host configuration surfaces, including network, service/NTP, updates and
  performance parameters when backend contracts are absent.
- `Permissions`: explicit pending/blocked state for host-local users/rights until a PAM/RBAC contract
  is approved.
- `VMs`: server-paginated related VM list, not a full browser-side inventory copy.
- relationship tabs such as `Resource Pools`, `Datastores`, `Networks` and `Updates` only when a
  backend contract or explicit disabled-state placeholder exists.

The hypervisor `Monitor` secondary navigation should include:

- `Issues and Alarms`: all issues, triggered alarms and issue-scoped pending actions.
- `Performance Overview`: CPU, memory, disk and network time-series placeholders with
  datasource/freshness state.
- `Advanced Performance`: planned metric selection and drill-down placeholder.
- `Tasks`: operation timeline and audit/event links by correlation ID.
- `Events`: dense server-paginated event table.
- `Resource Allocation`: CPU, memory and storage allocation pages.
- `Utilization`: current host CPU, memory and storage capacity bars with absolute used/free/capacity
  values and freshness.
- `Hardware Health` and `Service Health`: explicit disabled/pending placeholders until corresponding
  adapters exist.

Required hypervisor actions are visible, but most are not executable in this slice:

- view state: enabled when `hypervisor.read` exists;
- collect diagnostics: pending until backend diagnostic contract exists;
- view metrics: pending/degraded unless a backend telemetry endpoint is available;
- reboot/shutdown: pending;
- enter maintenance with VM evacuation and placement ban: pending first mutating candidate;
- change network/NTP/performance parameters: pending;
- manage host users/rights: blocked until security owner/PAM/RBAC contract exists.

### VM workspace

The VM object workspace should expose these top-level tabs:

- `Summary`: VM identity, project, host, hypervisor, AZ, power/status/task state, flavor, image or boot
  volume, addresses, issue strip, compact capacity/status summary and freshness.
- `Monitor`: secondary navigation for VM issues, performance, utilization, tasks and events.
- `Configure`: hardware, network, media and advanced configuration surfaces, with mutating controls
  pending/blocked until backend operation contracts exist.
- `Permissions`: capability and ownership context where exposed by backend policy.
- `Hardware`: CPU, RAM, disk and NIC summary plus pending modification actions when kept as a
  first-level relationship tab by route design.
- `Network`: NIC list placeholder, IP/gateway/DNS/MTU/VLAN labels where available, enable/disable
  actions pending.
- `Snapshots`: one-time snapshot action pending until backend operation contract exists.
- `Console`: explicit placeholder for console proxy design; no token or console URL exposed.
- `ISO/Media`: ISO 9660 media mount action pending until backend workflow/API contract exists.

The VM `Monitor` secondary navigation should include:

- `Issues and Alarms`: all issues, triggered alarms and issue-scoped pending actions.
- `Performance Overview`: CPU, memory, disk and network time-series placeholders with
  datasource/freshness state.
- `Advanced Performance`: planned metric selection and drill-down placeholder.
- `Utilization`: current CPU, memory, disk and network utilization summary where backend data exists.
- `Tasks`: operation timeline and audit/event links by correlation ID.
- `Events`: dense server-paginated event table.

Required VM actions are visible, but most are not executable in this slice:

- view state: enabled when `instance.read` exists;
- create VM, including empty VM without OS: pending;
- delete/rename: pending;
- power on/off/reboot: pending first VM mutating candidate;
- enable/disable NICs: pending;
- modify CPU/RAM/disk/NICs: pending;
- collect diagnostics: pending;
- view metrics: pending/degraded unless backend telemetry endpoint is available;
- snapshot: pending;
- VM console: blocked until console proxy design is approved;
- ISO mount: pending;
- live migration inside an administration group without guest OS downtime: blocked until group
  boundary, workflow, Nova policy and live migration evidence exist.

## Action State Model

Every object action rendered by the UI must have one of these states:

- `enabled`: backend capability and backend contract exist.
- `disabled`: current subject or object state does not permit the action.
- `pending`: requirement is visible, but backend contract is not implemented in this slice.
- `blocked`: external evidence, security approval or design decision is missing.

For `pending` and `blocked` actions, the UI must show a short reason and must not render a submit
button that can mutate state. Hidden controls are not authorization; direct API requests must still
return protected outcomes when backend endpoints exist.

Enabled mutating actions, in later slices, must use only BFF/API, CSRF, idempotency key,
`operation_id`, backend authorization and audit. This slice prepares the UI surface but does not
enable those flows.

## Multi-object Model

The object workspace must support future multi-target operations without full browser inventory
loading. Selection state is scoped to the current server-paginated page or an explicit backend
selection contract.

For selected VMs or hypervisors the UI should show:

- total selected count;
- allowed count;
- denied count;
- stale/unknown count;
- blocked count;
- reason summary by capability, object state and missing external evidence.

Bulk actions remain `pending` until backend precheck and operation contracts exist. The UI must not
infer permission for objects it cannot see.

## Metrics and Diagnostics

Metrics charts are part of the visible design from this slice, but data source state must be explicit:

- `not_configured`: backend telemetry endpoint is absent;
- `unavailable`: backend reports datasource failure;
- `stale`: data is older than the accepted freshness window;
- `ready`: backend provides aggregated/downsampled series with source and freshness metadata.

Frontend tests may use synthetic chart fixtures. Runtime UI must not call Prometheus, Gnocchi,
Ceilometer, Aetos, OpenStack metrics APIs or host exporters directly.

`Performance Overview` and `Utilization` are separate surfaces:

- `Performance Overview` shows historical or real-time time-series for CPU, memory, disk and network.
- `Utilization` shows current allocation/capacity bars and absolute used/free/capacity values.

Both surfaces must display source, freshness and datasource state. Neither surface may imply that live
telemetry is configured when the backend contract is absent.

Diagnostics are modeled as asynchronous backend jobs in later slices. In this slice the UI shows
planned collection status and safe artifact placeholders only. It must not accept arbitrary shell
commands, paths, scripts, Python, Jinja or host credentials.

## Event and Table UX

Object `Tasks` and `Events` pages should use a dense operator table model:

- server-side pagination, stable sort and typed filters;
- visible page-size control bounded by backend maximum;
- per-column filter affordances and a global filter only when translated to backend query state;
- expandable rows for safe detail fields and correlation IDs;
- managed columns and density state stored as view preference, not result rows;
- target cells linking back to the relevant object workspace;
- `Open in new tab` for large journal views where route state is shareable;
- export shown only as a pending/disabled/backend-bounded action until an audited export contract
  exists.

The UI must not export or copy a full inventory/event dataset from browser memory. Any future export
must be a backend operation with capability checks, scope limits, audit and redaction.

## Data Flow

The slice uses existing BFF/API contracts where available:

- `GET /api/v1/instances`;
- `GET /api/v1/instances/{cloud_id}/{region_id}/{instance_id}`;
- `GET /api/v1/hypervisors`;
- `GET /api/v1/hypervisors/{cloud_id}/{region_id}/{hypervisor_id}`;
- current capabilities/session/readiness endpoints.

Placeholder metrics, diagnostics, console, ISO, snapshot, migration and host-user surfaces are static
frontend states until corresponding OpenAPI-backed backend contracts exist.

No direct browser calls are allowed to:

- OpenStack service endpoints;
- telemetry datasource endpoints;
- host management endpoints;
- Kolla/Ansible endpoints;
- Vault/SecMan, MariaDB, RabbitMQ or SIEM.

## Component Boundaries

The implementation should avoid expanding `frontend/src/App.tsx` further. The later plan should split
the new UI into focused frontend modules, for example:

- `frontend/src/workspace/ObjectWorkspace.tsx`;
- `frontend/src/workspace/ActionState.tsx`;
- `frontend/src/workspace/MetricsPanel.tsx`;
- `frontend/src/workspace/UtilizationPanel.tsx`;
- `frontend/src/workspace/ObjectEventTable.tsx`;
- `frontend/src/workspace/DiagnosticsPanel.tsx`;
- `frontend/src/workspace/SecondaryNavigation.tsx`;
- `frontend/src/workspace/SelectionSummary.tsx`;
- `frontend/src/workspace/vm/VirtualMachineWorkspace.tsx`;
- `frontend/src/workspace/hypervisor/HypervisorWorkspace.tsx`;
- focused tests beside the new components.

Existing shell components can remain stable and pass the selected object context down to the
workspace.

## Error and Empty States

The workspace must distinguish:

- loading object details;
- object not found;
- forbidden by capability or backend policy;
- stale/partial read model;
- telemetry not configured;
- telemetry unavailable;
- utilization data unavailable or stale;
- diagnostics contract not implemented;
- action blocked by missing backend contract;
- action denied by current capability;
- action unavailable because selected targets include stale or incompatible objects.

User-facing errors must be safe and include request/correlation ID when the backend provides it. No
stack traces, tokens, raw request bodies or host secrets are displayed.

## Testing Strategy

The implementation plan should add tests before code for:

- VM workspace renders all required tabs and pending/blocked actions.
- Hypervisor workspace renders all required tabs and pending/blocked actions.
- VM and hypervisor `Monitor` tabs render resource-specific secondary navigation.
- Multi-target summary shows allowed, denied, stale and blocked counts.
- Metrics panels show `not_configured`, `unavailable`, `stale` and `ready` states from fixtures.
- Utilization panels distinguish current capacity bars from performance time-series.
- Event tables use server-side page/filter/sort state and do not export from browser memory.
- Diagnostics panel is pending and does not render a shell/path/script input.
- Console and ISO surfaces are visible but blocked/pending.
- No direct browser call is made to OpenStack, telemetry or host endpoints.
- Browser storage does not receive token, password, private key, credential or console URL values.
- Large-list behavior remains server-paginated; selection does not require fetching the full
  inventory.

Relevant commands after implementation:

- `cd frontend && npm test -- --run src/App.test.tsx src/shell/CloudShell.test.tsx`;
- focused workspace component tests;
- `cd frontend && npm run typecheck`;
- `cd frontend && npm run lint`;
- `./scripts/secret-scan.sh`;
- `git diff --check`.

## Documentation and DKB Impact

This design does not change DKB compliance status. Later implementation must update generated UI
evidence and risk registers because it affects:

- ДКБ-01/03/12: visible protected resources and action surfaces;
- ДКБ-46/49: audit/event visibility for tasks and actions;
- ДКБ-55/56: confirmation that no secret material reaches browser UI;
- ДКБ-77/82: interface/API documentation and evidence;
- ДКБ-69/70 only indirectly through deployment/runtime evidence, not this UI slice.

The main risk is overclaiming: a visible action surface is not an implemented operation, not backend
authorization and not live OpenStack evidence.

## Acceptance For This Design

- The design is committed as a standalone spec.
- The scope is implementable without test stand access.
- Multi-hypervisor and multi-VM action context is explicit.
- Top-level tabs and resource-specific secondary monitor navigation are explicit.
- Mutating requirements are visible but not enabled without backend contracts.
- Metrics and diagnostics are represented as explicit datasource/contract states.
- Utilization and event-table behavior are represented without browser-side full data export.
- Security boundaries remain backend/BFF-only and browser-secret-free.
