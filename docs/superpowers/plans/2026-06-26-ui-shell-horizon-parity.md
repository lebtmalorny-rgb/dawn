# UI Shell And Horizon Parity Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the first UI slice from the approved DKB-aware vSphere-informed design: a modular Cloud UI shell with object navigation, bottom work panel, Horizon parity registry and existing views re-homed without changing backend behavior.

**Architecture:** Keep the backend contracts unchanged. Split the current frontend monolith by introducing typed navigation/parity registries and shell components, then wrap existing inventory/groups/operations/audit work areas in the new shell. Use capability data only for UX visibility; backend authorization remains authoritative.

**Tech Stack:** React 19, TypeScript, Vite, PatternFly 6, Vitest, React Testing Library. This slice does not require new runtime infrastructure. React Router, TanStack Query and TanStack Table remain planned follow-up dependencies unless this slice proves the shell cannot remain maintainable without them.

---

## Scope

Implement this slice only:

- vSphere-informed top chrome, object navigator, object workbench header/tabs and bottom work panel;
- static Horizon parity registry and module/status registry;
- no storage of vSphere screenshots, credentials, cookies or session artifacts;
- no new backend endpoints;
- no production auth flow changes;
- no broad Horizon module implementation yet.

Do not implement:

- full Horizon parity workflows;
- direct vSphere integration;
- real Keycloak/LDAP/AD/FreeIPA login;
- WebSocket or new real-time backend behavior;
- table package replacement.

## File Structure

Create focused frontend modules:

- `frontend/src/navigation/types.ts`  
  Shared UI registry types for modules, tabs, parity rows and shell context.
- `frontend/src/navigation/horizonParity.ts`  
  Static Horizon parity rows with implementation statuses and DKB notes.
- `frontend/src/navigation/cloudModules.ts`  
  High-level navigation groups for Inventory, Operations, Administration and Audit/DKB.
- `frontend/src/shell/CloudShell.tsx`  
  Layout component for top chrome, left navigator, object header, content and bottom work panel.
- `frontend/src/shell/CloudShell.test.tsx`  
  Shell rendering and accessibility tests.
- `frontend/src/shell/BottomWorkPanel.tsx`  
  Recent Tasks / Alarms / Audit Tail / Approvals panel.
- `frontend/src/shell/ObjectNavigator.tsx`  
  Left mode-aware tree placeholder, backed by static module registry for this slice.
- `frontend/src/shell/TopChrome.tsx`  
  Product menu, global search, refresh, scope/session/policy display.
- `frontend/src/shell/objectWorkbench.ts`  
  Helper that derives object title/tabs from active view and capabilities.

Modify existing files:

- `frontend/src/App.tsx`  
  Keep existing data loading and work-area functions, but render them inside `CloudShell`.
- `frontend/src/App.test.tsx`  
  Add tests for shell regions, no token storage, capability-aware routes and bottom panel.
- `frontend/src/styles.css`  
  Move shell-specific styles to predictable class names while keeping current table styles.
- `docs/generated/risk-register.md`  
  Add a risk row that UI shell/parity registry must not be mistaken for implemented Horizon parity.
- `docs/11_DKB_TRACEABILITY.md`  
  Add a short UI design/first-slice note only if implementation changes visible auth/session/audit behavior. If this slice stays layout-only, record that DKB posture is unchanged in the final report instead of editing traceability.

## Task 1: Navigation And Horizon Parity Registry

**Files:**

- Create: `frontend/src/navigation/types.ts`
- Create: `frontend/src/navigation/horizonParity.ts`
- Create: `frontend/src/navigation/cloudModules.ts`
- Test: `frontend/src/App.test.tsx`

- [ ] **Step 1: Write failing registry tests**

Add these tests near the existing navigation tests in `frontend/src/App.test.tsx`:

```tsx
import { CLOUD_MODULE_GROUPS } from "./navigation/cloudModules";
import { HORIZON_PARITY_ROWS } from "./navigation/horizonParity";

test("cloud module registry exposes the agreed shell groups", () => {
  expect(CLOUD_MODULE_GROUPS.map((group) => group.key)).toEqual([
    "inventory",
    "operations",
    "administration",
    "audit_dkb",
  ]);
  expect(
    CLOUD_MODULE_GROUPS.flatMap((group) => group.items).map((item) => item.key),
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
        horizonArea: "Project / Compute / Instances",
        cloudUiModule: "Inventory / Instances",
        requiredCapability: "instance.read",
        status: "implemented",
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
    HORIZON_PARITY_ROWS.every((row) => row.auditEvent.length > 0 && row.dkbNotes.length > 0),
  ).toBe(true);
});
```

- [ ] **Step 2: Run tests and verify they fail**

Run:

```bash
cd frontend
npm test -- --run src/App.test.tsx
```

Expected: fail with unresolved imports for `./navigation/cloudModules` and
`./navigation/horizonParity`.

- [ ] **Step 3: Add shared navigation types**

Create `frontend/src/navigation/types.ts`:

```ts
export type CloudModuleStatus = "implemented" | "planned" | "disabled";

export type CloudModuleItem = {
  key: string;
  title: string;
  view: string;
  requiredCapability: string | null;
  status: CloudModuleStatus;
  reason: string;
};

export type CloudModuleGroup = {
  key: "inventory" | "operations" | "administration" | "audit_dkb";
  title: string;
  items: CloudModuleItem[];
};

export type HorizonParityStatus =
  | "implemented"
  | "planned"
  | "blocked_external_evidence"
  | "out_of_scope";

export type HorizonParityRow = {
  horizonArea: string;
  cloudUiModule: string;
  requiredCapability: string;
  openStackAuthority: string;
  auditEvent: string;
  dkbNotes: string;
  status: HorizonParityStatus;
};

export type ShellContext = {
  productTitle: string;
  searchPlaceholder: string;
  scopeLabel: string;
  identityLabel: string;
  policyRevision: string;
  freshnessLabel: string;
};
```

- [ ] **Step 4: Add module registry**

Create `frontend/src/navigation/cloudModules.ts`:

```ts
import type { CloudModuleGroup } from "./types";

export const CLOUD_MODULE_GROUPS: CloudModuleGroup[] = [
  {
    key: "inventory",
    title: "Инвентарь",
    items: [
      {
        key: "instances",
        title: "ВМ",
        view: "instances",
        requiredCapability: "instance.read",
        status: "implemented",
        reason: "E04 inventory list exists",
      },
      {
        key: "hypervisors",
        title: "Гипервизоры",
        view: "hypervisors",
        requiredCapability: "hypervisor.read",
        status: "implemented",
        reason: "E04 hypervisor list exists",
      },
      {
        key: "networks",
        title: "Сети",
        view: "networks",
        requiredCapability: "network.read",
        status: "planned",
        reason: "Horizon parity row, backend adapter not enabled in this slice",
      },
      {
        key: "volumes",
        title: "Тома",
        view: "volumes",
        requiredCapability: "volume.read",
        status: "planned",
        reason: "Horizon parity row, backend adapter not enabled in this slice",
      },
    ],
  },
  {
    key: "operations",
    title: "Операции",
    items: [
      {
        key: "mistral_operations",
        title: "Mistral",
        view: "operations",
        requiredCapability: "operation.read",
        status: "implemented",
        reason: "E06 operation center foundation exists",
      },
      {
        key: "watcher",
        title: "Watcher",
        view: "watcher",
        requiredCapability: "operation.read",
        status: "planned",
        reason: "First-class module planned; direct action apply remains approval-gated",
      },
      {
        key: "masakari",
        title: "Masakari",
        view: "masakari",
        requiredCapability: "operation.read",
        status: "planned",
        reason: "First-class recovery module planned; no direct browser recovery",
      },
    ],
  },
  {
    key: "administration",
    title: "Администрирование",
    items: [
      {
        key: "identity",
        title: "Identity",
        view: "identity",
        requiredCapability: "role.manage",
        status: "planned",
        reason: "Requires IAM/Keystone federation implementation plan",
      },
      {
        key: "horizon_parity",
        title: "Horizon parity",
        view: "horizon-parity",
        requiredCapability: "role.manage",
        status: "planned",
        reason: "Coverage matrix in this slice; workflows implemented later",
      },
    ],
  },
  {
    key: "audit_dkb",
    title: "Аудит и ДКБ",
    items: [
      {
        key: "audit",
        title: "Аудит",
        view: "audit",
        requiredCapability: "audit.read",
        status: "implemented",
        reason: "E07 audit UI foundation exists",
      },
      {
        key: "dkb_evidence",
        title: "ДКБ evidence",
        view: "dkb-evidence",
        requiredCapability: "audit.read",
        status: "planned",
        reason: "Evidence view planned; current slice must not claim compliance",
      },
    ],
  },
];
```

- [ ] **Step 5: Add Horizon parity registry**

Create `frontend/src/navigation/horizonParity.ts`:

```ts
import type { HorizonParityRow } from "./types";

export const HORIZON_PARITY_ROWS: HorizonParityRow[] = [
  {
    horizonArea: "Project / Compute / Instances",
    cloudUiModule: "Inventory / Instances",
    requiredCapability: "instance.read",
    openStackAuthority: "Nova policy",
    auditEvent: "inventory.instance.read",
    dkbNotes: "Browser reads portal API only; backend enforces capability and OpenStack policy.",
    status: "implemented",
  },
  {
    horizonArea: "Project / Compute / Images",
    cloudUiModule: "Inventory / Images",
    requiredCapability: "image.read",
    openStackAuthority: "Glance policy",
    auditEvent: "inventory.image.read",
    dkbNotes: "Planned module; image actions require OpenAPI, audit and negative authorization tests.",
    status: "planned",
  },
  {
    horizonArea: "Project / Network / Routers",
    cloudUiModule: "Inventory / Networks",
    requiredCapability: "network.read",
    openStackAuthority: "Neutron policy",
    auditEvent: "inventory.network.read",
    dkbNotes: "Planned module; no direct Neutron calls from browser.",
    status: "planned",
  },
  {
    horizonArea: "Project / Volumes / Volumes",
    cloudUiModule: "Inventory / Volumes",
    requiredCapability: "volume.read",
    openStackAuthority: "Cinder policy",
    auditEvent: "inventory.volume.read",
    dkbNotes: "Planned module; no Cinder credential in browser.",
    status: "planned",
  },
  {
    horizonArea: "Admin / Identity / Users",
    cloudUiModule: "Administration / Identity",
    requiredCapability: "role.manage",
    openStackAuthority: "Keystone policy and corporate IAM",
    auditEvent: "identity.user.read",
    dkbNotes: "Requires SoD/IAM evidence; portal capability cannot expand Keystone authority.",
    status: "planned",
  },
  {
    horizonArea: "Admin / Compute / Host Aggregates",
    cloudUiModule: "Inventory / Host Aggregates",
    requiredCapability: "hypervisor.read",
    openStackAuthority: "Nova policy",
    auditEvent: "inventory.aggregate.read",
    dkbNotes: "Planned module; mutations require operation workflow and audit.",
    status: "planned",
  },
];
```

- [ ] **Step 6: Run tests and commit**

Run:

```bash
cd frontend
npm test -- --run src/App.test.tsx
npm run typecheck
```

Expected: tests pass, typecheck passes.

Commit:

```bash
git add frontend/src/navigation frontend/src/App.test.tsx
git commit -m "feat: add UI navigation parity registry"
```

## Task 2: Shell Components

**Files:**

- Create: `frontend/src/shell/TopChrome.tsx`
- Create: `frontend/src/shell/ObjectNavigator.tsx`
- Create: `frontend/src/shell/BottomWorkPanel.tsx`
- Create: `frontend/src/shell/CloudShell.tsx`
- Create: `frontend/src/shell/CloudShell.test.tsx`
- Modify: `frontend/src/styles.css`

- [ ] **Step 1: Write failing shell tests**

Create `frontend/src/shell/CloudShell.test.tsx`:

```tsx
import { render, screen, within } from "@testing-library/react";
import { describe, expect, test } from "vitest";

import { CloudShell } from "./CloudShell";

const shellContext = {
  productTitle: "Cloud UI",
  searchPlaceholder: "Search in all clouds, projects, hosts, VMs, operations",
  scopeLabel: "Scope: RegionOne / project-a",
  identityLabel: "operator@example",
  policyRevision: "Policy rev 42",
  freshnessLabel: "Observed 18:47 MSK",
};

describe("CloudShell", () => {
  test("renders vSphere-informed shell landmarks", () => {
    render(
      <CloudShell
        context={shellContext}
        activeView="instances"
        objectTitle="compute-03"
        objectType="Hypervisor"
        tabs={["Summary", "Monitor", "Configure", "Permissions", "VMs", "Operations", "Audit"]}
      >
        <section aria-label="Рабочая область">Instances table</section>
      </CloudShell>,
    );

    expect(screen.getByRole("banner")).toHaveTextContent("Cloud UI");
    expect(screen.getByRole("searchbox", { name: "Глобальный поиск" })).toHaveAttribute(
      "placeholder",
      shellContext.searchPlaceholder,
    );
    expect(screen.getByRole("navigation", { name: "Объекты облака" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "compute-03" })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "Summary" })).toHaveAttribute("aria-selected", "true");
    expect(screen.getByRole("region", { name: "Нижняя рабочая панель" })).toHaveTextContent(
      "Recent Tasks",
    );
    expect(screen.getByRole("region", { name: "Рабочая область" })).toHaveTextContent(
      "Instances table",
    );
  });

  test("bottom panel exposes operations, audit and approvals tabs", () => {
    render(
      <CloudShell
        context={shellContext}
        activeView="audit"
        objectTitle="Audit"
        objectType="Evidence"
        tabs={["Summary", "Audit"]}
      >
        <span>Audit content</span>
      </CloudShell>,
    );

    const bottomPanel = screen.getByRole("region", { name: "Нижняя рабочая панель" });
    expect(within(bottomPanel).getByRole("tab", { name: "Recent Tasks" })).toBeInTheDocument();
    expect(within(bottomPanel).getByRole("tab", { name: "Alarms" })).toBeInTheDocument();
    expect(within(bottomPanel).getByRole("tab", { name: "Audit Tail" })).toBeInTheDocument();
    expect(within(bottomPanel).getByRole("tab", { name: "Approvals" })).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run tests and verify they fail**

Run:

```bash
cd frontend
npm test -- --run src/shell/CloudShell.test.tsx
```

Expected: fail with unresolved `./CloudShell`.

- [ ] **Step 3: Add `TopChrome`**

Create `frontend/src/shell/TopChrome.tsx`:

```tsx
import type { ShellContext } from "../navigation/types";

type TopChromeProps = {
  context: ShellContext;
};

export function TopChrome({ context }: TopChromeProps) {
  return (
    <header className="cloud-ui-top-chrome" role="banner">
      <button className="cloud-ui-icon-button" type="button" aria-label="Меню продукта">
        ☰
      </button>
      <div className="cloud-ui-product-title">{context.productTitle}</div>
      <label className="cloud-ui-global-search">
        <span className="cloud-ui-sr-only">Глобальный поиск</span>
        <input
          aria-label="Глобальный поиск"
          type="search"
          placeholder={context.searchPlaceholder}
        />
      </label>
      <button className="cloud-ui-icon-button" type="button" aria-label="Обновить">
        ↻
      </button>
      <div className="cloud-ui-shell-meta">{context.scopeLabel}</div>
      <div className="cloud-ui-shell-meta">{context.policyRevision}</div>
      <div className="cloud-ui-shell-user">{context.identityLabel}</div>
    </header>
  );
}
```

- [ ] **Step 4: Add `ObjectNavigator`**

Create `frontend/src/shell/ObjectNavigator.tsx`:

```tsx
import { CLOUD_MODULE_GROUPS } from "../navigation/cloudModules";

type ObjectNavigatorProps = {
  activeView: string;
};

export function ObjectNavigator({ activeView }: ObjectNavigatorProps) {
  return (
    <nav className="cloud-ui-object-navigator" aria-label="Объекты облака">
      <div className="cloud-ui-object-mode-strip" aria-label="Режимы навигации">
        <span aria-label="Hosts and clusters">▥</span>
        <span aria-label="VMs and templates">▦</span>
        <span aria-label="Storage">◉</span>
        <span aria-label="Networking">◇</span>
      </div>
      <div className="cloud-ui-object-tree">
        {CLOUD_MODULE_GROUPS.map((group) => (
          <section key={group.key} aria-label={group.title}>
            <h3>{group.title}</h3>
            <ul>
              {group.items.map((item) => (
                <li key={item.key}>
                  <a
                    href={`?view=${encodeURIComponent(item.view)}`}
                    aria-current={activeView === item.view ? "page" : undefined}
                    data-status={item.status}
                  >
                    {item.title}
                  </a>
                </li>
              ))}
            </ul>
          </section>
        ))}
      </div>
    </nav>
  );
}
```

- [ ] **Step 5: Add bottom work panel**

Create `frontend/src/shell/BottomWorkPanel.tsx`:

```tsx
const BOTTOM_PANEL_TABS = ["Recent Tasks", "Alarms", "Audit Tail", "Approvals"] as const;

export function BottomWorkPanel() {
  return (
    <section className="cloud-ui-bottom-panel" aria-label="Нижняя рабочая панель">
      <div className="cloud-ui-bottom-tabs" role="tablist" aria-label="Рабочие события">
        {BOTTOM_PANEL_TABS.map((tab, index) => (
          <button
            key={tab}
            type="button"
            role="tab"
            aria-selected={index === 0}
            className={index === 0 ? "cloud-ui-bottom-tab-active" : undefined}
          >
            {tab}
          </button>
        ))}
      </div>
      <div className="cloud-ui-bottom-empty">
        No active tasks · operation history remains available by correlation ID
      </div>
    </section>
  );
}
```

- [ ] **Step 6: Add CloudShell**

Create `frontend/src/shell/CloudShell.tsx`:

```tsx
import type { ReactNode } from "react";

import type { ShellContext } from "../navigation/types";
import { BottomWorkPanel } from "./BottomWorkPanel";
import { ObjectNavigator } from "./ObjectNavigator";
import { TopChrome } from "./TopChrome";

type CloudShellProps = {
  context: ShellContext;
  activeView: string;
  objectTitle: string;
  objectType: string;
  tabs: string[];
  children: ReactNode;
};

export function CloudShell({
  context,
  activeView,
  objectTitle,
  objectType,
  tabs,
  children,
}: CloudShellProps) {
  return (
    <div className="cloud-ui-shell-v2">
      <TopChrome context={context} />
      <div className="cloud-ui-shell-body">
        <ObjectNavigator activeView={activeView} />
        <main className="cloud-ui-workbench" id="main-content">
          <header className="cloud-ui-object-header">
            <div className="cloud-ui-object-icon" aria-hidden="true">
              ▥
            </div>
            <div>
              <h1>{objectTitle}</h1>
              <p>{objectType} · {context.freshnessLabel}</p>
            </div>
            <button type="button" className="cloud-ui-actions-button">
              ⋮ Actions
            </button>
          </header>
          <nav className="cloud-ui-object-tabs" aria-label="Разделы объекта">
            {tabs.map((tab, index) => (
              <button key={tab} type="button" role="tab" aria-selected={index === 0}>
                {tab}
              </button>
            ))}
          </nav>
          <div className="cloud-ui-workbench-content">{children}</div>
          <BottomWorkPanel />
        </main>
      </div>
    </div>
  );
}
```

- [ ] **Step 7: Add shell CSS**

Append to `frontend/src/styles.css`:

```css
.cloud-ui-sr-only {
  clip: rect(0 0 0 0);
  clip-path: inset(50%);
  height: 1px;
  overflow: hidden;
  position: absolute;
  white-space: nowrap;
  width: 1px;
}

.cloud-ui-shell-v2 {
  background: #f5f7fa;
  min-height: 100vh;
}

.cloud-ui-top-chrome {
  align-items: center;
  background: #253746;
  color: #f0f5f8;
  display: grid;
  gap: 0.75rem;
  grid-template-columns: auto auto minmax(16rem, 1fr) auto auto auto auto;
  min-height: 3.25rem;
  padding: 0 1rem;
}

.cloud-ui-icon-button,
.cloud-ui-actions-button {
  background: transparent;
  border: 1px solid transparent;
  color: inherit;
  cursor: pointer;
  font: inherit;
}

.cloud-ui-product-title {
  font-weight: 700;
}

.cloud-ui-global-search input {
  background: #ffffff;
  border: 1px solid #8a8d90;
  min-height: 2rem;
  padding: 0.25rem 0.5rem;
  width: 100%;
}

.cloud-ui-shell-meta,
.cloud-ui-shell-user {
  color: #dce6ed;
  font-size: 0.875rem;
}

.cloud-ui-shell-body {
  display: grid;
  grid-template-columns: 16rem minmax(0, 1fr);
  min-height: calc(100vh - 3.25rem);
}

.cloud-ui-object-navigator {
  background: #f7f9fb;
  border-right: 1px solid #d2d2d2;
  min-width: 0;
}

.cloud-ui-object-mode-strip {
  border-bottom: 1px solid #d2d2d2;
  display: grid;
  grid-template-columns: repeat(4, 1fr);
}

.cloud-ui-object-mode-strip span {
  padding: 0.75rem;
  text-align: center;
}

.cloud-ui-object-tree {
  display: grid;
  gap: 0.75rem;
  padding: 0.75rem;
}

.cloud-ui-object-tree h3 {
  font-size: 0.875rem;
  margin: 0 0 0.25rem;
}

.cloud-ui-object-tree ul {
  list-style: none;
  margin: 0;
  padding: 0;
}

.cloud-ui-object-tree a {
  color: #151515;
  display: block;
  padding: 0.25rem 0.375rem;
  text-decoration: none;
}

.cloud-ui-object-tree a[aria-current="page"] {
  background: #253746;
  color: #ffffff;
}

.cloud-ui-workbench {
  display: grid;
  grid-template-rows: auto auto minmax(0, 1fr) auto;
  min-width: 0;
}

.cloud-ui-object-header {
  align-items: center;
  display: flex;
  gap: 0.75rem;
  padding: 0.75rem 1rem 0.375rem;
}

.cloud-ui-object-header h1 {
  font-size: 1.5rem;
  margin: 0;
}

.cloud-ui-object-header p {
  color: #6a6e73;
  margin: 0.125rem 0 0;
}

.cloud-ui-object-tabs,
.cloud-ui-bottom-tabs {
  border-bottom: 1px solid #d2d2d2;
  display: flex;
  gap: 1.5rem;
  padding: 0 1rem;
}

.cloud-ui-object-tabs button,
.cloud-ui-bottom-tabs button {
  background: transparent;
  border: 0;
  color: #151515;
  cursor: pointer;
  font: inherit;
  padding: 0.625rem 0;
}

.cloud-ui-object-tabs button[aria-selected="true"],
.cloud-ui-bottom-tab-active {
  border-bottom: 3px solid #0066cc;
}

.cloud-ui-workbench-content {
  min-width: 0;
  overflow: auto;
  padding: 0.75rem 1rem;
}

.cloud-ui-bottom-panel {
  background: #ffffff;
  border-top: 2px solid #d2d2d2;
}

.cloud-ui-bottom-empty {
  color: #6a6e73;
  padding: 1rem;
  text-align: center;
}
```

- [ ] **Step 8: Run tests and commit**

Run:

```bash
cd frontend
npm test -- --run src/shell/CloudShell.test.tsx
npm run typecheck
npm run lint
```

Expected: all pass.

Commit:

```bash
git add frontend/src/shell frontend/src/styles.css
git commit -m "feat: add vSphere-informed cloud shell"
```

## Task 3: Re-home Existing Views Into The Shell

**Files:**

- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/App.test.tsx`

- [ ] **Step 1: Add failing integration test for shell-wrapped app**

Add this test to `frontend/src/App.test.tsx` using existing authenticated fetch helpers already in
the file:

```tsx
test("authenticated inventory view renders inside CloudShell", async () => {
  window.history.pushState({}, "", "/?view=instances");
  const fetchMock = vi.spyOn(globalThis, "fetch").mockImplementation((input) => {
    const url = String(input);
    if (url === "/api/v1/session") {
      return Promise.resolve(jsonResponse(operatorSessionPayload));
    }
    if (url === "/api/v1/health/ready") {
      return Promise.resolve(jsonResponse(readyPayload));
    }
    if (url === "/api/v1/capabilities") {
      return Promise.resolve(
        jsonResponse(
          capabilitiesPayload([
            "instance.read",
            "hypervisor.read",
            "group.read",
            "operation.read",
            "audit.read",
          ]),
        ),
      );
    }
    if (url === "/api/v1/inventory/modules") {
      return Promise.resolve(jsonResponse(inventoryModulesPayload()));
    }
    if (url === "/api/v1/instances?limit=50&sort=name.asc") {
      return Promise.resolve(
        jsonResponse(
          inventoryPage([
            {
              cloud_id: "synthetic",
              region_id: "RegionOne",
              instance_id: "instance-0001",
              name: "vm-prod-api-01",
              project_id: "project-a",
              user_id: "user-a",
              status: "ACTIVE",
              power_state: "RUNNING",
              task_state: null,
              vm_state: "active",
              host_name: "compute-03",
              hypervisor_id: "hyp-03",
              availability_zone: "az1",
              flavor_id: "m1.small",
              vcpus: 2,
              ram_mb: 4096,
              disk_gb: 40,
              image_id: "image-1",
              boot_volume_id: null,
              addresses: {},
              source_created_at: "2026-06-21T09:00:00Z",
              source_updated_at: "2026-06-21T09:30:00Z",
              observed_at: "2026-06-21T10:00:00Z",
              sync_generation: 1,
              sync_status: "ok",
            },
          ]),
        ),
      );
    }
    return Promise.resolve(jsonResponse({}, 404));
  });

  render(<App />);

  expect(await screen.findByRole("banner")).toHaveTextContent("Cloud UI");
  expect(screen.getByRole("navigation", { name: "Объекты облака" })).toBeInTheDocument();
  expect(screen.getByRole("heading", { name: "ВМ" })).toBeInTheDocument();
  expect(screen.getByRole("region", { name: "Нижняя рабочая панель" })).toHaveTextContent(
    "Recent Tasks",
  );
  expect(await screen.findByRole("table", { name: "Таблица ВМ" })).toBeInTheDocument();
  expect(fetchMock).toHaveBeenCalledWith(
    "/api/v1/instances?limit=50&sort=name.asc",
    expect.objectContaining({ signal: expect.any(AbortSignal) }),
  );
});
```

- [ ] **Step 2: Run test and verify it fails**

Run:

```bash
cd frontend
npm test -- --run src/App.test.tsx -t "authenticated inventory view renders inside CloudShell"
```

Expected: fail because `CloudShell` is not used by `App`.

- [ ] **Step 3: Import CloudShell and derive shell context**

In `frontend/src/App.tsx`, add imports:

```tsx
import { CloudShell } from "./shell/CloudShell";
import type { ShellContext } from "./navigation/types";
```

Add helpers near existing view helpers:

```tsx
function buildShellContext(
  authState: AuthState,
  capabilities: Capabilities | null,
  readiness: LoadState,
): ShellContext {
  const identityLabel =
    authState.type === "authenticated" ? authState.subject.display_name : "anonymous";
  const scope =
    capabilities === null
      ? "Scope: unknown"
      : `Scope: ${capabilities.scope.type}${capabilities.scope.id ? ` / ${capabilities.scope.id}` : ""}`;
  const policyRevision =
    capabilities === null ? "Policy rev unknown" : `Policy rev ${capabilities.policy_revision}`;
  const freshnessLabel =
    readiness.type === "ready" ? `API readiness: ${readiness.readiness.status}` : "API readiness unknown";

  return {
    productTitle: "Cloud UI",
    searchPlaceholder: "Search in all clouds, projects, hosts, VMs, operations",
    scopeLabel: scope,
    identityLabel,
    policyRevision,
    freshnessLabel,
  };
}

function objectTitleForView(view: PortalView | InventoryView | null): string {
  if (view === "hypervisors") return "Гипервизоры";
  if (view === "groups") return "Группы";
  if (view === "operations") return "Операции";
  if (view === "audit") return "Аудит";
  return "ВМ";
}

function objectTypeForView(view: PortalView | InventoryView | null): string {
  if (view === "hypervisors") return "Inventory / Hypervisors";
  if (view === "groups") return "Resource groups";
  if (view === "operations") return "Mistral operation center";
  if (view === "audit") return "Audit and evidence";
  return "Inventory / Instances";
}

function objectTabsForView(view: PortalView | InventoryView | null): string[] {
  if (view === "audit") return ["Summary", "Audit Tail", "Exports"];
  if (view === "operations") return ["Summary", "Catalog", "Executions", "Approvals", "Audit"];
  if (view === "groups") return ["Summary", "Members", "Rules", "Audit"];
  return ["Summary", "Monitor", "Configure", "Permissions", "VMs", "Operations", "Audit"];
}
```

- [ ] **Step 4: Wrap authenticated work area in CloudShell**

In `App`, immediately before the `return (` statement, create a local `authenticatedWorkArea`
constant:

```tsx
  const authenticatedWorkArea =
    authState.type !== "authenticated" ? null : activePortalView === "groups" ? (
      <GroupsWorkArea
        capabilities={authState.capabilities}
        detailState={groupDetailState}
        locationSearch={locationSearch}
        onGroupInventoryOpen={handleGroupInventoryOpen}
        onGroupSelect={handleGroupSelect}
        state={groupState}
      />
    ) : activePortalView === "operations" ? (
      <OperationsWorkArea
        capabilities={authState.capabilities}
        csrf={authState.csrf}
        detailState={operationDetailState}
        onOperationSubmitted={handleOperationSubmitted}
        selectedOperationId={selectedOperationId}
        state={workflowDefinitionsState}
      />
    ) : activePortalView === "audit" ? (
      <AuditWorkArea
        capabilities={authState.capabilities}
        csrf={authState.csrf}
        exportState={auditExportState}
        onAuditExport={handleAuditExport}
        onAuditNextPage={handleAuditNextPage}
        state={auditState}
      />
    ) : (
      <InventoryWorkArea
        activeView={activeInventoryView}
        capabilities={authState.capabilities}
        locationSearch={locationSearch}
        modulesState={inventoryModulesState}
        onInventoryLinkSelect={handleInventoryLinkSelect}
        onInventoryNextPage={handleInventoryNextPage}
        onInventoryViewSelect={handleInventoryViewSelect}
        state={inventoryState}
      />
    );
```

Immediately after that constant, derive shell display state:

```tsx
const shellContext = buildShellContext(authState, currentCapabilities, state);
const shellActiveView = activePortalView ?? activeInventoryView ?? "instances";
const shellObjectTitle = objectTitleForView(activePortalView ?? activeInventoryView);
const shellObjectType = objectTypeForView(activePortalView ?? activeInventoryView);
const shellTabs = objectTabsForView(activePortalView ?? activeInventoryView);
```

Inside the existing `return`, keep the current login/status cards for anonymous/loading/error states.
Replace the four repeated authenticated conditional blocks:

```tsx
{authState.type === "authenticated" && activePortalView === "groups" && (...)}
{authState.type === "authenticated" && activePortalView === "operations" && (...)}
{authState.type === "authenticated" && activePortalView === "audit" && (...)}
{authState.type === "authenticated" && activePortalView !== "groups" && ... && (...)}
```

with one authenticated shell block:

```tsx
{authState.type === "authenticated" && authenticatedWorkArea !== null && (
  <CloudShell
    context={shellContext}
    activeView={shellActiveView}
    objectTitle={shellObjectTitle}
    objectType={shellObjectType}
    tabs={shellTabs}
  >
    {authenticatedWorkArea}
  </CloudShell>
)}
```

- [ ] **Step 5: Run app tests and fix query labels only**

Run:

```bash
cd frontend
npm test -- --run src/App.test.tsx
```

Expected: existing tests may need updated landmark expectations because the layout wrapper changed.
Do not relax capability or API request assertions.

- [ ] **Step 6: Run verification and commit**

Run:

```bash
cd frontend
npm test -- --run src/App.test.tsx src/shell/CloudShell.test.tsx
npm run typecheck
npm run lint
```

Expected: all pass.

Commit:

```bash
git add frontend/src/App.tsx frontend/src/App.test.tsx
git commit -m "feat: rehome portal views in cloud shell"
```

## Task 4: Bottom Panel Evidence And No-Secret Browser Checks

**Files:**

- Modify: `frontend/src/App.test.tsx`
- Modify: `frontend/src/shell/BottomWorkPanel.tsx`

- [ ] **Step 1: Write failing tests for bottom panel and browser storage**

Add to `frontend/src/App.test.tsx`:

```tsx
test("shell does not write tokens or identity secrets to browser storage", async () => {
  const localStorageSet = vi.spyOn(Storage.prototype, "setItem");
  window.history.pushState({}, "", "/?view=instances");
  vi.spyOn(globalThis, "fetch").mockImplementation((input) => {
    const url = String(input);
    if (url === "/api/v1/session") {
      return Promise.resolve(jsonResponse(operatorSessionPayload));
    }
    if (url === "/api/v1/health/ready") {
      return Promise.resolve(jsonResponse(readyPayload));
    }
    if (url === "/api/v1/capabilities") {
      return Promise.resolve(
        jsonResponse(
          capabilitiesPayload(["instance.read", "hypervisor.read", "operation.read"]),
        ),
      );
    }
    if (url === "/api/v1/inventory/modules") {
      return Promise.resolve(jsonResponse(inventoryModulesPayload()));
    }
    if (url === "/api/v1/instances?limit=50&sort=name.asc") {
      return Promise.resolve(
        jsonResponse(
          inventoryPage([
            {
              cloud_id: "synthetic",
              region_id: "RegionOne",
              instance_id: "instance-0001",
              name: "vm-prod-api-01",
              project_id: "project-a",
              user_id: "user-a",
              status: "ACTIVE",
              power_state: "RUNNING",
              task_state: null,
              vm_state: "active",
              host_name: "compute-03",
              hypervisor_id: "hyp-03",
              availability_zone: "az1",
              flavor_id: "m1.small",
              vcpus: 2,
              ram_mb: 4096,
              disk_gb: 40,
              image_id: "image-1",
              boot_volume_id: null,
              addresses: {},
              source_created_at: "2026-06-21T09:00:00Z",
              source_updated_at: "2026-06-21T09:30:00Z",
              observed_at: "2026-06-21T10:00:00Z",
              sync_generation: 1,
              sync_status: "ok",
            },
          ]),
        ),
      );
    }
    return Promise.resolve(jsonResponse({}, 404));
  });

  render(<App />);

  await screen.findByRole("table", { name: "Таблица ВМ" });
  expect(localStorageSet).not.toHaveBeenCalledWith(
    expect.stringMatching(/token|password|credential|secret/i),
    expect.any(String),
  );
  expect(window.localStorage.getItem("keystone_token")).toBeNull();
  expect(window.sessionStorage.getItem("keystone_token")).toBeNull();
});

test("bottom panel states that audit tail and approvals are planned when backend data is absent", async () => {
  render(
    <BottomWorkPanel
      auditTailState="planned"
      approvalsState="planned"
    />,
  );

  expect(screen.getByRole("region", { name: "Нижняя рабочая панель" })).toHaveTextContent(
    "Audit Tail planned",
  );
  expect(screen.getByRole("region", { name: "Нижняя рабочая панель" })).toHaveTextContent(
    "Approvals planned",
  );
});
```

Import `BottomWorkPanel` and `vi` if not already imported:

```tsx
import { vi } from "vitest";
import { BottomWorkPanel } from "./shell/BottomWorkPanel";
```

- [ ] **Step 2: Run tests and verify they fail**

Run:

```bash
cd frontend
npm test -- --run src/App.test.tsx -t "bottom panel states|does not write tokens"
```

Expected: bottom panel props are not implemented yet.

- [ ] **Step 3: Add planned-state props to `BottomWorkPanel`**

Replace `frontend/src/shell/BottomWorkPanel.tsx` with:

```tsx
type BottomWorkPanelProps = {
  auditTailState?: "ready" | "planned";
  approvalsState?: "ready" | "planned";
};

const BOTTOM_PANEL_TABS = ["Recent Tasks", "Alarms", "Audit Tail", "Approvals"] as const;

export function BottomWorkPanel({
  auditTailState = "planned",
  approvalsState = "planned",
}: BottomWorkPanelProps) {
  return (
    <section className="cloud-ui-bottom-panel" aria-label="Нижняя рабочая панель">
      <div className="cloud-ui-bottom-tabs" role="tablist" aria-label="Рабочие события">
        {BOTTOM_PANEL_TABS.map((tab, index) => (
          <button
            key={tab}
            type="button"
            role="tab"
            aria-selected={index === 0}
            className={index === 0 ? "cloud-ui-bottom-tab-active" : undefined}
          >
            {tab}
          </button>
        ))}
      </div>
      <div className="cloud-ui-bottom-empty">
        No active tasks · operation history remains available by correlation ID
      </div>
      <div className="cloud-ui-bottom-planned">
        Audit Tail {auditTailState} · Approvals {approvalsState}
      </div>
    </section>
  );
}
```

- [ ] **Step 4: Run tests and commit**

Run:

```bash
cd frontend
npm test -- --run src/App.test.tsx src/shell/CloudShell.test.tsx
npm run typecheck
npm run lint
```

Expected: all pass.

Commit:

```bash
git add frontend/src/App.test.tsx frontend/src/shell/BottomWorkPanel.tsx
git commit -m "test: cover shell storage and bottom panel states"
```

## Task 5: Documentation And Risk Register

**Files:**

- Modify: `docs/generated/risk-register.md`
- Modify: `docs/11_DKB_TRACEABILITY.md` only if implementation changes visible security behavior
- Create: `docs/generated/ui-shell-horizon-parity.md`

- [ ] **Step 1: Add generated evidence summary**

Create `docs/generated/ui-shell-horizon-parity.md`:

```md
# UI shell and Horizon parity first slice

- Scope: frontend shell and registry only.
- vSphere reference: used as visual/product reference through temporary browser inspection; no
  credentials, cookies, screenshots or session artifacts are committed.
- Horizon parity: registry added for coverage tracking; not all Horizon workflows are implemented.
- Security posture: browser still calls only portal `/api/v1`; no OpenStack token or corporate
  credential is stored in browser storage.
- DKB posture: UI shell exposes session/scope/policy/freshness context but does not claim compliance
  without backend tests and external evidence.

## Verification

- `cd frontend && npm test -- --run src/App.test.tsx src/shell/CloudShell.test.tsx`
- `cd frontend && npm run typecheck`
- `cd frontend && npm run lint`
- `./scripts/secret-scan.sh`
- `git diff --check`
```

- [ ] **Step 2: Add risk row**

Append to `docs/generated/risk-register.md` after the latest UI/E09 risk row:

```md
| R-072 | UI shell and Horizon parity registry mistaken for implemented Horizon replacement | The first UI slice creates a vSphere-informed shell and static Horizon parity registry, but it does not implement every Horizon workflow, production federation, real Watcher/Masakari workflows, export approvals or DKB compliance evidence. | Keep parity rows, disabled-state reasons, backend/API tests and DKB evidence gates explicit before claiming Horizon replacement or production compliance. | UI/E04/E08 |
```

- [ ] **Step 3: Decide traceability update**

If the implementation only changes frontend layout and registry, do not edit
`docs/11_DKB_TRACEABILITY.md`. Instead, include this statement in the final report:

```text
DKB posture is unchanged by this layout-only slice; the UI exposes shell context and registry
status, while backend/session/audit enforcement remains under the existing E02/E07/E08 controls.
```

If the implementation changes auth/session/audit behavior, add a short section before `## Полная
матрица` with evidence paths and affected DKB rows.

- [ ] **Step 4: Run documentation checks and commit**

Run:

```bash
./scripts/secret-scan.sh
git diff --check
```

Expected: both pass.

Commit:

```bash
git add docs/generated/ui-shell-horizon-parity.md docs/generated/risk-register.md docs/11_DKB_TRACEABILITY.md
git commit -m "docs: record UI shell parity evidence"
```

## Task 6: Final Verification And Review

**Files:**

- Review all modified files

- [ ] **Step 1: Run frontend checks**

Run:

```bash
cd frontend
npm test -- --run src/App.test.tsx src/shell/CloudShell.test.tsx
npm run typecheck
npm run lint
```

Expected: tests, typecheck and lint pass.

- [ ] **Step 2: Run repository checks**

Run:

```bash
./scripts/secret-scan.sh
git diff --check
git status --short --branch
```

Expected:

- secret scan exit 0;
- diff-check exit 0;
- status shows only expected committed branch state or clean tree.

- [ ] **Step 3: Manual UI smoke**

Run local stack if it is not running:

```bash
docker compose up -d --no-build
```

Open:

```bash
open http://127.0.0.1:3000/
```

Expected:

- login page appears;
- after mock login, shell top chrome and object navigator are visible;
- instances table still loads through `/api/v1/instances`;
- groups, operations and audit routes still use existing API requests;
- bottom panel is visible and does not overlap table content.

- [ ] **Step 4: Request code review**

Use `superpowers:requesting-code-review` and ask the reviewer to focus on:

- no credential/token leakage;
- no frontend-only authorization claims;
- no full inventory browser load;
- no accidental Horizon parity overclaim;
- accessibility regressions in shell landmarks/tabs;
- no committed vSphere artifacts.

- [ ] **Step 5: Fix review findings, rerun checks and finish branch**

If review finds issues, apply fixes and rerun the commands from Steps 1 and 2.

When checks and review pass, use `superpowers:finishing-a-development-branch` to choose merge, PR or
keep-branch workflow.

## Self-Review

Spec coverage:

- vSphere-informed shell: Tasks 2 and 3.
- Horizon parity matrix: Tasks 1 and 5.
- Auth and no-token constraints: Task 4 plus final review focus.
- DKB-aware UX: Tasks 2, 4 and 5.
- Large-data table constraints: Task 3 keeps existing server-side inventory behavior; no full
  browser fetch is introduced.
- First implementation slice recommendation: Tasks 1 through 6 match shell, decomposition, registry
  and tests without backend changes.

Known gaps intentionally left for later plans:

- real Keycloak/LDAP/MS AD/FreeIPA production auth;
- OpenAPI-generated frontend client;
- React Router/TanStack Query/TanStack Table adoption;
- full Horizon workflow implementation;
- Playwright e2e setup;
- real Watcher/Masakari UI modules.

Placeholder scan:

- The plan contains no forbidden placeholder markers.
- Planned/disabled product states are explicit data values, not placeholders.

Type consistency:

- `CloudModuleGroup`, `HorizonParityRow` and `ShellContext` are defined before use.
- `CloudShell` props match tests and `App.tsx` integration steps.
