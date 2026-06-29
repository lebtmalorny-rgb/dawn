import { render, screen, within } from "@testing-library/react";
import { describe, expect, test } from "vitest";

import { ActionStateList } from "./ActionState";
import type { WorkspaceAction } from "./types";

const actions: WorkspaceAction[] = [
  {
    key: "view-state",
    title: "Просмотр состояния",
    state: "enabled",
    reason: "Доступно через read model",
  },
  {
    key: "power-on",
    title: "Включить ВМ",
    state: "pending",
    reason: "Нет backend operation contract",
  },
  {
    key: "vm-console",
    title: "Консоль ВМ",
    state: "blocked",
    reason: "Console proxy design is not approved",
  },
  {
    key: "rename",
    title: "Переименовать",
    state: "disabled",
    reason: "Требуется capability: instance.manage",
  },
];

describe("ActionStateList", () => {
  test("renders explicit enabled, disabled, pending and blocked states", () => {
    render(<ActionStateList actions={actions} title="Действия ВМ" />);

    expect(screen.getByRole("heading", { name: "Действия ВМ" })).toBeInTheDocument();
    for (const action of actions) {
      const row = screen.getByText(action.title).closest("li");
      expect(row).not.toBeNull();
      expect(within(row as HTMLElement).getByText(action.reason)).toBeInTheDocument();
      expect(within(row as HTMLElement).getByText(action.state)).toBeInTheDocument();
    }
  });

  test("does not render mutation buttons for pending or blocked actions", () => {
    render(<ActionStateList actions={actions} title="Действия ВМ" />);

    expect(screen.queryByRole("button", { name: /Включить ВМ/ })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Консоль ВМ/ })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Переименовать/ })).not.toBeInTheDocument();
  });
});
