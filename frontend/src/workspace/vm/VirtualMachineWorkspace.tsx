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

const VM_TABS = [
  "Summary",
  "Hardware",
  "Network",
  "Performance",
  "Snapshots",
  "Console",
  "ISO/Media",
  "Tasks/Events",
];

export function VirtualMachineWorkspace({
  capabilities,
  instance,
}: VirtualMachineWorkspaceProps) {
  const canRead = capabilities.includes("instance.read");
  const isStale = instance.sync_status !== "ok";
  const actions: WorkspaceAction[] = [
    {
      key: "view",
      title: "View state",
      state: canRead ? "enabled" : "disabled",
      reason: canRead ? "Read model projection available" : "Требуется capability: instance.read",
    },
    {
      key: "create-empty",
      title: "Create VM without OS",
      state: "pending",
      reason: "Create operation contract is not enabled",
    },
    {
      key: "delete-rename",
      title: "Delete or rename",
      state: "pending",
      reason: "Mutation contract and audit mapping are not enabled",
    },
    {
      key: "power",
      title: "Power on/off/reboot",
      state: "pending",
      reason: "First VM mutating candidate, backend operation contract required",
    },
    {
      key: "nics",
      title: "Enable or disable NICs",
      state: "pending",
      reason: "Network mutation contract required",
    },
    {
      key: "modify",
      title: "Modify CPU/RAM/disk/NIC",
      state: "pending",
      reason: "Validation and rollback contract required",
    },
    {
      key: "snapshot",
      title: "One-time snapshot",
      state: "pending",
      reason: "Snapshot operation contract required",
    },
    {
      key: "console",
      title: "VM console",
      state: "blocked",
      reason: "Console proxy design is not approved",
    },
    {
      key: "iso",
      title: "ISO 9660 media mount",
      state: "pending",
      reason: "Media workflow/API contract required",
    },
    {
      key: "migration",
      title: "Live migration inside administration group",
      state: "blocked",
      reason: "Group boundary, workflow, Nova policy and live evidence required",
    },
  ];

  return (
    <section className="cloud-ui-object-workspace" aria-label="VM object workspace">
      <nav className="cloud-ui-workspace-tabs" aria-label="VM workspace tabs">
        {VM_TABS.map((tab) => (
          <span key={tab}>{tab}</span>
        ))}
      </nav>

      <section className="cloud-ui-workspace-panel" aria-label="VM summary">
        <h3>VM summary</h3>
        <dl className="cloud-ui-detail-list">
          <div>
            <dt>Name</dt>
            <dd>{instance.name}</dd>
          </div>
          <div>
            <dt>Status</dt>
            <dd>
              {instance.status} / {instance.power_state}
            </dd>
          </div>
          <div>
            <dt>Host</dt>
            <dd>{instance.host_name ?? "-"}</dd>
          </div>
          <div>
            <dt>Flavor</dt>
            <dd>
              {instance.vcpus} vCPU / {instance.ram_mb} MB / {instance.disk_gb} GB
            </dd>
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
        title="Selected VM targets"
      />
      <ActionStateList actions={actions} title="VM actions" />
      <MetricsPanel metrics={VM_METRICS} title="VM performance metrics" />
      <DiagnosticsPanel
        state={{
          state: "pending",
          title: "VM diagnostics",
          reason: "Backend diagnostic bundle contract is not enabled",
        }}
      />
      <TasksEventsPanel objectId={instance.instance_id} />
    </section>
  );
}
