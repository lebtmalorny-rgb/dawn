import { render, screen } from "@testing-library/react";
import { describe, expect, test } from "vitest";

import { DiagnosticsPanel } from "./DiagnosticsPanel";

describe("DiagnosticsPanel", () => {
  test("shows safe pending diagnostic state without shell inputs", () => {
    render(
      <DiagnosticsPanel
        state={{
          state: "pending",
          title: "Диагностика гипервизора",
          reason: "Backend diagnostic bundle contract is not enabled",
        }}
      />,
    );

    expect(
      screen.getByRole("heading", { name: "Диагностика гипервизора" }),
    ).toBeInTheDocument();
    expect(screen.getByText("pending")).toBeInTheDocument();
    expect(screen.queryByLabelText(/command|script|path|shell/i)).not.toBeInTheDocument();
    expect(screen.queryByRole("textbox")).not.toBeInTheDocument();
  });
});
