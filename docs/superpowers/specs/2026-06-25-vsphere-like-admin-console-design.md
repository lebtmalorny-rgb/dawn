# vSphere-like Admin Console Design

## User Outcome

Cloud UI should present a dense administrative console for hypervisors and virtual machines, using
VMware vSphere as the visual and workflow reference: inventory tree on the left, selected object
workspace in the center, and tasks/events on the right. The first UI slice must show the full
administrative surface, while actions without approved backend workflow/API contracts are visible as
disabled or pending rather than hidden as if they did not exist.

This document captures UI requirements and scope only. It does not implement UI code, backend
workflow contracts, live host operations or production compliance evidence.

## Approved Layout Direction

The approved layout is the classic vSphere shell:

- left inventory tree for region, administration group, hypervisors, VMs, networks and resource groups;
- center object workspace for list/detail pages, tabs, metrics and object actions;
- right tasks/events rail for operation timeline, prechecks, audit-visible status and pending actions;
- top navigation for inventory, operations, audit and administration modules.

The console should feel like an operational tool: compact, table-first, low decoration, stable
dimensions, strong status visibility and no marketing-style landing page.

## Primary Workspaces

### Hypervisors

The hypervisor workspace must support these screens and action states:

| Capability | Initial UI state | Execution path |
|---|---|---|
| View state | Enabled | Read model / backend inventory API |
| Reboot and shutdown | Pending/disabled until workflow exists | Allowlisted workflow with precheck, audit and operation timeline |
| Enter maintenance with VM evacuation and placement ban | First mutating candidate | Allowlisted Mistral workflow; returns `operation_id` |
| VM network settings change: IP, mask, gateway, VLAN, DNS, MTU | Pending/disabled | Backend workflow/API contract required; no browser direct host/API calls |
| Performance parameter changes | Pending/disabled | Backend workflow/API contract required |
| NTP settings and NTP service start/stop | Pending/disabled | Backend automation/workflow contract required |
| Enable/disable network adapters | Pending/disabled | Backend workflow/API contract required |
| Diagnostics collection and viewing | Enabled when diagnostic bundle endpoint exists; otherwise pending | Backend job creates sanitized artifact |
| Performance metrics: CPU, RAM, disk, NICs | Enabled as charts when telemetry endpoint exists; placeholder until then | Backend-only metrics API; no raw browser PromQL |
| Host users and rights management | Pending/disabled | Separate RBAC/workflow design; must not bypass Keystone/PAM policy |

Tabs for a hypervisor detail page:

- Summary;
- VMs;
- Performance;
- Network;
- Services/NTP;
- Diagnostics;
- Users/Roles;
- Tasks/Events.

### Virtual Machines

The VM workspace must support these screens and action states:

| Capability | Initial UI state | Execution path |
|---|---|---|
| Create VM, including empty VM without OS | Pending until create contract exists | Backend API/workflow; idempotency key and operation timeline |
| Delete, rename, view state | State view enabled; mutations pending until contracts exist | Backend API/workflow, audit and prechecks |
| Power on/off, reboot | Good first mutating VM action candidate | Backend operation API; no direct browser OpenStack token |
| Enable/disable VM NICs | Pending/disabled | Backend workflow/API contract required |
| Modify CPU, RAM, disks, NICs | Pending/disabled | Backend workflow/API contract with validation and rollback notes |
| Diagnostics collection and viewing | Pending until endpoint exists | Backend job creates sanitized artifact |
| Metrics charts: CPU, RAM, disk, NICs | Enabled when telemetry API exists; placeholder until then | Backend-only metrics API |
| One-time snapshot | Pending/disabled | Backend operation API; OpenStack policy remains final authority |
| VM console connection | Pending/disabled | Console proxy design required; no tokens exposed to browser |
| Mount ISO 9660 media | Pending/disabled | Backend workflow/API contract required |
| VM migration within administration group without guest OS downtime | Pending/disabled | Backend workflow with group preconditions and live migration evidence |

Tabs for a VM detail page:

- Summary;
- Hardware;
- Network;
- Performance;
- Snapshots;
- Console;
- ISO/Media;
- Tasks/Events.

## Navigation and Object Model

Inventory tree nodes should be:

- cloud/region;
- administration group;
- hypervisors;
- virtual machines;
- networks;
- resource groups.

The tree is navigation and selection, not authorization. Backend capabilities decide whether an action
can be submitted, and direct API calls must still return `401/403` when the subject lacks permission.

Lists remain server-paginated and filterable. The UI must not load the full inventory into the browser.

## Action Model

Every mutating action shown in the console must be one of:

- `enabled`: backend capability and workflow/API contract exists;
- `disabled`: subject lacks capability or object state makes action invalid;
- `pending`: requirement is visible but backend contract is not implemented in this slice;
- `blocked`: action exists but precheck failed or external owner evidence is missing.

Enabled mutating actions must:

- use backend/BFF only;
- include CSRF and idempotency key where required;
- return `operation_id`;
- create sanitized audit events;
- show progress in the tasks/events rail;
- keep OpenStack/host credentials, Vault secrets and tokens out of the browser.

No arbitrary shell command, user-provided workflow name, user-provided Jinja/Python or direct host
credential entry is allowed.

## Metrics and Diagnostics

Performance charts should be present in the screen design from the first UI slice, but data source
availability must be explicit:

- placeholder/skeleton state when backend telemetry endpoint is absent;
- degraded state when datasource is unavailable;
- freshness timestamp and source label when data is present;
- no direct browser access to Prometheus or OpenStack metrics APIs.

Diagnostics should be modeled as asynchronous operations. The UI should display bundle metadata,
safe status and download/view actions only after backend redaction and authorization checks.

## Visual Style

Use PatternFly as the existing implementation base and keep a vSphere-like information architecture:

- compact tables;
- fixed action toolbar;
- status badges and health summary;
- tabs for object details;
- right-side tasks/events rail;
- restrained neutral palette with status colors;
- no hero page, card-heavy marketing layout or decorative backgrounds.

Icons may be used for toolbar actions when a clear PatternFly/lucide equivalent exists. Text labels
remain available for destructive and high-risk actions.

## Security and Compliance Boundaries

The UI design must preserve existing architecture invariants:

- browser calls only frontend/BFF/API;
- no OpenStack tokens, application credentials, Vault tokens, host passwords, private keys or
  certificates in browser storage;
- backend rechecks authorization for every action;
- Keystone/OpenStack policy remains final for OpenStack operations;
- long-running actions use allowlisted workflows or backend operation contracts;
- audit payloads do not include secrets or sensitive request bodies.

This spec does not change DKB compliance status. It defines future UI behavior and must be paired
with backend tests, OpenAPI/contracts, traceability updates and live evidence when implemented.

## Implementation Slicing Recommendation

Recommended first UI implementation slice after deployment gates:

1. Shell/navigation: vSphere-like layout, inventory tree, object workspace and tasks/events rail.
2. Read-only hypervisor/VM detail pages using existing inventory APIs and disabled/pending actions.
3. Metrics and diagnostics placeholders with explicit unavailable/degraded states.
4. First safe operations: host maintenance mode and VM power actions, only after backend workflow
   contracts and negative authorization tests exist.
5. Expanded VM/host administration actions in separate slices, each with precheck, workflow, audit,
   rollback and evidence.

## Open Questions

- Which telemetry backend is authoritative for first charts: Prometheus path, OpenStack telemetry or
  synthetic/read-model metrics?
- Which console proxy architecture will be approved for VM console access without exposing tokens?
- Which host-level operations are allowed through portal workflows versus kept in external PAM/CLI
  runbooks?
- What exact administration group boundary controls live migration and bulk operations?
