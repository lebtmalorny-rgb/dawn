import type { HorizonParityRow } from "./types";

export const HORIZON_PARITY_ROWS: HorizonParityRow[] = [
  {
    horizonArea: "Project / Compute / Instances / List and detail",
    cloudUiModule: "Inventory / Instances",
    requiredCapability: "instance.read",
    openStackAuthority: "Nova policy",
    apiContract:
      "GET /api/v1/instances; GET /api/v1/instances/{cloud_id}/{region_id}/{instance_id}",
    statusReason:
      "E04 implements read-only server-side list/detail from the portal BFF/read model; launch, lifecycle and console workflows are separate planned rows.",
    auditEvent: "inventory.instance.read",
    dkbNotes: "Browser reads portal API only; backend enforces capability and OpenStack policy.",
    status: "implemented",
  },
  {
    horizonArea: "Project / Compute / Instances / Launch instance",
    cloudUiModule: "Operations / Workflow catalog",
    requiredCapability: "instance.launch",
    openStackAuthority: "Nova policy and portal workflow allowlist",
    apiContract:
      "Planned: POST /api/v1/operations with an allowlisted launch-instance workflow; no enabled launch contract in this slice.",
    statusReason:
      "Not implemented in E04; requires workflow schema, idempotency, CSRF, audit and negative authorization evidence before UI enablement.",
    auditEvent: "operation.instance.launch.requested",
    dkbNotes:
      "Mutating Nova behavior must go through backend workflow allowlist; browser must not submit arbitrary Nova action payloads.",
    status: "planned",
  },
  {
    horizonArea: "Project / Compute / Instances / Power or lifecycle actions",
    cloudUiModule: "Operations / Workflow catalog",
    requiredCapability: "instance.lifecycle.manage",
    openStackAuthority: "Nova policy and portal workflow allowlist",
    apiContract:
      "Planned: POST /api/v1/operations with allowlisted lifecycle workflows; no enabled lifecycle action contract in this slice.",
    statusReason:
      "Not implemented in E04; power, reboot, resize, shelve, migrate and delete-style actions need explicit workflow contracts and operation evidence.",
    auditEvent: "operation.instance.lifecycle.requested",
    dkbNotes:
      "Lifecycle mutations require idempotency key, operation_id, CSRF, backend authorization and sanitized audit events.",
    status: "planned",
  },
  {
    horizonArea: "Project / Compute / Instances / Console access",
    cloudUiModule: "Inventory / Instances",
    requiredCapability: "instance.console.read",
    openStackAuthority: "Nova policy",
    apiContract:
      "Planned: backend-mediated console access endpoint; no enabled console contract in this slice.",
    statusReason:
      "Not implemented in E04; console access needs a BFF contract that does not expose OpenStack tokens, credentials or direct service endpoints to the browser.",
    auditEvent: "inventory.instance.console.requested",
    dkbNotes:
      "Console URLs and session material must be issued only through backend policy checks and must not be stored in browser storage.",
    status: "planned",
  },
  {
    horizonArea: "Project / Compute / Images",
    cloudUiModule: "Inventory / Images",
    requiredCapability: "image.read",
    openStackAuthority: "Glance policy",
    apiContract:
      "Planned: read-model image list/detail under /api/v1; no enabled image inventory contract in this slice.",
    statusReason:
      "Planned module only; Glance read contracts, pagination, authorization and audit evidence are not part of the implemented E04 instance/hypervisor slice.",
    auditEvent: "inventory.image.read",
    dkbNotes: "Planned module; image actions require OpenAPI, audit and negative authorization tests.",
    status: "planned",
  },
  {
    horizonArea: "Project / Network / Routers",
    cloudUiModule: "Inventory / Networks",
    requiredCapability: "network.read",
    openStackAuthority: "Neutron policy",
    apiContract:
      "Planned: read-model network/router list/detail under /api/v1; no enabled Neutron inventory contract in this slice.",
    statusReason:
      "Planned module only; router inventory needs Neutron adapter contract, server-side pagination and capability tests before enablement.",
    auditEvent: "inventory.network.read",
    dkbNotes: "Planned module; no direct Neutron calls from browser.",
    status: "planned",
  },
  {
    horizonArea: "Project / Volumes / Volumes",
    cloudUiModule: "Inventory / Volumes",
    requiredCapability: "volume.read",
    openStackAuthority: "Cinder policy",
    apiContract:
      "Planned: read-model volume list/detail under /api/v1; no enabled Cinder inventory contract in this slice.",
    statusReason:
      "Planned module only; volume inventory needs Cinder adapter contract, OpenAPI coverage and negative authorization tests.",
    auditEvent: "inventory.volume.read",
    dkbNotes: "Planned module; no Cinder credential in browser.",
    status: "planned",
  },
  {
    horizonArea: "Admin / Identity / Users",
    cloudUiModule: "Administration / Identity",
    requiredCapability: "role.manage",
    openStackAuthority: "Keystone policy and corporate IAM",
    apiContract:
      "Planned: administrative identity API under /api/v1; no enabled user-management contract in this slice.",
    statusReason:
      "Planned module only; identity administration requires SoD/IAM evidence, Keystone policy mapping and audit coverage before enablement.",
    auditEvent: "identity.user.read",
    dkbNotes: "Requires SoD/IAM evidence; portal capability cannot expand Keystone authority.",
    status: "planned",
  },
  {
    horizonArea: "Admin / Compute / Host Aggregates",
    cloudUiModule: "Inventory / Host Aggregates",
    requiredCapability: "hypervisor.read",
    openStackAuthority: "Nova policy",
    apiContract:
      "Planned: read-model aggregate list/detail under /api/v1; no enabled host aggregate contract in this slice.",
    statusReason:
      "Planned module only; aggregate read and mutation workflows need Nova adapter coverage, OpenAPI and operation/audit evidence.",
    auditEvent: "inventory.aggregate.read",
    dkbNotes: "Planned module; mutations require operation workflow and audit.",
    status: "planned",
  },
];
