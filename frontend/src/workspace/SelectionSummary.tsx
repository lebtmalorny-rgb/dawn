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
