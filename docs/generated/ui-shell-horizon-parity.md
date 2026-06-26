# UI shell and Horizon parity first slice

- Scope: frontend shell, static navigation/parity registry, existing view re-home and tests only.
- vSphere reference: used as visual/product reference through temporary browser inspection; no
  credentials, cookies, screenshots or session artifacts are committed.
- Horizon parity: registry tracks coverage; this slice does not implement every Horizon workflow.
- Security posture: browser still calls only portal `/api/v1`; no OpenStack token, corporate
  credential or identity secret is stored in browser storage.
- Capability posture: frontend capability checks are UX hints only; backend and OpenStack policy
  remain the authorization boundary.
- DKB posture: unchanged by this layout-first slice; shell context, registry status and planned
  states do not claim compliance without backend tests and external evidence.

## Evidence

- `frontend/src/navigation/horizonParity.ts` keeps Horizon source workflows, status reasons,
  API-contract notes, audit events and DKB notes explicit.
- `frontend/src/navigation/cloudModules.ts` keeps planned/disabled module reasons explicit.
- `frontend/src/shell/ObjectNavigator.tsx` renders implemented modules as links only when the
  current capabilities include the required capability; otherwise the item is visible but disabled.
- `frontend/src/shell/BottomWorkPanel.tsx` exposes `Audit Tail` and `Approvals` as planned states
  when backend data is absent.
- `frontend/src/App.test.tsx` verifies shell integration, no direct OpenStack browser calls, no
  full inventory browser load, no shell for users without accessible sections and no token/secret
  browser storage on the rendered shell path.

## Verification

- `cd frontend && npm test -- --run src/App.test.tsx src/shell/CloudShell.test.tsx`
- `cd frontend && npm run typecheck`
- `cd frontend && npm run lint`
- `cd frontend && npm test`
- `./scripts/secret-scan.sh`
- `git diff --check`
