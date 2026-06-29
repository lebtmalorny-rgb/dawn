import { render, screen } from "@testing-library/react";
import { describe, expect, test } from "vitest";

import type { InstanceItem } from "../../api";
import { VirtualMachineWorkspace } from "./VirtualMachineWorkspace";

const vm: InstanceItem = {
  cloud_id: "synthetic",
  region_id: "RegionOne",
  instance_id: "instance-0001",
  name: "vm-active",
  project_id: "project-a",
  user_id: "user-a",
  status: "ACTIVE",
  power_state: "running",
  task_state: null,
  vm_state: "active",
  host_name: "compute-a",
  hypervisor_id: "hypervisor-0001",
  availability_zone: "nova",
  flavor_id: "small",
  vcpus: 2,
  ram_mb: 4096,
  disk_gb: 40,
  image_id: "image-0001",
  boot_volume_id: null,
  addresses: { private: ["10.0.0.10"] },
  source_created_at: "2026-06-20T10:00:00Z",
  source_updated_at: "2026-06-21T09:59:00Z",
  observed_at: "2026-06-21T10:00:00Z",
  sync_generation: 1,
  sync_status: "ok",
};

describe("VirtualMachineWorkspace", () => {
  test("renders required VM administration tabs and blocked/pending actions", () => {
    render(<VirtualMachineWorkspace capabilities={["instance.read"]} instance={vm} />);

    for (const label of [
      "Summary",
      "Hardware",
      "Network",
      "Performance",
      "Snapshots",
      "Console",
      "ISO/Media",
      "Tasks/Events",
    ]) {
      expect(screen.getByText(label)).toBeInTheDocument();
    }
    expect(screen.getByText("Create VM without OS")).toBeInTheDocument();
    expect(screen.getByText("Power on/off/reboot")).toBeInTheDocument();
    expect(screen.getByText("VM console")).toBeInTheDocument();
    expect(screen.getByText("ISO 9660 media mount")).toBeInTheDocument();
    expect(screen.getByText("Live migration inside administration group")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Power on/i })).not.toBeInTheDocument();
  });
});
