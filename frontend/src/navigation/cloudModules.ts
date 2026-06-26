import type { CloudModuleGroup } from "./types";

export const CLOUD_MODULE_GROUPS: CloudModuleGroup[] = [
  {
    key: "inventory",
    title: "Инвентарь",
    items: [
      {
        key: "instances",
        title: "ВМ",
        view: "instances",
        requiredCapability: "instance.read",
        status: "implemented",
        reason: "E04 inventory list exists",
      },
      {
        key: "hypervisors",
        title: "Гипервизоры",
        view: "hypervisors",
        requiredCapability: "hypervisor.read",
        status: "implemented",
        reason: "E04 hypervisor list exists",
      },
      {
        key: "networks",
        title: "Сети",
        view: "networks",
        requiredCapability: "network.read",
        status: "planned",
        reason: "Horizon parity row, backend adapter not enabled in this slice",
      },
      {
        key: "volumes",
        title: "Тома",
        view: "volumes",
        requiredCapability: "volume.read",
        status: "planned",
        reason: "Horizon parity row, backend adapter not enabled in this slice",
      },
    ],
  },
  {
    key: "operations",
    title: "Операции",
    items: [
      {
        key: "mistral_operations",
        title: "Mistral",
        view: "operations",
        requiredCapability: "operation.read",
        status: "implemented",
        reason: "E06 operation center foundation exists",
      },
      {
        key: "watcher",
        title: "Watcher",
        view: "watcher",
        requiredCapability: "operation.read",
        status: "planned",
        reason: "First-class module planned; direct action apply remains approval-gated",
      },
      {
        key: "masakari",
        title: "Masakari",
        view: "masakari",
        requiredCapability: "operation.read",
        status: "planned",
        reason: "First-class recovery module planned; no direct browser recovery",
      },
    ],
  },
  {
    key: "administration",
    title: "Администрирование",
    items: [
      {
        key: "identity",
        title: "Identity",
        view: "identity",
        requiredCapability: "role.manage",
        status: "planned",
        reason: "Requires IAM/Keystone federation implementation plan",
      },
      {
        key: "horizon_parity",
        title: "Horizon parity",
        view: "horizon-parity",
        requiredCapability: "role.manage",
        status: "planned",
        reason: "Coverage matrix in this slice; workflows implemented later",
      },
    ],
  },
  {
    key: "audit_dkb",
    title: "Аудит и ДКБ",
    items: [
      {
        key: "audit",
        title: "Аудит",
        view: "audit",
        requiredCapability: "audit.read",
        status: "implemented",
        reason: "E07 audit UI foundation exists",
      },
      {
        key: "dkb_evidence",
        title: "ДКБ evidence",
        view: "dkb-evidence",
        requiredCapability: "audit.read",
        status: "planned",
        reason: "Evidence view planned; current slice must not claim compliance",
      },
    ],
  },
];
