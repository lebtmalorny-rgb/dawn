import {
  type AuditEventListResponse,
  type AuditExportRequest,
  type AuditExportResponse,
  isAuditEventListResponse,
  isAuditExportResponse,
} from "./audit";
import {
  type GroupDeleteResponse,
  type GroupListResponse,
  type GroupMember,
  type GroupMemberMutationResponse,
  type GroupMembersResponse,
  type GroupPreviewResponse,
  type GroupResourceType,
  type ResourceGroup,
  isGroupDeleteResponse,
  isGroupListResponse,
  isGroupMemberMutationResponse,
  isGroupMembersResponse,
  isGroupPreviewResponse,
  isResourceGroup,
} from "./groups";

export type {
  AuditEvent,
  AuditEventListResponse,
  AuditExportRequest,
  AuditExportResponse,
} from "./audit";

export type {
  GroupDeleteResponse,
  GroupListResponse,
  GroupMember,
  GroupMemberMutationResponse,
  GroupMembersResponse,
  GroupPreviewResponse,
  GroupResourceType,
  ResourceGroup,
} from "./groups";

export type DependencyState = {
  status: "ok" | "down";
  detail: string;
};

export type Readiness = {
  status: "ok" | "degraded";
  dependencies: Record<string, DependencyState>;
};

export type Subject = {
  subject_id: string;
  display_name: string;
  subject_type: "human" | "service";
  roles: string[];
};

export type CurrentSession = {
  subject: Subject;
};

export type LoginResult = {
  subject: Subject;
  csrf: string;
  expires_at: string;
};

export type Capabilities = {
  scope: { type: string; id: string | null };
  capabilities: string[];
  expires_at: string;
  policy_revision: string;
};

export type InventoryWarning = {
  code: string;
  title: string;
  detail: string;
  source: string;
};

export type InventoryFreshness = {
  observed_at: string | null;
  last_successful_sync_at: string | null;
  stale_after_seconds: number;
  is_stale: boolean;
};

export type InstanceItem = {
  cloud_id: string;
  region_id: string;
  instance_id: string;
  name: string;
  project_id: string;
  user_id: string;
  status: string;
  power_state: string;
  task_state: string | null;
  vm_state: string;
  host_name: string | null;
  hypervisor_id: string | null;
  availability_zone: string | null;
  flavor_id: string | null;
  vcpus: number;
  ram_mb: number;
  disk_gb: number;
  image_id: string | null;
  boot_volume_id: string | null;
  addresses: Record<string, unknown>;
  source_created_at: string | null;
  source_updated_at: string | null;
  observed_at: string;
  sync_generation: number;
  sync_status: string;
};

export type HypervisorItem = {
  cloud_id: string;
  region_id: string;
  hypervisor_id: string;
  host_name: string;
  service_id: string | null;
  service_status: string;
  service_state: string;
  hypervisor_type: string | null;
  hypervisor_version: string | null;
  availability_zone: string | null;
  aggregates: string[];
  vcpus_total: number;
  vcpus_used: number;
  ram_mb_total: number;
  ram_mb_used: number;
  disk_gb_total: number;
  disk_gb_used: number;
  running_vms: number;
  disabled_reason: string | null;
  maintenance_status: string | null;
  observed_at: string;
  sync_generation: number;
  sync_status: string;
};

export type InventoryPage<T> = {
  items: T[];
  next_cursor: string | null;
  limit: number;
  sort: string;
  partial: boolean;
  warnings: InventoryWarning[];
  freshness: InventoryFreshness | null;
};

export type InventoryModuleDescriptor = {
  key: string;
  title: string;
  path: string | null;
  enabled: boolean;
  required_capability: string | null;
  status: "enabled" | "disabled";
  reason: string | null;
};

export type WorkflowDefinition = {
  workflow_key: string;
  version: string;
  title: string;
  description: string;
  target_type: "host" | "vm" | "group";
  required_capability: string;
  risk_level: string;
  approval_mode: string;
  cancel_policy: string;
  checksum: string;
  mistral_workflow_name: null;
};

export type WorkflowDefinitionListResponse = {
  items: WorkflowDefinition[];
  limit: number;
};

export type OperationTargetRequest = {
  target_type: "host" | "vm" | "group";
  cloud_id: string;
  region_id: string;
  resource_id: string;
  expected_revision?: number;
};

export type OperationSubmitRequest = {
  workflow_key: string;
  version: string;
  targets: OperationTargetRequest[];
  input: Record<string, unknown>;
};

export type OperationSubmitResponse = {
  operation_id: string;
  status: string;
};

export type OperationEvent = {
  event_id: string;
  event_type: string;
  from_status: string | null;
  to_status: string | null;
  outcome: string;
  safe_message: string;
  safe_error_code: string | null;
  metadata: Record<string, unknown>;
  created_at: string;
};

export type OperationDetail = {
  operation_id: string;
  workflow_key: string;
  workflow_version: string;
  status: string;
  correlation_id: string;
  external_execution_id: string | null;
  created_at: string;
  updated_at: string;
  events: OperationEvent[];
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

function isDependencyState(value: unknown): value is DependencyState {
  if (!isPlainRecord(value)) {
    return false;
  }

  return (
    (value.status === "ok" || value.status === "down") &&
    typeof value.detail === "string"
  );
}

function isReadiness(payload: unknown): payload is Readiness {
  if (!isPlainRecord(payload)) {
    return false;
  }

  const dependencies = payload.dependencies;
  return (
    (payload.status === "ok" || payload.status === "degraded") &&
    isPlainRecord(dependencies) &&
    Object.values(dependencies).every(isDependencyState)
  );
}

function isSubject(value: unknown): value is Subject {
  if (!isPlainRecord(value)) {
    return false;
  }

  return (
    typeof value.subject_id === "string" &&
    typeof value.display_name === "string" &&
    (value.subject_type === "human" || value.subject_type === "service") &&
    Array.isArray(value.roles) &&
    value.roles.every((role) => typeof role === "string")
  );
}

function isCurrentSession(payload: unknown): payload is CurrentSession {
  return isPlainRecord(payload) && isSubject(payload.subject);
}

function isLoginResult(payload: unknown): payload is LoginResult {
  return (
    isPlainRecord(payload) &&
    isSubject(payload.subject) &&
    typeof payload.csrf === "string" &&
    typeof payload.expires_at === "string"
  );
}

function isCapabilities(payload: unknown): payload is Capabilities {
  if (!isPlainRecord(payload)) {
    return false;
  }

  const scope = payload.scope;
  return (
    isPlainRecord(scope) &&
    typeof scope.type === "string" &&
    (typeof scope.id === "string" || scope.id === null) &&
    Array.isArray(payload.capabilities) &&
    payload.capabilities.every(
      (capability) => typeof capability === "string",
    ) &&
    typeof payload.expires_at === "string" &&
    typeof payload.policy_revision === "string"
  );
}

function isInventoryWarning(value: unknown): value is InventoryWarning {
  return (
    isPlainRecord(value) &&
    typeof value.code === "string" &&
    typeof value.title === "string" &&
    typeof value.detail === "string" &&
    typeof value.source === "string"
  );
}

function isInventoryFreshness(value: unknown): value is InventoryFreshness {
  return (
    isPlainRecord(value) &&
    isStringOrNull(value.observed_at) &&
    isStringOrNull(value.last_successful_sync_at) &&
    isNumber(value.stale_after_seconds) &&
    typeof value.is_stale === "boolean"
  );
}

function isInstanceItem(value: unknown): value is InstanceItem {
  return (
    isPlainRecord(value) &&
    typeof value.cloud_id === "string" &&
    typeof value.region_id === "string" &&
    typeof value.instance_id === "string" &&
    typeof value.name === "string" &&
    typeof value.project_id === "string" &&
    typeof value.user_id === "string" &&
    typeof value.status === "string" &&
    typeof value.power_state === "string" &&
    isStringOrNull(value.task_state) &&
    typeof value.vm_state === "string" &&
    isStringOrNull(value.host_name) &&
    isStringOrNull(value.hypervisor_id) &&
    isStringOrNull(value.availability_zone) &&
    isStringOrNull(value.flavor_id) &&
    isNumber(value.vcpus) &&
    isNumber(value.ram_mb) &&
    isNumber(value.disk_gb) &&
    isStringOrNull(value.image_id) &&
    isStringOrNull(value.boot_volume_id) &&
    isPlainRecord(value.addresses) &&
    isStringOrNull(value.source_created_at) &&
    isStringOrNull(value.source_updated_at) &&
    typeof value.observed_at === "string" &&
    isNumber(value.sync_generation) &&
    typeof value.sync_status === "string"
  );
}

function isHypervisorItem(value: unknown): value is HypervisorItem {
  return (
    isPlainRecord(value) &&
    typeof value.cloud_id === "string" &&
    typeof value.region_id === "string" &&
    typeof value.hypervisor_id === "string" &&
    typeof value.host_name === "string" &&
    isStringOrNull(value.service_id) &&
    typeof value.service_status === "string" &&
    typeof value.service_state === "string" &&
    isStringOrNull(value.hypervisor_type) &&
    isStringOrNull(value.hypervisor_version) &&
    isStringOrNull(value.availability_zone) &&
    Array.isArray(value.aggregates) &&
    value.aggregates.every((aggregate) => typeof aggregate === "string") &&
    isNumber(value.vcpus_total) &&
    isNumber(value.vcpus_used) &&
    isNumber(value.ram_mb_total) &&
    isNumber(value.ram_mb_used) &&
    isNumber(value.disk_gb_total) &&
    isNumber(value.disk_gb_used) &&
    isNumber(value.running_vms) &&
    isStringOrNull(value.disabled_reason) &&
    isStringOrNull(value.maintenance_status) &&
    typeof value.observed_at === "string" &&
    isNumber(value.sync_generation) &&
    typeof value.sync_status === "string"
  );
}

function isInventoryPage<T>(
  payload: unknown,
  isItem: (value: unknown) => value is T,
): payload is InventoryPage<T> {
  if (!isPlainRecord(payload)) {
    return false;
  }

  const warnings = payload.warnings;
  return (
    Array.isArray(payload.items) &&
    payload.items.every(isItem) &&
    isStringOrNull(payload.next_cursor) &&
    isNumber(payload.limit) &&
    typeof payload.sort === "string" &&
    typeof payload.partial === "boolean" &&
    Array.isArray(warnings) &&
    warnings.every(isInventoryWarning) &&
    (payload.freshness === null || isInventoryFreshness(payload.freshness))
  );
}

function isInventoryModuleDescriptor(
  value: unknown,
): value is InventoryModuleDescriptor {
  return (
    isPlainRecord(value) &&
    typeof value.key === "string" &&
    typeof value.title === "string" &&
    isStringOrNull(value.path) &&
    typeof value.enabled === "boolean" &&
    isStringOrNull(value.required_capability) &&
    (value.status === "enabled" || value.status === "disabled") &&
    isStringOrNull(value.reason)
  );
}

function isInventoryModulesPayload(
  payload: unknown,
): payload is { modules: InventoryModuleDescriptor[] } {
  return (
    isPlainRecord(payload) &&
    Array.isArray(payload.modules) &&
    payload.modules.every(isInventoryModuleDescriptor)
  );
}

function isWorkflowDefinition(value: unknown): value is WorkflowDefinition {
  return (
    isPlainRecord(value) &&
    typeof value.workflow_key === "string" &&
    typeof value.version === "string" &&
    typeof value.title === "string" &&
    typeof value.description === "string" &&
    (value.target_type === "host" ||
      value.target_type === "vm" ||
      value.target_type === "group") &&
    typeof value.required_capability === "string" &&
    typeof value.risk_level === "string" &&
    typeof value.approval_mode === "string" &&
    typeof value.cancel_policy === "string" &&
    typeof value.checksum === "string" &&
    value.mistral_workflow_name === null
  );
}

function isWorkflowDefinitionListResponse(
  payload: unknown,
): payload is WorkflowDefinitionListResponse {
  return (
    isPlainRecord(payload) &&
    Array.isArray(payload.items) &&
    payload.items.every(isWorkflowDefinition) &&
    isNumber(payload.limit)
  );
}

function isOperationSubmitResponse(
  payload: unknown,
): payload is OperationSubmitResponse {
  return (
    isPlainRecord(payload) &&
    typeof payload.operation_id === "string" &&
    typeof payload.status === "string"
  );
}

function isOperationEvent(value: unknown): value is OperationEvent {
  return (
    isPlainRecord(value) &&
    typeof value.event_id === "string" &&
    typeof value.event_type === "string" &&
    isStringOrNull(value.from_status) &&
    isStringOrNull(value.to_status) &&
    typeof value.outcome === "string" &&
    typeof value.safe_message === "string" &&
    isStringOrNull(value.safe_error_code) &&
    isPlainRecord(value.metadata) &&
    typeof value.created_at === "string"
  );
}

function isOperationDetail(payload: unknown): payload is OperationDetail {
  return (
    isPlainRecord(payload) &&
    typeof payload.operation_id === "string" &&
    typeof payload.workflow_key === "string" &&
    typeof payload.workflow_version === "string" &&
    typeof payload.status === "string" &&
    typeof payload.correlation_id === "string" &&
    isStringOrNull(payload.external_execution_id) &&
    typeof payload.created_at === "string" &&
    typeof payload.updated_at === "string" &&
    Array.isArray(payload.events) &&
    payload.events.every(isOperationEvent)
  );
}

const DEFAULT_LIST_LIMIT = 50;
const MAX_LIST_LIMIT = 200;

const COMMON_LIST_PARAMS = [
  "cursor",
  "sort",
  "q",
  "cloud_id",
  "region_id",
  "group_id",
] as const;
const SORT_DIRECTIONS = ["asc", "desc"] as const;
const INSTANCE_LIST_PARAMS = [
  ...COMMON_LIST_PARAMS,
  "project_id",
  "status",
  "host_name",
  "hypervisor_id",
  "availability_zone",
] as const;
const HYPERVISOR_LIST_PARAMS = [
  ...COMMON_LIST_PARAMS,
  "service_status",
  "service_state",
  "host_name",
  "availability_zone",
  "maintenance_status",
] as const;
const INSTANCE_SORT_FIELDS = [
  "instance_id",
  "name",
  "project_id",
  "status",
  "host_name",
  "availability_zone",
  "source_updated_at",
  "observed_at",
] as const;
const HYPERVISOR_SORT_FIELDS = [
  "hypervisor_id",
  "host_name",
  "service_status",
  "service_state",
  "availability_zone",
  "observed_at",
] as const;

type SortConfig = {
  allowedFields: readonly string[];
  defaultSort: string;
};

const INSTANCE_SORT_CONFIG: SortConfig = {
  allowedFields: INSTANCE_SORT_FIELDS,
  defaultSort: "name.asc",
};
const HYPERVISOR_SORT_CONFIG: SortConfig = {
  allowedFields: HYPERVISOR_SORT_FIELDS,
  defaultSort: "host_name.asc",
};

const AUDIT_LIST_PARAMS = [
  "cursor",
  "from",
  "to",
  "action",
  "outcome",
  "actor_id",
  "target_type",
  "target_id",
  "request_id",
  "correlation_id",
  "operation_id",
  "delivery_state",
  "safe_error_code",
] as const;

function boundedLimit(rawLimit: string | null): string {
  if (rawLimit === null) {
    return String(DEFAULT_LIST_LIMIT);
  }

  const requestedLimit = Number(rawLimit);
  if (!Number.isFinite(requestedLimit)) {
    return String(DEFAULT_LIST_LIMIT);
  }

  return String(
    Math.max(1, Math.min(Math.trunc(requestedLimit), MAX_LIST_LIMIT)),
  );
}

function normalizedSort(rawSort: string | null, config: SortConfig): string {
  if (rawSort === null) {
    return config.defaultSort;
  }

  const [field, direction, extra] = rawSort.split(".");
  if (
    extra !== undefined ||
    field === undefined ||
    direction === undefined ||
    !config.allowedFields.includes(field) ||
    !(SORT_DIRECTIONS as readonly string[]).includes(direction)
  ) {
    return config.defaultSort;
  }

  return `${field}.${direction}`;
}

function inventoryUrl(
  path: string,
  params: URLSearchParams,
  supportedParams: readonly string[],
  sortConfig: SortConfig,
): string {
  const query = new URLSearchParams();
  query.set("limit", boundedLimit(params.get("limit")));

  for (const key of supportedParams) {
    if (key === "limit") {
      continue;
    }
    if (key === "sort") {
      query.set("sort", normalizedSort(params.get("sort"), sortConfig));
      continue;
    }
    for (const value of params.getAll(key)) {
      query.append(key, value);
    }
  }

  return `${path}?${query.toString()}`;
}

function listUrl(path: string, params: URLSearchParams): string {
  const query = new URLSearchParams();
  query.set("limit", boundedLimit(params.get("limit")));
  return `${path}?${query.toString()}`;
}

function auditUrl(params: URLSearchParams): string {
  const query = new URLSearchParams();
  query.set("limit", boundedLimit(params.get("limit")));
  for (const key of AUDIT_LIST_PARAMS) {
    for (const value of params.getAll(key)) {
      query.append(key, value);
    }
  }
  return `/api/v1/audit/events?${query.toString()}`;
}

function groupUrl(groupId: string, suffix = ""): string {
  return `/api/v1/groups/${encodeURIComponent(groupId)}${suffix}`;
}

function errorMessage(payload: unknown, fallback: string): string {
  if (isPlainRecord(payload) && isPlainRecord(payload.error)) {
    const message = payload.error.message;
    if (typeof message === "string" && message !== "") {
      return message;
    }
  }
  return fallback;
}

export async function fetchReadiness(): Promise<Readiness> {
  const response = await fetch("/api/v1/health/ready");
  const payload: unknown = await response.json();

  if (isReadiness(payload)) {
    return payload;
  }

  throw new Error("Готовность API недоступна");
}

export async function fetchCurrentSession(): Promise<CurrentSession | null> {
  const response = await fetch("/api/v1/session");
  const payload: unknown = await response.json();

  if (response.status === 401) {
    return null;
  }
  if (isCurrentSession(payload)) {
    return payload;
  }

  throw new Error("Сессия недоступна");
}

export async function login(
  loginName: string,
  credential: string,
): Promise<LoginResult> {
  const response = await fetch("/api/v1/session/login", {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ login: loginName, credential }),
  });
  const payload: unknown = await response.json();

  if (response.ok && isLoginResult(payload)) {
    return payload;
  }

  throw new Error("Не удалось выполнить вход");
}

export async function fetchCapabilities(): Promise<Capabilities> {
  const response = await fetch("/api/v1/capabilities");
  const payload: unknown = await response.json();

  if (response.ok && isCapabilities(payload)) {
    return payload;
  }

  throw new Error("Список прав недоступен");
}

export async function fetchInstances(
  params: URLSearchParams,
  signal?: AbortSignal,
): Promise<InventoryPage<InstanceItem>> {
  const response = await fetch(
    inventoryUrl(
      "/api/v1/instances",
      params,
      INSTANCE_LIST_PARAMS,
      INSTANCE_SORT_CONFIG,
    ),
    signal === undefined ? undefined : { signal },
  );
  const payload: unknown = await response.json();

  if (response.ok && isInventoryPage(payload, isInstanceItem)) {
    return payload;
  }

  throw new Error("Список ВМ недоступен");
}

export async function fetchHypervisors(
  params: URLSearchParams,
  signal?: AbortSignal,
): Promise<InventoryPage<HypervisorItem>> {
  const response = await fetch(
    inventoryUrl(
      "/api/v1/hypervisors",
      params,
      HYPERVISOR_LIST_PARAMS,
      HYPERVISOR_SORT_CONFIG,
    ),
    signal === undefined ? undefined : { signal },
  );
  const payload: unknown = await response.json();

  if (response.ok && isInventoryPage(payload, isHypervisorItem)) {
    return payload;
  }

  throw new Error("Список гипервизоров недоступен");
}

export async function fetchInventoryModules(): Promise<
  InventoryModuleDescriptor[]
> {
  const response = await fetch("/api/v1/inventory/modules");
  const payload: unknown = await response.json();

  if (response.ok && isInventoryModulesPayload(payload)) {
    return payload.modules;
  }

  throw new Error("Список модулей inventory недоступен");
}

export async function fetchWorkflowDefinitions(): Promise<WorkflowDefinitionListResponse> {
  const response = await fetch("/api/v1/workflow-definitions?limit=50");
  const payload: unknown = await response.json();

  if (response.ok && isWorkflowDefinitionListResponse(payload)) {
    return payload;
  }

  throw new Error("Каталог операций недоступен");
}

export async function submitOperation(
  body: OperationSubmitRequest,
  csrf: string,
  idempotencyKey: string,
): Promise<OperationSubmitResponse> {
  const response = await fetch("/api/v1/operations", {
    method: "POST",
    headers: {
      "content-type": "application/json",
      "idempotency-key": idempotencyKey,
      "x-csrf-token": csrf,
    },
    body: JSON.stringify(body),
  });
  const payload: unknown = await response.json();

  if (response.ok && isOperationSubmitResponse(payload)) {
    return payload;
  }

  throw new Error(errorMessage(payload, "Операцию не удалось отправить"));
}

export async function fetchOperation(
  operationId: string,
  signal?: AbortSignal,
): Promise<OperationDetail> {
  const response = await fetch(
    `/api/v1/operations/${encodeURIComponent(operationId)}`,
    signal === undefined ? undefined : { signal },
  );
  const payload: unknown = await response.json();

  if (response.ok && isOperationDetail(payload)) {
    return payload;
  }

  throw new Error(errorMessage(payload, "Операция недоступна"));
}

export async function fetchAuditEvents(
  params: URLSearchParams,
  signal?: AbortSignal,
): Promise<AuditEventListResponse> {
  const response = await fetch(
    auditUrl(params),
    signal === undefined ? undefined : { signal },
  );
  const payload: unknown = await response.json();

  if (response.ok && isAuditEventListResponse(payload)) {
    return payload;
  }

  throw new Error(errorMessage(payload, "Журнал аудита недоступен"));
}

export async function requestAuditExport(
  body: AuditExportRequest,
  csrf: string,
): Promise<AuditExportResponse> {
  const response = await fetch("/api/v1/audit/export", {
    method: "POST",
    headers: { "content-type": "application/json", "x-csrf-token": csrf },
    body: JSON.stringify(body),
  });
  const payload: unknown = await response.json();

  if (response.ok && isAuditExportResponse(payload)) {
    return payload;
  }

  throw new Error(errorMessage(payload, "Экспорт аудита не запрошен"));
}

export async function fetchGroups(
  params: URLSearchParams = new URLSearchParams(),
): Promise<GroupListResponse> {
  const response = await fetch(listUrl("/api/v1/groups", params));
  const payload: unknown = await response.json();

  if (response.ok && isGroupListResponse(payload)) {
    return payload;
  }

  throw new Error("Список групп недоступен");
}

export async function fetchGroup(groupId: string): Promise<ResourceGroup> {
  const response = await fetch(groupUrl(groupId));
  const payload: unknown = await response.json();

  if (response.ok && isResourceGroup(payload)) {
    return payload;
  }

  throw new Error("Группа недоступна");
}

export async function createGroup(
  body: {
    name: string;
    description: string | null;
    resource_type: GroupResourceType;
    membership_mode: "explicit" | "dynamic" | "imported";
    scope_id: string | null;
  },
  csrf: string,
): Promise<ResourceGroup> {
  const response = await fetch("/api/v1/groups", {
    method: "POST",
    headers: { "content-type": "application/json", "x-csrf-token": csrf },
    body: JSON.stringify(body),
  });
  const payload: unknown = await response.json();

  if (response.ok && isResourceGroup(payload)) {
    return payload;
  }

  throw new Error(errorMessage(payload, "Группу не удалось создать"));
}

export async function updateGroup(
  groupId: string,
  body: { revision: number; name: string; description: string | null },
  csrf: string,
): Promise<ResourceGroup> {
  const response = await fetch(groupUrl(groupId), {
    method: "PATCH",
    headers: { "content-type": "application/json", "x-csrf-token": csrf },
    body: JSON.stringify(body),
  });
  const payload: unknown = await response.json();

  if (response.ok && isResourceGroup(payload)) {
    return payload;
  }

  throw new Error(errorMessage(payload, "Группу не удалось обновить"));
}

export async function fetchGroupMembers(
  groupId: string,
  params: URLSearchParams = new URLSearchParams(),
): Promise<GroupMembersResponse> {
  const response = await fetch(listUrl(groupUrl(groupId, "/members"), params));
  const payload: unknown = await response.json();

  if (response.ok && isGroupMembersResponse(payload)) {
    return payload;
  }

  throw new Error("Участники группы недоступны");
}

export async function addGroupMember(
  groupId: string,
  member: Pick<
    GroupMember,
    "resource_type" | "cloud_id" | "region_id" | "resource_id"
  >,
  csrf: string,
  idempotencyKey: string,
): Promise<GroupMemberMutationResponse> {
  const response = await fetch(groupUrl(groupId, "/members"), {
    method: "POST",
    headers: {
      "content-type": "application/json",
      "idempotency-key": idempotencyKey,
      "x-csrf-token": csrf,
    },
    body: JSON.stringify(member),
  });
  const payload: unknown = await response.json();

  if (response.ok && isGroupMemberMutationResponse(payload)) {
    return payload;
  }

  throw new Error(errorMessage(payload, "Участник группы не добавлен"));
}

export async function removeGroupMember(
  groupId: string,
  member: Pick<
    GroupMember,
    "resource_type" | "cloud_id" | "region_id" | "resource_id"
  >,
  csrf: string,
  idempotencyKey: string,
): Promise<GroupDeleteResponse> {
  const path = [
    groupUrl(groupId, "/members"),
    encodeURIComponent(member.resource_type),
    encodeURIComponent(member.cloud_id),
    encodeURIComponent(member.region_id),
    encodeURIComponent(member.resource_id),
  ].join("/");
  const response = await fetch(path, {
    method: "DELETE",
    headers: {
      "idempotency-key": idempotencyKey,
      "x-csrf-token": csrf,
    },
  });
  const payload: unknown = await response.json();

  if (response.ok && isGroupDeleteResponse(payload)) {
    return payload;
  }

  throw new Error(errorMessage(payload, "Участник группы не удален"));
}

export async function previewGroupRule(
  groupId: string,
  rule: Record<string, unknown>,
  signal?: AbortSignal,
): Promise<GroupPreviewResponse> {
  const response = await fetch(groupUrl(groupId, "/preview"), {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({
      rule,
      cloud_id: "synthetic",
      region_id: "RegionOne",
      limit: 50,
    }),
    signal,
  });
  const payload: unknown = await response.json();

  if (response.ok && isGroupPreviewResponse(payload)) {
    return payload;
  }

  throw new Error(errorMessage(payload, "Правило группы отклонено"));
}
