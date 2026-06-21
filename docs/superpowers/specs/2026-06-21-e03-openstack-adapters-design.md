# E03 OpenStack Adapters Design

## Goal

Build the contracts-first OpenStack adapter layer for Keystone, Nova and Placement. E03 proves that backend code can normalize read-only OpenStack data and errors through typed adapters, while tests run offline against deterministic mocks and no browser or route handler receives OpenStack tokens or raw service schemas.

## Accepted Scope

- Adapter contracts, DTOs, typed errors, retry/timeout policy and correlation propagation.
- Deterministic mock service layer for Keystone, Nova and Placement.
- Read-only Keystone, Nova and Placement adapters over an explicit HTTP client boundary.
- Contract tests for successful mapping, pagination/microversion handling and error mapping.
- API/integration registry updates for ДКБ-77 evidence.
- Optional read-only lab smoke command is allowed only when a safe test credential is available; otherwise evidence stays pending.

Out of scope:

- Inventory read model and browser list endpoints.
- Mutating Nova/Placement/Keystone operations.
- Event consumers and reconciliation.
- Mistral, Watcher, Masakari and telemetry adapters.
- Production federation or Vault/SecMan integration.

## Architecture

E03 adds `backend/src/cloud_ui/integrations/` with a small shared core and focused service modules:

- `integrations/base.py` defines `AdapterRequestContext`, typed error classes, retry decisions and response parsing helpers.
- `integrations/http.py` wraps `httpx` with request timeout, retry for temporary read errors, correlation headers and redaction-safe errors.
- `integrations/openstack_config.py` holds trusted endpoint and microversion settings.
- `integrations/keystone/`, `integrations/nova/`, `integrations/placement/` contain DTOs and adapter methods.
- `tests/integrations/` contains respx/httpx mock tests and fixtures.

Route handlers and frontend code do not call these adapters in E03. Later E04 services may depend on adapter interfaces, not on raw `httpx` or OpenStack response dictionaries.

## Data Flow

Caller code creates an `AdapterRequestContext` with:

- `request_id`;
- `correlation_id`;
- cloud/region identifiers;
- optional server-side auth reference.

The adapter uses trusted configuration for endpoints and microversions. It sends correlation/request headers to the mock or real OpenStack endpoint, maps the response to DTOs and raises typed exceptions:

- `OpenStackAuthenticationError`;
- `OpenStackForbiddenError`;
- `OpenStackNotFoundError`;
- `OpenStackConflictError`;
- `OpenStackRateLimitError`;
- `OpenStackTemporaryError`;
- `OpenStackTimeoutError`;
- `OpenStackInvalidResponseError`.

Permanent errors are never retried. GET requests may retry bounded temporary errors and timeouts within the configured deadline. Error messages and repr output must not include token or authorization header values.

## Keystone Contract

E03 implements read-only discovery/service catalog mapping:

- version discovery from `/v3`;
- service catalog endpoint extraction from token-like fixture payloads;
- roles/scope references represented as DTOs.

Keystone auth token acquisition is not implemented until a safe P1 test identity flow is approved. Fixtures must not contain real tokens.

## Nova Contract

E03 fixes a first Nova microversion in configuration and tests it via request headers. The read-only adapter covers:

- paged server list/detail DTO;
- hypervisor list DTO;
- compute service list DTO;
- aggregate/server-group list DTO shape sufficient for E04 contracts.

The adapter must preserve Nova `403` as final denial and must distinguish `404`, `409`, `429`, temporary `5xx` and timeout.

## Placement Contract

E03 fixes a first Placement microversion in configuration and tests it via request headers. The read-only adapter covers:

- resource provider list DTO;
- provider inventory DTO;
- provider usage DTO;
- graceful temporary-error mapping so E04 can later produce partial/stale warnings.

Placement data is enrichment only and cannot override Nova status.

## Mock Layer

The mock layer is deterministic and lives under tests, not as production service code. It must model:

- success responses;
- pagination and next links where used;
- microversion headers;
- `401`, `403`, `404`, `409`, `429`, `500/503`;
- timeout;
- malformed JSON or schema.

All fixtures are synthetic and sanitized. No production URLs, passwords, tokens, cookies or private keys are committed.

## Testing

E03 is TDD-first:

- unit tests for retry decisions and error redaction;
- adapter contract tests with mocked HTTP;
- mapping tests for Keystone/Nova/Placement DTOs;
- negative tests for permanent errors without retry;
- timeout tests;
- microversion header tests;
- optional smoke command documented as skipped/pending unless safe read-only test credential exists.

Quality gates remain:

```text
git diff --check
./scripts/secret-scan.sh
make lint
make typecheck
make test
```

## Documentation And Evidence

Update:

- `docs/generated/api-register.md` for Keystone/Nova/Placement versions, timeout/retry and evidence status;
- `docs/generated/integration-register.md` for mock-only vs optional lab smoke state;
- `docs/generated/risk-register.md` for E03 risks such as live fan-out, token leakage and microversion drift;
- an E03 ExecPlan in `docs/execplans/`.

Do not claim ДКБ-22.02/24 deployment TLS compliance from adapter tests. E03 only creates contract-level evidence.

## Rollback

Rollback is a normal git revert of the E03 commit(s). E03 adds no database migration and no runtime route dependency, so rollback does not require DB downgrade. Optional lab smoke artifacts must stay outside git unless sanitized and explicitly documented.
