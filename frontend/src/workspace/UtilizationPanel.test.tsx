import { render, screen } from "@testing-library/react";
import { describe, expect, test } from "vitest";

import { UtilizationPanel } from "./UtilizationPanel";
import type { UtilizationMetric } from "./types";

const metrics: UtilizationMetric[] = [
  {
    key: "cpu",
    title: "Host CPU",
    usedLabel: "0.43 GHz used",
    freeLabel: "33.1 GHz free",
    capacityLabel: "33.53 GHz capacity",
    usedPercent: 1.3,
    state: "ready",
    freshnessLabel: "Observed 10:23 PM UTC",
  },
  {
    key: "memory",
    title: "Host Memory",
    usedLabel: "14.41 GB used",
    freeLabel: "1.59 GB free",
    capacityLabel: "16 GB capacity",
    usedPercent: 90,
    state: "stale",
    freshnessLabel: "Stale after 300s",
  },
];

describe("UtilizationPanel", () => {
  test("renders current capacity bars separately from performance series", () => {
    render(<UtilizationPanel metrics={metrics} title="Utilization" />);

    expect(screen.getByRole("heading", { name: "Utilization" })).toBeInTheDocument();
    expect(screen.getByText("Host CPU")).toBeInTheDocument();
    expect(screen.getByText("0.43 GHz used")).toBeInTheDocument();
    expect(screen.getByText("33.1 GHz free")).toBeInTheDocument();
    expect(screen.getByText("33.53 GHz capacity")).toBeInTheDocument();
    expect(screen.getByText("Host Memory")).toBeInTheDocument();
    expect(screen.getByText("ready")).toBeInTheDocument();
    expect(screen.getByText("stale")).toBeInTheDocument();
    expect(screen.queryByLabelText(/series/i)).not.toBeInTheDocument();
    expect(screen.queryByRole("textbox")).not.toBeInTheDocument();
  });
});
