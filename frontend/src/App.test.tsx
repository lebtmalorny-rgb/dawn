import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, expect, test, vi } from "vitest";

import { App } from "./App";

beforeEach(() => {
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
          return {
            subject: {
              subject_id: "mock-user-operator",
              display_name: "Оператор облака",
              subject_type: "human",
              roles: ["cloud_operator"]
            }
          };
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
          return {
            subject: {
              subject_id: "mock-user-operator",
              display_name: "Оператор облака",
              subject_type: "human",
              roles: ["cloud_operator"]
            }
          };
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
          return {
            subject: {
              subject_id: "mock-user-operator",
              display_name: "Оператор облака",
              subject_type: "human",
              roles: ["cloud_operator"]
            }
          };
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
          json: async () => ({
            subject: {
              subject_id: "mock-user-operator",
              display_name: "Оператор облака",
              subject_type: "human",
              roles: ["cloud_operator"]
            }
          })
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
