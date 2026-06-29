import { render, screen } from "@testing-library/react";
import { describe, expect, test } from "vitest";

import { SelectionSummaryPanel } from "./SelectionSummary";

describe("SelectionSummaryPanel", () => {
  test("renders allowed denied stale and blocked counts", () => {
    render(
      <SelectionSummaryPanel
        summary={{ total: 4, allowed: 1, denied: 1, stale: 1, blocked: 1 }}
        title="Выбранные цели"
      />,
    );

    expect(screen.getByText("Total 4")).toBeInTheDocument();
    expect(screen.getByText("Allowed 1")).toBeInTheDocument();
    expect(screen.getByText("Denied 1")).toBeInTheDocument();
    expect(screen.getByText("Stale 1")).toBeInTheDocument();
    expect(screen.getByText("Blocked 1")).toBeInTheDocument();
  });
});
