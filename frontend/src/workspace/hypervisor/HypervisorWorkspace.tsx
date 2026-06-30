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

const HYPERVISOR_TABS = [
  "Summary",
  "VMs",
  "Performance",
  "Network",
  "Services/NTP",
  "Diagnostics",
  "Users/Roles",
  "Tasks/Events",
];

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
          <span key={tab}>{tab}</span>
        ))}
      </nav>

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
      <MetricsPanel metrics={HYPERVISOR_METRICS} title="Hypervisor performance metrics" />
      <DiagnosticsPanel
        state={{
          state: "pending",
          title: "Hypervisor diagnostics",
          reason: "Backend diagnostic bundle contract is not enabled",
        }}
      />
      <TasksEventsPanel objectId={hypervisor.hypervisor_id} />
    </section>
  );
}
