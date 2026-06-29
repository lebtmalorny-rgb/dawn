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
