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

export type WorkspaceTab = {
  key: string;
  label: string;
};

export type SecondaryNavigationSection = {
  key: string;
  title: string;
  items: string[];
};

export type UtilizationMetric = {
  key: string;
  title: string;
  usedLabel: string;
  freeLabel: string;
  capacityLabel: string;
  usedPercent: number;
  state: MetricDatasourceState;
  freshnessLabel: string;
};

export type ObjectEventRow = {
  id: string;
  description: string;
  type: string;
  dateTime: string;
  task: string;
  targetLabel: string;
  userLabel: string;
  correlationId: string;
};

export type ObjectEventTableState = {
  pageSize: number;
  totalItems: number;
  sortLabel: string;
  filterLabel: string;
  exportState: "disabled" | "pending" | "blocked";
  exportReason: string;
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
