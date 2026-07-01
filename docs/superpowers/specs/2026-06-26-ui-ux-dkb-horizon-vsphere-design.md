# UI/UX design: DKB-aware Horizon parity with vSphere-informed shell

## Status

Approved design direction as of 2026-06-26. This is a design/specification artifact only:
no production frontend code is changed by this spec.

## Goal

Define the target UI model for the OpenStack administrative portal so that it:

- preserves available Horizon workflows through an explicit parity matrix;
- extends Horizon with first-class Operations/Mistral, Watcher, Masakari, audit, approvals,
  topology, capacity and DKB evidence views;
- uses a vSphere-informed workbench shell for dense operator workflows;
- supports multiple identity sources without exposing OpenStack or corporate credentials to the
  browser;
- keeps DKB/security constraints visible in the product model, not only in backend code.

## Inputs and references

Project documents read for this design:

- `tasks/E04_INVENTORY_UI.md`
- `docs/01_SCOPE_AND_REQUIREMENTS.md`
- `docs/02_TARGET_ARCHITECTURE.md`
- `docs/03_TECH_STACK.md`
- `docs/04_DOMAIN_AND_DATA.md`
- `docs/05_API_AND_INTEGRATIONS.md`
- `docs/06_AUTH_RBAC_SESSIONS.md`
- `docs/09_PERFORMANCE_HA.md`
- `docs/10_SECURITY_DKB.md`
- `docs/13_TEST_STRATEGY.md`
- `frontend/AGENTS.md`

External references checked:

- OpenStack Horizon user documentation:
  `https://docs.openstack.org/horizon/latest/user/`
- OpenStack Horizon administration documentation:
  `https://docs.openstack.org/horizon/latest/admin/`
- Keystone federation introduction:
  `https://docs.openstack.org/keystone/latest/admin/federation/introduction.html`
- Kolla-Ansible Keystone federation guide:
  `https://docs.openstack.org/kolla-ansible/latest/reference/shared-services/keystone-guide.html`

Reference UI observation:

- A test vSphere Client was inspected in a temporary browser profile through read-only DevTools/CDP
  snapshots.
- Additional local screenshot review on 2026-07-01 refined the object workspace recommendations.
- Captured screenshots, local screenshots and DOM snapshots are not committed.
- Credentials, cookies, tokens and session data were not written to the repository or this spec.

## Key decisions

### 1. Product direction

Use a hybrid console:

- Horizon parity is mandatory functional coverage.
- vSphere-style object navigation is the primary working model.
- Operations, Watcher, Masakari, audit, approvals and DKB evidence are first-class modules.
- UI is dense, utilitarian and optimized for repeated operational work, not a landing page.

Rejected alternatives:

- Horizon-first clone: lower migration risk, but weak for large inventory, operations and DKB
  evidence.
- Operations-first dashboard: strong NOC/SOC posture, but insufficient as a Horizon replacement.

### 2. Shell and information architecture

The target shell has these stable regions:

- Top global chrome:
  product menu, global search, refresh, scope selector, session/identity context, help.
- Left object navigator:
  mode-aware tree for hosts/clusters, VMs, storage, networking, operations and audit/evidence.
- Object workbench:
  selected object title, resource type icon, action menu and object tabs.
- Object tabs:
  `Summary`, `Monitor`, `Configure`, `Permissions`, related resource tabs, `Operations`,
  `Audit`.
- Secondary object navigation:
  resource-specific pages inside dense tabs, especially `Monitor` pages for issues, performance,
  utilization, tasks, events, allocation and health.
- Bottom work panel:
  `Recent Tasks`, `Alarms`, `Audit Tail`, `Approvals`.

The vSphere reference specifically validated:

- persistent object tree;
- global search in the top chrome;
- object title plus `Actions`;
- object-level tabs;
- resource-specific secondary navigation inside `Monitor`;
- global warning banners, object issue strips and inventory-tree warning markers;
- separate performance time-series and current utilization/capacity views;
- dense datagrid with quick filter, advanced filter, resizable columns, manage columns, export and
  page-size control;
- expandable tasks/events rows and target links back to object workspaces;
- persistent bottom tasks/alarms panel.

Cloud UI keeps those interaction patterns but adapts them to OpenStack read-model constraints,
capabilities, DKB evidence and partial/stale states. In particular, export, copy, filtering and
pagination remain backend-bounded when they operate on inventory, audit, task or event datasets.

### 3. Horizon parity model

Horizon parity is tracked as a coverage matrix, not copied as a one-to-one menu.

Each Horizon workflow must have a row with:

- Horizon source area;
- Cloud UI target module;
- backend API or planned API;
- required portal capability;
- OpenStack policy/service authority;
- audit event mapping;
- DKB notes;
- implementation status;
- disabled/blocked reason when not implemented.

Initial parity groups:

- Project:
  instances, images, access/security, key pairs, floating IPs, networks, routers, ports,
  object containers, volumes and snapshots.
- Admin:
  images, roles, projects, users, instances, flavors, volume types, quotas, services and host
  aggregates.
- Identity/settings:
  domains/projects/users/groups/roles where enabled by policy, preferences and theme.
- Cloud UI extensions:
  resource groups, Mistral operation center, Watcher governance, Masakari recovery, audit, DKB
  evidence, topology, capacity, live events and approvals.

The UI may reorganize these workflows around object context, but must not silently drop Horizon
functionality.

### 4. Authentication and session UX

The production-preferred model is federation-first:

- Primary path: corporate IdP or Keycloak as broker, with Keystone federation via OIDC/SAML.
- Kolla-Ansible currently supports Keystone federation automation for OpenID Connect; SAML requires
  manual extension or separate deployment work.
- LDAP, MS AD and FreeIPA should normally feed the IdP/Keycloak layer through user federation,
  trust or LDAP integration.
- Direct Keystone domain-specific LDAP is allowed only as a compatibility/fallback path, not the
  preferred UX model, because Keystone LDAP means Keystone handles passwords directly.

Login UX:

- production login starts with server-provided identity methods;
- browser redirects to the trusted IdP/Keystone WebSSO flow;
- local mock login remains P0/test-only and visibly disabled in production configuration;
- UI may show identity source, domain, scope, idle timeout and policy revision.

Security invariants:

- browser receives only an opaque portal session cookie;
- no Keystone token, application credential, LDAP bind password or service credential is stored in
  JS, `localStorage`, `sessionStorage`, logs or audit payloads;
- backend owns server-side session, CSRF, capability snapshot and OpenStack context;
- backend re-checks authorization for every action;
- Keystone and OpenStack service policies remain final authority for OpenStack operations.

### 5. DKB-aware UX

Security and compliance must be visible as operator state:

- session timeout and policy revision shown in the shell;
- scope/domain/source shown without exposing protected internals;
- action menus distinguish allowed, denied, stale and approval-required actions;
- direct URL access denial uses safe messages and request/correlation IDs;
- partial and stale data are shown in tables, summaries and bottom task/audit panels;
- audit tail and approvals are first-class bottom-panel tabs;
- SoD and role conflict reports belong in the Administration/Audit areas;
- DKB evidence views show status and required external evidence without claiming compliance from UI
  visibility alone.

Controls that are explicitly not UI-only:

- hidden/disabled buttons are not authorization;
- frontend capabilities are UX hints only;
- backend and OpenStack policy enforce every protected action;
- raw OpenStack API, telemetry and notification endpoints are never called directly from browser.

### 6. Table and large-data behavior

Datagrids must support:

- server-side pagination and signed cursors;
- page-size limits aligned with backend maximum 200;
- quick filter and advanced typed filters;
- stable server-side sort;
- column management and density controls;
- row selection with explicit allowed/denied/stale counts;
- export as a bounded server-side operation with audit and limits;
- visible freshness, partial warnings and redaction markers;
- current page/window rendering only, not browser-side full inventory filtering.

For implementation, the frontend should evolve toward the existing documented stack:

- route modules by domain;
- React Router for route state;
- TanStack Query for server state;
- TanStack Table for table state/model;
- OpenAPI-generated client/types;
- Playwright for critical browser flows.

The current `frontend/src/App.tsx` monolith should not be expanded further for this UI track.
The first implementation plan should include decomposition before adding broad Horizon parity.

## First implementation slice recommendation

Do not start by implementing every Horizon module.

Recommended first slice:

1. Create the UI shell architecture:
   top chrome, object navigator placeholder, workbench layout and bottom work panel.
2. Decompose frontend into route/domain modules without changing backend behavior.
3. Re-home existing inventory, groups, operations and audit views into the shell.
4. Add a static Horizon parity registry and disabled-state module list.
5. Add tests for navigation, capability-hidden routes, no token storage, partial/stale indicators and
   bottom panel behavior.

This produces a visible UI foundation while keeping current backend contracts intact.

## Open questions

- Which corporate IdP is authoritative in the target environment: Keycloak, AD FS, another OIDC
  provider, or Keystone-domain LDAP fallback?
- Should Cloud UI expose a login-method picker, or should the deployment route all users through a
  single corporate SSO button?
- Which Horizon workflows are mandatory for the first parity milestone versus later parity rows?
- Which exports are permitted under DKB and what size/scope limits are acceptable?
- Should the bottom work panel be always visible on small laptop screens, or collapsible by default?

## Acceptance criteria for the design track

- This spec is committed.
- No vSphere credential, cookie, screenshot or session artifact is committed.
- The visual companion remains untracked/ignored.
- The next plan can be written from this spec without additional product ambiguity.
