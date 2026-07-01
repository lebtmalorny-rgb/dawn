import { render, screen, within } from "@testing-library/react";
import { describe, expect, test } from "vitest";

import { ObjectEventTable } from "./ObjectEventTable";
import type { ObjectEventRow, ObjectEventTableState } from "./types";

const rows: ObjectEventRow[] = [
  {
    id: "event-1",
    description: "Alarm changed from Green to Yellow",
    type: "Information",
    dateTime: "2026-07-01T19:18:17Z",
    task: "Alarm update",
    targetLabel: "compute-a",
    userLabel: "system",
    correlationId: "corr-1",
  },
];

const state: ObjectEventTableState = {
  pageSize: 100,
  totalItems: 100,
  sortLabel: "Date Time descending",
  filterLabel: "Typed filters are server-side",
  exportState: "pending",
  exportReason: "Backend-bounded audited export contract is not enabled",
};

describe("ObjectEventTable", () => {
  test("renders dense server-driven event table state without browser export", () => {
    render(<ObjectEventTable rows={rows} state={state} title="Events" />);

    expect(screen.getByRole("heading", { name: "Events" })).toBeInTheDocument();
    const table = screen.getByRole("table", { name: "Events table" });
    for (const header of ["Description", "Type", "Date Time", "Task", "Target", "User"]) {
      expect(within(table).getByRole("columnheader", { name: header })).toBeInTheDocument();
    }
    expect(within(table).getByText("Alarm changed from Green to Yellow")).toBeInTheDocument();
    expect(within(table).getByText("compute-a")).toBeInTheDocument();
    expect(screen.getByText("Page size 100")).toBeInTheDocument();
    expect(screen.getByText("100 events")).toBeInTheDocument();
    expect(screen.getByText("Typed filters are server-side")).toBeInTheDocument();
    expect(screen.getByText("Backend-bounded audited export contract is not enabled")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Export pending" })).toBeDisabled();
    expect(screen.queryByText(/download full dataset/i)).not.toBeInTheDocument();
  });
});
