import { render, screen } from "@testing-library/react";
import { describe, expect, test } from "vitest";

import { MetricsPanel } from "./MetricsPanel";
import type { MetricSeries } from "./types";

const metrics: MetricSeries[] = [
  {
    key: "cpu",
    title: "CPU",
    unit: "%",
    state: "ready",
    freshnessLabel: "Observed 10:00 UTC",
    points: [10, 20, 30],
  },
  {
    key: "memory",
    title: "RAM",
    unit: "%",
    state: "stale",
    freshnessLabel: "Stale after 300s",
    points: [55, 57],
  },
  {
    key: "disk",
    title: "Disk",
    unit: "iops",
    state: "unavailable",
    freshnessLabel: "Datasource down",
    points: [],
  },
  {
    key: "network",
    title: "Network",
    unit: "Mbps",
    state: "not_configured",
    freshnessLabel: "Telemetry endpoint absent",
    points: [],
  },
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
