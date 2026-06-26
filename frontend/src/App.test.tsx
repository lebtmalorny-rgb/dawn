import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
  within,
} from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, expect, test, vi } from "vitest";

import { App } from "./App";
import { CLOUD_MODULE_GROUPS } from "./navigation/cloudModules";
import { HORIZON_PARITY_ROWS } from "./navigation/horizonParity";

const readyPayload = {
  status: "ok",
  dependencies: {
    database: { status: "ok", detail: "reachable" },
  },
};

const operatorSessionPayload = {
  subject: {
    subject_id: "mock-user-operator",
    display_name: "Оператор облака",
    subject_type: "human",
    roles: ["cloud_operator"],
  },
};

function capabilitiesPayload(capabilities: string[]) {
  return {
    scope: { type: "system", id: null },
    capabilities,
    expires_at: "2026-06-21T15:00:00Z",
    policy_revision: "p0-mock-policy-v1",
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
            source: "nova",
          },
        ]
      : [],
    freshness: {
      observed_at: "2026-06-21T10:00:00Z",
      last_successful_sync_at: "2026-06-21T09:55:00Z",
      stale_after_seconds: 300,
      is_stale: isStale,
    },
  };
}

function inventoryPageWithNextCursor<T>(items: T[], nextCursor: string) {
  return {
    ...inventoryPage(items),
    next_cursor: nextCursor,
  };
}

function inventoryModulesPayload() {
  return {
    modules: [
      {
        key: "instances",
        title: "Инстансы",
        path: "/api/v1/instances",
        enabled: true,
        required_capability: "instance.read",
        status: "enabled",
        reason: null,
      },
      {
        key: "hypervisors",
        title: "Гипервизоры",
        path: "/api/v1/hypervisors",
        enabled: true,
        required_capability: "hypervisor.read",
        status: "enabled",
        reason: null,
      },
      {
        key: "compute_services",
        title: "Сервисы Nova Compute",
        path: null,
        enabled: false,
        required_capability: null,
        status: "disabled",
        reason: "adapter_not_enabled",
      },
      {
        key: "topology",
        title: "Топология",
        path: null,
        enabled: false,
        required_capability: null,
        status: "disabled",
        reason: "adapter_not_enabled",
      },
      {
        key: "capacity",
        title: "Емкость",
        path: null,
        enabled: false,
        required_capability: null,
        status: "disabled",
        reason: "adapter_not_enabled",
      },
    ],
  };
}

function workflowDefinitionsPayload() {
  return {
    items: [
      {
        workflow_key: "maintenance-host-precheck",
        version: "1.0.0",
        title: "Host maintenance precheck",
        description: "Dry-run host maintenance readiness check",
        target_type: "host",
        required_capability: "workflow.execute.maintenance-host",
        risk_level: "low",
        approval_mode: "none",
        cancel_policy: "best_effort",
        checksum: "definition-checksum",
        mistral_workflow_name: null,
      },
    ],
    limit: 50,
  };
}

function operationDetailPayload(overrides: Record<string, unknown> = {}) {
  return {
    operation_id: "op-precheck-1",
    workflow_key: "maintenance-host-precheck",
    workflow_version: "1.0.0",
    status: "accepted",
    correlation_id: "op-precheck-1",
    external_execution_id: null,
    created_at: "2026-06-21T10:00:00Z",
    updated_at: "2026-06-21T10:00:00Z",
    events: [
      {
        event_id: "event-1",
        event_type: "operation.accepted",
        from_status: null,
        to_status: "accepted",
        outcome: "success",
        safe_message: "Operation accepted",
        safe_error_code: null,
        metadata: { workflow_key: "maintenance-host-precheck" },
        created_at: "2026-06-21T10:00:00Z",
      },
    ],
    ...overrides,
  };
}

function auditEventPayload(overrides: Record<string, unknown> = {}) {
  return {
    event_id: "audit-event-1",
    event_version: "1.0",
    occurred_at: "2026-06-22T10:00:00Z",
    actor: {
      type: "human",
      id: "mock-user-operator",
      display: "Оператор облака",
      authentication_method: "mock",
      session_reference: "session-operator",
    },
    action: "session.login",
    event_type: "auth",
    outcome: "success",
    target: { type: "session", id: "session-operator" },
    scope: {
      cloud_id: null,
      region_id: null,
      project_id: null,
      scope_type: "project",
      scope_id: "project-a",
    },
    source: { ip: "192.0.2.10", trusted_proxy_chain: [] },
    request_id: "request-1",
    correlation_id: "correlation-1",
    operation_id: null,
    external_execution_id: null,
    service: "cloud-ui-api",
    component: "security",
    safe_error_code: null,
    delivery_state: "delivered",
    metadata: { normal: "visible" },
    ...overrides,
  };
}

function auditListPayload(items: unknown[], nextCursor: string | null = null) {
  return {
    items,
    next_cursor: nextCursor,
    limit: 50,
    sort: "occurred_at.desc,event_id.desc",
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
    ...overrides,
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
    ...overrides,
  };
}

function groupItem(overrides: Record<string, unknown> = {}) {
  return {
    group_id: "group-vm-prod",
    name: "Prod VMs",
    description: "Production project instances",
    resource_type: "vm",
    scope: { type: "project", id: "project-0001" },
    membership_mode: "explicit",
    rule_version: 1,
    rule_body_json: null,
    owner_subject_id: "mock-user-operator",
    revision: 3,
    created_at: "2026-06-21T10:00:00Z",
    updated_at: "2026-06-21T10:05:00Z",
    ...overrides,
  };
}

function groupListPayload(items: unknown[]) {
  return {
    items,
    limit: 50,
  };
}

function groupMembersPayload(items: unknown[] = []) {
  return {
    items,
    limit: 50,
  };
}

function groupPreviewPayload(
  items: unknown[],
  overrides: Record<string, unknown> = {},
) {
  return {
    items,
    count_estimate: items.length,
    limit: 50,
    explain: ["status == ACTIVE"],
    warnings: [],
    ...overrides,
  };
}

function jsonResponse(payload: unknown, status = 200) {
  return {
    ok: status >= 200 && status < 300,
    status,
    json: async () => payload,
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
            rabbitmq: { status: "ok", detail: "reachable" },
          },
        };
      },
    })),
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
            rabbitmq: { status: "down", detail: "connection refused" },
          },
        };
      },
    })),
  );

  render(<App />);

  expect(
    await screen.findByText("Готовность API: degraded"),
  ).toBeInTheDocument();
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
            database: null,
          },
        };
      },
    })),
  );

  render(<App />);

  expect(
    await screen.findByText("Готовность API недоступна"),
  ).toBeInTheDocument();
});

test("renders safe error when readiness fetch fails", async () => {
  vi.stubGlobal(
    "fetch",
    vi.fn(async (input: RequestInfo | URL) => {
      if (String(input) === "/api/v1/session") {
        return {
          ok: true,
          status: 200,
          json: async () => operatorSessionPayload,
        };
      }
      if (String(input) === "/api/v1/capabilities") {
        return {
          ok: true,
          status: 200,
          json: async () => capabilitiesPayload(["operation.read"]),
        };
      }
      throw new Error("network failure");
    }),
  );

  render(<App />);

  expect(
    await screen.findByText("Готовность API недоступна"),
  ).toBeInTheDocument();
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
            error: { code: "not_authenticated", message: "Требуется вход" },
          }),
        };
      }
      if (url === "/api/v1/health/ready") {
        return {
          ok: true,
          status: 200,
          json: async () => ({
            status: "ok",
            dependencies: {
              database: { status: "ok", detail: "reachable" },
            },
          }),
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
              roles: ["cloud_operator"],
            },
            csrf: "csrf-value",
            expires_at: "2026-06-21T15:00:00Z",
          }),
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
            policy_revision: "p0-mock-policy-v1",
          }),
        };
      }
      if (url === "/api/v1/instances?limit=50&sort=name.asc") {
        return {
          ok: true,
          status: 200,
          json: async () => inventoryPage([]),
        };
      }
      throw new Error(`unexpected fetch ${url}`);
    }),
  );

  render(<App />);

  await user.type(await screen.findByLabelText("Логин"), "operator");
  await user.type(screen.getByLabelText("Код доступа"), "operator-code");
  await user.click(screen.getByRole("button", { name: "Войти" }));

  expect(await screen.findAllByText("Оператор облака")).not.toHaveLength(0);
  const portalNav = screen.getByRole("navigation", { name: "Разделы портала" });
  expect(
    within(portalNav).getByRole("link", { name: "Операции" }),
  ).toBeInTheDocument();
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
          dependencies: {},
        };
      },
    })),
  );

  render(<App />);

  expect(await screen.findByText("Сессия недоступна")).toBeInTheDocument();
});

test("cloud module registry exposes the agreed shell groups", () => {
  expect(CLOUD_MODULE_GROUPS.map((group) => group.key)).toEqual([
    "inventory",
    "operations",
    "administration",
    "audit_dkb",
  ]);
  expect(
    CLOUD_MODULE_GROUPS.flatMap((group) => group.items).map(
      (item) => item.key,
    ),
  ).toEqual(
    expect.arrayContaining([
      "instances",
      "hypervisors",
      "networks",
      "volumes",
      "mistral_operations",
      "watcher",
      "masakari",
      "horizon_parity",
      "dkb_evidence",
    ]),
  );
});

test("horizon parity registry keeps source workflows explicit", () => {
  expect(HORIZON_PARITY_ROWS).toEqual(
    expect.arrayContaining([
      expect.objectContaining({
        horizonArea: "Project / Compute / Instances / List and detail",
        cloudUiModule: "Inventory / Instances",
        requiredCapability: "instance.read",
        status: "implemented",
      }),
      expect.objectContaining({
        horizonArea: "Project / Compute / Instances / Launch instance",
        cloudUiModule: "Operations / Workflow catalog",
        requiredCapability: "instance.launch",
        status: "planned",
      }),
      expect.objectContaining({
        horizonArea: "Project / Compute / Instances / Power or lifecycle actions",
        cloudUiModule: "Operations / Workflow catalog",
        requiredCapability: "instance.lifecycle.manage",
        status: "planned",
      }),
      expect.objectContaining({
        horizonArea: "Project / Compute / Instances / Console access",
        cloudUiModule: "Inventory / Instances",
        requiredCapability: "instance.console.read",
        status: "planned",
      }),
      expect.objectContaining({
        horizonArea: "Project / Network / Routers",
        cloudUiModule: "Inventory / Networks",
        requiredCapability: "network.read",
        status: "planned",
      }),
      expect.objectContaining({
        horizonArea: "Admin / Identity / Users",
        cloudUiModule: "Administration / Identity",
        requiredCapability: "role.manage",
        status: "planned",
      }),
    ]),
  );
  expect(
    HORIZON_PARITY_ROWS.every(
      (row) =>
        row.apiContract.length > 0 &&
        row.statusReason.length > 0 &&
        row.auditEvent.length > 0 &&
        row.dkbNotes.length > 0,
    ),
  ).toBe(true);
});

test("authenticated inventory view renders inside CloudShell", async () => {
  window.history.pushState({}, "", "/?view=instances");
  const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input);
    if (url === "/api/v1/session") {
      return jsonResponse(operatorSessionPayload);
    }
    if (url === "/api/v1/health/ready") {
      return jsonResponse(readyPayload);
    }
    if (url === "/api/v1/capabilities") {
      return jsonResponse(
        capabilitiesPayload([
          "instance.read",
          "hypervisor.read",
          "group.read",
          "operation.read",
          "audit.read",
        ]),
      );
    }
    if (url === "/api/v1/inventory/modules") {
      return jsonResponse(inventoryModulesPayload());
    }
    if (url === "/api/v1/instances?limit=50&sort=name.asc") {
      expect(init).toEqual(
        expect.objectContaining({ signal: expect.any(AbortSignal) }),
      );
      return jsonResponse(
        inventoryPage([
          instanceItem({
            name: "vm-prod-api-01",
            project_id: "project-a",
            user_id: "user-a",
            power_state: "RUNNING",
            vm_state: "active",
            host_name: "compute-03",
            hypervisor_id: "hyp-03",
            availability_zone: "az1",
            flavor_id: "m1.small",
            image_id: "image-1",
            addresses: {},
          }),
        ]),
      );
    }
    throw new Error(`unexpected fetch ${url}`);
  });
  vi.stubGlobal("fetch", fetchMock);

  render(<App />);

  expect(await screen.findByRole("banner")).toHaveTextContent("Cloud UI");
  expect(
    screen.getByRole("navigation", { name: "Объекты облака" }),
  ).toBeInTheDocument();
  expect(screen.getByRole("heading", { name: "ВМ" })).toBeInTheDocument();
  expect(
    screen.getByRole("region", { name: "Нижняя рабочая панель" }),
  ).toHaveTextContent("Recent Tasks");
  expect(
    await screen.findByRole("table", { name: "Таблица ВМ" }),
  ).toBeInTheDocument();
  expect(fetchMock).toHaveBeenCalledWith(
    "/api/v1/instances?limit=50&sort=name.asc",
    expect.objectContaining({ signal: expect.any(AbortSignal) }),
  );
  expect(
    fetchMock.mock.calls.some(([input]) => String(input).includes("openstack")),
  ).toBe(false);
});

test("authenticated user without accessible portal sections does not mount CloudShell", async () => {
  window.history.pushState({}, "", "/?view=instances");
  const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
    const url = String(input);
    if (url === "/api/v1/session") {
      return jsonResponse(operatorSessionPayload);
    }
    if (url === "/api/v1/health/ready") {
      return jsonResponse(readyPayload);
    }
    if (url === "/api/v1/capabilities") {
      return jsonResponse(capabilitiesPayload([]));
    }
    throw new Error(`unexpected fetch ${url}`);
  });
  vi.stubGlobal("fetch", fetchMock);

  render(<App />);

  expect(
    await screen.findByText("Нет доступных разделов портала"),
  ).toBeInTheDocument();
  expect(
    screen.queryByRole("navigation", { name: "Объекты облака" }),
  ).not.toBeInTheDocument();
  expect(screen.queryByRole("heading", { name: "ВМ" })).not.toBeInTheDocument();
  expect(
    fetchMock.mock.calls.some(([input]) =>
      String(input).startsWith("/api/v1/instances"),
    ),
  ).toBe(false);
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
      if (url === "/api/v1/instances?limit=50&sort=name.asc") {
        return jsonResponse(inventoryPage([]));
      }
      throw new Error(`unexpected fetch ${url}`);
    }),
  );

  render(<App />);

  const inventoryNav = await screen.findByRole("navigation", {
    name: "Разделы инвентаря",
  });
  expect(within(inventoryNav).getByRole("link", { name: "ВМ" })).toBeInTheDocument();
  expect(
    within(inventoryNav).queryByRole("link", { name: "Гипервизоры" }),
  ).not.toBeInTheDocument();
});

test("renders groups navigation for group read capability", async () => {
  const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
    const url = String(input);
    if (url === "/api/v1/session") {
      return jsonResponse(operatorSessionPayload);
    }
    if (url === "/api/v1/health/ready") {
      return jsonResponse(readyPayload);
    }
    if (url === "/api/v1/capabilities") {
      return jsonResponse(capabilitiesPayload(["group.read"]));
    }
    if (url === "/api/v1/groups?limit=50") {
      return jsonResponse(groupListPayload([groupItem()]));
    }
    throw new Error(`unexpected fetch ${url}`);
  });
  vi.stubGlobal("fetch", fetchMock);

  render(<App />);

  const portalNav = await screen.findByRole("navigation", {
    name: "Разделы портала",
  });
  expect(
    within(portalNav).getByRole("link", { name: "Группы" }),
  ).toBeInTheDocument();
  expect(await screen.findByText("Prod VMs")).toBeInTheDocument();
  expect(within(portalNav).queryByRole("link", { name: "ВМ" })).not.toBeInTheDocument();
  const objectNav = screen.getByRole("navigation", { name: "Объекты облака" });
  expect(within(objectNav).queryByRole("link", { name: "ВМ" })).not.toBeInTheDocument();
  expect(
    within(objectNav).queryByRole("link", { name: "Гипервизоры" }),
  ).not.toBeInTheDocument();
  const vmItem = within(objectNav).getByText("ВМ").closest("li");
  expect(vmItem).not.toBeNull();
  expect(within(vmItem as HTMLElement).getByText("Недоступно")).toBeInTheDocument();
  expect(
    within(vmItem as HTMLElement).getByText("Требуется capability: instance.read"),
  ).toBeInTheDocument();
});

test("renders operations catalog for operation read capability", async () => {
  const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
    const url = String(input);
    if (url === "/api/v1/session") {
      return jsonResponse(operatorSessionPayload);
    }
    if (url === "/api/v1/health/ready") {
      return jsonResponse(readyPayload);
    }
    if (url === "/api/v1/capabilities") {
      return jsonResponse(capabilitiesPayload(["operation.read"]));
    }
    if (url === "/api/v1/workflow-definitions?limit=50") {
      return jsonResponse(workflowDefinitionsPayload());
    }
    throw new Error(`unexpected fetch ${url}`);
  });
  vi.stubGlobal("fetch", fetchMock);

  render(<App />);

  expect(
    await screen.findByRole("link", { name: "Операции" }),
  ).toBeInTheDocument();
  expect(await screen.findByText("Host maintenance precheck")).toBeInTheDocument();
  expect(screen.getByText("Dry-run host maintenance readiness check")).toBeInTheDocument();
  expect(screen.getByText("workflow.execute.maintenance-host")).toBeInTheDocument();
  expect(screen.getByLabelText("Хост")).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Запустить precheck" })).toBeDisabled();
  const objectNav = screen.getByRole("navigation", { name: "Объекты облака" });
  expect(within(objectNav).queryByRole("link", { name: "ВМ" })).not.toBeInTheDocument();
  expect(
    within(objectNav).queryByRole("link", { name: "Гипервизоры" }),
  ).not.toBeInTheDocument();
});

test("audit view fetches a server-side page and follows next cursor", async () => {
  window.history.replaceState({}, "", "/?view=audit&action=session.login");
  const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
    const url = String(input);
    if (url === "/api/v1/session") {
      return jsonResponse(operatorSessionPayload);
    }
    if (url === "/api/v1/health/ready") {
      return jsonResponse(readyPayload);
    }
    if (url === "/api/v1/capabilities") {
      return jsonResponse(capabilitiesPayload(["audit.read"]));
    }
    if (url === "/api/v1/audit/events?limit=50&action=session.login") {
      return jsonResponse(
        auditListPayload(
          [
            auditEventPayload({
              event_id: "audit-event-page-1",
              metadata: { token: "***" },
            }),
          ],
          "cursor-next",
        ),
      );
    }
    if (
      url ===
      "/api/v1/audit/events?limit=50&cursor=cursor-next&action=session.login"
    ) {
      return jsonResponse(
        auditListPayload([
          auditEventPayload({
            event_id: "audit-event-page-2",
            action: "audit.events.list",
            target: { type: "audit_event", id: null },
          }),
        ]),
      );
    }
    throw new Error(`unexpected fetch ${url}`);
  });
  vi.stubGlobal("fetch", fetchMock);
  const user = userEvent.setup();

  render(<App />);

  const portalNav = await screen.findByRole("navigation", {
    name: "Разделы портала",
  });
  expect(
    within(portalNav).getByRole("link", { name: "Аудит" }),
  ).toBeInTheDocument();
  const auditTable = await screen.findByRole("table", {
    name: "Таблица аудита",
  });
  expect(within(auditTable).getByText("audit-event-page-1")).toBeInTheDocument();
  expect(within(auditTable).getByText("session.login")).toBeInTheDocument();
  expect(within(auditTable).getByText("Оператор облака")).toBeInTheDocument();
  expect(within(auditTable).getByText("delivered")).toBeInTheDocument();
  expect(
    screen.queryByRole("button", { name: "Запросить экспорт" }),
  ).not.toBeInTheDocument();
  expect(screen.queryByText("DKB_CANARY_TOKEN")).not.toBeInTheDocument();

  await user.click(screen.getByRole("button", { name: "Следующая страница" }));

  expect(await screen.findByText("audit-event-page-2")).toBeInTheDocument();
  expect(window.location.search).toBe(
    "?view=audit&action=session.login&cursor=cursor-next",
  );
});

test("audit navigation is hidden without audit read capability", async () => {
  const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
    const url = String(input);
    if (url === "/api/v1/session") {
      return jsonResponse(operatorSessionPayload);
    }
    if (url === "/api/v1/health/ready") {
      return jsonResponse(readyPayload);
    }
    if (url === "/api/v1/capabilities") {
      return jsonResponse(capabilitiesPayload(["operation.read"]));
    }
    if (url === "/api/v1/workflow-definitions?limit=50") {
      return jsonResponse(workflowDefinitionsPayload());
    }
    throw new Error(`unexpected fetch ${url}`);
  });
  vi.stubGlobal("fetch", fetchMock);

  render(<App />);

  expect(await screen.findByText("Host maintenance precheck")).toBeInTheDocument();
  const portalNav = screen.getByRole("navigation", { name: "Разделы портала" });
  expect(within(portalNav).queryByRole("link", { name: "Аудит" })).not.toBeInTheDocument();
});

test("audit export is separated from audit read and uses csrf", async () => {
  const user = userEvent.setup();
  const fetchMock = vi.fn(
    async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url === "/api/v1/session") {
        return jsonResponse(
          {
            error: { code: "not_authenticated", message: "Требуется вход" },
          },
          401,
        );
      }
      if (url === "/api/v1/health/ready") {
        return jsonResponse(readyPayload);
      }
      if (url === "/api/v1/session/login") {
        return jsonResponse({
          subject: operatorSessionPayload.subject,
          csrf: "csrf-value",
          expires_at: "2026-06-21T15:00:00Z",
        });
      }
      if (url === "/api/v1/capabilities") {
        return jsonResponse(capabilitiesPayload(["audit.read", "audit.export"]));
      }
      if (url === "/api/v1/audit/events?limit=50") {
        return jsonResponse(auditListPayload([auditEventPayload()]));
      }
      if (url === "/api/v1/audit/export") {
        const headers = init?.headers as Record<string, string>;
        const body = JSON.parse(String(init?.body));
        expect(init?.method).toBe("POST");
        expect(headers["content-type"]).toBe("application/json");
        expect(headers["x-csrf-token"]).toBe("csrf-value");
        expect(body.limit).toBe(1000);
        expect(body.from).toEqual(expect.any(String));
        expect(body.to).toEqual(expect.any(String));
        return jsonResponse(
          { export_request_id: "audit-export-1", status: "accepted" },
          202,
        );
      }
      throw new Error(`unexpected fetch ${url}`);
    },
  );
  vi.stubGlobal("fetch", fetchMock);

  render(<App />);

  await user.type(await screen.findByLabelText("Логин"), "admin");
  await user.type(screen.getByLabelText("Код доступа"), "admin-code");
  await user.click(screen.getByRole("button", { name: "Войти" }));
  expect(await screen.findByText("audit-event-1")).toBeInTheDocument();
  await user.click(screen.getByRole("button", { name: "Запросить экспорт" }));

  expect(await screen.findByText("Экспорт принят: audit-export-1")).toBeInTheDocument();
});

test("submits host precheck through BFF with csrf and idempotency key", async () => {
  const user = userEvent.setup();
  const storageSet = vi.spyOn(Storage.prototype, "setItem");
  const fetchMock = vi.fn(
    async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url === "/api/v1/session") {
        return jsonResponse(
          {
            error: { code: "not_authenticated", message: "Требуется вход" },
          },
          401,
        );
      }
      if (url === "/api/v1/health/ready") {
        return jsonResponse(readyPayload);
      }
      if (url === "/api/v1/session/login") {
        return jsonResponse({
          subject: operatorSessionPayload.subject,
          csrf: "csrf-value",
          expires_at: "2026-06-21T15:00:00Z",
        });
      }
      if (url === "/api/v1/capabilities") {
        return jsonResponse(
          capabilitiesPayload([
            "operation.read",
            "workflow.execute.maintenance-host",
          ]),
        );
      }
      if (url === "/api/v1/workflow-definitions?limit=50") {
        return jsonResponse(workflowDefinitionsPayload());
      }
      if (url === "/api/v1/operations") {
        const headers = init?.headers as Record<string, string>;
        const body = JSON.parse(String(init?.body));
        expect(init?.method).toBe("POST");
        expect(headers["content-type"]).toBe("application/json");
        expect(headers["x-csrf-token"]).toBe("csrf-value");
        expect(headers["idempotency-key"]).toEqual(expect.any(String));
        expect(body).toEqual({
          workflow_key: "maintenance-host-precheck",
          version: "1.0.0",
          targets: [
            {
              target_type: "host",
              cloud_id: "synthetic",
              region_id: "RegionOne",
              resource_id: "compute-a",
            },
          ],
          input: { reason: "Плановое обслуживание", dry_run: true },
        });
        return jsonResponse({ operation_id: "op-precheck-1", status: "accepted" }, 202);
      }
      if (url === "/api/v1/operations/op-precheck-1") {
        return jsonResponse(
          operationDetailPayload({
            status: "running",
            external_execution_id: "exec-1",
            events: [
              {
                event_id: "event-1",
                event_type: "operation.accepted",
                from_status: null,
                to_status: "accepted",
                outcome: "success",
                safe_message: "Operation accepted",
                safe_error_code: null,
                metadata: {},
                created_at: "2026-06-21T10:00:00Z",
              },
              {
                event_id: "event-2",
                event_type: "operation.dispatched",
                from_status: "dispatching",
                to_status: "running",
                outcome: "success",
                safe_message: "Mistral execution started",
                safe_error_code: null,
                metadata: {},
                created_at: "2026-06-21T10:00:05Z",
              },
            ],
          }),
        );
      }
      throw new Error(`unexpected fetch ${url}`);
    },
  );
  vi.stubGlobal("fetch", fetchMock);

  render(<App />);

  await user.type(await screen.findByLabelText("Логин"), "operator");
  await user.type(screen.getByLabelText("Код доступа"), "operator-code");
  await user.click(screen.getByRole("button", { name: "Войти" }));
  await user.type(await screen.findByLabelText("Хост"), "compute-a");
  fireEvent.change(screen.getByLabelText("Причина"), {
    target: { value: "Плановое обслуживание" },
  });
  await user.click(screen.getByRole("button", { name: "Запустить precheck" }));

  expect(await screen.findByText("Статус: running")).toBeInTheDocument();
  expect(screen.getByText("Mistral execution: exec-1")).toBeInTheDocument();
  expect(screen.getByText("Mistral execution started")).toBeInTheDocument();
  expect(window.location.search).toBe(
    "?view=operations&operation_id=op-precheck-1",
  );
  expect(storageSet).not.toHaveBeenCalled();
});

test("restored session bootstraps csrf before submitting host precheck", async () => {
  const user = userEvent.setup();
  const storageSet = vi.spyOn(Storage.prototype, "setItem");
  const fetchMock = vi.fn(
    async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url === "/api/v1/session") {
        return jsonResponse(operatorSessionPayload);
      }
      if (url === "/api/v1/health/ready") {
        return jsonResponse(readyPayload);
      }
      if (url === "/api/v1/capabilities") {
        return jsonResponse(
          capabilitiesPayload([
            "operation.read",
            "workflow.execute.maintenance-host",
          ]),
        );
      }
      if (url === "/api/v1/session/csrf") {
        return jsonResponse({
          subject: operatorSessionPayload.subject,
          csrf: "restored-csrf-value",
          expires_at: "2026-06-21T15:00:00Z",
        });
      }
      if (url === "/api/v1/workflow-definitions?limit=50") {
        return jsonResponse(workflowDefinitionsPayload());
      }
      if (url === "/api/v1/operations") {
        const headers = init?.headers as Record<string, string>;
        expect(init?.method).toBe("POST");
        expect(headers["x-csrf-token"]).toBe("restored-csrf-value");
        expect(headers["idempotency-key"]).toEqual(expect.any(String));
        return jsonResponse({ operation_id: "op-precheck-1", status: "accepted" }, 202);
      }
      if (url === "/api/v1/operations/op-precheck-1") {
        return jsonResponse(operationDetailPayload({ status: "running" }));
      }
      throw new Error(`unexpected fetch ${url}`);
    },
  );
  vi.stubGlobal("fetch", fetchMock);

  render(<App />);

  await waitFor(() => {
    expect(
      fetchMock.mock.calls.some(([input]) => String(input) === "/api/v1/session/csrf"),
    ).toBe(true);
  });
  await user.type(await screen.findByLabelText("Хост"), "compute-a");
  fireEvent.change(screen.getByLabelText("Причина"), {
    target: { value: "Плановое обслуживание" },
  });
  await user.click(screen.getByRole("button", { name: "Запустить precheck" }));

  expect(await screen.findByText("Статус: running")).toBeInTheDocument();
  expect(storageSet).not.toHaveBeenCalled();
});

test("operation detail route renders timeline without direct OpenStack calls", async () => {
  window.history.replaceState(
    {},
    "",
    "/?view=operations&operation_id=op-precheck-1",
  );
  const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
    const url = String(input);
    if (url === "/api/v1/session") {
      return jsonResponse(operatorSessionPayload);
    }
    if (url === "/api/v1/health/ready") {
      return jsonResponse(readyPayload);
    }
    if (url === "/api/v1/capabilities") {
      return jsonResponse(capabilitiesPayload(["operation.read"]));
    }
    if (url === "/api/v1/workflow-definitions?limit=50") {
      return jsonResponse(workflowDefinitionsPayload());
    }
    if (url === "/api/v1/operations/op-precheck-1") {
      return jsonResponse(operationDetailPayload());
    }
    throw new Error(`unexpected fetch ${url}`);
  });
  vi.stubGlobal("fetch", fetchMock);

  render(<App />);

  const timeline = await screen.findByLabelText("Timeline операции");
  expect(screen.getByText("Операция op-precheck-1")).toBeInTheDocument();
  expect(screen.getByText("Correlation: op-precheck-1")).toBeInTheDocument();
  expect(screen.getByText("Mistral execution: -")).toBeInTheDocument();
  expect(within(timeline).getByText("Operation accepted")).toBeInTheDocument();
  expect(
    screen.getByRole("button", { name: "Запросить отмену" }),
  ).toBeDisabled();
  expect(
    fetchMock.mock.calls.some(([input]) => String(input).includes("openstack")),
  ).toBe(false);
});

test("group list renders loading, empty and error states", async () => {
  let resolveGroups: (response: ReturnType<typeof jsonResponse>) => void = () =>
    undefined;
  const groupsPromise = new Promise<ReturnType<typeof jsonResponse>>(
    (resolve) => {
      resolveGroups = resolve;
    },
  );
  const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
    const url = String(input);
    if (url === "/api/v1/session") {
      return jsonResponse(operatorSessionPayload);
    }
    if (url === "/api/v1/health/ready") {
      return jsonResponse(readyPayload);
    }
    if (url === "/api/v1/capabilities") {
      return jsonResponse(capabilitiesPayload(["group.read"]));
    }
    if (url === "/api/v1/groups?limit=50") {
      return groupsPromise;
    }
    throw new Error(`unexpected fetch ${url}`);
  });
  vi.stubGlobal("fetch", fetchMock);

  render(<App />);

  expect(await screen.findByLabelText("Загрузка групп")).toBeInTheDocument();
  resolveGroups(jsonResponse(groupListPayload([])));
  expect(await screen.findByText("Группы не найдены.")).toBeInTheDocument();

  cleanup();
  window.history.replaceState({}, "", "/");
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
        return jsonResponse(capabilitiesPayload(["group.read"]));
      }
      if (url === "/api/v1/groups?limit=50") {
        return jsonResponse({ error: { code: "groups_unavailable" } }, 503);
      }
      throw new Error(`unexpected fetch ${url}`);
    }),
  );

  render(<App />);

  expect(
    await screen.findByText("Список групп недоступен"),
  ).toBeInTheDocument();
});

test("group detail shows owner, scope and revision", async () => {
  const user = userEvent.setup();
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
        return jsonResponse(capabilitiesPayload(["group.read"]));
      }
      if (url === "/api/v1/groups?limit=50") {
        return jsonResponse(groupListPayload([groupItem()]));
      }
      if (url === "/api/v1/groups/group-vm-prod") {
        return jsonResponse(groupItem());
      }
      if (url === "/api/v1/groups/group-vm-prod/members?limit=50") {
        return jsonResponse(groupMembersPayload());
      }
      throw new Error(`unexpected fetch ${url}`);
    }),
  );

  render(<App />);
  await user.click(await screen.findByRole("button", { name: "Prod VMs" }));

  const detail = await screen.findByLabelText("Детали группы");
  expect(within(detail).getByText("mock-user-operator")).toBeInTheDocument();
  expect(within(detail).getByText("project:project-0001")).toBeInTheDocument();
  expect(within(detail).getByText("3")).toBeInTheDocument();
});

test("member picker fetches a bounded paginated inventory page", async () => {
  window.history.replaceState({}, "", "/?view=groups&group_id=group-vm-prod");
  const user = userEvent.setup();
  const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
    const url = String(input);
    if (url === "/api/v1/session") {
      return jsonResponse(operatorSessionPayload);
    }
    if (url === "/api/v1/health/ready") {
      return jsonResponse(readyPayload);
    }
    if (url === "/api/v1/capabilities") {
      return jsonResponse(
        capabilitiesPayload(["group.read", "group.manage", "instance.read"]),
      );
    }
    if (url === "/api/v1/groups?limit=50") {
      return jsonResponse(groupListPayload([groupItem()]));
    }
    if (url === "/api/v1/groups/group-vm-prod") {
      return jsonResponse(groupItem());
    }
    if (url === "/api/v1/groups/group-vm-prod/members?limit=50") {
      return jsonResponse(groupMembersPayload());
    }
    if (url === "/api/v1/instances?limit=50&sort=name.asc&q=vm-candidate") {
      return jsonResponse(
        inventoryPage([instanceItem({ name: "vm-candidate" })]),
      );
    }
    throw new Error(`unexpected fetch ${url}`);
  });
  vi.stubGlobal("fetch", fetchMock);

  render(<App />);
  await user.type(
    await screen.findByLabelText("Поиск ресурсов"),
    "vm-candidate",
  );
  await user.click(screen.getByRole("button", { name: "Найти ВМ" }));

  expect(await screen.findByText("vm-candidate")).toBeInTheDocument();
  const inventoryUrls = fetchMock.mock.calls
    .map(([input]) => String(input))
    .filter((url) => url.startsWith("/api/v1/instances?"));
  expect(inventoryUrls).toEqual([
    "/api/v1/instances?limit=50&sort=name.asc&q=vm-candidate",
  ]);
});

test("dynamic preview renders validation errors and bounded preview rows", async () => {
  window.history.replaceState({}, "", "/?view=groups&group_id=group-dynamic");
  const user = userEvent.setup();
  const fetchMock = vi.fn(
    async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url === "/api/v1/session") {
        return jsonResponse(operatorSessionPayload);
      }
      if (url === "/api/v1/health/ready") {
        return jsonResponse(readyPayload);
      }
      if (url === "/api/v1/capabilities") {
        return jsonResponse(
          capabilitiesPayload(["group.read", "instance.read"]),
        );
      }
      if (url === "/api/v1/groups?limit=50") {
        return jsonResponse(
          groupListPayload([
            groupItem({
              group_id: "group-dynamic",
              name: "Dynamic active VMs",
              membership_mode: "dynamic",
              rule_body_json: {
                field: "status",
                operator: "eq",
                value: "ACTIVE",
              },
            }),
          ]),
        );
      }
      if (url === "/api/v1/groups/group-dynamic") {
        return jsonResponse(
          groupItem({
            group_id: "group-dynamic",
            name: "Dynamic active VMs",
            membership_mode: "dynamic",
            rule_body_json: {
              field: "status",
              operator: "eq",
              value: "ACTIVE",
            },
          }),
        );
      }
      if (url === "/api/v1/groups/group-dynamic/members?limit=50") {
        return jsonResponse(groupMembersPayload());
      }
      if (url === "/api/v1/groups/group-dynamic/preview") {
        const body = JSON.parse(String(init?.body));
        if (body.rule.value === "ERROR") {
          return jsonResponse(
            {
              error: {
                code: "invalid_rule_value",
                message: "Правило группы отклонено",
              },
            },
            400,
          );
        }
        expect(body.limit).toBe(50);
        return jsonResponse(
          groupPreviewPayload([instanceItem({ name: "vm-preview" })], {
            count_estimate: 2,
            warnings: ["preview_truncated"],
          }),
        );
      }
      throw new Error(`unexpected fetch ${url}`);
    },
  );
  vi.stubGlobal("fetch", fetchMock);

  render(<App />);

  const ruleInput = await screen.findByLabelText("Правило preview");
  fireEvent.change(ruleInput, {
    target: { value: '{"field":"status","operator":"eq","value":"ERROR"}' },
  });
  await user.click(screen.getByRole("button", { name: "Предпросмотр" }));
  expect(
    await screen.findByText("Правило группы отклонено"),
  ).toBeInTheDocument();

  fireEvent.change(ruleInput, {
    target: { value: '{"field":"status","operator":"eq","value":"ACTIVE"}' },
  });
  await user.click(screen.getByRole("button", { name: "Предпросмотр" }));

  expect(await screen.findByText("vm-preview")).toBeInTheDocument();
  expect(screen.getByText("Ограничение: 50")).toBeInTheDocument();
  expect(screen.getByText("preview_truncated")).toBeInTheDocument();
});

test("inventory group filter round trips through URL and BFF request", async () => {
  window.history.replaceState(
    {},
    "",
    "/?view=instances&group_id=group-vm-prod",
  );
  const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
    const url = String(input);
    if (url === "/api/v1/session") {
      return jsonResponse(operatorSessionPayload);
    }
    if (url === "/api/v1/health/ready") {
      return jsonResponse(readyPayload);
    }
    if (url === "/api/v1/capabilities") {
      return jsonResponse(capabilitiesPayload(["instance.read", "group.read"]));
    }
    if (url === "/api/v1/inventory/modules") {
      return jsonResponse(inventoryModulesPayload());
    }
    if (
      url === "/api/v1/instances?limit=50&sort=name.asc&group_id=group-vm-prod"
    ) {
      return jsonResponse(
        inventoryPage([instanceItem({ name: "vm-in-group" })]),
      );
    }
    throw new Error(`unexpected fetch ${url}`);
  });
  vi.stubGlobal("fetch", fetchMock);

  render(<App />);

  expect(await screen.findByText("vm-in-group")).toBeInTheDocument();
  expect(window.location.search).toBe("?view=instances&group_id=group-vm-prod");
  expect(fetchMock).toHaveBeenCalledWith(
    "/api/v1/instances?limit=50&sort=name.asc&group_id=group-vm-prod",
    expect.objectContaining({ signal: expect.any(Object) }),
  );
});

test("instances page fetches server-side page from BFF with URL filters", async () => {
  window.history.replaceState(
    {},
    "",
    "/?view=instances&status=ACTIVE&sort=name.asc",
  );
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
    if (url === "/api/v1/session/csrf") {
      return jsonResponse({
        subject: operatorSessionPayload.subject,
        csrf: "restored-csrf-value",
        expires_at: "2026-06-21T15:00:00Z",
      });
    }
    if (url === "/api/v1/inventory/modules") {
      return jsonResponse(inventoryModulesPayload());
    }
    if (url === "/api/v1/instances?limit=50&sort=name.asc&status=ACTIVE") {
      return jsonResponse(
        inventoryPage([instanceItem({ name: "vm-from-server" })]),
      );
    }
    throw new Error(`unexpected fetch ${url}`);
  });
  vi.stubGlobal("fetch", fetchMock);

  render(<App />);

  expect(await screen.findByText("vm-from-server")).toBeInTheDocument();
  expect(screen.queryByText("vm-not-returned")).not.toBeInTheDocument();
  await waitFor(() => {
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/v1/instances?limit=50&sort=name.asc&status=ACTIVE",
      expect.objectContaining({ signal: expect.any(Object) }),
    );
  });
});

test("inventory navigation and table render outside constrained status layout", async () => {
  const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
    const url = String(input);
    if (url === "/api/v1/session") {
      return jsonResponse(operatorSessionPayload);
    }
    if (url === "/api/v1/health/ready") {
      return jsonResponse(readyPayload);
    }
    if (url === "/api/v1/capabilities") {
      return jsonResponse(
        capabilitiesPayload(["instance.read", "hypervisor.read"]),
      );
    }
    if (url === "/api/v1/instances?limit=50&sort=name.asc") {
      return jsonResponse(
        inventoryPage([instanceItem({ name: "vm-wide-screen" })]),
      );
    }
    throw new Error(`unexpected fetch ${url}`);
  });
  vi.stubGlobal("fetch", fetchMock);

  render(<App />);

  const table = await screen.findByRole("table", { name: "Таблица ВМ" });
  const inventorySection = table.closest("section[aria-label='Инвентарь']");

  expect(inventorySection).not.toBeNull();
  expect(inventorySection?.closest(".cloud-ui-layout")).toBeNull();
  expect(
    within(inventorySection as HTMLElement).getByRole("link", { name: "ВМ" }),
  ).toBeInTheDocument();
  expect(
    within(inventorySection as HTMLElement).getByRole("link", {
      name: "Гипервизоры",
    }),
  ).toBeInTheDocument();
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
      if (url === "/api/v1/hypervisors?limit=50&sort=host_name.asc") {
        return jsonResponse(
          inventoryPage(
            [hypervisorItem({ host_name: "compute-stale" })],
            true,
            true,
          ),
        );
      }
      throw new Error(`unexpected fetch ${url}`);
    }),
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
      if (url === "/api/v1/instances?limit=50&sort=name.asc") {
        return jsonResponse(
          inventoryPage([instanceItem({ name: "vm-storage-check" })]),
        );
      }
      throw new Error(`unexpected fetch ${url}`);
    }),
  );

  render(<App />);

  expect(await screen.findByText("vm-storage-check")).toBeInTheDocument();
  expect(storageSet).not.toHaveBeenCalled();
});

test("inventory requests clamp limit and exclude unsupported URL view state", async () => {
  window.history.replaceState(
    {},
    "",
    "/?view=instances&status=ACTIVE&sort=name.asc&limit=999&cursor=cursor-1&columns=name,host_name&density=compact&rows=copied&unsupported=value",
  );
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
    if (url === "/api/v1/inventory/modules") {
      return jsonResponse(inventoryModulesPayload());
    }
    if (
      url ===
      "/api/v1/instances?limit=200&cursor=cursor-1&sort=name.asc&status=ACTIVE"
    ) {
      return jsonResponse(
        inventoryPage([instanceItem({ name: "vm-sanitized" })]),
      );
    }
    throw new Error(`unexpected fetch ${url}`);
  });
  vi.stubGlobal("fetch", fetchMock);

  render(<App />);

  expect(await screen.findByText("vm-sanitized")).toBeInTheDocument();
  expect(fetchMock).toHaveBeenCalledWith(
    "/api/v1/instances?limit=200&cursor=cursor-1&sort=name.asc&status=ACTIVE",
    expect.objectContaining({ signal: expect.any(Object) }),
  );
});

test("inventory requests default malformed and unsupported instance sort values", async () => {
  window.history.replaceState(
    {},
    "",
    "/?view=instances&sort=project_id.sideways",
  );
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
    if (url === "/api/v1/inventory/modules") {
      return jsonResponse(inventoryModulesPayload());
    }
    if (url === "/api/v1/instances?limit=50&sort=name.asc") {
      return jsonResponse(
        inventoryPage([instanceItem({ name: "vm-default-sort" })]),
      );
    }
    throw new Error(`unexpected fetch ${url}`);
  });
  vi.stubGlobal("fetch", fetchMock);

  render(<App />);

  expect(await screen.findByText("vm-default-sort")).toBeInTheDocument();
  expect(fetchMock).toHaveBeenCalledWith(
    "/api/v1/instances?limit=50&sort=name.asc",
    expect.objectContaining({ signal: expect.any(Object) }),
  );
});

test("inventory requests default unsupported hypervisor sort values", async () => {
  window.history.replaceState(
    {},
    "",
    "/?view=hypervisors&sort=running_vms.desc",
  );
  const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
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
    if (url === "/api/v1/inventory/modules") {
      return jsonResponse(inventoryModulesPayload());
    }
    if (url === "/api/v1/hypervisors?limit=50&sort=host_name.asc") {
      return jsonResponse(
        inventoryPage([hypervisorItem({ host_name: "compute-default-sort" })]),
      );
    }
    throw new Error(`unexpected fetch ${url}`);
  });
  vi.stubGlobal("fetch", fetchMock);

  render(<App />);

  expect(await screen.findByText("compute-default-sort")).toBeInTheDocument();
  expect(fetchMock).toHaveBeenCalledWith(
    "/api/v1/hypervisors?limit=50&sort=host_name.asc",
    expect.objectContaining({ signal: expect.any(Object) }),
  );
});

test("aborts superseded inventory requests when changing inventory view", async () => {
  window.history.replaceState({}, "", "/?view=instances");
  const inventorySignals: Array<AbortSignal | null> = [];
  const fetchMock = vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input);
    if (url === "/api/v1/session") {
      return Promise.resolve(jsonResponse(operatorSessionPayload));
    }
    if (url === "/api/v1/health/ready") {
      return Promise.resolve(jsonResponse(readyPayload));
    }
    if (url === "/api/v1/capabilities") {
      return Promise.resolve(
        jsonResponse(capabilitiesPayload(["instance.read", "hypervisor.read"])),
      );
    }
    if (url === "/api/v1/inventory/modules") {
      return Promise.resolve(jsonResponse(inventoryModulesPayload()));
    }
    if (url === "/api/v1/instances?limit=50&sort=name.asc") {
      inventorySignals.push(init?.signal ?? null);
      return new Promise(() => undefined);
    }
    if (url === "/api/v1/hypervisors?limit=50&sort=host_name.asc") {
      return Promise.resolve(
        jsonResponse(
          inventoryPage([hypervisorItem({ host_name: "compute-after-abort" })]),
        ),
      );
    }
    throw new Error(`unexpected fetch ${url}`);
  });
  vi.stubGlobal("fetch", fetchMock);
  const user = userEvent.setup();

  render(<App />);

  const inventoryNav = await screen.findByRole("navigation", {
    name: "Разделы инвентаря",
  });
  await user.click(within(inventoryNav).getByRole("link", { name: "Гипервизоры" }));

  expect(await screen.findByText("compute-after-abort")).toBeInTheDocument();
  expect(inventorySignals[0]).not.toBeNull();
  expect(inventorySignals[0]?.aborted).toBe(true);
});

test("next cursor pagination updates URL and fetches one next BFF page", async () => {
  window.history.replaceState({}, "", "/?view=instances&sort=name.asc");
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
    if (url === "/api/v1/inventory/modules") {
      return jsonResponse(inventoryModulesPayload());
    }
    if (url === "/api/v1/instances?limit=50&sort=name.asc") {
      return jsonResponse(
        inventoryPageWithNextCursor(
          [instanceItem({ name: "vm-page-1" })],
          "cursor-next",
        ),
      );
    }
    if (url === "/api/v1/instances?limit=50&cursor=cursor-next&sort=name.asc") {
      return jsonResponse(inventoryPage([instanceItem({ name: "vm-page-2" })]));
    }
    throw new Error(`unexpected fetch ${url}`);
  });
  vi.stubGlobal("fetch", fetchMock);
  const user = userEvent.setup();

  render(<App />);

  expect(await screen.findByText("vm-page-1")).toBeInTheDocument();
  await user.click(screen.getByRole("button", { name: "Следующая страница" }));

  expect(await screen.findByText("vm-page-2")).toBeInTheDocument();
  expect(window.location.search).toBe(
    "?view=instances&sort=name.asc&cursor=cursor-next",
  );
  const instanceFetches = fetchMock.mock.calls.filter(([input]) =>
    String(input).startsWith("/api/v1/instances?"),
  );
  expect(instanceFetches).toHaveLength(2);
  expect(instanceFetches[1]).toEqual([
    "/api/v1/instances?limit=50&cursor=cursor-next&sort=name.asc",
    expect.objectContaining({ signal: expect.any(Object) }),
  ]);
});

test("columns and density round trip through URL and control visible table state", async () => {
  window.history.replaceState(
    {},
    "",
    "/?view=instances&columns=name,host_name&density=compact",
  );
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
        return jsonResponse(
          capabilitiesPayload(["instance.read", "hypervisor.read"]),
        );
      }
      if (url === "/api/v1/inventory/modules") {
        return jsonResponse(inventoryModulesPayload());
      }
      if (url === "/api/v1/instances?limit=50&sort=name.asc") {
        return jsonResponse(
          inventoryPage([instanceItem({ name: "vm-url-view" })]),
        );
      }
      throw new Error(`unexpected fetch ${url}`);
    }),
  );

  render(<App />);

  const table = await screen.findByRole("table", { name: "Таблица ВМ" });
  expect(within(table).getByText("Имя")).toBeInTheDocument();
  expect(within(table).getByText("Узел")).toBeInTheDocument();
  expect(within(table).queryByText("Проект")).not.toBeInTheDocument();
  expect(table).toHaveAttribute("data-density", "compact");
  expect(window.location.search).toBe(
    "?view=instances&columns=name,host_name&density=compact",
  );
});

test("renders disabled inventory modules from BFF instead of broken links", async () => {
  const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
    const url = String(input);
    if (url === "/api/v1/session") {
      return jsonResponse(operatorSessionPayload);
    }
    if (url === "/api/v1/health/ready") {
      return jsonResponse(readyPayload);
    }
    if (url === "/api/v1/capabilities") {
      return jsonResponse(
        capabilitiesPayload(["instance.read", "hypervisor.read"]),
      );
    }
    if (url === "/api/v1/inventory/modules") {
      return jsonResponse(inventoryModulesPayload());
    }
    if (url === "/api/v1/instances?limit=50&sort=name.asc") {
      return jsonResponse(inventoryPage([]));
    }
    throw new Error(`unexpected fetch ${url}`);
  });
  vi.stubGlobal("fetch", fetchMock);

  render(<App />);

  expect(await screen.findByText("Сервисы Nova Compute")).toBeInTheDocument();
  expect(screen.getByText("Топология")).toBeInTheDocument();
  expect(screen.getByText("Емкость")).toBeInTheDocument();
  expect(screen.getAllByText("Отключено")).toHaveLength(3);
  expect(
    screen.queryByRole("link", { name: "Сервисы Nova Compute" }),
  ).not.toBeInTheDocument();
  expect(fetchMock).toHaveBeenCalledWith("/api/v1/inventory/modules");
});

test("links instance host and hypervisor relationships to filtered hypervisors view", async () => {
  window.history.replaceState({}, "", "/?view=instances");
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
        return jsonResponse(
          capabilitiesPayload(["instance.read", "hypervisor.read"]),
        );
      }
      if (url === "/api/v1/inventory/modules") {
        return jsonResponse(inventoryModulesPayload());
      }
      if (url === "/api/v1/instances?limit=50&sort=name.asc") {
        return jsonResponse(
          inventoryPage([
            instanceItem({
              name: "vm-linked",
              host_name: "compute-a",
              hypervisor_id: "hypervisor-0001",
            }),
          ]),
        );
      }
      throw new Error(`unexpected fetch ${url}`);
    }),
  );

  render(<App />);

  expect(await screen.findByText("vm-linked")).toBeInTheDocument();
  expect(screen.getByRole("link", { name: "compute-a" })).toHaveAttribute(
    "href",
    "?view=hypervisors&host_name=compute-a",
  );
  expect(screen.getByRole("link", { name: "hypervisor-0001" })).toHaveAttribute(
    "href",
    "?view=hypervisors&q=hypervisor-0001",
  );
});

test("links hypervisor host and running VM count to filtered instances view", async () => {
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
        return jsonResponse(
          capabilitiesPayload(["instance.read", "hypervisor.read"]),
        );
      }
      if (url === "/api/v1/inventory/modules") {
        return jsonResponse(inventoryModulesPayload());
      }
      if (url === "/api/v1/hypervisors?limit=50&sort=host_name.asc") {
        return jsonResponse(
          inventoryPage([
            hypervisorItem({ host_name: "compute-a", running_vms: 7 }),
          ]),
        );
      }
      throw new Error(`unexpected fetch ${url}`);
    }),
  );

  render(<App />);

  expect(await screen.findByText("compute-a")).toBeInTheDocument();
  expect(screen.getByRole("link", { name: "compute-a" })).toHaveAttribute(
    "href",
    "?view=instances&host_name=compute-a",
  );
  expect(screen.getByRole("link", { name: "7 ВМ" })).toHaveAttribute(
    "href",
    "?view=instances&host_name=compute-a",
  );
});

test("renders instance actions only for relevant capabilities", async () => {
  window.history.replaceState({}, "", "/?view=instances");
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
      if (url === "/api/v1/inventory/modules") {
        return jsonResponse(inventoryModulesPayload());
      }
      if (url === "/api/v1/instances?limit=50&sort=name.asc") {
        return jsonResponse(
          inventoryPage([instanceItem({ name: "vm-no-action" })]),
        );
      }
      throw new Error(`unexpected fetch ${url}`);
    }),
  );

  render(<App />);

  expect(await screen.findByText("vm-no-action")).toBeInTheDocument();
  expect(screen.queryByText("Действия")).not.toBeInTheDocument();
  expect(
    screen.queryByRole("button", { name: "Обновить vm-no-action" }),
  ).not.toBeInTheDocument();
});

test("renders allowed instance refresh affordance disabled until refresh contract exists", async () => {
  window.history.replaceState({}, "", "/?view=instances");
  const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
    const url = String(input);
    if (url === "/api/v1/session") {
      return jsonResponse(operatorSessionPayload);
    }
    if (url === "/api/v1/health/ready") {
      return jsonResponse(readyPayload);
    }
    if (url === "/api/v1/capabilities") {
      return jsonResponse(
        capabilitiesPayload(["instance.read", "instance.refresh"]),
      );
    }
    if (url === "/api/v1/inventory/modules") {
      return jsonResponse(inventoryModulesPayload());
    }
    if (url === "/api/v1/instances?limit=50&sort=name.asc") {
      return jsonResponse(inventoryPage([instanceItem({ name: "vm-action" })]));
    }
    throw new Error(`unexpected fetch ${url}`);
  });
  vi.stubGlobal("fetch", fetchMock);
  const user = userEvent.setup();

  render(<App />);

  expect(await screen.findByText("vm-action")).toBeInTheDocument();
  expect(screen.getByText("Действия")).toBeInTheDocument();
  const refreshButton = screen.getByRole("button", {
    name: "Обновить vm-action",
  });

  expect(refreshButton).toBeDisabled();
  expect(refreshButton).not.toHaveAttribute("title");
  await user.click(refreshButton);
  expect(fetchMock).not.toHaveBeenCalledWith(
    "/api/v1/instances/synthetic/RegionOne/instance-0001/refresh",
    expect.anything(),
  );
});
