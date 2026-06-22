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
          dependencies: {},
        };
      },
    })),
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
      if (url === "/api/v1/instances?limit=50&sort=name.asc") {
        return jsonResponse(inventoryPage([]));
      }
      throw new Error(`unexpected fetch ${url}`);
    }),
  );

  render(<App />);

  expect(await screen.findByText("ВМ")).toBeInTheDocument();
  expect(screen.queryByText("Гипервизоры")).not.toBeInTheDocument();
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

  expect(
    await screen.findByRole("link", { name: "Группы" }),
  ).toBeInTheDocument();
  expect(await screen.findByText("Prod VMs")).toBeInTheDocument();
  expect(screen.queryByRole("link", { name: "ВМ" })).not.toBeInTheDocument();
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

  await user.click(await screen.findByRole("link", { name: "Гипервизоры" }));

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
  expect(fetchMock).toHaveBeenCalledTimes(6);
  expect(fetchMock).toHaveBeenCalledWith(
    "/api/v1/instances?limit=50&cursor=cursor-next&sort=name.asc",
    expect.objectContaining({ signal: expect.any(Object) }),
  );
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
