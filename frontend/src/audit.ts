export type AuditActor = {
  type: string;
  id: string;
  display: string;
  authentication_method: string;
  session_reference: string | null;
};

export type AuditTarget = {
  type: string;
  id: string | null;
};

export type AuditScope = {
  cloud_id: string | null;
  region_id: string | null;
  project_id: string | null;
  scope_type: string | null;
  scope_id: string | null;
};

export type AuditSource = {
  ip: string | null;
  trusted_proxy_chain: string[];
};

export type AuditEvent = {
  event_id: string;
  event_version: string;
  occurred_at: string;
  actor: AuditActor;
  action: string;
  event_type: string;
  outcome: string;
  target: AuditTarget;
  scope: AuditScope;
  source: AuditSource;
  request_id: string;
  correlation_id: string;
  operation_id: string | null;
  external_execution_id: string | null;
  service: string;
  component: string | null;
  safe_error_code: string | null;
  delivery_state: string;
  metadata: Record<string, unknown>;
};

export type AuditEventListResponse = {
  items: AuditEvent[];
  next_cursor: string | null;
  limit: number;
  sort: string;
};

export type AuditExportRequest = {
  from: string;
  to: string;
  limit: number;
};

export type AuditExportResponse = {
  export_request_id: string;
  status: string;
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

function isAuditActor(value: unknown): value is AuditActor {
  return (
    isPlainRecord(value) &&
    typeof value.type === "string" &&
    typeof value.id === "string" &&
    typeof value.display === "string" &&
    typeof value.authentication_method === "string" &&
    isStringOrNull(value.session_reference)
  );
}

function isAuditTarget(value: unknown): value is AuditTarget {
  return (
    isPlainRecord(value) &&
    typeof value.type === "string" &&
    isStringOrNull(value.id)
  );
}

function isAuditScope(value: unknown): value is AuditScope {
  return (
    isPlainRecord(value) &&
    isStringOrNull(value.cloud_id) &&
    isStringOrNull(value.region_id) &&
    isStringOrNull(value.project_id) &&
    isStringOrNull(value.scope_type) &&
    isStringOrNull(value.scope_id)
  );
}

function isAuditSource(value: unknown): value is AuditSource {
  return (
    isPlainRecord(value) &&
    isStringOrNull(value.ip) &&
    Array.isArray(value.trusted_proxy_chain) &&
    value.trusted_proxy_chain.every((item) => typeof item === "string")
  );
}

export function isAuditEvent(value: unknown): value is AuditEvent {
  return (
    isPlainRecord(value) &&
    typeof value.event_id === "string" &&
    typeof value.event_version === "string" &&
    typeof value.occurred_at === "string" &&
    isAuditActor(value.actor) &&
    typeof value.action === "string" &&
    typeof value.event_type === "string" &&
    typeof value.outcome === "string" &&
    isAuditTarget(value.target) &&
    isAuditScope(value.scope) &&
    isAuditSource(value.source) &&
    typeof value.request_id === "string" &&
    typeof value.correlation_id === "string" &&
    isStringOrNull(value.operation_id) &&
    isStringOrNull(value.external_execution_id) &&
    typeof value.service === "string" &&
    isStringOrNull(value.component) &&
    isStringOrNull(value.safe_error_code) &&
    typeof value.delivery_state === "string" &&
    isPlainRecord(value.metadata)
  );
}

export function isAuditEventListResponse(
  payload: unknown,
): payload is AuditEventListResponse {
  return (
    isPlainRecord(payload) &&
    Array.isArray(payload.items) &&
    payload.items.every(isAuditEvent) &&
    isStringOrNull(payload.next_cursor) &&
    isNumber(payload.limit) &&
    typeof payload.sort === "string"
  );
}

export function isAuditExportResponse(
  payload: unknown,
): payload is AuditExportResponse {
  return (
    isPlainRecord(payload) &&
    typeof payload.export_request_id === "string" &&
    typeof payload.status === "string"
  );
}
