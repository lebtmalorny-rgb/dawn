import { render, screen, within } from "@testing-library/react";
import { describe, expect, test } from "vitest";

import { CloudShell } from "./CloudShell";

const shellContext = {
  productTitle: "Cloud UI",
  searchPlaceholder: "Search in all clouds, projects, hosts, VMs, operations",
  scopeLabel: "Scope: RegionOne / project-a",
  identityLabel: "operator@example",
  policyRevision: "Policy rev 42",
  freshnessLabel: "Observed 18:47 MSK",
};

describe("CloudShell", () => {
  test("renders vSphere-informed shell landmarks", () => {
    render(
      <CloudShell
        context={shellContext}
        activeView="instances"
        objectTitle="compute-03"
        objectType="Hypervisor"
        tabs={["Summary", "Monitor", "Configure", "Permissions", "VMs", "Operations", "Audit"]}
      >
        <section aria-label="Рабочая область">Instances table</section>
      </CloudShell>,
    );

    expect(screen.getByRole("banner")).toHaveTextContent("Cloud UI");
    expect(screen.getByRole("searchbox", { name: "Глобальный поиск" })).toHaveAttribute(
      "placeholder",
      shellContext.searchPlaceholder,
    );
    expect(screen.getByRole("navigation", { name: "Объекты облака" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "compute-03" })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "Summary" })).toHaveAttribute("aria-selected", "true");
    expect(screen.getByRole("region", { name: "Нижняя рабочая панель" })).toHaveTextContent(
      "Recent Tasks",
    );
    expect(screen.getByRole("region", { name: "Рабочая область" })).toHaveTextContent(
      "Instances table",
    );
  });

  test("bottom panel exposes operations, audit and approvals tabs", () => {
    render(
      <CloudShell
        context={shellContext}
        activeView="audit"
        objectTitle="Audit"
        objectType="Evidence"
        tabs={["Summary", "Audit"]}
      >
        <span>Audit content</span>
      </CloudShell>,
    );

    const bottomPanel = screen.getByRole("region", { name: "Нижняя рабочая панель" });
    expect(within(bottomPanel).getByRole("tab", { name: "Recent Tasks" })).toBeInTheDocument();
    expect(within(bottomPanel).getByRole("tab", { name: "Alarms" })).toBeInTheDocument();
    expect(within(bottomPanel).getByRole("tab", { name: "Audit Tail" })).toBeInTheDocument();
    expect(within(bottomPanel).getByRole("tab", { name: "Approvals" })).toBeInTheDocument();
  });
});
