export type CloudModuleStatus = "implemented" | "planned" | "disabled";

export type CloudModuleItem = {
  key: string;
  title: string;
  view: string;
  requiredCapability: string | null;
  status: CloudModuleStatus;
  reason: string;
};

export type CloudModuleGroup = {
  key: "inventory" | "operations" | "administration" | "audit_dkb";
  title: string;
  items: CloudModuleItem[];
};

export type HorizonParityStatus =
  | "implemented"
  | "planned"
  | "blocked_external_evidence"
  | "out_of_scope";

export type HorizonParityRow = {
  horizonArea: string;
  cloudUiModule: string;
  requiredCapability: string;
  openStackAuthority: string;
  auditEvent: string;
  dkbNotes: string;
  status: HorizonParityStatus;
};

export type ShellContext = {
  productTitle: string;
  searchPlaceholder: string;
  scopeLabel: string;
  identityLabel: string;
  policyRevision: string;
  freshnessLabel: string;
};
