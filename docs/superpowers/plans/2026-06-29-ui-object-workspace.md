# UI Object Workspace Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build an offline, vSphere-informed VM/Hypervisor object workspace with visible pending/blocked administration actions, metrics/diagnostics states and multi-target summaries.

**Architecture:** Keep the existing `CloudShell` and inventory API flow. Add focused `frontend/src/workspace/*` components that receive existing `InstanceItem`, `HypervisorItem` and capability data, then integrate them below the current server-paginated inventory tables without adding live backend contracts or browser calls outside `/api/v1`.

**Tech Stack:** React, TypeScript, PatternFly base styles, Vitest/React Testing Library, existing BFF API types from `frontend/src/api.ts`.

---

## File Structure

- Create `frontend/src/workspace/types.ts`: shared action, metric, diagnostic and selection state types plus small pure helper functions.
- Create `frontend/src/workspace/ActionState.tsx`: renders `enabled`, `disabled`, `pending` and `blocked` action rows without mutation controls for non-enabled states.
- Create `frontend/src/workspace/SelectionSummary.tsx`: renders selected/allowed/denied/stale/blocked counts for current-page selections.
- Create `frontend/src/workspace/MetricsPanel.tsx`: renders datasource states for CPU, memory, disk and network metrics.
- Create `frontend/src/workspace/DiagnosticsPanel.tsx`: renders diagnostic collection placeholder without shell/path/script inputs.
- Create `frontend/src/workspace/TasksEventsPanel.tsx`: renders static operation/audit correlation placeholders for object workspaces.
- Create `frontend/src/workspace/vm/VirtualMachineWorkspace.tsx`: renders VM tabs and required pending/blocked actions.
- Create `frontend/src/workspace/hypervisor/HypervisorWorkspace.tsx`: renders hypervisor tabs and required pending/blocked actions.
- Create focused tests beside each component.
- Modify `frontend/src/App.tsx`: import workspace components and render a selected-object preview for the first item on the current server-paginated page.
- Modify `frontend/src/styles.css`: add dense workspace styles with stable dimensions and no decorative layout.
- Modify `docs/generated/ui-shell-horizon-parity.md`: add evidence lines for object workspace when implementation passes.
- Modify `docs/generated/risk-register.md`: add one risk row that object workspace surfaces are not implemented backend actions.

## Task 1: Shared Workspace Model And Action State

**Files:**
- Create: `frontend/src/workspace/types.ts`
- Create: `frontend/src/workspace/ActionState.tsx`
- Create: `frontend/src/workspace/ActionState.test.tsx`

- [x] **Step 1: Write the failing action-state tests**

Create `frontend/src/workspace/ActionState.test.tsx`:

```tsx
import { render, screen, within } from "@testing-library/react";
import { describe, expect, test } from "vitest";

import { ActionStateList } from "./ActionState";
import type { WorkspaceAction } from "./types";

const actions: WorkspaceAction[] = [
  {
    key: "view-state",
    title: "Просмотр состояния",
    state: "enabled",
    reason: "Доступно через read model",
  },
  {
    key: "power-on",
    title: "Включить ВМ",
    state: "pending",
    reason: "Нет backend operation contract",
  },
  {
    key: "vm-console",
    title: "Консоль ВМ",
    state: "blocked",
    reason: "Console proxy design is not approved",
  },
  {
    key: "rename",
    title: "Переименовать",
    state: "disabled",
    reason: "Требуется capability: instance.manage",
  },
];

describe("ActionStateList", () => {
  test("renders explicit enabled, disabled, pending and blocked states", () => {
    render(<ActionStateList actions={actions} title="Действия ВМ" />);

    expect(screen.getByRole("heading", { name: "Действия ВМ" })).toBeInTheDocument();
    for (const action of actions) {
      const row = screen.getByText(action.title).closest("li");
      expect(row).not.toBeNull();
      expect(within(row as HTMLElement).getByText(action.reason)).toBeInTheDocument();
      expect(within(row as HTMLElement).getByText(action.state)).toBeInTheDocument();
    }
  });

  test("does not render mutation buttons for pending or blocked actions", () => {
    render(<ActionStateList actions={actions} title="Действия ВМ" />);

    expect(screen.queryByRole("button", { name: /Включить ВМ/ })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Консоль ВМ/ })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Переименовать/ })).not.toBeInTheDocument();
  });
});
```

- [x] **Step 2: Run the failing action-state tests**

Run:

```bash
cd frontend && npm test -- --run src/workspace/ActionState.test.tsx
```

Expected result: fail because `frontend/src/workspace/ActionState.tsx` does not exist.

- [x] **Step 3: Add shared types**

Create `frontend/src/workspace/types.ts`:

```ts
export type WorkspaceActionState = "enabled" | "disabled" | "pending" | "blocked";

export type WorkspaceAction = {
  key: string;
  title: string;
  state: WorkspaceActionState;
  reason: string;
};

export type SelectionSummary = {
  total: number;
  allowed: number;
  denied: number;
  stale: number;
  blocked: number;
};

export type MetricDatasourceState =
  | "not_configured"
  | "unavailable"
  | "stale"
  | "ready";

export type MetricSeries = {
  key: "cpu" | "memory" | "disk" | "network";
  title: string;
  unit: string;
  state: MetricDatasourceState;
  freshnessLabel: string;
  points: number[];
};

export type DiagnosticState = {
  state: "pending" | "blocked";
  title: string;
  reason: string;
};

export function actionStateLabel(state: WorkspaceActionState): string {
  if (state === "enabled") return "enabled";
  if (state === "disabled") return "disabled";
  if (state === "pending") return "pending";
  return "blocked";
}
```

- [x] **Step 4: Implement action-state component**

Create `frontend/src/workspace/ActionState.tsx`:

```tsx
import type { WorkspaceAction } from "./types";
import { actionStateLabel } from "./types";

type ActionStateListProps = {
  title: string;
  actions: WorkspaceAction[];
};

export function ActionStateList({ actions, title }: ActionStateListProps) {
  return (
    <section className="cloud-ui-workspace-panel" aria-label={title}>
      <h3>{title}</h3>
      <ul className="cloud-ui-action-state-list">
        {actions.map((action) => (
          <li key={action.key} data-state={action.state}>
            <div>
              <strong>{action.title}</strong>
              <p className="cloud-ui-muted">{action.reason}</p>
            </div>
            <span className={`cloud-ui-badge cloud-ui-action-${action.state}`}>
              {actionStateLabel(action.state)}
            </span>
          </li>
        ))}
      </ul>
    </section>
  );
}
```

- [x] **Step 5: Run action-state tests**

Run:

```bash
cd frontend && npm test -- --run src/workspace/ActionState.test.tsx
```

Expected result: tests pass.

- [x] **Step 6: Commit Task 1**

Run:

```bash
git add frontend/src/workspace/types.ts frontend/src/workspace/ActionState.tsx frontend/src/workspace/ActionState.test.tsx
git commit -m "feat: add ui workspace action states"
```

## Task 2: Metrics, Diagnostics And Selection Panels

**Files:**
- Create: `frontend/src/workspace/MetricsPanel.tsx`
- Create: `frontend/src/workspace/MetricsPanel.test.tsx`
- Create: `frontend/src/workspace/DiagnosticsPanel.tsx`
- Create: `frontend/src/workspace/DiagnosticsPanel.test.tsx`
- Create: `frontend/src/workspace/SelectionSummary.tsx`
- Create: `frontend/src/workspace/SelectionSummary.test.tsx`
- Modify: `frontend/src/workspace/types.ts`

- [x] **Step 1: Write failing panel tests**

Create `frontend/src/workspace/MetricsPanel.test.tsx`:

```tsx
import { render, screen } from "@testing-library/react";
import { describe, expect, test } from "vitest";

import { MetricsPanel } from "./MetricsPanel";
import type { MetricSeries } from "./types";

const metrics: MetricSeries[] = [
  { key: "cpu", title: "CPU", unit: "%", state: "ready", freshnessLabel: "Observed 10:00 UTC", points: [10, 20, 30] },
  { key: "memory", title: "RAM", unit: "%", state: "stale", freshnessLabel: "Stale after 300s", points: [55, 57] },
  { key: "disk", title: "Disk", unit: "iops", state: "unavailable", freshnessLabel: "Datasource down", points: [] },
  { key: "network", title: "Network", unit: "Mbps", state: "not_configured", freshnessLabel: "Telemetry endpoint absent", points: [] },
];

describe("MetricsPanel", () => {
  test("renders metric datasource states without direct datasource controls", () => {
    render(<MetricsPanel metrics={metrics} title="Performance" />);

    expect(screen.getByRole("heading", { name: "Performance" })).toBeInTheDocument();
    expect(screen.getByText("CPU")).toBeInTheDocument();
    expect(screen.getByText("ready")).toBeInTheDocument();
    expect(screen.getByText("stale")).toBeInTheDocument();
    expect(screen.getByText("unavailable")).toBeInTheDocument();
    expect(screen.getByText("not_configured")).toBeInTheDocument();
    expect(screen.queryByRole("textbox")).not.toBeInTheDocument();
    expect(screen.queryByText(/PromQL/i)).not.toBeInTheDocument();
  });
});
```

Create `frontend/src/workspace/DiagnosticsPanel.test.tsx`:

```tsx
import { render, screen } from "@testing-library/react";
import { describe, expect, test } from "vitest";

import { DiagnosticsPanel } from "./DiagnosticsPanel";

describe("DiagnosticsPanel", () => {
  test("shows safe pending diagnostic state without shell inputs", () => {
    render(
      <DiagnosticsPanel
        state={{
          state: "pending",
          title: "Диагностика гипервизора",
          reason: "Backend diagnostic bundle contract is not enabled",
        }}
      />,
    );

    expect(screen.getByRole("heading", { name: "Диагностика гипервизора" })).toBeInTheDocument();
    expect(screen.getByText("pending")).toBeInTheDocument();
    expect(screen.queryByLabelText(/command|script|path|shell/i)).not.toBeInTheDocument();
    expect(screen.queryByRole("textbox")).not.toBeInTheDocument();
  });
});
```

Create `frontend/src/workspace/SelectionSummary.test.tsx`:

```tsx
import { render, screen } from "@testing-library/react";
import { describe, expect, test } from "vitest";

import { SelectionSummaryPanel } from "./SelectionSummary";

describe("SelectionSummaryPanel", () => {
  test("renders allowed denied stale and blocked counts", () => {
    render(
      <SelectionSummaryPanel
        summary={{ total: 4, allowed: 1, denied: 1, stale: 1, blocked: 1 }}
        title="Выбранные цели"
      />,
    );

    expect(screen.getByText("Total 4")).toBeInTheDocument();
    expect(screen.getByText("Allowed 1")).toBeInTheDocument();
    expect(screen.getByText("Denied 1")).toBeInTheDocument();
    expect(screen.getByText("Stale 1")).toBeInTheDocument();
    expect(screen.getByText("Blocked 1")).toBeInTheDocument();
  });
});
```

- [x] **Step 2: Run failing panel tests**

Run:

```bash
cd frontend && npm test -- --run src/workspace/MetricsPanel.test.tsx src/workspace/DiagnosticsPanel.test.tsx src/workspace/SelectionSummary.test.tsx
```

Expected result: fail because the panel components do not exist.

- [x] **Step 3: Implement panels**

Create `frontend/src/workspace/MetricsPanel.tsx`:

```tsx
import type { MetricSeries } from "./types";

type MetricsPanelProps = {
  title: string;
  metrics: MetricSeries[];
};

export function MetricsPanel({ metrics, title }: MetricsPanelProps) {
  return (
    <section className="cloud-ui-workspace-panel" aria-label={title}>
      <h3>{title}</h3>
      <div className="cloud-ui-metrics-grid">
        {metrics.map((metric) => (
          <article key={metric.key} className="cloud-ui-metric-tile">
            <div className="cloud-ui-metric-header">
              <strong>{metric.title}</strong>
              <span className={`cloud-ui-badge cloud-ui-metric-${metric.state}`}>
                {metric.state}
              </span>
            </div>
            <p className="cloud-ui-muted">{metric.freshnessLabel}</p>
            <div className="cloud-ui-metric-sparkline" aria-label={`${metric.title} series`}>
              {metric.points.length === 0
                ? "No series"
                : metric.points.map((point) => `${point}${metric.unit}`).join(" / ")}
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}
```

Create `frontend/src/workspace/DiagnosticsPanel.tsx`:

```tsx
import type { DiagnosticState } from "./types";

type DiagnosticsPanelProps = {
  state: DiagnosticState;
};

export function DiagnosticsPanel({ state }: DiagnosticsPanelProps) {
  return (
    <section className="cloud-ui-workspace-panel" aria-label={state.title}>
      <div className="cloud-ui-workspace-panel-header">
        <h3>{state.title}</h3>
        <span className={`cloud-ui-badge cloud-ui-action-${state.state}`}>
          {state.state}
        </span>
      </div>
      <p className="cloud-ui-muted">{state.reason}</p>
      <p className="cloud-ui-empty">
        Diagnostic bundle collection will appear here after an approved backend contract returns a sanitized artifact.
      </p>
    </section>
  );
}
```

Create `frontend/src/workspace/SelectionSummary.tsx`:

```tsx
import type { SelectionSummary } from "./types";

type SelectionSummaryPanelProps = {
  title: string;
  summary: SelectionSummary;
};

export function SelectionSummaryPanel({ summary, title }: SelectionSummaryPanelProps) {
  return (
    <section className="cloud-ui-workspace-panel" aria-label={title}>
      <h3>{title}</h3>
      <div className="cloud-ui-selection-summary">
        <span>Total {summary.total}</span>
        <span>Allowed {summary.allowed}</span>
        <span>Denied {summary.denied}</span>
        <span>Stale {summary.stale}</span>
        <span>Blocked {summary.blocked}</span>
      </div>
    </section>
  );
}
```

- [x] **Step 4: Run panel tests**

Run:

```bash
cd frontend && npm test -- --run src/workspace/MetricsPanel.test.tsx src/workspace/DiagnosticsPanel.test.tsx src/workspace/SelectionSummary.test.tsx
```

Expected result: tests pass.

- [x] **Step 5: Commit Task 2**

Run:

```bash
git add frontend/src/workspace/MetricsPanel.tsx frontend/src/workspace/MetricsPanel.test.tsx frontend/src/workspace/DiagnosticsPanel.tsx frontend/src/workspace/DiagnosticsPanel.test.tsx frontend/src/workspace/SelectionSummary.tsx frontend/src/workspace/SelectionSummary.test.tsx frontend/src/workspace/types.ts
git commit -m "feat: add ui workspace status panels"
```

## Task 3: VM And Hypervisor Workspace Components

**Files:**
- Create: `frontend/src/workspace/TasksEventsPanel.tsx`
- Create: `frontend/src/workspace/vm/VirtualMachineWorkspace.tsx`
- Create: `frontend/src/workspace/vm/VirtualMachineWorkspace.test.tsx`
- Create: `frontend/src/workspace/hypervisor/HypervisorWorkspace.tsx`
- Create: `frontend/src/workspace/hypervisor/HypervisorWorkspace.test.tsx`

- [x] **Step 1: Write failing VM workspace test**

Create `frontend/src/workspace/vm/VirtualMachineWorkspace.test.tsx`:

```tsx
import { render, screen } from "@testing-library/react";
import { describe, expect, test } from "vitest";

import type { InstanceItem } from "../../api";
import { VirtualMachineWorkspace } from "./VirtualMachineWorkspace";

const vm: InstanceItem = {
  cloud_id: "synthetic",
  region_id: "RegionOne",
  instance_id: "instance-0001",
  name: "vm-active",
  project_id: "project-a",
  user_id: "user-a",
  status: "ACTIVE",
  power_state: "running",
  task_state: null,
  vm_state: "active",
  host_name: "compute-a",
  hypervisor_id: "hypervisor-0001",
  availability_zone: "nova",
  flavor_id: "small",
  vcpus: 2,
  ram_mb: 4096,
  disk_gb: 40,
  image_id: "image-0001",
  boot_volume_id: null,
  addresses: { private: ["10.0.0.10"] },
  source_created_at: "2026-06-20T10:00:00Z",
  source_updated_at: "2026-06-21T09:59:00Z",
  observed_at: "2026-06-21T10:00:00Z",
  sync_generation: 1,
  sync_status: "ok",
};

describe("VirtualMachineWorkspace", () => {
  test("renders required VM administration tabs and blocked/pending actions", () => {
    render(<VirtualMachineWorkspace capabilities={["instance.read"]} instance={vm} />);

    for (const label of ["Summary", "Hardware", "Network", "Performance", "Snapshots", "Console", "ISO/Media", "Tasks/Events"]) {
      expect(screen.getByText(label)).toBeInTheDocument();
    }
    expect(screen.getByText("Create VM without OS")).toBeInTheDocument();
    expect(screen.getByText("Power on/off/reboot")).toBeInTheDocument();
    expect(screen.getByText("VM console")).toBeInTheDocument();
    expect(screen.getByText("ISO 9660 media mount")).toBeInTheDocument();
    expect(screen.getByText("Live migration inside administration group")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Power on/i })).not.toBeInTheDocument();
  });
});
```

- [x] **Step 2: Write failing hypervisor workspace test**

Create `frontend/src/workspace/hypervisor/HypervisorWorkspace.test.tsx`:

```tsx
import { render, screen } from "@testing-library/react";
import { describe, expect, test } from "vitest";

import type { HypervisorItem } from "../../api";
import { HypervisorWorkspace } from "./HypervisorWorkspace";

const hypervisor: HypervisorItem = {
  cloud_id: "synthetic",
  region_id: "RegionOne",
  hypervisor_id: "hypervisor-0001",
  host_name: "compute-a",
  service_id: "service-0001",
  service_status: "enabled",
  service_state: "up",
  hypervisor_type: "QEMU",
  hypervisor_version: "8.2",
  availability_zone: "nova",
  aggregates: ["az-a"],
  vcpus_total: 64,
  vcpus_used: 24,
  ram_mb_total: 262144,
  ram_mb_used: 98304,
  disk_gb_total: 2048,
  disk_gb_used: 512,
  running_vms: 18,
  disabled_reason: null,
  maintenance_status: null,
  observed_at: "2026-06-21T10:00:00Z",
  sync_generation: 1,
  sync_status: "ok",
};

describe("HypervisorWorkspace", () => {
  test("renders required hypervisor administration tabs and blocked/pending actions", () => {
    render(<HypervisorWorkspace capabilities={["hypervisor.read"]} hypervisor={hypervisor} />);

    for (const label of ["Summary", "VMs", "Performance", "Network", "Services/NTP", "Diagnostics", "Users/Roles", "Tasks/Events"]) {
      expect(screen.getByText(label)).toBeInTheDocument();
    }
    expect(screen.getByText("Enter maintenance with evacuation")).toBeInTheDocument();
    expect(screen.getByText("Reboot or shutdown")).toBeInTheDocument();
    expect(screen.getByText("Network adapter configuration")).toBeInTheDocument();
    expect(screen.getByText("Host users and rights")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Reboot/i })).not.toBeInTheDocument();
  });
});
```

- [x] **Step 3: Run failing workspace tests**

Run:

```bash
cd frontend && npm test -- --run src/workspace/vm/VirtualMachineWorkspace.test.tsx src/workspace/hypervisor/HypervisorWorkspace.test.tsx
```

Expected result: fail because workspace components do not exist.

- [x] **Step 4: Implement tasks/events panel**

Create `frontend/src/workspace/TasksEventsPanel.tsx`:

```tsx
type TasksEventsPanelProps = {
  objectId: string;
};

export function TasksEventsPanel({ objectId }: TasksEventsPanelProps) {
  return (
    <section className="cloud-ui-workspace-panel" aria-label="Tasks and events">
      <h3>Tasks/Events</h3>
      <p className="cloud-ui-muted">
        Operation timeline and audit links will be correlated by object ID and request ID.
      </p>
      <code>{objectId}</code>
    </section>
  );
}
```

- [x] **Step 5: Implement VM workspace**

Create `frontend/src/workspace/vm/VirtualMachineWorkspace.tsx`:

```tsx
import type { InstanceItem } from "../../api";
import { ActionStateList } from "../ActionState";
import { DiagnosticsPanel } from "../DiagnosticsPanel";
import { MetricsPanel } from "../MetricsPanel";
import { SelectionSummaryPanel } from "../SelectionSummary";
import { TasksEventsPanel } from "../TasksEventsPanel";
import type { MetricSeries, WorkspaceAction } from "../types";

type VirtualMachineWorkspaceProps = {
  instance: InstanceItem;
  capabilities: string[];
};

const VM_METRICS: MetricSeries[] = [
  { key: "cpu", title: "CPU", unit: "%", state: "not_configured", freshnessLabel: "Backend telemetry endpoint absent", points: [] },
  { key: "memory", title: "RAM", unit: "%", state: "not_configured", freshnessLabel: "Backend telemetry endpoint absent", points: [] },
  { key: "disk", title: "Disk", unit: "iops", state: "not_configured", freshnessLabel: "Backend telemetry endpoint absent", points: [] },
  { key: "network", title: "Network", unit: "Mbps", state: "not_configured", freshnessLabel: "Backend telemetry endpoint absent", points: [] },
];

export function VirtualMachineWorkspace({ capabilities, instance }: VirtualMachineWorkspaceProps) {
  const canRead = capabilities.includes("instance.read");
  const actions: WorkspaceAction[] = [
    { key: "view", title: "View state", state: canRead ? "enabled" : "disabled", reason: canRead ? "Read model projection available" : "Требуется capability: instance.read" },
    { key: "create-empty", title: "Create VM without OS", state: "pending", reason: "Create operation contract is not enabled" },
    { key: "delete-rename", title: "Delete or rename", state: "pending", reason: "Mutation contract and audit mapping are not enabled" },
    { key: "power", title: "Power on/off/reboot", state: "pending", reason: "First VM mutating candidate, backend operation contract required" },
    { key: "nics", title: "Enable or disable NICs", state: "pending", reason: "Network mutation contract required" },
    { key: "modify", title: "Modify CPU/RAM/disk/NIC", state: "pending", reason: "Validation and rollback contract required" },
    { key: "snapshot", title: "One-time snapshot", state: "pending", reason: "Snapshot operation contract required" },
    { key: "console", title: "VM console", state: "blocked", reason: "Console proxy design is not approved" },
    { key: "iso", title: "ISO 9660 media mount", state: "pending", reason: "Media workflow/API contract required" },
    { key: "migration", title: "Live migration inside administration group", state: "blocked", reason: "Group boundary, workflow, Nova policy and live evidence required" },
  ];

  return (
    <section className="cloud-ui-object-workspace" aria-label="VM object workspace">
      <nav className="cloud-ui-workspace-tabs" aria-label="VM workspace tabs">
        {["Summary", "Hardware", "Network", "Performance", "Snapshots", "Console", "ISO/Media", "Tasks/Events"].map((tab) => (
          <span key={tab}>{tab}</span>
        ))}
      </nav>
      <section className="cloud-ui-workspace-panel" aria-label="VM summary">
        <h3>Summary</h3>
        <dl className="cloud-ui-detail-list">
          <div><dt>Name</dt><dd>{instance.name}</dd></div>
          <div><dt>Status</dt><dd>{instance.status} / {instance.power_state}</dd></div>
          <div><dt>Host</dt><dd>{instance.host_name ?? "-"}</dd></div>
          <div><dt>Flavor</dt><dd>{instance.vcpus} vCPU / {instance.ram_mb} MB / {instance.disk_gb} GB</dd></div>
        </dl>
      </section>
      <SelectionSummaryPanel summary={{ total: 1, allowed: canRead ? 1 : 0, denied: canRead ? 0 : 1, stale: instance.sync_status === "ok" ? 0 : 1, blocked: 0 }} title="Selected VM targets" />
      <ActionStateList actions={actions} title="VM actions" />
      <MetricsPanel metrics={VM_METRICS} title="Performance" />
      <DiagnosticsPanel state={{ state: "pending", title: "Diagnostics", reason: "Backend diagnostic bundle contract is not enabled" }} />
      <TasksEventsPanel objectId={instance.instance_id} />
    </section>
  );
}
```

- [x] **Step 6: Implement hypervisor workspace**

Create `frontend/src/workspace/hypervisor/HypervisorWorkspace.tsx`:

```tsx
import type { HypervisorItem } from "../../api";
import { ActionStateList } from "../ActionState";
import { DiagnosticsPanel } from "../DiagnosticsPanel";
import { MetricsPanel } from "../MetricsPanel";
import { SelectionSummaryPanel } from "../SelectionSummary";
import { TasksEventsPanel } from "../TasksEventsPanel";
import type { MetricSeries, WorkspaceAction } from "../types";

type HypervisorWorkspaceProps = {
  hypervisor: HypervisorItem;
  capabilities: string[];
};

const HYPERVISOR_METRICS: MetricSeries[] = [
  { key: "cpu", title: "CPU", unit: "%", state: "not_configured", freshnessLabel: "Backend telemetry endpoint absent", points: [] },
  { key: "memory", title: "RAM", unit: "%", state: "not_configured", freshnessLabel: "Backend telemetry endpoint absent", points: [] },
  { key: "disk", title: "Disk", unit: "iops", state: "not_configured", freshnessLabel: "Backend telemetry endpoint absent", points: [] },
  { key: "network", title: "Network", unit: "Mbps", state: "not_configured", freshnessLabel: "Backend telemetry endpoint absent", points: [] },
];

export function HypervisorWorkspace({ capabilities, hypervisor }: HypervisorWorkspaceProps) {
  const canRead = capabilities.includes("hypervisor.read");
  const actions: WorkspaceAction[] = [
    { key: "view", title: "View state", state: canRead ? "enabled" : "disabled", reason: canRead ? "Read model projection available" : "Требуется capability: hypervisor.read" },
    { key: "maintenance", title: "Enter maintenance with evacuation", state: "pending", reason: "First host mutating candidate, Mistral workflow contract required" },
    { key: "reboot", title: "Reboot or shutdown", state: "pending", reason: "Host lifecycle workflow contract required" },
    { key: "network", title: "Network adapter configuration", state: "pending", reason: "Backend workflow/API contract required" },
    { key: "ntp", title: "NTP and service management", state: "pending", reason: "Backend automation contract required" },
    { key: "users", title: "Host users and rights", state: "blocked", reason: "Security owner, PAM and RBAC contract required" },
  ];

  return (
    <section className="cloud-ui-object-workspace" aria-label="Hypervisor object workspace">
      <nav className="cloud-ui-workspace-tabs" aria-label="Hypervisor workspace tabs">
        {["Summary", "VMs", "Performance", "Network", "Services/NTP", "Diagnostics", "Users/Roles", "Tasks/Events"].map((tab) => (
          <span key={tab}>{tab}</span>
        ))}
      </nav>
      <section className="cloud-ui-workspace-panel" aria-label="Hypervisor summary">
        <h3>Summary</h3>
        <dl className="cloud-ui-detail-list">
          <div><dt>Host</dt><dd>{hypervisor.host_name}</dd></div>
          <div><dt>Service</dt><dd>{hypervisor.service_status} / {hypervisor.service_state}</dd></div>
          <div><dt>Capacity</dt><dd>{hypervisor.vcpus_used}/{hypervisor.vcpus_total} vCPU · {hypervisor.ram_mb_used}/{hypervisor.ram_mb_total} MB RAM · {hypervisor.disk_gb_used}/{hypervisor.disk_gb_total} GB disk</dd></div>
          <div><dt>Running VMs</dt><dd>{hypervisor.running_vms}</dd></div>
        </dl>
      </section>
      <SelectionSummaryPanel summary={{ total: 1, allowed: canRead ? 1 : 0, denied: canRead ? 0 : 1, stale: hypervisor.sync_status === "ok" ? 0 : 1, blocked: 0 }} title="Selected hypervisor targets" />
      <ActionStateList actions={actions} title="Hypervisor actions" />
      <MetricsPanel metrics={HYPERVISOR_METRICS} title="Performance" />
      <DiagnosticsPanel state={{ state: "pending", title: "Diagnostics", reason: "Backend diagnostic bundle contract is not enabled" }} />
      <TasksEventsPanel objectId={hypervisor.hypervisor_id} />
    </section>
  );
}
```

- [x] **Step 7: Run workspace tests**

Run:

```bash
cd frontend && npm test -- --run src/workspace/vm/VirtualMachineWorkspace.test.tsx src/workspace/hypervisor/HypervisorWorkspace.test.tsx
```

Expected result: tests pass.

- [x] **Step 8: Commit Task 3**

Run:

```bash
git add frontend/src/workspace/TasksEventsPanel.tsx frontend/src/workspace/vm/VirtualMachineWorkspace.tsx frontend/src/workspace/vm/VirtualMachineWorkspace.test.tsx frontend/src/workspace/hypervisor/HypervisorWorkspace.tsx frontend/src/workspace/hypervisor/HypervisorWorkspace.test.tsx
git commit -m "feat: add vm and hypervisor workspaces"
```

## Task 4: Integrate Workspace Into Inventory UI

**Files:**
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/App.test.tsx`
- Modify: `frontend/src/styles.css`

- [x] **Step 1: Write failing App integration tests**

Append these tests to `frontend/src/App.test.tsx`:

```tsx
test("renders VM object workspace from the current paginated inventory page", async () => {
  window.history.replaceState({}, "", "/?view=instances");
  const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
    const url = String(input);
    if (url === "/api/v1/session") {
      return jsonResponse(operatorSessionPayload);
    }
    if (url === "/api/v1/health/ready") {
      return jsonResponse(readyPayload);
    }
    if (url === "/api/v1/capabilities") {
      return jsonResponse(capabilitiesPayload(["instance.read", "hypervisor.read"]));
    }
    if (url === "/api/v1/session/csrf") {
      return jsonResponse({
        subject: operatorSessionPayload.subject,
        csrf: "restored-csrf-value",
        expires_at: "2026-06-21T15:00:00Z",
      });
    }
    if (url === "/api/v1/inventory/modules") {
      return jsonResponse(inventoryModulesPayload());
    }
    if (url === "/api/v1/instances?limit=50&sort=name.asc") {
      return jsonResponse(inventoryPage([instanceItem({ name: "vm-workspace" })]));
    }
    throw new Error(`unexpected fetch ${url}`);
  });
  vi.stubGlobal("fetch", fetchMock);

  render(<App />);

  expect(await screen.findByRole("region", { name: "VM object workspace" })).toBeInTheDocument();
  expect(screen.getByText("Power on/off/reboot")).toBeInTheDocument();
  expect(screen.getByText("VM console")).toBeInTheDocument();
  expect(screen.getByText("Selected VM targets")).toBeInTheDocument();
  expect(screen.queryByText(/prometheus/i)).not.toBeInTheDocument();
});

test("renders hypervisor object workspace from the current paginated inventory page", async () => {
  window.history.replaceState({}, "", "/?view=hypervisors");
  const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
    const url = String(input);
    if (url === "/api/v1/session") {
      return jsonResponse(operatorSessionPayload);
    }
    if (url === "/api/v1/health/ready") {
      return jsonResponse(readyPayload);
    }
    if (url === "/api/v1/capabilities") {
      return jsonResponse(capabilitiesPayload(["instance.read", "hypervisor.read"]));
    }
    if (url === "/api/v1/session/csrf") {
      return jsonResponse({
        subject: operatorSessionPayload.subject,
        csrf: "restored-csrf-value",
        expires_at: "2026-06-21T15:00:00Z",
      });
    }
    if (url === "/api/v1/inventory/modules") {
      return jsonResponse(inventoryModulesPayload());
    }
    if (url === "/api/v1/hypervisors?limit=50&sort=host_name.asc") {
      return jsonResponse(inventoryPage([hypervisorItem({ host_name: "compute-workspace" })]));
    }
    throw new Error(`unexpected fetch ${url}`);
  });
  vi.stubGlobal("fetch", fetchMock);

  render(<App />);

  expect(await screen.findByRole("region", { name: "Hypervisor object workspace" })).toBeInTheDocument();
  expect(screen.getByText("Enter maintenance with evacuation")).toBeInTheDocument();
  expect(screen.getByText("Host users and rights")).toBeInTheDocument();
  expect(screen.getByText("Selected hypervisor targets")).toBeInTheDocument();
  expect(screen.queryByRole("textbox", { name: /shell|command|path|script/i })).not.toBeInTheDocument();
});
```

- [x] **Step 2: Run failing App integration tests**

Run:

```bash
cd frontend && npm test -- --run src/App.test.tsx
```

Expected result: new tests fail because `InventoryWorkArea` does not render workspace components.

- [x] **Step 3: Import workspace components in App**

Modify `frontend/src/App.tsx` imports:

```tsx
import { HypervisorWorkspace } from "./workspace/hypervisor/HypervisorWorkspace";
import { VirtualMachineWorkspace } from "./workspace/vm/VirtualMachineWorkspace";
```

- [x] **Step 4: Render workspace after current inventory tables**

In `InventoryWorkArea`, after the existing `renderInstancesPage(...)` block, add:

```tsx
      {state.type === "ready" &&
        state.view === "instances" &&
        activeView === "instances" &&
        state.page.items.length > 0 && (
          <VirtualMachineWorkspace
            capabilities={capabilities.capabilities}
            instance={state.page.items[0]}
          />
        )}
```

After the existing `renderHypervisorsPage(...)` block, add:

```tsx
      {state.type === "ready" &&
        state.view === "hypervisors" &&
        activeView === "hypervisors" &&
        state.page.items.length > 0 && (
          <HypervisorWorkspace
            capabilities={capabilities.capabilities}
            hypervisor={state.page.items[0]}
          />
        )}
```

This intentionally uses the first item on the current server-paginated page. It does not fetch a full
inventory and does not create a new backend route.

- [x] **Step 5: Add dense workspace styles**

Append to `frontend/src/styles.css`:

```css
.cloud-ui-object-workspace {
  border-top: 1px solid #d2d2d2;
  display: grid;
  gap: 0.75rem;
  min-width: 0;
  padding-top: 0.75rem;
}

.cloud-ui-workspace-tabs {
  display: flex;
  flex-wrap: wrap;
  gap: 0.375rem;
}

.cloud-ui-workspace-tabs span {
  background: #ffffff;
  border: 1px solid #d2d2d2;
  color: #151515;
  padding: 0.25rem 0.5rem;
}

.cloud-ui-workspace-panel {
  background: #ffffff;
  border: 1px solid #d2d2d2;
  display: grid;
  gap: 0.5rem;
  min-width: 0;
  padding: 0.75rem;
}

.cloud-ui-workspace-panel h3 {
  font-size: 1rem;
  margin: 0;
}

.cloud-ui-workspace-panel-header,
.cloud-ui-metric-header {
  align-items: center;
  display: flex;
  gap: 0.5rem;
  justify-content: space-between;
  min-width: 0;
}

.cloud-ui-action-state-list {
  display: grid;
  gap: 0.5rem;
  list-style: none;
  margin: 0;
  padding: 0;
}

.cloud-ui-action-state-list li {
  align-items: start;
  border-top: 1px solid #d2d2d2;
  display: grid;
  gap: 0.5rem;
  grid-template-columns: minmax(0, 1fr) auto;
  padding-top: 0.5rem;
}

.cloud-ui-action-enabled {
  border-color: #3e8635;
  background: #f3faf2;
}

.cloud-ui-action-disabled {
  border-color: #8a8d90;
  background: #f0f0f0;
}

.cloud-ui-action-pending {
  border-color: #f0ab00;
  background: #fff7db;
}

.cloud-ui-action-blocked {
  border-color: #c9190b;
  background: #faeae8;
}

.cloud-ui-selection-summary,
.cloud-ui-metrics-grid {
  display: grid;
  gap: 0.5rem;
  grid-template-columns: repeat(auto-fit, minmax(9rem, 1fr));
}

.cloud-ui-selection-summary span,
.cloud-ui-metric-tile {
  background: #f5f7fa;
  border: 1px solid #d2d2d2;
  min-width: 0;
  padding: 0.5rem;
}

.cloud-ui-metric-sparkline {
  color: #151515;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  overflow-wrap: anywhere;
}
```

- [x] **Step 6: Run App integration tests**

Run:

```bash
cd frontend && npm test -- --run src/App.test.tsx
```

Expected result: App tests pass.

- [x] **Step 7: Commit Task 4**

Run:

```bash
git add frontend/src/App.tsx frontend/src/App.test.tsx frontend/src/styles.css
git commit -m "feat: surface object workspaces in inventory"
```

## Task 5: UI Evidence, Risk Register And Full Verification

**Files:**
- Modify: `docs/generated/ui-shell-horizon-parity.md`
- Modify: `docs/generated/risk-register.md`
- Modify: `docs/superpowers/plans/2026-06-29-ui-object-workspace.md`

- [x] **Step 1: Update generated UI evidence**

Add to `docs/generated/ui-shell-horizon-parity.md` under `## Evidence`:

```markdown
- `frontend/src/workspace/vm/VirtualMachineWorkspace.tsx` and
  `frontend/src/workspace/hypervisor/HypervisorWorkspace.tsx` expose the offline VM/hypervisor object
  workspaces with required pending/blocked actions, metrics datasource states, diagnostics placeholder
  and current-page multi-target summaries.
```

Add under `## Verification`:

```markdown
- `cd frontend && npm test -- --run src/workspace/ActionState.test.tsx src/workspace/MetricsPanel.test.tsx src/workspace/DiagnosticsPanel.test.tsx src/workspace/SelectionSummary.test.tsx src/workspace/vm/VirtualMachineWorkspace.test.tsx src/workspace/hypervisor/HypervisorWorkspace.test.tsx src/App.test.tsx src/shell/CloudShell.test.tsx`
```

- [x] **Step 2: Update risk register**

Add one row after `R-072` in `docs/generated/risk-register.md`:

```markdown
| R-075 | UI object workspace mistaken for implemented hypervisor/VM operations | The offline VM/hypervisor object workspace exposes vSphere-like administration surfaces and pending/blocked actions, but it does not implement backend contracts, live metrics, diagnostics, console proxy, snapshots, ISO mount, migration, host user management or OpenStack mutations. | Keep action states explicit, require backend OpenAPI contracts, negative authorization tests, audit mapping, operation evidence and live stand evidence before enabling any mutating control. | UI/E04/E06/E08 |
```

- [x] **Step 3: Run focused frontend verification**

Run:

```bash
cd frontend && npm test -- --run src/workspace/ActionState.test.tsx src/workspace/MetricsPanel.test.tsx src/workspace/DiagnosticsPanel.test.tsx src/workspace/SelectionSummary.test.tsx src/workspace/vm/VirtualMachineWorkspace.test.tsx src/workspace/hypervisor/HypervisorWorkspace.test.tsx src/App.test.tsx src/shell/CloudShell.test.tsx
```

Expected result: all listed frontend tests pass.

- [x] **Step 4: Run frontend typecheck and lint**

Run:

```bash
cd frontend && npm run typecheck
cd frontend && npm run lint
```

Expected result: both commands pass. The local Node engine warning from install is acceptable if tests,
typecheck and lint pass.

- [x] **Step 5: Run repository hygiene checks**

Run:

```bash
./scripts/secret-scan.sh
git diff --check
git status --short
```

Expected result: secret scan and diff check pass. `git status --short` shows only intentional files
before the final commit.

- [x] **Step 6: Update this plan progress**

Verification results:

- frontend focused tests: passed, 8 test files and 55 tests.
- frontend typecheck: passed.
- frontend lint: passed.
- secret scan: passed.
- `git diff --check`: passed.

- [x] **Step 7: Commit Task 5**

Run:

```bash
git add docs/generated/ui-shell-horizon-parity.md docs/generated/risk-register.md docs/superpowers/plans/2026-06-29-ui-object-workspace.md
git commit -m "docs: record ui object workspace evidence"
```

## Final Review Checklist

- [x] The UI shows VM and hypervisor object workspaces on current paginated inventory data.
- [x] VM and hypervisor required actions are visible but not executable unless explicitly `enabled`.
- [x] Metrics and diagnostics states are explicit and do not create direct datasource or host calls.
- [x] Multi-target summaries do not imply permission for resources outside the current page.
- [x] Frontend tests cover no direct OpenStack/telemetry/host browser calls and no browser secret storage through existing App tests plus new workspace tests.
- [x] `App.tsx` changes are integration-only; new UI logic lives under `frontend/src/workspace`.
- [x] Generated evidence and risk register do not claim full Horizon replacement, live operations, live telemetry, diagnostics, console proxy or DKB compliance.
