export type GroupScope = {
  type: string;
  id: string | null;
};

export type GroupResourceType = "vm" | "host" | "mixed";
export type GroupMembershipMode = "explicit" | "dynamic" | "imported";

export type ResourceGroup = {
  group_id: string;
  name: string;
  description: string | null;
  resource_type: GroupResourceType;
  scope: GroupScope;
  membership_mode: GroupMembershipMode;
  rule_version: number;
  rule_body_json: Record<string, unknown> | null;
  owner_subject_id: string;
  revision: number;
  created_at: string;
  updated_at: string;
};

export type GroupMember = {
  group_id: string;
  resource_type: "vm" | "host";
  cloud_id: string;
  region_id: string;
  resource_id: string;
  source: string;
  added_by: string;
  added_at: string;
  expires_at: string | null;
};

export type GroupListResponse = {
  items: ResourceGroup[];
  limit: number;
};

export type GroupMembersResponse = {
  items: GroupMember[];
  limit: number;
};

export type GroupPreviewItem = Record<string, unknown>;

export type GroupPreviewResponse = {
  items: GroupPreviewItem[];
  count_estimate: number;
  limit: number;
  explain: string[];
  warnings: string[];
};

export type GroupMemberMutationResponse = {
  member: GroupMember;
  operation_id: string;
};

export type GroupDeleteResponse = {
  status: "deleted";
};

function isPlainRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function isStringOrNull(value: unknown): value is string | null {
  return typeof value === "string" || value === null;
}

function isNumber(value: unknown): value is number {
  return typeof value === "number" && Number.isFinite(value);
}

function isStringArray(value: unknown): value is string[] {
  return (
    Array.isArray(value) && value.every((item) => typeof item === "string")
  );
}

function isScope(value: unknown): value is GroupScope {
  return (
    isPlainRecord(value) &&
    typeof value.type === "string" &&
    isStringOrNull(value.id)
  );
}

export function isResourceGroup(value: unknown): value is ResourceGroup {
  return (
    isPlainRecord(value) &&
    typeof value.group_id === "string" &&
    typeof value.name === "string" &&
    isStringOrNull(value.description) &&
    (value.resource_type === "vm" ||
      value.resource_type === "host" ||
      value.resource_type === "mixed") &&
    isScope(value.scope) &&
    (value.membership_mode === "explicit" ||
      value.membership_mode === "dynamic" ||
      value.membership_mode === "imported") &&
    isNumber(value.rule_version) &&
    (value.rule_body_json === null || isPlainRecord(value.rule_body_json)) &&
    typeof value.owner_subject_id === "string" &&
    isNumber(value.revision) &&
    typeof value.created_at === "string" &&
    typeof value.updated_at === "string"
  );
}

export function isGroupListResponse(
  value: unknown,
): value is GroupListResponse {
  return (
    isPlainRecord(value) &&
    Array.isArray(value.items) &&
    value.items.every(isResourceGroup) &&
    isNumber(value.limit)
  );
}

export function isGroupMember(value: unknown): value is GroupMember {
  return (
    isPlainRecord(value) &&
    typeof value.group_id === "string" &&
    (value.resource_type === "vm" || value.resource_type === "host") &&
    typeof value.cloud_id === "string" &&
    typeof value.region_id === "string" &&
    typeof value.resource_id === "string" &&
    typeof value.source === "string" &&
    typeof value.added_by === "string" &&
    typeof value.added_at === "string" &&
    isStringOrNull(value.expires_at)
  );
}

export function isGroupMembersResponse(
  value: unknown,
): value is GroupMembersResponse {
  return (
    isPlainRecord(value) &&
    Array.isArray(value.items) &&
    value.items.every(isGroupMember) &&
    isNumber(value.limit)
  );
}

export function isGroupPreviewResponse(
  value: unknown,
): value is GroupPreviewResponse {
  return (
    isPlainRecord(value) &&
    Array.isArray(value.items) &&
    value.items.every(isPlainRecord) &&
    isNumber(value.count_estimate) &&
    isNumber(value.limit) &&
    isStringArray(value.explain) &&
    isStringArray(value.warnings)
  );
}

export function isGroupMemberMutationResponse(
  value: unknown,
): value is GroupMemberMutationResponse {
  return (
    isPlainRecord(value) &&
    isGroupMember(value.member) &&
    typeof value.operation_id === "string"
  );
}

export function isGroupDeleteResponse(
  value: unknown,
): value is GroupDeleteResponse {
  return isPlainRecord(value) && value.status === "deleted";
}
