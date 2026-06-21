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

function isPlainRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function isDependencyState(value: unknown): value is DependencyState {
  if (!isPlainRecord(value)) {
    return false;
  }

  return (
    (value.status === "ok" || value.status === "down") && typeof value.detail === "string"
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
    payload.capabilities.every((capability) => typeof capability === "string") &&
    typeof payload.expires_at === "string" &&
    typeof payload.policy_revision === "string"
  );
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

export async function login(loginName: string, credential: string): Promise<LoginResult> {
  const response = await fetch("/api/v1/session/login", {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ login: loginName, credential })
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
