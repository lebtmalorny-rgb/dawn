import type { HypervisorItem } from "../../api";
import { ActionStateList } from "../ActionState";
import { DiagnosticsPanel } from "../DiagnosticsPanel";
import { MetricsPanel } from "../MetricsPanel";
import { ObjectEventTable } from "../ObjectEventTable";
import { SecondaryNavigation } from "../SecondaryNavigation";
import { SelectionSummaryPanel } from "../SelectionSummary";
import { TasksEventsPanel } from "../TasksEventsPanel";
import { UtilizationPanel } from "../UtilizationPanel";
import type {
  MetricSeries,
  ObjectEventRow,
  ObjectEventTableState,
  SecondaryNavigationSection,
  UtilizationMetric,
  WorkspaceAction,
  WorkspaceTab,
} from "../types";

type HypervisorWorkspaceProps = {
  hypervisor: HypervisorItem;
  capabilities: string[];
};

const HYPERVISOR_METRICS: MetricSeries[] = [
  {
    key: "cpu",
    title: "CPU",
    unit: "%",
    state: "not_configured",
    freshnessLabel: "Backend telemetry endpoint absent",
    points: [],
  },
  {
    key: "memory",
    title: "RAM",
    unit: "%",
    state: "not_configured",
    freshnessLabel: "Backend telemetry endpoint absent",
    points: [],
  },
  {
    key: "disk",
    title: "Disk",
    unit: "iops",
    state: "not_configured",
    freshnessLabel: "Backend telemetry endpoint absent",
    points: [],
  },
  {
    key: "network",
    title: "Network throughput",
    unit: "Mbps",
    state: "not_configured",
    freshnessLabel: "Backend telemetry endpoint absent",
    points: [],
  },
];

const HYPERVISOR_TABS: WorkspaceTab[] = [
  { key: "summary", label: "Summary" },
  { key: "monitor", label: "Monitor" },
  { key: "configure", label: "Configure" },
  { key: "permissions", label: "Permissions" },
  { key: "vms", label: "VMs" },
  { key: "resource-pools", label: "Resource Pools" },
  { key: "datastores", label: "Datastores" },
  { key: "networks", label: "Networks" },
  { key: "updates", label: "Updates" },
];

const HYPERVISOR_MONITOR_NAVIGATION: SecondaryNavigationSection[] = [
  {
    key: "issues",
    title: "Issues and Alarms",
    items: ["All Issues", "Triggered Alarms"],
  },
  {
    key: "performance",
    title: "Performance",
    items: ["Performance Overview", "Advanced Performance"],
  },
  {
    key: "tasks-events",
    title: "Tasks and Events",
    items: ["Tasks", "Events"],
  },
  {
    key: "allocation",
    title: "Resource Allocation",
    items: ["CPU", "Memory", "Storage", "Utilization"],
  },
  {
    key: "health",
    title: "Health",
    items: ["Hardware Health", "Service Health"],
  },
];

const HYPERVISOR_EVENT_TABLE_STATE: ObjectEventTableState = {
  pageSize: 100,
  totalItems: 1,
  sortLabel: "Date Time descending",
  filterLabel: "Typed filters are server-side",
  exportState: "pending",
  exportReason: "Backend-bounded audited export contract is not enabled",
};

function percent(used: number, total: number): number {
  if (total <= 0) return 0;
  return Math.round((used / total) * 1000) / 10;
}

function buildHypervisorUtilization(hypervisor: HypervisorItem): UtilizationMetric[] {
  return [
    {
      key: "cpu",
      title: "Host CPU",
      usedLabel: `${hypervisor.vcpus_used} vCPU used`,
      freeLabel: `${Math.max(hypervisor.vcpus_total - hypervisor.vcpus_used, 0)} vCPU free`,
      capacityLabel: `${hypervisor.vcpus_total} vCPU capacity`,
      usedPercent: percent(hypervisor.vcpus_used, hypervisor.vcpus_total),
      state: "ready",
      freshnessLabel: `Observed ${hypervisor.observed_at}`,
    },
    {
      key: "memory",
      title: "Host Memory",
      usedLabel: `${hypervisor.ram_mb_used} MB used`,
      freeLabel: `${Math.max(hypervisor.ram_mb_total - hypervisor.ram_mb_used, 0)} MB free`,
      capacityLabel: `${hypervisor.ram_mb_total} MB capacity`,
      usedPercent: percent(hypervisor.ram_mb_used, hypervisor.ram_mb_total),
      state: "ready",
      freshnessLabel: `Observed ${hypervisor.observed_at}`,
    },
    {
      key: "storage",
      title: "Host Storage",
      usedLabel: `${hypervisor.disk_gb_used} GB used`,
      freeLabel: `${Math.max(hypervisor.disk_gb_total - hypervisor.disk_gb_used, 0)} GB free`,
      capacityLabel: `${hypervisor.disk_gb_total} GB capacity`,
      usedPercent: percent(hypervisor.disk_gb_used, hypervisor.disk_gb_total),
      state: "ready",
      freshnessLabel: `Observed ${hypervisor.observed_at}`,
    },
  ];
}

function buildHypervisorEvents(hypervisor: HypervisorItem): ObjectEventRow[] {
  return [
    {
      id: `hypervisor-event-${hypervisor.hypervisor_id}`,
      description: `Read-model observation for ${hypervisor.host_name}`,
      type: "Information",
      dateTime: hypervisor.observed_at,
      task: "Inventory observation",
      targetLabel: "Current hypervisor",
      userLabel: "portal-system",
      correlationId: hypervisor.hypervisor_id,
    },
  ];
}

export function HypervisorWorkspace({ capabilities, hypervisor }: HypervisorWorkspaceProps) {
  const canRead = capabilities.includes("hypervisor.read");
  const isStale = hypervisor.sync_status !== "ok";
  const actions: WorkspaceAction[] = [
    {
      key: "view",
      title: "View state",
      state: canRead ? "enabled" : "disabled",
      reason: canRead ? "Read model projection available" : "Требуется capability: hypervisor.read",
    },
    {
      key: "maintenance",
      title: "Enter maintenance with evacuation",
      state: "pending",
      reason: "First host mutating candidate, Mistral workflow contract required",
    },
    {
      key: "reboot",
      title: "Reboot or shutdown",
      state: "pending",
      reason: "Host lifecycle workflow contract required",
    },
    {
      key: "network",
      title: "Network adapter configuration",
      state: "pending",
      reason: "Backend workflow/API contract required",
    },
    {
      key: "ntp",
      title: "NTP and service management",
      state: "pending",
      reason: "Backend automation contract required",
    },
    {
      key: "users",
      title: "Host users and rights",
      state: "blocked",
      reason: "Security owner, PAM and RBAC contract required",
    },
  ];

  return (
    <section className="cloud-ui-object-workspace" aria-label="Hypervisor object workspace">
      <nav className="cloud-ui-workspace-tabs" aria-label="Hypervisor workspace tabs">
        {HYPERVISOR_TABS.map((tab) => (
          <span key={tab.key}>{tab.label}</span>
        ))}
      </nav>
      <SecondaryNavigation
        activeItem="Performance Overview"
        ariaLabel="Hypervisor Monitor navigation"
        sections={HYPERVISOR_MONITOR_NAVIGATION}
      />

      <section className="cloud-ui-workspace-panel" aria-label="Hypervisor summary">
        <h3>Hypervisor summary</h3>
        <dl className="cloud-ui-detail-list">
          <div>
            <dt>Host</dt>
            <dd>Host: {hypervisor.host_name}</dd>
          </div>
          <div>
            <dt>Service</dt>
            <dd>
              {hypervisor.service_status} / {hypervisor.service_state}
            </dd>
          </div>
          <div>
            <dt>Capacity</dt>
            <dd>
              {hypervisor.vcpus_used}/{hypervisor.vcpus_total} vCPU / {hypervisor.ram_mb_used}/
              {hypervisor.ram_mb_total} MB RAM / {hypervisor.disk_gb_used}/
              {hypervisor.disk_gb_total} GB disk
            </dd>
          </div>
          <div>
            <dt>Running VMs</dt>
            <dd>{hypervisor.running_vms}</dd>
          </div>
        </dl>
      </section>

      <SelectionSummaryPanel
        summary={{
          total: 1,
          allowed: canRead ? 1 : 0,
          denied: canRead ? 0 : 1,
          stale: isStale ? 1 : 0,
          blocked: 0,
        }}
        title="Selected hypervisor targets"
      />
      <ActionStateList actions={actions} title="Hypervisor actions" />
      <MetricsPanel metrics={HYPERVISOR_METRICS} title="Performance Overview" />
      <UtilizationPanel metrics={buildHypervisorUtilization(hypervisor)} title="Utilization" />
      <DiagnosticsPanel
        state={{
          state: "pending",
          title: "Hypervisor diagnostics",
          reason: "Backend diagnostic bundle contract is not enabled",
        }}
      />
      <TasksEventsPanel objectId={hypervisor.hypervisor_id} />
      <ObjectEventTable
        rows={buildHypervisorEvents(hypervisor)}
        state={HYPERVISOR_EVENT_TABLE_STATE}
        title="Events"
      />
    </section>
  );
}
