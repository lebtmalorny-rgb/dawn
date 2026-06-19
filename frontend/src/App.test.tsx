import { render, screen } from "@testing-library/react";
import { beforeEach, expect, test, vi } from "vitest";

import { App } from "./App";

beforeEach(() => {
  vi.unstubAllGlobals();
});

test("renders API readiness ok with dependency names", async () => {
  vi.stubGlobal(
    "fetch",
    vi.fn(async () => ({
      ok: true,
      status: 200,
      json: async () => ({
        status: "ok",
        dependencies: {
          database: { status: "ok", detail: "reachable" },
          rabbitmq: { status: "ok", detail: "reachable" }
        }
      })
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
    vi.fn(async () => ({
      ok: false,
      status: 503,
      json: async () => ({
        status: "degraded",
        dependencies: {
          database: { status: "ok", detail: "reachable" },
          rabbitmq: { status: "down", detail: "connection refused" }
        }
      })
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
    vi.fn(async () => ({
      ok: true,
      status: 200,
      json: async () => ({
        status: "ok",
        dependencies: {
          database: null
        }
      })
    }))
  );

  render(<App />);

  expect(await screen.findByText("Готовность API недоступна")).toBeInTheDocument();
});

test("renders safe error when readiness fetch fails", async () => {
  vi.stubGlobal(
    "fetch",
    vi.fn(async () => {
      throw new Error("network failure");
    })
  );

  render(<App />);

  expect(await screen.findByText("Готовность API недоступна")).toBeInTheDocument();
});
