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
        capabilities={["instance.read", "hypervisor.read", "operation.read", "audit.read"]}
        objectTitle="compute-03"
        objectType="Hypervisor"
        tabs={["Summary", "Monitor", "Configure", "Permissions", "VMs", "Operations", "Audit"]}
      >
        <section aria-label="Рабочая область">Instances table</section>
      </CloudShell>,
    );

    expect(screen.getByRole("banner")).toHaveTextContent("Cloud UI");
    expect(
      screen.getByRole("button", { name: "Меню продукта запланировано для следующего этапа" }),
    ).toBeDisabled();
    expect(screen.getByRole("searchbox", { name: "Глобальный поиск" })).toHaveAttribute(
      "placeholder",
      shellContext.searchPlaceholder,
    );
    expect(screen.getByRole("searchbox", { name: "Глобальный поиск" })).toBeDisabled();
    expect(screen.getByText("Поиск запланирован")).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Обновление данных запланировано для следующего этапа" }),
    ).toBeDisabled();
    expect(screen.getByRole("navigation", { name: "Объекты облака" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "compute-03" })).toBeInTheDocument();
    const objectSections = screen.getByRole("navigation", { name: "Разделы объекта" });
    expect(within(objectSections).queryAllByRole("button")).toHaveLength(0);
    expect(within(objectSections).queryAllByRole("link")).toHaveLength(0);
    expect(within(objectSections).getByText("Summary")).toHaveAttribute("aria-current", "page");
    expect(
      screen.getByRole("button", { name: "Действия объекта запланированы для следующего этапа" }),
    ).toBeDisabled();
    expect(screen.getByRole("region", { name: "Нижняя рабочая панель" })).toHaveTextContent(
      "Recent Tasks",
    );
    expect(screen.getByRole("region", { name: "Рабочая область" })).toHaveTextContent(
      "Instances table",
    );
    expect(screen.queryAllByRole("tab")).toHaveLength(0);
  });

  test("bottom panel exposes static operations, audit and approvals status labels", () => {
    render(
      <CloudShell
        context={shellContext}
        activeView="audit"
        capabilities={["instance.read", "hypervisor.read", "operation.read", "audit.read"]}
        objectTitle="Audit"
        objectType="Evidence"
        tabs={["Summary", "Audit"]}
      >
        <span>Audit content</span>
      </CloudShell>,
    );

    const bottomPanel = screen.getByRole("region", { name: "Нижняя рабочая панель" });
    expect(within(bottomPanel).queryAllByRole("button")).toHaveLength(0);
    expect(within(bottomPanel).queryByRole("tablist")).not.toBeInTheDocument();
    expect(within(bottomPanel).queryAllByRole("tab")).toHaveLength(0);
    expect(within(bottomPanel).getByText("Recent Tasks")).toHaveAttribute("aria-current", "true");
    expect(within(bottomPanel).getByText("Alarms")).toBeInTheDocument();
    expect(within(bottomPanel).getByText("Audit Tail")).toBeInTheDocument();
    expect(within(bottomPanel).getByText("Approvals")).toBeInTheDocument();
    expect(screen.queryByRole("tablist")).not.toBeInTheDocument();
    expect(screen.queryAllByRole("tab")).toHaveLength(0);
  });

  test("planned modules are visible but not links or enabled controls", () => {
    render(
      <CloudShell
        context={shellContext}
        activeView="instances"
        capabilities={["instance.read", "hypervisor.read", "operation.read", "audit.read"]}
        objectTitle="compute-03"
        objectType="Hypervisor"
        tabs={["Summary"]}
      >
        <span>Instances table</span>
      </CloudShell>,
    );

    expect(screen.getByRole("link", { name: "ВМ" })).toHaveAttribute("href", "?view=instances");
    expect(screen.queryByRole("link", { name: /Watcher/ })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Watcher/ })).not.toBeInTheDocument();
    const watcherItem = screen.getByText("Watcher").closest("li");
    expect(watcherItem).not.toBeNull();
    expect(within(watcherItem as HTMLElement).getByText("Watcher").closest("[aria-disabled='true']"))
      .toHaveAttribute("data-status", "planned");
    expect(within(watcherItem as HTMLElement).getByText("Запланировано")).toBeInTheDocument();
    expect(
      screen.getByText("First-class module planned; direct action apply remains approval-gated"),
    ).toBeInTheDocument();
  });

  test("implemented modules without required capability are visible but disabled", () => {
    render(
      <CloudShell
        context={shellContext}
        activeView="groups"
        capabilities={["group.read"]}
        objectTitle="Группы"
        objectType="Resource groups"
        tabs={["Summary"]}
      >
        <span>Groups table</span>
      </CloudShell>,
    );

    expect(screen.queryByRole("link", { name: "ВМ" })).not.toBeInTheDocument();
    const vmItem = screen.getByText("ВМ").closest("li");
    expect(vmItem).not.toBeNull();
    expect(within(vmItem as HTMLElement).getByText("ВМ").closest("[aria-disabled='true']"))
      .toHaveAttribute("data-status", "disabled");
    expect(within(vmItem as HTMLElement).getByText("Недоступно")).toBeInTheDocument();
    expect(
      within(vmItem as HTMLElement).getByText("Требуется capability: instance.read"),
    ).toBeInTheDocument();
  });
});
