import { render, screen } from "@testing-library/react";
import { describe, expect, test } from "vitest";

import type { HypervisorItem } from "../../api";
import { HypervisorWorkspace } from "./HypervisorWorkspace";

const hypervisor: HypervisorItem = {
  cloud_id: "synthetic",
  region_id: "RegionOne",
  hypervisor_id: "hypervisor-0001",
  host_name: "compute-a",
  service_id: "service-0001",
  service_status: "enabled",
  service_state: "up",
  hypervisor_type: "QEMU",
  hypervisor_version: "8.2",
  availability_zone: "nova",
  aggregates: ["az-a"],
  vcpus_total: 64,
  vcpus_used: 24,
  ram_mb_total: 262144,
  ram_mb_used: 98304,
  disk_gb_total: 2048,
  disk_gb_used: 512,
  running_vms: 18,
  disabled_reason: null,
  maintenance_status: null,
  observed_at: "2026-06-21T10:00:00Z",
  sync_generation: 1,
  sync_status: "ok",
};

describe("HypervisorWorkspace", () => {
  test("renders required hypervisor administration tabs and blocked/pending actions", () => {
    render(<HypervisorWorkspace capabilities={["hypervisor.read"]} hypervisor={hypervisor} />);

    for (const label of [
      "Summary",
      "VMs",
      "Performance",
      "Network",
      "Services/NTP",
      "Diagnostics",
      "Users/Roles",
      "Tasks/Events",
    ]) {
      expect(screen.getByText(label)).toBeInTheDocument();
    }
    expect(screen.getByText("Enter maintenance with evacuation")).toBeInTheDocument();
    expect(screen.getByText("Reboot or shutdown")).toBeInTheDocument();
    expect(screen.getByText("Network adapter configuration")).toBeInTheDocument();
    expect(screen.getByText("Host users and rights")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Reboot/i })).not.toBeInTheDocument();
  });
});
