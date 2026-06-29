import type { DiagnosticState } from "./types";

type DiagnosticsPanelProps = {
  state: DiagnosticState;
};

export function DiagnosticsPanel({ state }: DiagnosticsPanelProps) {
  return (
    <section className="cloud-ui-workspace-panel" aria-label={state.title}>
      <div className="cloud-ui-workspace-panel-header">
        <h3>{state.title}</h3>
        <span className={`cloud-ui-badge cloud-ui-action-${state.state}`}>{state.state}</span>
      </div>
      <p className="cloud-ui-muted">{state.reason}</p>
      <p className="cloud-ui-empty">
        Diagnostic bundle collection will appear here after an approved backend contract returns a
        sanitized artifact.
      </p>
    </section>
  );
}
