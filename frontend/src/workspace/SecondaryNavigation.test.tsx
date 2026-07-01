import { render, screen, within } from "@testing-library/react";
import { describe, expect, test } from "vitest";

import { SecondaryNavigation } from "./SecondaryNavigation";
import type { SecondaryNavigationSection } from "./types";

const sections: SecondaryNavigationSection[] = [
  {
    key: "performance",
    title: "Performance",
    items: ["Performance Overview", "Advanced Performance"],
  },
  {
    key: "events",
    title: "Tasks and Events",
    items: ["Tasks", "Events"],
  },
];

describe("SecondaryNavigation", () => {
  test("renders grouped object-local monitor navigation", () => {
    render(<SecondaryNavigation activeItem="Events" ariaLabel="VM Monitor navigation" sections={sections} />);

    const nav = screen.getByRole("navigation", { name: "VM Monitor navigation" });
    expect(within(nav).getByText("Performance")).toBeInTheDocument();
    expect(within(nav).getByText("Performance Overview")).toBeInTheDocument();
    expect(within(nav).getByText("Advanced Performance")).toBeInTheDocument();
    expect(within(nav).getByText("Tasks and Events")).toBeInTheDocument();
    expect(within(nav).getByText("Tasks")).toBeInTheDocument();
    expect(within(nav).getByText("Events")).toHaveAttribute("aria-current", "page");
  });
});
