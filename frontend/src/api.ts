export type DependencyState = {
  status: "ok" | "down";
  detail: string;
};

export type Readiness = {
  status: "ok" | "degraded";
  dependencies: Record<string, DependencyState>;
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

export async function fetchReadiness(): Promise<Readiness> {
  const response = await fetch("/api/v1/health/ready");
  const payload: unknown = await response.json();

  if (isReadiness(payload)) {
    return payload;
  }

  throw new Error("Готовность API недоступна");
}
