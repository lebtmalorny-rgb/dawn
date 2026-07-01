import type { UtilizationMetric } from "./types";

type UtilizationPanelProps = {
  title: string;
  metrics: UtilizationMetric[];
};

function boundedPercent(value: number): number {
  if (value < 0) return 0;
  if (value > 100) return 100;
  return value;
}

export function UtilizationPanel({ metrics, title }: UtilizationPanelProps) {
  return (
    <section className="cloud-ui-workspace-panel" aria-label={title}>
      <h3>{title}</h3>
      <div className="cloud-ui-utilization-grid">
        {metrics.map((metric) => {
          const usedPercent = boundedPercent(metric.usedPercent);

          return (
            <article key={metric.key} className="cloud-ui-utilization-tile">
              <div className="cloud-ui-workspace-panel-header">
                <strong>{metric.title}</strong>
                <span className={`cloud-ui-badge cloud-ui-metric-${metric.state}`}>
                  {metric.state}
                </span>
              </div>
              <div
                className="cloud-ui-utilization-bar"
                role="progressbar"
                aria-label={metric.title}
                aria-valuemin={0}
                aria-valuemax={100}
                aria-valuenow={usedPercent}
              >
                <span style={{ width: `${usedPercent}%` }} />
              </div>
              <div className="cloud-ui-utilization-labels">
                <span>{metric.usedLabel}</span>
                <span>{metric.freeLabel}</span>
                <span>{metric.capacityLabel}</span>
              </div>
              <p className="cloud-ui-muted">{metric.freshnessLabel}</p>
            </article>
          );
        })}
      </div>
    </section>
  );
}
