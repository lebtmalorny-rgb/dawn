import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, expect, test, vi } from "vitest";

import { App } from "./App";

const readyPayload = {
  status: "ok",
  dependencies: {
    database: { status: "ok", detail: "reachable" }
  }
};

const operatorSessionPayload = {
  subject: {
    subject_id: "mock-user-operator",
    display_name: "Оператор облака",
    subject_type: "human",
    roles: ["cloud_operator"]
  }
};

function capabilitiesPayload(capabilities: string[]) {
  return {
    scope: { type: "system", id: null },
    capabilities,
    expires_at: "2026-06-21T15:00:00Z",
    policy_revision: "p0-mock-policy-v1"
  };
}

function inventoryPage<T>(items: T[], partial = false, isStale = false) {
  return {
    items,
    next_cursor: null,
    limit: 50,
    sort: "name.asc",
    partial,
    warnings: partial
      ? [
          {
            code: "source_unavailable",
            title: "Источник недоступен",
            detail: "RegionOne вернул timeout",
            source: "nova"
          }
        ]
      : [],
    freshness: {
      observed_at: "2026-06-21T10:00:00Z",
      last_successful_sync_at: "2026-06-21T09:55:00Z",
      stale_after_seconds: 300,
      is_stale: isStale
    }
  };
}

function instanceItem(overrides: Record<string, unknown> = {}) {
  return {
    cloud_id: "synthetic",
    region_id: "RegionOne",
    instance_id: "instance-0001",
    name: "vm-active",
    project_id: "project-0001",
    user_id: "user-0001",
    status: "ACTIVE",
    power_state: "running",
    task_state: null,
    vm_state: "active",
    host_name: "compute-a",
    hypervisor_id: "hypervisor-0001",
    availability_zone: "nova",
    flavor_id: "flavor-small",
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
    ...overrides
  };
}

function hypervisorItem(overrides: Record<string, unknown> = {}) {
  return {
    cloud_id: "synthetic",
    region_id: "RegionOne",
    hypervisor_id: "hypervisor-0001",
    host_name: "compute-a",
    service_id: "service-hypervisor-0001",
    service_status: "enabled",
    service_state: "up",
    hypervisor_type: "QEMU",
    hypervisor_version: "9.0",
    availability_zone: "nova",
    aggregates: ["az-nova"],
    vcpus_total: 64,
    vcpus_used: 8,
    ram_mb_total: 262144,
    ram_mb_used: 32768,
    disk_gb_total: 4000,
    disk_gb_used: 1000,
    running_vms: 4,
    disabled_reason: null,
    maintenance_status: null,
    observed_at: "2026-06-21T10:00:00Z",
    sync_generation: 1,
    sync_status: "ok",
    ...overrides
  };
}

function jsonResponse(payload: unknown, status = 200) {
  return {
    ok: status >= 200 && status < 300,
    status,
    json: async () => payload
  };
}

beforeEach(() => {
  window.history.replaceState({}, "", "/");
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

test("renders API readiness ok with dependency names", async () => {
  vi.stubGlobal(
    "fetch",
    vi.fn(async (input: RequestInfo | URL) => ({
      ok: true,
      status: 200,
      json: async () => {
        if (String(input) === "/api/v1/session") {
          return operatorSessionPayload;
        }
        if (String(input) === "/api/v1/capabilities") {
          return capabilitiesPayload(["operation.read"]);
        }
        return {
          status: "ok",
          dependencies: {
            database: { status: "ok", detail: "reachable" },
            rabbitmq: { status: "ok", detail: "reachable" }
          }
        };
      }
    }))
  );

  render(<App />);

  expect(await screen.findByText("Готовность API: ok")).toBeInTheDocument();
  expect(screen.getByText("database")).toBeInTheDocument();
  expect(screen.getByText("rabbitmq")).toBeInTheDocument();
});

test("renders degraded readiness from a 503 response body", async () => {
  vi.stubGlobal(
    "fetch",
    vi.fn(async (input: RequestInfo | URL) => ({
      ok: String(input) === "/api/v1/session",
      status: String(input) === "/api/v1/session" ? 200 : 503,
      json: async () => {
        if (String(input) === "/api/v1/session") {
          return operatorSessionPayload;
        }
        if (String(input) === "/api/v1/capabilities") {
          return capabilitiesPayload(["operation.read"]);
        }
        return {
          status: "degraded",
          dependencies: {
            database: { status: "ok", detail: "reachable" },
            rabbitmq: { status: "down", detail: "connection refused" }
          }
        };
      }
    }))
  );

  render(<App />);

  expect(await screen.findByText("Готовность API: degraded")).toBeInTheDocument();
  expect(screen.getByText("rabbitmq")).toBeInTheDocument();
  expect(screen.getByText("down - connection refused")).toBeInTheDocument();
});

test("renders safe error when dependency payload is malformed", async () => {
  vi.stubGlobal(
    "fetch",
    vi.fn(async (input: RequestInfo | URL) => ({
      ok: true,
      status: 200,
      json: async () => {
        if (String(input) === "/api/v1/session") {
          return operatorSessionPayload;
        }
        if (String(input) === "/api/v1/capabilities") {
          return capabilitiesPayload(["operation.read"]);
        }
        return {
          status: "ok",
          dependencies: {
            database: null
          }
        };
      }
    }))
  );

  render(<App />);

  expect(await screen.findByText("Готовность API недоступна")).toBeInTheDocument();
});

test("renders safe error when readiness fetch fails", async () => {
  vi.stubGlobal(
    "fetch",
    vi.fn(async (input: RequestInfo | URL) => {
      if (String(input) === "/api/v1/session") {
        return {
          ok: true,
          status: 200,
          json: async () => operatorSessionPayload
        };
      }
      if (String(input) === "/api/v1/capabilities") {
        return {
          ok: true,
          status: 200,
          json: async () => capabilitiesPayload(["operation.read"])
        };
      }
      throw new Error("network failure");
    })
  );

  render(<App />);

  expect(await screen.findByText("Готовность API недоступна")).toBeInTheDocument();
});

test("logs in through BFF and hides forbidden role management action", async () => {
  const user = userEvent.setup();
  const storageSet = vi.spyOn(Storage.prototype, "setItem");
  vi.stubGlobal(
    "fetch",
    vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input);
      if (url === "/api/v1/session") {
        return {
          ok: false,
          status: 401,
          json: async () => ({
            error: { code: "not_authenticated", message: "Требуется вход" }
          })
        };
      }
      if (url === "/api/v1/health/ready") {
        return {
          ok: true,
          status: 200,
          json: async () => ({
            status: "ok",
            dependencies: {
              database: { status: "ok", detail: "reachable" }
            }
          })
        };
      }
      if (url === "/api/v1/session/login") {
        return {
          ok: true,
          status: 200,
          json: async () => ({
            subject: {
              subject_id: "mock-user-operator",
              display_name: "Оператор облака",
              subject_type: "human",
              roles: ["cloud_operator"]
            },
            csrf: "csrf-value",
            expires_at: "2026-06-21T15:00:00Z"
          })
        };
      }
      if (url === "/api/v1/capabilities") {
        return {
          ok: true,
          status: 200,
          json: async () => ({
            scope: { type: "system", id: null },
            capabilities: ["instance.read", "operation.read"],
            expires_at: "2026-06-21T15:00:00Z",
            policy_revision: "p0-mock-policy-v1"
          })
        };
      }
      if (url === "/api/v1/instances?limit=50") {
        return {
          ok: true,
          status: 200,
          json: async () => inventoryPage([])
        };
      }
      throw new Error(`unexpected fetch ${url}`);
    })
  );

  render(<App />);

  await user.type(await screen.findByLabelText("Логин"), "operator");
  await user.type(screen.getByLabelText("Код доступа"), "operator-code");
  await user.click(screen.getByRole("button", { name: "Войти" }));

  expect(await screen.findByText("Оператор облака")).toBeInTheDocument();
  expect(screen.getByText("Операции")).toBeInTheDocument();
  expect(screen.queryByText("Управление ролями")).not.toBeInTheDocument();
  expect(storageSet).not.toHaveBeenCalled();
});

test("renders safe auth error when session payload is malformed", async () => {
  vi.stubGlobal(
    "fetch",
    vi.fn(async (input: RequestInfo | URL) => ({
      ok: true,
      status: 200,
      json: async () => {
        if (String(input) === "/api/v1/session") {
          return { subject: null };
        }
        return {
          status: "ok",
          dependencies: {}
        };
      }
    }))
  );

  render(<App />);

  expect(await screen.findByText("Сессия недоступна")).toBeInTheDocument();
});

test("renders inventory navigation only when capabilities allow it", async () => {
  vi.stubGlobal(
    "fetch",
    vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input);
      if (url === "/api/v1/session") {
        return jsonResponse(operatorSessionPayload);
      }
      if (url === "/api/v1/health/ready") {
        return jsonResponse(readyPayload);
      }
      if (url === "/api/v1/capabilities") {
        return jsonResponse(capabilitiesPayload(["instance.read"]));
      }
      if (url === "/api/v1/instances?limit=50") {
        return jsonResponse(inventoryPage([]));
      }
      throw new Error(`unexpected fetch ${url}`);
    })
  );

  render(<App />);

  expect(await screen.findByText("ВМ")).toBeInTheDocument();
  expect(screen.queryByText("Гипервизоры")).not.toBeInTheDocument();
});

test("instances page fetches server-side page from BFF with URL filters", async () => {
  window.history.replaceState({}, "", "/?view=instances&status=ACTIVE&sort=name.asc");
  const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
    const url = String(input);
    if (url === "/api/v1/session") {
      return jsonResponse(operatorSessionPayload);
    }
    if (url === "/api/v1/health/ready") {
      return jsonResponse(readyPayload);
    }
    if (url === "/api/v1/capabilities") {
      return jsonResponse(capabilitiesPayload(["instance.read"]));
    }
    if (url === "/api/v1/instances?limit=50&status=ACTIVE&sort=name.asc") {
      return jsonResponse(inventoryPage([instanceItem({ name: "vm-from-server" })]));
    }
    throw new Error(`unexpected fetch ${url}`);
  });
  vi.stubGlobal("fetch", fetchMock);

  render(<App />);

  expect(await screen.findByText("vm-from-server")).toBeInTheDocument();
  expect(screen.queryByText("vm-not-returned")).not.toBeInTheDocument();
  await waitFor(() => {
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/v1/instances?limit=50&status=ACTIVE&sort=name.asc"
    );
  });
});

test("hypervisors page renders partial and stale state", async () => {
  window.history.replaceState({}, "", "/?view=hypervisors");
  vi.stubGlobal(
    "fetch",
    vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input);
      if (url === "/api/v1/session") {
        return jsonResponse(operatorSessionPayload);
      }
      if (url === "/api/v1/health/ready") {
        return jsonResponse(readyPayload);
      }
      if (url === "/api/v1/capabilities") {
        return jsonResponse(capabilitiesPayload(["hypervisor.read"]));
      }
      if (url === "/api/v1/hypervisors?limit=50") {
        return jsonResponse(
          inventoryPage([hypervisorItem({ host_name: "compute-stale" })], true, true)
        );
      }
      throw new Error(`unexpected fetch ${url}`);
    })
  );

  render(<App />);

  expect(await screen.findByText("compute-stale")).toBeInTheDocument();
  expect(screen.getByText("Частичные данные")).toBeInTheDocument();
  expect(screen.getByText("Данные устарели")).toBeInTheDocument();
  expect(screen.getByText("RegionOne вернул timeout")).toBeInTheDocument();
});

test("inventory pages do not store result rows in browser storage", async () => {
  const storageSet = vi.spyOn(Storage.prototype, "setItem");
  vi.stubGlobal(
    "fetch",
    vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input);
      if (url === "/api/v1/session") {
        return jsonResponse(operatorSessionPayload);
      }
      if (url === "/api/v1/health/ready") {
        return jsonResponse(readyPayload);
      }
      if (url === "/api/v1/capabilities") {
        return jsonResponse(capabilitiesPayload(["instance.read"]));
      }
      if (url === "/api/v1/instances?limit=50") {
        return jsonResponse(inventoryPage([instanceItem({ name: "vm-storage-check" })]));
      }
      throw new Error(`unexpected fetch ${url}`);
    })
  );

  render(<App />);

  expect(await screen.findByText("vm-storage-check")).toBeInTheDocument();
  expect(storageSet).not.toHaveBeenCalled();
});
