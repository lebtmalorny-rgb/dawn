# E03 OpenStack Adapters Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the offline-tested Keystone, Nova and Placement adapter contract layer without exposing OpenStack credentials or raw schemas to browser code.

**Architecture:** Add a focused `cloud_ui.integrations` package: shared adapter context/errors/retry, an `httpx` transport wrapper, and service-specific DTO/adapters for Keystone, Nova and Placement. Tests use `httpx.MockTransport`, so the main contract suite runs without network access or credentials.

**Tech Stack:** Python 3.11, Pydantic, httpx 0.28.1, pytest, Ruff, mypy.

---

## File Structure

Create:

```text
backend/src/cloud_ui/integrations/__init__.py
backend/src/cloud_ui/integrations/base.py
backend/src/cloud_ui/integrations/http.py
backend/src/cloud_ui/integrations/openstack_config.py
backend/src/cloud_ui/integrations/keystone/__init__.py
backend/src/cloud_ui/integrations/keystone/adapter.py
backend/src/cloud_ui/integrations/keystone/dto.py
backend/src/cloud_ui/integrations/nova/__init__.py
backend/src/cloud_ui/integrations/nova/adapter.py
backend/src/cloud_ui/integrations/nova/dto.py
backend/src/cloud_ui/integrations/placement/__init__.py
backend/src/cloud_ui/integrations/placement/adapter.py
backend/src/cloud_ui/integrations/placement/dto.py
backend/tests/integrations/test_base.py
backend/tests/integrations/test_http.py
backend/tests/integrations/test_keystone_adapter.py
backend/tests/integrations/test_nova_adapter.py
backend/tests/integrations/test_placement_adapter.py
```

Modify:

```text
backend/pyproject.toml
backend/src/cloud_ui/config.py
backend/tests/test_config.py
docs/execplans/E03-openstack-adapters.md
docs/generated/api-register.md
docs/generated/integration-register.md
docs/generated/risk-register.md
```

---

### Task 1: Shared Adapter Contracts

**Files:**
- Create: `backend/src/cloud_ui/integrations/__init__.py`
- Create: `backend/src/cloud_ui/integrations/base.py`
- Test: `backend/tests/integrations/test_base.py`

- [ ] **Step 1: Write failing tests for typed errors, redaction and retry policy**

Create `backend/tests/integrations/test_base.py`:

```python
from cloud_ui.integrations.base import (
    AdapterRequestContext,
    OpenStackForbiddenError,
    OpenStackTemporaryError,
    OpenStackTimeoutError,
    RetryDecision,
    should_retry,
)


def test_adapter_error_repr_redacts_sensitive_values() -> None:
    error = OpenStackForbiddenError(
        service="nova",
        message="Authorization failed",
        status_code=403,
        request_id="request-1",
        correlation_id="corr-1",
        details={
            "authorization": "Bearer secret-token",
            "normal": "visible",
            "token": "secret-token",
        },
    )

    rendered = repr(error)

    assert "secret-token" not in rendered
    assert "Bearer" not in rendered
    assert "visible" in rendered
    assert error.code == "openstack_forbidden"


def test_retry_policy_retries_only_temporary_read_failures() -> None:
    context = AdapterRequestContext(
        request_id="request-1",
        correlation_id="corr-1",
        cloud_id="lab",
        region_id="RegionOne",
    )

    temporary = OpenStackTemporaryError(
        service="nova",
        message="temporary",
        status_code=503,
        request_id=context.request_id,
        correlation_id=context.correlation_id,
    )
    timeout = OpenStackTimeoutError(
        service="nova",
        message="timeout",
        status_code=None,
        request_id=context.request_id,
        correlation_id=context.correlation_id,
    )
    forbidden = OpenStackForbiddenError(
        service="nova",
        message="forbidden",
        status_code=403,
        request_id=context.request_id,
        correlation_id=context.correlation_id,
    )

    assert should_retry("GET", temporary, attempt=1, max_attempts=2) == RetryDecision.RETRY
    assert should_retry("GET", timeout, attempt=1, max_attempts=2) == RetryDecision.RETRY
    assert should_retry("GET", temporary, attempt=2, max_attempts=2) == RetryDecision.STOP
    assert should_retry("GET", forbidden, attempt=1, max_attempts=2) == RetryDecision.STOP
    assert should_retry("POST", temporary, attempt=1, max_attempts=2) == RetryDecision.STOP
```

- [ ] **Step 2: Run tests and verify RED**

Run:

```bash
cd backend && .venv/bin/python -m pytest tests/integrations/test_base.py -q
```

Expected: fail with `ModuleNotFoundError: No module named 'cloud_ui.integrations'`.

- [ ] **Step 3: Implement shared contracts**

Create `backend/src/cloud_ui/integrations/__init__.py`:

```python
"""OpenStack and external service integration contracts."""
```

Create `backend/src/cloud_ui/integrations/base.py`:

```python
from __future__ import annotations

from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict

from cloud_ui.logging import redact_mapping

HttpMethod = Literal["GET", "HEAD", "POST", "PUT", "PATCH", "DELETE"]


class AdapterRequestContext(BaseModel):
    model_config = ConfigDict(frozen=True)

    request_id: str
    correlation_id: str
    cloud_id: str
    region_id: str


class OpenStackAdapterError(Exception):
    code = "openstack_error"

    def __init__(
        self,
        *,
        service: str,
        message: str,
        status_code: int | None,
        request_id: str,
        correlation_id: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        self.service = service
        self.message = message
        self.status_code = status_code
        self.request_id = request_id
        self.correlation_id = correlation_id
        self.details = redact_mapping(details or {})
        super().__init__(message)

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}(code={self.code!r}, service={self.service!r}, "
            f"status_code={self.status_code!r}, request_id={self.request_id!r}, "
            f"correlation_id={self.correlation_id!r}, details={self.details!r})"
        )


class OpenStackAuthenticationError(OpenStackAdapterError):
    code = "openstack_authentication_failed"


class OpenStackForbiddenError(OpenStackAdapterError):
    code = "openstack_forbidden"


class OpenStackNotFoundError(OpenStackAdapterError):
    code = "openstack_not_found"


class OpenStackConflictError(OpenStackAdapterError):
    code = "openstack_conflict"


class OpenStackRateLimitError(OpenStackAdapterError):
    code = "openstack_rate_limited"


class OpenStackTemporaryError(OpenStackAdapterError):
    code = "openstack_temporary_error"


class OpenStackTimeoutError(OpenStackAdapterError):
    code = "openstack_timeout"


class OpenStackInvalidResponseError(OpenStackAdapterError):
    code = "openstack_invalid_response"


class RetryDecision(str, Enum):
    RETRY = "retry"
    STOP = "stop"


def should_retry(
    method: HttpMethod,
    error: OpenStackAdapterError,
    *,
    attempt: int,
    max_attempts: int,
) -> RetryDecision:
    if method not in {"GET", "HEAD"}:
        return RetryDecision.STOP
    if attempt >= max_attempts:
        return RetryDecision.STOP
    if isinstance(error, (OpenStackTemporaryError, OpenStackTimeoutError, OpenStackRateLimitError)):
        return RetryDecision.RETRY
    return RetryDecision.STOP
```

- [ ] **Step 4: Run tests and verify GREEN**

Run:

```bash
cd backend && .venv/bin/python -m pytest tests/integrations/test_base.py -q
```

Expected: `2 passed`.

---

### Task 2: Runtime Config And HTTP Transport

**Files:**
- Modify: `backend/pyproject.toml`
- Modify: `backend/src/cloud_ui/config.py`
- Modify: `backend/tests/test_config.py`
- Create: `backend/src/cloud_ui/integrations/http.py`
- Test: `backend/tests/integrations/test_http.py`

- [ ] **Step 1: Write failing HTTP transport tests**

Create `backend/tests/integrations/test_http.py`:

```python
from __future__ import annotations

import httpx

from cloud_ui.integrations.base import (
    AdapterRequestContext,
    OpenStackForbiddenError,
    OpenStackInvalidResponseError,
    OpenStackTemporaryError,
    OpenStackTimeoutError,
)
from cloud_ui.integrations.http import OpenStackHttpClient


def test_http_client_sends_correlation_and_microversion_headers() -> None:
    seen_headers: dict[str, str] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen_headers["x-openstack-request-id"] = request.headers["x-openstack-request-id"]
        seen_headers["x-correlation-id"] = request.headers["x-correlation-id"]
        seen_headers["openstack-api-version"] = request.headers["openstack-api-version"]
        return httpx.Response(200, json={"ok": True})

    client = OpenStackHttpClient(
        service="nova",
        endpoint="https://nova.example/v2.1",
        transport=httpx.MockTransport(handler),
        timeout_seconds=1.0,
        max_attempts=1,
    )
    context = AdapterRequestContext(
        request_id="request-1",
        correlation_id="corr-1",
        cloud_id="lab",
        region_id="RegionOne",
    )

    payload = client.get_json("/servers/detail", context=context, microversion="compute 2.96")

    assert payload == {"ok": True}
    assert seen_headers == {
        "x-openstack-request-id": "request-1",
        "x-correlation-id": "corr-1",
        "openstack-api-version": "compute 2.96",
    }


def test_http_client_does_not_retry_permanent_403() -> None:
    calls = 0

    def handler(_request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(403, json={"forbidden": {"message": "denied"}})

    client = OpenStackHttpClient(
        service="nova",
        endpoint="https://nova.example/v2.1",
        transport=httpx.MockTransport(handler),
        timeout_seconds=1.0,
        max_attempts=3,
    )
    context = AdapterRequestContext(
        request_id="request-1",
        correlation_id="corr-1",
        cloud_id="lab",
        region_id="RegionOne",
    )

    try:
        client.get_json("/servers/detail", context=context)
    except OpenStackForbiddenError as exc:
        assert exc.status_code == 403
    else:
        raise AssertionError("expected OpenStackForbiddenError")

    assert calls == 1


def test_http_client_retries_temporary_503_then_succeeds() -> None:
    calls = 0

    def handler(_request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        if calls == 1:
            return httpx.Response(503, json={"error": "temporary"})
        return httpx.Response(200, json={"ok": True})

    client = OpenStackHttpClient(
        service="placement",
        endpoint="https://placement.example",
        transport=httpx.MockTransport(handler),
        timeout_seconds=1.0,
        max_attempts=2,
    )
    context = AdapterRequestContext(
        request_id="request-1",
        correlation_id="corr-1",
        cloud_id="lab",
        region_id="RegionOne",
    )

    assert client.get_json("/resource_providers", context=context) == {"ok": True}
    assert calls == 2


def test_http_client_rejects_malformed_json() -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=b"{not-json")

    client = OpenStackHttpClient(
        service="keystone",
        endpoint="https://keystone.example/v3",
        transport=httpx.MockTransport(handler),
        timeout_seconds=1.0,
        max_attempts=1,
    )
    context = AdapterRequestContext(
        request_id="request-1",
        correlation_id="corr-1",
        cloud_id="lab",
        region_id="RegionOne",
    )

    try:
        client.get_json("/", context=context)
    except OpenStackInvalidResponseError:
        pass
    else:
        raise AssertionError("expected invalid response")


def test_http_client_maps_timeout_to_distinct_error_after_retries() -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("timeout")

    client = OpenStackHttpClient(
        service="nova",
        endpoint="https://nova.example/v2.1",
        transport=httpx.MockTransport(handler),
        timeout_seconds=1.0,
        max_attempts=1,
    )
    context = AdapterRequestContext(
        request_id="request-1",
        correlation_id="corr-1",
        cloud_id="lab",
        region_id="RegionOne",
    )

    try:
        client.get_json("/servers/detail", context=context)
    except OpenStackTimeoutError as exc:
        assert exc.code == "openstack_timeout"
    else:
        raise AssertionError("expected timeout error")
```

- [ ] **Step 2: Run tests and verify RED**

Run:

```bash
cd backend && .venv/bin/python -m pytest tests/integrations/test_http.py -q
```

Expected: fail because `cloud_ui.integrations.http` does not exist.

- [ ] **Step 3: Move `httpx` into runtime dependencies**

Modify `backend/pyproject.toml`:

```toml
dependencies = [
  "alembic==1.16.2",
  "fastapi==0.115.13",
  "httpx==0.28.1",
  "pika==1.3.2",
  "pydantic-settings==2.9.1",
  "pymysql==1.1.1",
  "python-json-logger==3.3.0",
  "sqlalchemy==2.0.41",
  "uvicorn[standard]==0.34.3"
]

[project.optional-dependencies]
dev = [
  "mypy==1.16.1",
  "pytest==8.4.1",
  "pytest-cov==6.2.1",
  "ruff==0.12.0"
]
```

- [ ] **Step 4: Add OpenStack settings**

Modify `backend/src/cloud_ui/config.py` by adding fields to `Settings`:

```python
    openstack_timeout_seconds: float = Field(default=2.0, gt=0)
    openstack_max_attempts: int = Field(default=2, ge=1, le=5)
    nova_microversion: str = Field(default="2.96")
    placement_microversion: str = Field(default="1.39")
```

Modify `_CLOUD_UI_ENVIRONMENT_NAMES` in `backend/tests/test_config.py`:

```python
    "CLOUD_UI_OPENSTACK_TIMEOUT_SECONDS",
    "CLOUD_UI_OPENSTACK_MAX_ATTEMPTS",
    "CLOUD_UI_NOVA_MICROVERSION",
    "CLOUD_UI_PLACEMENT_MICROVERSION",
```

- [ ] **Step 5: Implement HTTP client wrapper**

Create `backend/src/cloud_ui/integrations/http.py`:

```python
from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import httpx

from cloud_ui.integrations.base import (
    AdapterRequestContext,
    HttpMethod,
    OpenStackAdapterError,
    OpenStackAuthenticationError,
    OpenStackConflictError,
    OpenStackForbiddenError,
    OpenStackInvalidResponseError,
    OpenStackNotFoundError,
    OpenStackRateLimitError,
    OpenStackTemporaryError,
    OpenStackTimeoutError,
    should_retry,
)


class OpenStackHttpClient:
    def __init__(
        self,
        *,
        service: str,
        endpoint: str,
        timeout_seconds: float,
        max_attempts: int,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self._service = service
        self._endpoint = endpoint.rstrip("/")
        self._timeout_seconds = timeout_seconds
        self._max_attempts = max_attempts
        self._client = httpx.Client(
            base_url=self._endpoint,
            timeout=timeout_seconds,
            transport=transport,
            follow_redirects=False,
        )

    def get_json(
        self,
        path: str,
        *,
        context: AdapterRequestContext,
        microversion: str | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> dict[str, Any]:
        return self._request_json(
            "GET",
            path,
            context=context,
            microversion=microversion,
            headers=headers,
        )

    def _request_json(
        self,
        method: HttpMethod,
        path: str,
        *,
        context: AdapterRequestContext,
        microversion: str | None,
        headers: Mapping[str, str] | None,
    ) -> dict[str, Any]:
        attempt = 1
        while True:
            try:
                response = self._client.request(
                    method,
                    path,
                    headers=self._headers(context, microversion, headers),
                )
                self._raise_for_status(response, context)
                payload = response.json()
                if not isinstance(payload, dict):
                    raise ValueError("JSON payload is not an object")
                return payload
            except httpx.TimeoutException as exc:
                error: OpenStackAdapterError = OpenStackTimeoutError(
                    service=self._service,
                    message="OpenStack request timed out",
                    status_code=None,
                    request_id=context.request_id,
                    correlation_id=context.correlation_id,
                    details={"exception": exc.__class__.__name__},
                )
            except ValueError as exc:
                raise OpenStackInvalidResponseError(
                    service=self._service,
                    message="OpenStack response is not valid JSON object",
                    status_code=None,
                    request_id=context.request_id,
                    correlation_id=context.correlation_id,
                    details={"exception": exc.__class__.__name__},
                ) from exc
            except OpenStackAdapterError as exc:
                error = exc

            if should_retry(method, error, attempt=attempt, max_attempts=self._max_attempts).value == "retry":
                attempt += 1
                continue
            raise error

    def _headers(
        self,
        context: AdapterRequestContext,
        microversion: str | None,
        headers: Mapping[str, str] | None,
    ) -> dict[str, str]:
        result = {
            "accept": "application/json",
            "x-openstack-request-id": context.request_id,
            "x-correlation-id": context.correlation_id,
        }
        if microversion is not None:
            result["openstack-api-version"] = microversion
        if headers:
            result.update(headers)
        return result

    def _raise_for_status(
        self, response: httpx.Response, context: AdapterRequestContext
    ) -> None:
        status = response.status_code
        if status < 400:
            return
        details = {"status_code": status}
        error_type: type[OpenStackAdapterError]
        if status == 401:
            error_type = OpenStackAuthenticationError
        elif status == 403:
            error_type = OpenStackForbiddenError
        elif status == 404:
            error_type = OpenStackNotFoundError
        elif status == 409:
            error_type = OpenStackConflictError
        elif status == 429:
            error_type = OpenStackRateLimitError
        elif status >= 500:
            error_type = OpenStackTemporaryError
        else:
            error_type = OpenStackInvalidResponseError
        raise error_type(
            service=self._service,
            message=f"OpenStack {self._service} returned HTTP {status}",
            status_code=status,
            request_id=context.request_id,
            correlation_id=context.correlation_id,
            details=details,
        )
```

- [ ] **Step 6: Run tests and verify GREEN**

Run:

```bash
cd backend && .venv/bin/python -m pytest tests/integrations/test_base.py tests/integrations/test_http.py -q
```

Expected: all tests pass.

---

### Task 3: Keystone Adapter

**Files:**
- Create: `backend/src/cloud_ui/integrations/keystone/__init__.py`
- Create: `backend/src/cloud_ui/integrations/keystone/dto.py`
- Create: `backend/src/cloud_ui/integrations/keystone/adapter.py`
- Test: `backend/tests/integrations/test_keystone_adapter.py`

- [ ] **Step 1: Write failing Keystone adapter tests**

Create `backend/tests/integrations/test_keystone_adapter.py`:

```python
from __future__ import annotations

import httpx

from cloud_ui.integrations.base import AdapterRequestContext, OpenStackForbiddenError
from cloud_ui.integrations.http import OpenStackHttpClient
from cloud_ui.integrations.keystone.adapter import KeystoneAdapter


def _context() -> AdapterRequestContext:
    return AdapterRequestContext(
        request_id="request-1",
        correlation_id="corr-1",
        cloud_id="lab",
        region_id="RegionOne",
    )


def test_keystone_adapter_maps_version_discovery() -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "version": {
                    "id": "v3.14",
                    "status": "stable",
                    "links": [{"rel": "self", "href": "https://keystone.example/v3/"}],
                }
            },
        )

    adapter = KeystoneAdapter(
        OpenStackHttpClient(
            service="keystone",
            endpoint="https://keystone.example/v3",
            timeout_seconds=1.0,
            max_attempts=1,
            transport=httpx.MockTransport(handler),
        )
    )

    version = adapter.discover_version(_context())

    assert version.id == "v3.14"
    assert version.status == "stable"
    assert version.self_url == "https://keystone.example/v3/"


def test_keystone_adapter_maps_service_catalog() -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "token": {
                    "project": {"id": "project-1", "name": "demo"},
                    "roles": [{"id": "role-1", "name": "reader"}],
                    "catalog": [
                        {
                            "id": "service-1",
                            "name": "nova",
                            "type": "compute",
                            "endpoints": [
                                {
                                    "id": "endpoint-1",
                                    "interface": "public",
                                    "region": "RegionOne",
                                    "url": "https://nova.example/v2.1",
                                }
                            ],
                        }
                    ],
                }
            },
        )

    adapter = KeystoneAdapter(
        OpenStackHttpClient(
            service="keystone",
            endpoint="https://keystone.example/v3",
            timeout_seconds=1.0,
            max_attempts=1,
            transport=httpx.MockTransport(handler),
        )
    )

    catalog = adapter.get_catalog(_context())

    assert catalog.project_id == "project-1"
    assert catalog.roles == ["reader"]
    assert catalog.services[0].service_type == "compute"
    assert catalog.services[0].endpoints[0].url == "https://nova.example/v2.1"


def test_keystone_adapter_preserves_forbidden_error() -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(403, json={"error": "denied"})

    adapter = KeystoneAdapter(
        OpenStackHttpClient(
            service="keystone",
            endpoint="https://keystone.example/v3",
            timeout_seconds=1.0,
            max_attempts=1,
            transport=httpx.MockTransport(handler),
        )
    )

    try:
        adapter.get_catalog(_context())
    except OpenStackForbiddenError as exc:
        assert exc.code == "openstack_forbidden"
    else:
        raise AssertionError("expected forbidden")
```

- [ ] **Step 2: Run tests and verify RED**

Run:

```bash
cd backend && .venv/bin/python -m pytest tests/integrations/test_keystone_adapter.py -q
```

Expected: fail because Keystone adapter module does not exist.

- [ ] **Step 3: Implement Keystone DTOs and adapter**

Create `backend/src/cloud_ui/integrations/keystone/__init__.py`:

```python
"""Keystone read-only adapter."""
```

Create `backend/src/cloud_ui/integrations/keystone/dto.py`:

```python
from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class KeystoneVersion(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str
    status: str
    self_url: str


class KeystoneEndpoint(BaseModel):
    model_config = ConfigDict(frozen=True)

    endpoint_id: str
    interface: str
    region: str
    url: str


class KeystoneService(BaseModel):
    model_config = ConfigDict(frozen=True)

    service_id: str
    name: str
    service_type: str
    endpoints: list[KeystoneEndpoint]


class KeystoneCatalog(BaseModel):
    model_config = ConfigDict(frozen=True)

    project_id: str
    project_name: str
    roles: list[str]
    services: list[KeystoneService]
```

Create `backend/src/cloud_ui/integrations/keystone/adapter.py`:

```python
from __future__ import annotations

from typing import Any

from cloud_ui.integrations.base import AdapterRequestContext, OpenStackInvalidResponseError
from cloud_ui.integrations.http import OpenStackHttpClient
from cloud_ui.integrations.keystone.dto import (
    KeystoneCatalog,
    KeystoneEndpoint,
    KeystoneService,
    KeystoneVersion,
)


class KeystoneAdapter:
    def __init__(self, client: OpenStackHttpClient) -> None:
        self._client = client

    def discover_version(self, context: AdapterRequestContext) -> KeystoneVersion:
        payload = self._client.get_json("/", context=context)
        try:
            version = payload["version"]
            links = version["links"]
            self_url = next(link["href"] for link in links if link["rel"] == "self")
            return KeystoneVersion(
                id=version["id"],
                status=version["status"],
                self_url=self_url,
            )
        except (KeyError, TypeError, StopIteration) as exc:
            raise _invalid_response(context, "Invalid Keystone version payload") from exc

    def get_catalog(self, context: AdapterRequestContext) -> KeystoneCatalog:
        payload = self._client.get_json("/auth/catalog-fixture", context=context)
        try:
            token = payload["token"]
            project = token["project"]
            roles = [role["name"] for role in token["roles"]]
            services = [_service_from_payload(service) for service in token["catalog"]]
            return KeystoneCatalog(
                project_id=project["id"],
                project_name=project["name"],
                roles=roles,
                services=services,
            )
        except (KeyError, TypeError) as exc:
            raise _invalid_response(context, "Invalid Keystone catalog payload") from exc


def _service_from_payload(payload: dict[str, Any]) -> KeystoneService:
    return KeystoneService(
        service_id=payload["id"],
        name=payload["name"],
        service_type=payload["type"],
        endpoints=[
            KeystoneEndpoint(
                endpoint_id=endpoint["id"],
                interface=endpoint["interface"],
                region=endpoint["region"],
                url=endpoint["url"],
            )
            for endpoint in payload["endpoints"]
        ],
    )


def _invalid_response(context: AdapterRequestContext, message: str) -> OpenStackInvalidResponseError:
    return OpenStackInvalidResponseError(
        service="keystone",
        message=message,
        status_code=None,
        request_id=context.request_id,
        correlation_id=context.correlation_id,
    )
```

- [ ] **Step 4: Run tests and verify GREEN**

Run:

```bash
cd backend && .venv/bin/python -m pytest tests/integrations/test_keystone_adapter.py -q
```

Expected: `3 passed`.

---

### Task 4: Nova Adapter

**Files:**
- Create: `backend/src/cloud_ui/integrations/nova/__init__.py`
- Create: `backend/src/cloud_ui/integrations/nova/dto.py`
- Create: `backend/src/cloud_ui/integrations/nova/adapter.py`
- Test: `backend/tests/integrations/test_nova_adapter.py`

- [ ] **Step 1: Write failing Nova adapter tests**

Create `backend/tests/integrations/test_nova_adapter.py`:

```python
from __future__ import annotations

import httpx

from cloud_ui.integrations.base import AdapterRequestContext, OpenStackForbiddenError
from cloud_ui.integrations.http import OpenStackHttpClient
from cloud_ui.integrations.nova.adapter import NovaAdapter


def _context() -> AdapterRequestContext:
    return AdapterRequestContext(
        request_id="request-1",
        correlation_id="corr-1",
        cloud_id="lab",
        region_id="RegionOne",
    )


def _adapter(handler: httpx.MockTransport) -> NovaAdapter:
    return NovaAdapter(
        client=OpenStackHttpClient(
            service="nova",
            endpoint="https://nova.example/v2.1",
            timeout_seconds=1.0,
            max_attempts=1,
            transport=handler,
        ),
        microversion="2.96",
    )


def test_nova_adapter_lists_servers_with_microversion_and_pagination() -> None:
    seen_microversion = ""

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal seen_microversion
        seen_microversion = request.headers["openstack-api-version"]
        return httpx.Response(
            200,
            json={
                "servers": [
                    {
                        "id": "server-1",
                        "name": "vm-1",
                        "status": "ACTIVE",
                        "tenant_id": "project-1",
                        "user_id": "user-1",
                        "created": "2026-06-21T07:00:00Z",
                        "updated": "2026-06-21T07:05:00Z",
                        "OS-EXT-SRV-ATTR:host": "compute-1",
                    }
                ],
                "servers_links": [{"rel": "next", "href": "https://nova.example/v2.1/servers/detail?marker=server-1"}],
            },
        )

    page = _adapter(httpx.MockTransport(handler)).list_servers(_context(), limit=1)

    assert seen_microversion == "compute 2.96"
    assert page.next_marker == "server-1"
    assert page.items[0].server_id == "server-1"
    assert page.items[0].host == "compute-1"


def test_nova_adapter_gets_server_detail() -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "server": {
                    "id": "server-1",
                    "name": "vm-1",
                    "status": "SHUTOFF",
                    "tenant_id": "project-1",
                    "user_id": "user-1",
                    "created": "2026-06-21T07:00:00Z",
                    "updated": "2026-06-21T07:05:00Z",
                    "OS-EXT-SRV-ATTR:host": "compute-1",
                }
            },
        )

    server = _adapter(httpx.MockTransport(handler)).get_server(_context(), "server-1")

    assert server.server_id == "server-1"
    assert server.status == "SHUTOFF"


def test_nova_adapter_lists_hypervisors_services_and_aggregates() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if path.endswith("/os-hypervisors/detail"):
            return httpx.Response(200, json={"hypervisors": [{"id": 1, "hypervisor_hostname": "compute-1", "state": "up", "status": "enabled"}]})
        if path.endswith("/os-services"):
            return httpx.Response(200, json={"services": [{"id": 10, "binary": "nova-compute", "host": "compute-1", "state": "up", "status": "enabled"}]})
        if path.endswith("/os-aggregates"):
            return httpx.Response(200, json={"aggregates": [{"id": 20, "name": "az-a", "availability_zone": "az-a"}]})
        if path.endswith("/os-server-groups"):
            return httpx.Response(200, json={"server_groups": [{"id": "group-1", "name": "anti-affinity", "policies": ["anti-affinity"]}]})
        return httpx.Response(404)

    adapter = _adapter(httpx.MockTransport(handler))

    assert adapter.list_hypervisors(_context())[0].hostname == "compute-1"
    assert adapter.list_compute_services(_context())[0].binary == "nova-compute"
    assert adapter.list_aggregates(_context())[0].name == "az-a"
    assert adapter.list_server_groups(_context())[0].policies == ["anti-affinity"]


def test_nova_adapter_preserves_forbidden() -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(403, json={"forbidden": "denied"})

    try:
        _adapter(httpx.MockTransport(handler)).list_servers(_context(), limit=10)
    except OpenStackForbiddenError:
        pass
    else:
        raise AssertionError("expected forbidden")
```

- [ ] **Step 2: Run tests and verify RED**

Run:

```bash
cd backend && .venv/bin/python -m pytest tests/integrations/test_nova_adapter.py -q
```

Expected: fail because Nova adapter module does not exist.

- [ ] **Step 3: Implement Nova DTOs and adapter**

Create `backend/src/cloud_ui/integrations/nova/__init__.py`:

```python
"""Nova read-only adapter."""
```

Create DTO and adapter files using Pydantic frozen models with these fields:

```python
# backend/src/cloud_ui/integrations/nova/dto.py
from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class NovaServer(BaseModel):
    model_config = ConfigDict(frozen=True)
    server_id: str
    name: str
    status: str
    project_id: str
    user_id: str
    created_at: str
    updated_at: str
    host: str | None


class NovaServerPage(BaseModel):
    model_config = ConfigDict(frozen=True)
    items: list[NovaServer]
    next_marker: str | None


class NovaHypervisor(BaseModel):
    model_config = ConfigDict(frozen=True)
    hypervisor_id: str
    hostname: str
    state: str
    status: str


class NovaComputeService(BaseModel):
    model_config = ConfigDict(frozen=True)
    service_id: str
    binary: str
    host: str
    state: str
    status: str


class NovaAggregate(BaseModel):
    model_config = ConfigDict(frozen=True)
    aggregate_id: str
    name: str
    availability_zone: str | None


class NovaServerGroup(BaseModel):
    model_config = ConfigDict(frozen=True)
    group_id: str
    name: str
    policies: list[str]
```

Create `backend/src/cloud_ui/integrations/nova/adapter.py` with methods:

```python
from __future__ import annotations

from urllib.parse import parse_qs, urlparse

from cloud_ui.integrations.base import AdapterRequestContext, OpenStackInvalidResponseError
from cloud_ui.integrations.http import OpenStackHttpClient
from cloud_ui.integrations.nova.dto import (
    NovaAggregate,
    NovaComputeService,
    NovaHypervisor,
    NovaServer,
    NovaServerGroup,
    NovaServerPage,
)


class NovaAdapter:
    def __init__(self, *, client: OpenStackHttpClient, microversion: str) -> None:
        self._client = client
        self._microversion = f"compute {microversion}"

    def list_servers(
        self, context: AdapterRequestContext, *, limit: int, marker: str | None = None
    ) -> NovaServerPage:
        path = f"/servers/detail?limit={limit}"
        if marker is not None:
            path += f"&marker={marker}"
        payload = self._client.get_json(path, context=context, microversion=self._microversion)
        try:
            return NovaServerPage(
                items=[_server(server) for server in payload["servers"]],
                next_marker=_next_marker(payload.get("servers_links", [])),
            )
        except (KeyError, TypeError) as exc:
            raise _invalid(context, "Invalid Nova server list payload") from exc

    def get_server(self, context: AdapterRequestContext, server_id: str) -> NovaServer:
        payload = self._client.get_json(
            f"/servers/{server_id}", context=context, microversion=self._microversion
        )
        try:
            return _server(payload["server"])
        except (KeyError, TypeError) as exc:
            raise _invalid(context, "Invalid Nova server detail payload") from exc

    def list_hypervisors(self, context: AdapterRequestContext) -> list[NovaHypervisor]:
        payload = self._client.get_json(
            "/os-hypervisors/detail", context=context, microversion=self._microversion
        )
        return [
            NovaHypervisor(
                hypervisor_id=str(item["id"]),
                hostname=item["hypervisor_hostname"],
                state=item["state"],
                status=item["status"],
            )
            for item in payload["hypervisors"]
        ]

    def list_compute_services(self, context: AdapterRequestContext) -> list[NovaComputeService]:
        payload = self._client.get_json(
            "/os-services", context=context, microversion=self._microversion
        )
        return [
            NovaComputeService(
                service_id=str(item["id"]),
                binary=item["binary"],
                host=item["host"],
                state=item["state"],
                status=item["status"],
            )
            for item in payload["services"]
        ]

    def list_aggregates(self, context: AdapterRequestContext) -> list[NovaAggregate]:
        payload = self._client.get_json(
            "/os-aggregates", context=context, microversion=self._microversion
        )
        return [
            NovaAggregate(
                aggregate_id=str(item["id"]),
                name=item["name"],
                availability_zone=item.get("availability_zone"),
            )
            for item in payload["aggregates"]
        ]

    def list_server_groups(self, context: AdapterRequestContext) -> list[NovaServerGroup]:
        payload = self._client.get_json(
            "/os-server-groups", context=context, microversion=self._microversion
        )
        return [
            NovaServerGroup(
                group_id=item["id"],
                name=item["name"],
                policies=list(item["policies"]),
            )
            for item in payload["server_groups"]
        ]


def _server(payload: dict[str, object]) -> NovaServer:
    return NovaServer(
        server_id=str(payload["id"]),
        name=str(payload["name"]),
        status=str(payload["status"]),
        project_id=str(payload["tenant_id"]),
        user_id=str(payload["user_id"]),
        created_at=str(payload["created"]),
        updated_at=str(payload["updated"]),
        host=payload.get("OS-EXT-SRV-ATTR:host")
        if isinstance(payload.get("OS-EXT-SRV-ATTR:host"), str)
        else None,
    )


def _next_marker(links: object) -> str | None:
    if not isinstance(links, list):
        return None
    for link in links:
        if isinstance(link, dict) and link.get("rel") == "next" and isinstance(link.get("href"), str):
            parsed = parse_qs(urlparse(link["href"]).query)
            marker = parsed.get("marker")
            return marker[0] if marker else None
    return None


def _invalid(context: AdapterRequestContext, message: str) -> OpenStackInvalidResponseError:
    return OpenStackInvalidResponseError(
        service="nova",
        message=message,
        status_code=None,
        request_id=context.request_id,
        correlation_id=context.correlation_id,
    )
```

- [ ] **Step 4: Run tests and verify GREEN**

Run:

```bash
cd backend && .venv/bin/python -m pytest tests/integrations/test_nova_adapter.py -q
```

Expected: `4 passed`.

---

### Task 5: Placement Adapter

**Files:**
- Create: `backend/src/cloud_ui/integrations/placement/__init__.py`
- Create: `backend/src/cloud_ui/integrations/placement/dto.py`
- Create: `backend/src/cloud_ui/integrations/placement/adapter.py`
- Test: `backend/tests/integrations/test_placement_adapter.py`

- [ ] **Step 1: Write failing Placement tests**

Create `backend/tests/integrations/test_placement_adapter.py`:

```python
from __future__ import annotations

import httpx

from cloud_ui.integrations.base import AdapterRequestContext, OpenStackTemporaryError
from cloud_ui.integrations.http import OpenStackHttpClient
from cloud_ui.integrations.placement.adapter import PlacementAdapter


def _context() -> AdapterRequestContext:
    return AdapterRequestContext(
        request_id="request-1",
        correlation_id="corr-1",
        cloud_id="lab",
        region_id="RegionOne",
    )


def _adapter(handler: httpx.MockTransport) -> PlacementAdapter:
    return PlacementAdapter(
        client=OpenStackHttpClient(
            service="placement",
            endpoint="https://placement.example",
            timeout_seconds=1.0,
            max_attempts=1,
            transport=handler,
        ),
        microversion="1.39",
    )


def test_placement_lists_resource_providers_with_microversion() -> None:
    seen_microversion = ""

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal seen_microversion
        seen_microversion = request.headers["openstack-api-version"]
        return httpx.Response(
            200,
            json={"resource_providers": [{"uuid": "rp-1", "name": "compute-1", "generation": 7}]},
        )

    providers = _adapter(httpx.MockTransport(handler)).list_resource_providers(_context())

    assert seen_microversion == "placement 1.39"
    assert providers[0].provider_uuid == "rp-1"
    assert providers[0].generation == 7


def test_placement_gets_inventory_and_usage() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/inventories"):
            return httpx.Response(
                200,
                json={"inventories": {"VCPU": {"total": 16, "reserved": 2, "allocation_ratio": 1.0}}},
            )
        if request.url.path.endswith("/usages"):
            return httpx.Response(200, json={"usages": {"VCPU": 4}})
        return httpx.Response(404)

    adapter = _adapter(httpx.MockTransport(handler))

    inventory = adapter.get_inventory(_context(), "rp-1")
    usage = adapter.get_usage(_context(), "rp-1")

    assert inventory["VCPU"].total == 16
    assert inventory["VCPU"].reserved == 2
    assert usage["VCPU"] == 4


def test_placement_preserves_temporary_error_for_graceful_degradation() -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(503, json={"error": "temporary"})

    try:
        _adapter(httpx.MockTransport(handler)).list_resource_providers(_context())
    except OpenStackTemporaryError as exc:
        assert exc.code == "openstack_temporary_error"
    else:
        raise AssertionError("expected temporary error")
```

- [ ] **Step 2: Run tests and verify RED**

Run:

```bash
cd backend && .venv/bin/python -m pytest tests/integrations/test_placement_adapter.py -q
```

Expected: fail because Placement adapter module does not exist.

- [ ] **Step 3: Implement Placement DTOs and adapter**

Create `backend/src/cloud_ui/integrations/placement/__init__.py`:

```python
"""Placement read-only adapter."""
```

Create `backend/src/cloud_ui/integrations/placement/dto.py`:

```python
from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class PlacementResourceProvider(BaseModel):
    model_config = ConfigDict(frozen=True)
    provider_uuid: str
    name: str
    generation: int


class PlacementInventory(BaseModel):
    model_config = ConfigDict(frozen=True)
    total: int
    reserved: int
    allocation_ratio: float
```

Create `backend/src/cloud_ui/integrations/placement/adapter.py`:

```python
from __future__ import annotations

from cloud_ui.integrations.base import AdapterRequestContext
from cloud_ui.integrations.http import OpenStackHttpClient
from cloud_ui.integrations.placement.dto import (
    PlacementInventory,
    PlacementResourceProvider,
)


class PlacementAdapter:
    def __init__(self, *, client: OpenStackHttpClient, microversion: str) -> None:
        self._client = client
        self._microversion = f"placement {microversion}"

    def list_resource_providers(
        self, context: AdapterRequestContext
    ) -> list[PlacementResourceProvider]:
        payload = self._client.get_json(
            "/resource_providers", context=context, microversion=self._microversion
        )
        return [
            PlacementResourceProvider(
                provider_uuid=item["uuid"],
                name=item["name"],
                generation=item["generation"],
            )
            for item in payload["resource_providers"]
        ]

    def get_inventory(
        self, context: AdapterRequestContext, provider_uuid: str
    ) -> dict[str, PlacementInventory]:
        payload = self._client.get_json(
            f"/resource_providers/{provider_uuid}/inventories",
            context=context,
            microversion=self._microversion,
        )
        return {
            resource_class: PlacementInventory(
                total=values["total"],
                reserved=values["reserved"],
                allocation_ratio=values["allocation_ratio"],
            )
            for resource_class, values in payload["inventories"].items()
        }

    def get_usage(self, context: AdapterRequestContext, provider_uuid: str) -> dict[str, int]:
        payload = self._client.get_json(
            f"/resource_providers/{provider_uuid}/usages",
            context=context,
            microversion=self._microversion,
        )
        return {resource_class: int(value) for resource_class, value in payload["usages"].items()}
```

- [ ] **Step 4: Run tests and verify GREEN**

Run:

```bash
cd backend && .venv/bin/python -m pytest tests/integrations/test_placement_adapter.py -q
```

Expected: `3 passed`.

---

### Task 6: Documentation, Registers And Final Gates

**Files:**
- Modify: `docs/generated/api-register.md`
- Modify: `docs/generated/integration-register.md`
- Modify: `docs/generated/risk-register.md`
- Modify: `docs/execplans/E03-openstack-adapters.md`

- [ ] **Step 1: Update API register**

In `docs/generated/api-register.md`, update external rows:

```markdown
| Keystone Identity API v3 | version discovery and sanitized catalog fixture mapping | observed `v3.14`; E03 contract fixture | E02/E03 | offline adapter contract implemented; optional live smoke pending safe read-only credential | `tests/integrations/test_keystone_adapter.py`; production PKI gap remains |
| Nova API | read-only instances, hypervisors, compute services, aggregates, server groups | microversion `2.96` | E03/E04 | offline adapter contract implemented; no browser endpoint/read model yet | `tests/integrations/test_nova_adapter.py`; optional live smoke pending |
| Placement API | read-only resource providers, inventory, usage | microversion `1.39` | E03/E04 | offline adapter contract implemented; enrichment only | `tests/integrations/test_placement_adapter.py`; optional live smoke pending |
```

- [ ] **Step 2: Update integration register**

In `docs/generated/integration-register.md`, update Keystone/Nova/Placement rows to mention:

```text
E03 offline contract tests implemented; safe live smoke remains pending until a read-only test credential is available outside git.
```

- [ ] **Step 3: Update risk register**

In `docs/generated/risk-register.md`, add or update E03 risk notes:

```markdown
| R-060 | Adapter contract drift from real OpenStack | E03 uses sanitized fixtures and fixed microversions; optional live smoke is pending without approved read-only credential. | Keep fixtures versioned, run smoke only with safe test credential, update microversions deliberately. | E03/E04 |
| R-061 | Token/header leakage in adapter errors | E03 errors redact details and tests assert sensitive values do not appear in repr. | Continue canary tests for future auth adapter. | E03 |
```

- [ ] **Step 4: Update ExecPlan progress**

In `docs/execplans/E03-openstack-adapters.md`, mark completed milestones and include final command results:

```markdown
- `cd backend && .venv/bin/python -m pytest tests/integrations -q` -> expected pass count.
- `git diff --check` -> no output, exit 0.
- `./scripts/secret-scan.sh` -> no output, exit 0.
- `make lint` -> pass.
- `make typecheck` -> pass.
- `make test` -> backend and frontend pass counts.
```

- [ ] **Step 5: Run E03-specific tests**

Run:

```bash
cd backend && .venv/bin/python -m pytest tests/integrations -q
```

Expected: all integration contract tests pass offline.

- [ ] **Step 6: Run final gates**

Run:

```bash
git diff --check
./scripts/secret-scan.sh
make lint
make typecheck
make test
```

Expected:

- `git diff --check` no output;
- `./scripts/secret-scan.sh` no output;
- `make lint` passes ruff, eslint and secret scan;
- `make typecheck` passes mypy and `tsc -b`;
- `make test` passes backend pytest and frontend vitest.

- [ ] **Step 7: Self-review**

Run:

```bash
rg -n "token|authorization|password|secret|credential|localStorage|sessionStorage|httpx|requests" backend/src/cloud_ui backend/tests/integrations docs/generated docs/execplans/E03-openstack-adapters.md
git diff --stat
git diff --name-only
```

Expected:

- sensitive words appear only in tests/docs asserting redaction or describing requirements;
- no frontend storage changes;
- no route handler imports `httpx`;
- diff contains only E03 adapter/tests/docs and runtime dependency/config changes.

- [ ] **Step 8: Commit**

Run:

```bash
git add backend/pyproject.toml backend/src/cloud_ui/config.py backend/src/cloud_ui/integrations backend/tests/integrations backend/tests/test_config.py docs/execplans/E03-openstack-adapters.md docs/generated/api-register.md docs/generated/integration-register.md docs/generated/risk-register.md
git commit -m "feat: add OpenStack adapter contracts"
```

Expected: commit succeeds.
