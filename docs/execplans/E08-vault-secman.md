# ExecPlan: E08 Vault SecMan Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development
> (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use
> checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the E08 Vault/SecMan contract slice: a typed backend secret provider, local test
double, Vault HTTP adapter contract tests, readiness evidence, and lab runbook for a permanent Vault
on the Ansible host.

**Architecture:** The portal keeps secrets server-side through a narrow `cloud_ui.secrets` boundary.
Tests use `LocalSecretProvider`; the live adapter uses Vault HTTP API with TLS verification, token file
input, typed errors, bounded retry and redacted diagnostics. Deployment of Vault itself remains a
manual, explicitly approved lab runbook step.

**Tech Stack:** Python 3.11, Pydantic, httpx `MockTransport`, FastAPI readiness, pytest, Ruff, mypy,
Markdown evidence under `docs/generated/`.

---

## Цель и наблюдаемый результат

После этого E08-среза оператор и разработчик смогут:

- увидеть в документации точный Vault/SecMan path contract для портала;
- запустить backend contract tests и проверить, что портал читает synthetic secrets только через
  серверный `SecretProvider`;
- убедиться, что forbidden/missing/sealed/malformed/timeout/TLS failure cases дают typed safe errors
  без утечки secret values;
- увидеть `vault` dependency в readiness только когда `CLOUD_UI_SECRETS_PROVIDER=vault`;
- использовать runbook для постоянного lab Vault на Ansible host `192.168.10.15`;
- сохранить sanitized evidence без root token, unseal keys, client token, private keys or real
  OpenStack credentials.

До этого среза `docs/generated/secret-inventory.md` содержит только draft lifecycle, а
`docs/generated/integration-register.md` помечает Vault endpoint/auth/path policy как unknown. В коде
нет `cloud_ui.secrets` boundary, Vault adapter, Vault-specific readiness or contract tests.

## Контекст и текущее состояние

- Repository root: `/Users/dmitry/Desktop/dawn`.
- Active worktree: `/Users/dmitry/Desktop/dawn/.worktrees/e08-vault-secman-design`.
- Branch: `e08-vault-secman-design`.
- Base commit: `64eaf41 Merge pull request #1 from lebtmalorny-rgb/e07-audit`.
- Design spec: `docs/superpowers/specs/2026-06-22-e08-vault-secman-design.md`.
- Design commit: `abc3f75 docs: add E08 vault secman design`.
- Current E08 task file: `tasks/E08_HARDENING.md`.
- Existing config: `backend/src/cloud_ui/config.py` uses Pydantic settings with production validators
  for mock identity and development cursor signing keys.
- Existing HTTP adapter pattern: `backend/src/cloud_ui/integrations/http.py` uses `httpx.Client`,
  `MockTransport` in tests, typed errors and bounded retry for safe methods.
- Existing redaction: `backend/src/cloud_ui/audit/redaction.py` and `cloud_ui.logging.redact_mapping`
  redact password/token/credential/authorization/cookie/private key values and DKB canaries.
- Existing readiness: `backend/src/cloud_ui/health.py` checks MariaDB and RabbitMQ and returns
  `HealthReport`.
- Existing docs to update: `docs/generated/secret-inventory.md`, `docs/generated/tls-matrix.md`,
  `docs/generated/integration-register.md`, `docs/generated/risk-register.md`,
  `docs/11_DKB_TRACEABILITY.md`.
- Existing all-in-one notes: Ansible host `192.168.10.15`; all-in-one host `192.168.10.14`; Kolla
  OpenStack TLS lab evidence exists for VIP `192.168.10.250`; E07 observed Fluentd running while
  OpenSearch/central logging are disabled.

## Scope

- Add backend `cloud_ui.secrets` package with models, typed errors, local provider and Vault HTTP
  provider.
- Add Pydantic settings for secret provider selection, Vault endpoint, token file, CA bundle, timeout,
  attempts and allowed path prefix.
- Add readiness integration for Vault only when Vault provider is selected.
- Add pytest coverage for local provider, Vault HTTP success, retry, forbidden, not found, sealed,
  uninitialized, malformed response, timeout and TLS/transport failures.
- Add redaction tests proving secret values and Vault tokens do not appear in exception `repr`, logs,
  readiness output or API response.
- Add generated docs/evidence templates for Vault policy, lab deployment runbook, TLS smoke,
  secret lifecycle and DKB gap status.
- Update DKB traceability without claiming production SecMan compliance.
- Keep lab deployment as a manual approval-gated milestone.

## Non-goals

- No production Vault/SecMan endpoint or credential.
- No real secret values in Git.
- No Vault root token, client token, unseal key, private key, `clouds.yaml`, openrc, `.env` or DB dump.
- No direct browser-to-Vault access.
- No automatic remote deployment from this plan.
- No Kolla password rotation automation.
- No claim that lab CA is corporate PKI evidence.
- No claim that single-node Raft proves HA.
- No claim that portal-to-Vault server TLS proves full ДКБ-22.02 mTLS closure.
- No new frontend feature in this slice; browser behavior is only absence of secret exposure.

## Требования и ограничения

- Browser talks only to frontend and portal BFF/API.
- Secret paths come from trusted server-side config/code, not user input.
- Vault token is read from a file path and never from a committed file.
- `VaultSecretProvider` must verify TLS by default. Tests can inject `MockTransport`; production config
  cannot disable verification.
- Retry is limited to GET reads and only for temporary network/5xx/429/timeout failures.
- Forbidden, missing, sealed, uninitialized and malformed responses are permanent typed errors.
- Safe errors include code, correlation ID, provider and path alias; they do not include secret values,
  token content, raw response body or request headers.
- Readiness exposes dependency status and safe detail only.
- Local provider is allowed for local/test. Production rejects it.
- No migration is required; the secret provider reads external secrets and does not add tables.
- All docs/evidence must be sanitized.

## Связь с ДКБ

- ДКБ-22.02/24: this plan adds Vault server TLS contract, TLS negative tests at adapter level and lab
  TLS smoke instructions. Full mTLS remains owner decision and must stay marked as gap.
- ДКБ-13/51: this plan extends secret redaction to Vault adapter errors, readiness and evidence.
- ДКБ-46-53: this plan records Vault audit device/runbook evidence for secret-store access. It does
  not close full SIEM/FIM or host audit controls.
- ДКБ-55: this plan creates the portal Vault/SecMan adapter contract and lab service runbook.
- ДКБ-56: this plan documents lifecycle fields for portal secret classes and keeps Kolla/service
  rotation as an external deployment-pipeline gap.
- ДКБ-69/70: no new portal runtime image dependency is added. Vault host package/binary evidence is
  separate from portal container hardening and does not close image hardening.
- ДКБ-77: Vault endpoint, allowed paths and unused denied paths are documented in integration registers.

## Milestones

1. Contract and test double: create `cloud_ui.secrets` models/errors/local provider with unit tests.
2. Vault HTTP adapter: implement bounded read contract with `httpx.MockTransport` tests.
3. Config and readiness: wire settings and health dependency without leaking values.
4. Documentation and evidence: update generated docs, DKB traceability and risk register.
5. Optional lab runbook execution: after explicit approval, inspect/deploy Vault on `192.168.10.15`
   and save sanitized evidence.
6. Final verification and review: run lint/typecheck/tests/security and update this ExecPlan.

## Progress

- [x] 2026-06-22: E08 Vault/SecMan design spec written and committed. Evidence: commit
  `abc3f75 docs: add E08 vault secman design`.
- [x] 2026-06-22: User approved written spec. Evidence: conversation review gate response `ок`.
- [x] 2026-06-22: Implementation ExecPlan created. Evidence: this document.
- [ ] Contract and test double implemented.
- [ ] Vault HTTP adapter implemented.
- [ ] Config/readiness integration implemented.
- [ ] Documentation/evidence updated.
- [ ] Optional lab runbook execution completed or explicitly skipped.
- [ ] Final verification completed.

## Неожиданные открытия

- No unexpected implementation facts yet for this plan.

## Журнал решений

- 2026-06-22: Store the plan in `docs/execplans/E08-vault-secman.md` rather than the default
  `docs/superpowers/plans/` path because `PLANS.md` is the repository authority for E00-E12 ExecPlans.
- 2026-06-22: Use a token file setting for Vault auth. Alternative: token environment variable.
  Reason: environment variables are easier to leak through process inspection and shell history.
  Consequence: deploy/runbook must create a protected token file outside Git.
- 2026-06-22: Reject `local` secrets provider in production settings. Alternative: allow local provider
  with production explicit opt-in. Reason: E08 exists to avoid dummy production secret handling.
  Consequence: production smoke must configure Vault provider and non-dev cursor signing keys.
- 2026-06-22: Keep mTLS off by default in code until owner policy is known. Alternative: require client
  certificate settings now. Reason: mTLS authorization model is an E08/E09 owner decision. Consequence:
  TLS matrix must state server TLS plus Vault auth and keep mTLS gap open.

## File Structure

- Create `backend/src/cloud_ui/secrets/__init__.py`: package exports.
- Create `backend/src/cloud_ui/secrets/models.py`: secret references, allowed path policy, document
  model and safe path alias.
- Create `backend/src/cloud_ui/secrets/errors.py`: typed secret provider errors with redacted `repr`.
- Create `backend/src/cloud_ui/secrets/provider.py`: `SecretProvider` protocol and
  `LocalSecretProvider`.
- Create `backend/src/cloud_ui/secrets/vault.py`: Vault HTTP adapter and retry/status mapping.
- Create `backend/src/cloud_ui/secrets/readiness.py`: Vault readiness probe helper.
- Modify `backend/src/cloud_ui/config.py`: settings and production validators.
- Modify `backend/src/cloud_ui/health.py`: optional secret provider readiness dependency.
- Modify `backend/src/cloud_ui/api.py`: pass settings into readiness as today; no route handler uses
  Vault directly.
- Test `backend/tests/secrets/test_provider.py`: local provider, policy and safe errors.
- Test `backend/tests/secrets/test_vault_adapter.py`: Vault HTTP success and failure contract.
- Test `backend/tests/secrets/test_readiness.py`: readiness safe output.
- Modify `backend/tests/test_config.py`: env cleanup and production validation.
- Modify `backend/tests/test_api_health.py`: optional Vault dependency in `/health/ready`.
- Create `docs/generated/e08-vault-policy.hcl`: lab portal policy with allowed paths only.
- Create `docs/generated/e08-vault-lab-runbook.md`: permanent Vault runbook for Ansible host.
- Create `docs/generated/e08-vault-evidence-template.md`: sanitized evidence checklist.
- Modify `docs/generated/secret-inventory.md`, `docs/generated/tls-matrix.md`,
  `docs/generated/integration-register.md`, `docs/generated/risk-register.md`,
  `docs/11_DKB_TRACEABILITY.md`.

## Детальный план реализации

### Task 1: Contract Models, Errors And Local Provider

**Files:**
- Create: `backend/src/cloud_ui/secrets/__init__.py`
- Create: `backend/src/cloud_ui/secrets/models.py`
- Create: `backend/src/cloud_ui/secrets/errors.py`
- Create: `backend/src/cloud_ui/secrets/provider.py`
- Test: `backend/tests/secrets/test_provider.py`

- [ ] **Step 1: Write failing tests**

Create `backend/tests/secrets/test_provider.py`:

```python
from __future__ import annotations

import pytest

from cloud_ui.secrets.errors import SecretForbiddenError, SecretNotFoundError
from cloud_ui.secrets.models import SecretReference, SecretSchema
from cloud_ui.secrets.provider import LocalSecretProvider


def test_local_provider_reads_allowed_secret_with_schema() -> None:
    provider = LocalSecretProvider(
        documents={
            "kv/data/cloud-ui/local/session": {
                "signing_key": "synthetic-session-key",
                "active": True,
            }
        },
        allowed_prefix="kv/data/cloud-ui/local/",
    )

    document = provider.get(
        SecretReference(path="kv/data/cloud-ui/local/session", alias="session"),
        SecretSchema(required_keys=("signing_key", "active")),
        correlation_id="corr-1",
    )

    assert document.alias == "session"
    assert document.data == {"signing_key": "synthetic-session-key", "active": True}


def test_local_provider_denies_path_outside_allowed_prefix() -> None:
    provider = LocalSecretProvider(
        documents={"kv/data/other-service/local/test": {"value": "DKB_CANARY"}},
        allowed_prefix="kv/data/cloud-ui/local/",
    )

    with pytest.raises(SecretForbiddenError) as exc_info:
        provider.get(
            SecretReference(path="kv/data/other-service/local/test", alias="other"),
            SecretSchema(required_keys=("value",)),
            correlation_id="corr-2",
        )

    assert exc_info.value.code == "secret_forbidden"
    assert "DKB_CANARY" not in repr(exc_info.value)
    assert "kv/data/other-service" not in repr(exc_info.value)


def test_local_provider_reports_missing_secret_without_value_leak() -> None:
    provider = LocalSecretProvider(documents={}, allowed_prefix="kv/data/cloud-ui/local/")

    with pytest.raises(SecretNotFoundError) as exc_info:
        provider.get(
            SecretReference(path="kv/data/cloud-ui/local/session", alias="session"),
            SecretSchema(required_keys=("signing_key",)),
            correlation_id="corr-3",
        )

    assert exc_info.value.code == "secret_not_found"
    assert "session" in repr(exc_info.value)
    assert "signing_key" not in repr(exc_info.value)
```

- [ ] **Step 2: Run tests to verify RED**

Run:

```bash
cd backend && .venv/bin/python -m pytest tests/secrets/test_provider.py -q
```

Expected: FAIL during import because `cloud_ui.secrets` does not exist.

- [ ] **Step 3: Implement models and errors**

Create `backend/src/cloud_ui/secrets/models.py`:

```python
from __future__ import annotations

from typing import TypeAlias

from pydantic import BaseModel, ConfigDict, Field

SecretScalar: TypeAlias = str | int | float | bool


class SecretReference(BaseModel):
    model_config = ConfigDict(frozen=True)

    path: str = Field(min_length=1)
    alias: str = Field(min_length=1)

    def is_allowed(self, allowed_prefix: str) -> bool:
        return self.path.startswith(allowed_prefix)


class SecretSchema(BaseModel):
    model_config = ConfigDict(frozen=True)

    required_keys: tuple[str, ...]

    def validate_data(self, data: dict[str, SecretScalar]) -> dict[str, SecretScalar]:
        missing = [key for key in self.required_keys if key not in data]
        if missing:
            raise ValueError("secret document is missing required keys")
        return data


class SecretDocument(BaseModel):
    model_config = ConfigDict(frozen=True)

    alias: str
    data: dict[str, SecretScalar]
```

Create `backend/src/cloud_ui/secrets/errors.py`:

```python
from __future__ import annotations

from typing import Any

from cloud_ui.logging import redact_mapping


class SecretProviderError(Exception):
    code = "secret_provider_error"

    def __init__(
        self,
        *,
        message: str,
        alias: str,
        correlation_id: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        self.message = message
        self.alias = alias
        self.correlation_id = correlation_id
        self.details = redact_mapping(details or {})
        super().__init__(message)

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}(code={self.code!r}, alias={self.alias!r}, "
            f"correlation_id={self.correlation_id!r}, details={self.details!r})"
        )


class SecretForbiddenError(SecretProviderError):
    code = "secret_forbidden"


class SecretNotFoundError(SecretProviderError):
    code = "secret_not_found"


class SecretUnavailableError(SecretProviderError):
    code = "secret_unavailable"


class SecretTimeoutError(SecretProviderError):
    code = "secret_timeout"


class SecretInvalidResponseError(SecretProviderError):
    code = "secret_invalid_response"
```

- [ ] **Step 4: Implement provider protocol and local provider**

Create `backend/src/cloud_ui/secrets/provider.py`:

```python
from __future__ import annotations

from typing import Protocol

from cloud_ui.secrets.errors import SecretForbiddenError, SecretInvalidResponseError, SecretNotFoundError
from cloud_ui.secrets.models import SecretDocument, SecretReference, SecretScalar, SecretSchema


class SecretProvider(Protocol):
    def get(
        self,
        reference: SecretReference,
        schema: SecretSchema,
        *,
        correlation_id: str,
    ) -> SecretDocument:
        raise NotImplementedError


class LocalSecretProvider:
    def __init__(
        self,
        *,
        documents: dict[str, dict[str, SecretScalar]],
        allowed_prefix: str,
    ) -> None:
        self._documents = documents
        self._allowed_prefix = allowed_prefix

    def get(
        self,
        reference: SecretReference,
        schema: SecretSchema,
        *,
        correlation_id: str,
    ) -> SecretDocument:
        if not reference.is_allowed(self._allowed_prefix):
            raise SecretForbiddenError(
                message="Secret path is outside the allowed prefix",
                alias=reference.alias,
                correlation_id=correlation_id,
                details={"path_alias": reference.alias},
            )

        payload = self._documents.get(reference.path)
        if payload is None:
            raise SecretNotFoundError(
                message="Secret was not found",
                alias=reference.alias,
                correlation_id=correlation_id,
            )

        try:
            data = schema.validate_data(payload)
        except ValueError as exc:
            raise SecretInvalidResponseError(
                message="Secret document failed schema validation",
                alias=reference.alias,
                correlation_id=correlation_id,
                details={"exception": exc.__class__.__name__},
            ) from exc
        return SecretDocument(alias=reference.alias, data=data)
```

Create `backend/src/cloud_ui/secrets/__init__.py`:

```python
from cloud_ui.secrets.models import SecretDocument, SecretReference, SecretSchema
from cloud_ui.secrets.provider import LocalSecretProvider, SecretProvider

__all__ = [
    "LocalSecretProvider",
    "SecretDocument",
    "SecretProvider",
    "SecretReference",
    "SecretSchema",
]
```

- [ ] **Step 5: Run tests and checks**

Run:

```bash
cd backend && .venv/bin/python -m pytest tests/secrets/test_provider.py -q
cd backend && .venv/bin/python -m ruff check src/cloud_ui/secrets tests/secrets
cd backend && .venv/bin/python -m mypy src/cloud_ui/secrets
git diff --check
```

Expected: provider tests pass; Ruff passes; mypy passes; diff check is clean.

- [ ] **Step 6: Commit**

```bash
git add backend/src/cloud_ui/secrets backend/tests/secrets/test_provider.py
git commit -m "feat: add secret provider contract"
```

### Task 2: Vault HTTP Adapter Contract

**Files:**
- Create: `backend/src/cloud_ui/secrets/vault.py`
- Test: `backend/tests/secrets/test_vault_adapter.py`

- [ ] **Step 1: Write failing Vault adapter tests**

Create `backend/tests/secrets/test_vault_adapter.py`:

```python
from __future__ import annotations

from pathlib import Path

import httpx
import pytest

from cloud_ui.secrets.errors import (
    SecretForbiddenError,
    SecretInvalidResponseError,
    SecretNotFoundError,
    SecretTimeoutError,
    SecretUnavailableError,
)
from cloud_ui.secrets.models import SecretReference, SecretSchema
from cloud_ui.secrets.vault import VaultSecretProvider


def _token_file(tmp_path: Path) -> Path:
    token_path = tmp_path / "vault-token"
    token_path.write_text("synthetic-vault-token", encoding="utf-8")
    token_path.chmod(0o600)
    return token_path


def test_vault_provider_reads_kv_v2_secret(tmp_path: Path) -> None:
    seen_headers: dict[str, str] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen_headers["x-vault-token"] = request.headers["x-vault-token"]
        seen_headers["x-correlation-id"] = request.headers["x-correlation-id"]
        assert request.url.path == "/v1/kv/data/cloud-ui/local/session"
        return httpx.Response(
            200,
            json={"data": {"data": {"signing_key": "synthetic-session-key"}}},
        )

    provider = VaultSecretProvider(
        address="https://vault.lab.local:8200",
        token_file=_token_file(tmp_path),
        allowed_prefix="kv/data/cloud-ui/local/",
        timeout_seconds=1.0,
        max_attempts=1,
        transport=httpx.MockTransport(handler),
    )

    document = provider.get(
        SecretReference(path="kv/data/cloud-ui/local/session", alias="session"),
        SecretSchema(required_keys=("signing_key",)),
        correlation_id="corr-1",
    )

    assert document.data == {"signing_key": "synthetic-session-key"}
    assert seen_headers == {
        "x-vault-token": "synthetic-vault-token",
        "x-correlation-id": "corr-1",
    }


def test_vault_provider_does_not_retry_forbidden(tmp_path: Path) -> None:
    calls = 0

    def handler(_request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(403, json={"errors": ["denied DKB_CANARY"]})

    provider = VaultSecretProvider(
        address="https://vault.lab.local:8200",
        token_file=_token_file(tmp_path),
        allowed_prefix="kv/data/cloud-ui/local/",
        timeout_seconds=1.0,
        max_attempts=3,
        transport=httpx.MockTransport(handler),
    )

    with pytest.raises(SecretForbiddenError) as exc_info:
        provider.get(
            SecretReference(path="kv/data/cloud-ui/local/session", alias="session"),
            SecretSchema(required_keys=("signing_key",)),
            correlation_id="corr-2",
        )

    assert calls == 1
    assert "DKB_CANARY" not in repr(exc_info.value)
    assert "synthetic-vault-token" not in repr(exc_info.value)


def test_vault_provider_maps_missing_secret(tmp_path: Path) -> None:
    provider = VaultSecretProvider(
        address="https://vault.lab.local:8200",
        token_file=_token_file(tmp_path),
        allowed_prefix="kv/data/cloud-ui/local/",
        timeout_seconds=1.0,
        max_attempts=1,
        transport=httpx.MockTransport(lambda _request: httpx.Response(404, json={"errors": []})),
    )

    with pytest.raises(SecretNotFoundError):
        provider.get(
            SecretReference(path="kv/data/cloud-ui/local/session", alias="session"),
            SecretSchema(required_keys=("signing_key",)),
            correlation_id="corr-3",
        )


def test_vault_provider_retries_503_then_succeeds(tmp_path: Path) -> None:
    calls = 0

    def handler(_request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        if calls == 1:
            return httpx.Response(503, json={"errors": ["sealed"]})
        return httpx.Response(200, json={"data": {"data": {"value": "ok"}}})

    provider = VaultSecretProvider(
        address="https://vault.lab.local:8200",
        token_file=_token_file(tmp_path),
        allowed_prefix="kv/data/cloud-ui/local/",
        timeout_seconds=1.0,
        max_attempts=2,
        transport=httpx.MockTransport(handler),
    )

    assert provider.get(
        SecretReference(path="kv/data/cloud-ui/local/siem", alias="siem"),
        SecretSchema(required_keys=("value",)),
        correlation_id="corr-4",
    ).data == {"value": "ok"}
    assert calls == 2


def test_vault_provider_maps_timeout_after_attempts(tmp_path: Path) -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("timeout")

    provider = VaultSecretProvider(
        address="https://vault.lab.local:8200",
        token_file=_token_file(tmp_path),
        allowed_prefix="kv/data/cloud-ui/local/",
        timeout_seconds=1.0,
        max_attempts=1,
        transport=httpx.MockTransport(handler),
    )

    with pytest.raises(SecretTimeoutError):
        provider.get(
            SecretReference(path="kv/data/cloud-ui/local/session", alias="session"),
            SecretSchema(required_keys=("signing_key",)),
            correlation_id="corr-5",
        )


def test_vault_provider_rejects_malformed_payload(tmp_path: Path) -> None:
    provider = VaultSecretProvider(
        address="https://vault.lab.local:8200",
        token_file=_token_file(tmp_path),
        allowed_prefix="kv/data/cloud-ui/local/",
        timeout_seconds=1.0,
        max_attempts=1,
        transport=httpx.MockTransport(lambda _request: httpx.Response(200, json={"data": {}})),
    )

    with pytest.raises(SecretInvalidResponseError):
        provider.get(
            SecretReference(path="kv/data/cloud-ui/local/session", alias="session"),
            SecretSchema(required_keys=("signing_key",)),
            correlation_id="corr-6",
        )


def test_vault_provider_maps_transport_tls_failure_without_leak(tmp_path: Path) -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("certificate verify failed synthetic-vault-token")

    provider = VaultSecretProvider(
        address="https://vault.lab.local:8200",
        token_file=_token_file(tmp_path),
        allowed_prefix="kv/data/cloud-ui/local/",
        timeout_seconds=1.0,
        max_attempts=1,
        transport=httpx.MockTransport(handler),
    )

    with pytest.raises(SecretUnavailableError) as exc_info:
        provider.get(
            SecretReference(path="kv/data/cloud-ui/local/session", alias="session"),
            SecretSchema(required_keys=("signing_key",)),
            correlation_id="corr-7",
        )

    assert "synthetic-vault-token" not in repr(exc_info.value)
```

- [ ] **Step 2: Run tests to verify RED**

Run:

```bash
cd backend && .venv/bin/python -m pytest tests/secrets/test_vault_adapter.py -q
```

Expected: FAIL because `cloud_ui.secrets.vault` does not exist.

- [ ] **Step 3: Implement VaultSecretProvider**

Create `backend/src/cloud_ui/secrets/vault.py`:

```python
from __future__ import annotations

from pathlib import Path
from typing import Any

import httpx

from cloud_ui.secrets.errors import (
    SecretForbiddenError,
    SecretInvalidResponseError,
    SecretNotFoundError,
    SecretTimeoutError,
    SecretUnavailableError,
)
from cloud_ui.secrets.models import SecretDocument, SecretReference, SecretScalar, SecretSchema


class VaultSecretProvider:
    def __init__(
        self,
        *,
        address: str,
        token_file: Path,
        allowed_prefix: str,
        timeout_seconds: float,
        max_attempts: int,
        ca_bundle: Path | None = None,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        verify: str | bool = str(ca_bundle) if ca_bundle is not None else True
        self._client = httpx.Client(
            base_url=address.rstrip("/"),
            timeout=timeout_seconds,
            verify=verify,
            transport=transport,
            follow_redirects=False,
        )
        self._token_file = token_file
        self._allowed_prefix = allowed_prefix
        self._max_attempts = max_attempts

    def get(
        self,
        reference: SecretReference,
        schema: SecretSchema,
        *,
        correlation_id: str,
    ) -> SecretDocument:
        if not reference.is_allowed(self._allowed_prefix):
            raise SecretForbiddenError(
                message="Secret path is outside the allowed prefix",
                alias=reference.alias,
                correlation_id=correlation_id,
            )

        attempt = 1
        while True:
            try:
                response = self._client.get(
                    f"/v1/{reference.path}",
                    headers={
                        "accept": "application/json",
                        "x-vault-token": self._read_token(),
                        "x-correlation-id": correlation_id,
                    },
                )
                self._raise_for_status(response, reference, correlation_id)
                return self._document_from_response(response, reference, schema, correlation_id)
            except httpx.TimeoutException as exc:
                error: Exception = SecretTimeoutError(
                    message="Vault request timed out",
                    alias=reference.alias,
                    correlation_id=correlation_id,
                    details={"exception": exc.__class__.__name__},
                )
            except httpx.RequestError as exc:
                error = SecretUnavailableError(
                    message="Vault request failed before a response was received",
                    alias=reference.alias,
                    correlation_id=correlation_id,
                    details={"exception": exc.__class__.__name__},
                )
            except SecretUnavailableError as exc:
                error = exc

            if attempt < self._max_attempts:
                attempt += 1
                continue
            raise error

    def _read_token(self) -> str:
        return self._token_file.read_text(encoding="utf-8").strip()

    def _raise_for_status(
        self,
        response: httpx.Response,
        reference: SecretReference,
        correlation_id: str,
    ) -> None:
        status = response.status_code
        if status < 400:
            return
        if status == 403:
            raise SecretForbiddenError(
                message="Vault denied access to the secret",
                alias=reference.alias,
                correlation_id=correlation_id,
                details={"status_code": status},
            )
        if status == 404:
            raise SecretNotFoundError(
                message="Vault secret was not found",
                alias=reference.alias,
                correlation_id=correlation_id,
                details={"status_code": status},
            )
        if status in {429, 500, 502, 503, 504}:
            raise SecretUnavailableError(
                message="Vault is temporarily unavailable",
                alias=reference.alias,
                correlation_id=correlation_id,
                details={"status_code": status},
            )
        raise SecretInvalidResponseError(
            message="Vault returned an unsupported error status",
            alias=reference.alias,
            correlation_id=correlation_id,
            details={"status_code": status},
        )

    def _document_from_response(
        self,
        response: httpx.Response,
        reference: SecretReference,
        schema: SecretSchema,
        correlation_id: str,
    ) -> SecretDocument:
        try:
            payload = response.json()
            raw_data = payload["data"]["data"]
        except (KeyError, TypeError, ValueError) as exc:
            raise SecretInvalidResponseError(
                message="Vault response is not a valid KV v2 document",
                alias=reference.alias,
                correlation_id=correlation_id,
                details={"exception": exc.__class__.__name__},
            ) from exc
        if not isinstance(raw_data, dict):
            raise SecretInvalidResponseError(
                message="Vault KV v2 data is not an object",
                alias=reference.alias,
                correlation_id=correlation_id,
            )
        data = self._normalize_data(raw_data, reference, correlation_id)
        try:
            return SecretDocument(alias=reference.alias, data=schema.validate_data(data))
        except ValueError as exc:
            raise SecretInvalidResponseError(
                message="Vault secret failed schema validation",
                alias=reference.alias,
                correlation_id=correlation_id,
                details={"exception": exc.__class__.__name__},
            ) from exc

    def _normalize_data(
        self,
        raw_data: dict[str, Any],
        reference: SecretReference,
        correlation_id: str,
    ) -> dict[str, SecretScalar]:
        result: dict[str, SecretScalar] = {}
        for key, value in raw_data.items():
            if isinstance(value, str | int | float | bool):
                result[key] = value
            else:
                raise SecretInvalidResponseError(
                    message="Vault secret contains unsupported value type",
                    alias=reference.alias,
                    correlation_id=correlation_id,
                    details={"key": key, "value_type": value.__class__.__name__},
                )
        return result
```

- [ ] **Step 4: Run tests and checks**

Run:

```bash
cd backend && .venv/bin/python -m pytest tests/secrets -q
cd backend && .venv/bin/python -m ruff check src/cloud_ui/secrets tests/secrets
cd backend && .venv/bin/python -m mypy src/cloud_ui/secrets
git diff --check
```

Expected: secrets tests pass; Ruff passes; mypy passes; diff check is clean.

- [ ] **Step 5: Commit**

```bash
git add backend/src/cloud_ui/secrets backend/tests/secrets
git commit -m "feat: add vault secret provider adapter"
```

### Task 3: Settings And Readiness Integration

**Files:**
- Modify: `backend/src/cloud_ui/config.py`
- Modify: `backend/src/cloud_ui/health.py`
- Create: `backend/src/cloud_ui/secrets/readiness.py`
- Modify: `backend/tests/test_config.py`
- Modify: `backend/tests/test_api_health.py`
- Test: `backend/tests/secrets/test_readiness.py`

- [ ] **Step 1: Write failing config and readiness tests**

Add environment names to `_CLOUD_UI_ENVIRONMENT_NAMES` in `backend/tests/test_config.py` and append
these tests:

```python
def test_settings_accept_vault_secret_provider(tmp_path) -> None:
    token_path = tmp_path / "vault-token"
    token_path.write_text("synthetic-token", encoding="utf-8")

    settings = Settings(
        database_url="mysql+pymysql://cloud_ui:cloud_ui_dev@db:3306/cloud_ui",
        rabbitmq_url="amqp://cloud_ui:cloud_ui_dev@rabbitmq:5672/%2Fcloud-ui",
        secrets_provider="vault",
        vault_addr="https://192.168.10.15:8200",
        vault_token_file=token_path,
        vault_allowed_prefix="kv/data/cloud-ui/local/",
    )

    assert settings.secrets_provider == "vault"
    assert settings.vault_addr is not None
    assert settings.vault_token_file == token_path


def test_settings_reject_local_secret_provider_in_production() -> None:
    with pytest.raises(ValidationError, match="local secret provider"):
        Settings(
            database_url="mysql+pymysql://cloud_ui:cloud_ui_dev@db:3306/cloud_ui",
            rabbitmq_url="amqp://cloud_ui:cloud_ui_dev@rabbitmq:5672/%2Fcloud-ui",
            environment="production",
            identity_provider="external",
            mock_identity_enabled=False,
            inventory_cursor_signing_key="production-inventory-cursor-key",
            operation_cursor_signing_key="production-operation-cursor-key",
            audit_cursor_signing_key="production-audit-cursor-key",
            secrets_provider="local",
        )


def test_settings_require_vault_endpoint_and_token_file_when_vault_enabled() -> None:
    with pytest.raises(ValidationError, match="Vault address and token file"):
        Settings(
            database_url="mysql+pymysql://cloud_ui:cloud_ui_dev@db:3306/cloud_ui",
            rabbitmq_url="amqp://cloud_ui:cloud_ui_dev@rabbitmq:5672/%2Fcloud-ui",
            secrets_provider="vault",
        )
```

Create `backend/tests/secrets/test_readiness.py`:

```python
from __future__ import annotations

from cloud_ui.secrets.errors import SecretUnavailableError
from cloud_ui.secrets.models import SecretDocument, SecretReference, SecretSchema
from cloud_ui.secrets.readiness import build_secret_readiness_probe


class _OkProvider:
    def get(
        self,
        reference: SecretReference,
        schema: SecretSchema,
        *,
        correlation_id: str,
    ) -> SecretDocument:
        return SecretDocument(alias=reference.alias, data={"value": "synthetic"})


class _FailingProvider:
    def get(
        self,
        reference: SecretReference,
        schema: SecretSchema,
        *,
        correlation_id: str,
    ) -> SecretDocument:
        raise SecretUnavailableError(
            message="Vault unavailable DKB_CANARY",
            alias=reference.alias,
            correlation_id=correlation_id,
            details={"token": "synthetic-token"},
        )


def test_secret_readiness_probe_returns_safe_ok_detail() -> None:
    probe = build_secret_readiness_probe(
        provider=_OkProvider(),
        reference=SecretReference(path="kv/data/cloud-ui/local/session", alias="session"),
        schema=SecretSchema(required_keys=("value",)),
    )

    assert probe() == "vault reachable: session"


def test_secret_readiness_probe_returns_safe_failure_detail() -> None:
    probe = build_secret_readiness_probe(
        provider=_FailingProvider(),
        reference=SecretReference(path="kv/data/cloud-ui/local/session", alias="session"),
        schema=SecretSchema(required_keys=("value",)),
    )

    assert probe() == "vault unavailable: secret_unavailable"
```

Add a health test in `backend/tests/test_api_health.py` after existing readiness tests:

```python
def test_readiness_can_include_vault_dependency() -> None:
    def check() -> HealthReport:
        return HealthReport(
            status="degraded",
            dependencies={
                "database": DependencyState(status="ok", detail="reachable"),
                "rabbitmq": DependencyState(status="ok", detail="reachable"),
                "vault": DependencyState(status="down", detail="vault unavailable: secret_unavailable"),
            },
        )

    app = create_app(readiness_check=check)
    client = TestClient(app)

    response = client.get("/health/ready")

    assert response.status_code == 503
    assert response.json()["dependencies"]["vault"] == {
        "status": "down",
        "detail": "vault unavailable: secret_unavailable",
    }
```

- [ ] **Step 2: Run tests to verify RED**

Run:

```bash
cd backend && .venv/bin/python -m pytest tests/test_config.py tests/secrets/test_readiness.py tests/test_api_health.py -q
```

Expected: FAIL because settings fields and readiness helper are missing.

- [ ] **Step 3: Implement settings**

Modify `backend/src/cloud_ui/config.py`:

```python
from pathlib import Path
```

Add literal:

```python
SecretProviderName = Literal["local", "vault"]
```

Add settings fields inside `Settings`:

```python
    secrets_provider: SecretProviderName = Field(default="local")
    vault_addr: AnyUrl | None = None
    vault_token_file: Path | None = None
    vault_ca_bundle: Path | None = None
    vault_timeout_seconds: float = Field(default=2.0, gt=0)
    vault_max_attempts: int = Field(default=2, ge=1, le=5)
    vault_allowed_prefix: str = Field(default="kv/data/cloud-ui/local/", min_length=1)
```

Extend `reject_unsafe_production_settings`:

```python
        if self.environment == "production" and self.secrets_provider == "local":
            raise ValueError("Production cannot use the local secret provider")
        if self.secrets_provider == "vault" and (
            self.vault_addr is None or self.vault_token_file is None
        ):
            raise ValueError("Vault address and token file are required when Vault is enabled")
```

- [ ] **Step 4: Implement secret readiness helper**

Create `backend/src/cloud_ui/secrets/readiness.py`:

```python
from __future__ import annotations

from collections.abc import Callable

from cloud_ui.secrets.errors import SecretProviderError
from cloud_ui.secrets.models import SecretReference, SecretSchema
from cloud_ui.secrets.provider import SecretProvider


def build_secret_readiness_probe(
    *,
    provider: SecretProvider,
    reference: SecretReference,
    schema: SecretSchema,
) -> Callable[[], str]:
    def probe() -> str:
        try:
            provider.get(reference, schema, correlation_id="readiness-vault")
        except SecretProviderError as exc:
            return f"vault unavailable: {exc.code}"
        return f"vault reachable: {reference.alias}"

    return probe
```

- [ ] **Step 5: Wire optional Vault dependency in health**

Modify `backend/src/cloud_ui/health.py` so `build_readiness_check(settings)` adds a `vault` dependency
only when `settings.secrets_provider == "vault"`. Construct `VaultSecretProvider` with settings and a
readiness reference:

```python
from cloud_ui.secrets.models import SecretReference, SecretSchema
from cloud_ui.secrets.readiness import build_secret_readiness_probe
from cloud_ui.secrets.vault import VaultSecretProvider
```

Inside `check()` after `dependencies = {...}`:

```python
        if settings.secrets_provider == "vault":
            assert settings.vault_addr is not None
            assert settings.vault_token_file is not None
            vault_provider = VaultSecretProvider(
                address=settings.vault_addr.unicode_string(),
                token_file=settings.vault_token_file,
                ca_bundle=settings.vault_ca_bundle,
                allowed_prefix=settings.vault_allowed_prefix,
                timeout_seconds=settings.vault_timeout_seconds,
                max_attempts=settings.vault_max_attempts,
            )
            dependencies["vault"] = _probe_dependency(
                build_secret_readiness_probe(
                    provider=vault_provider,
                    reference=SecretReference(
                        path=f"{settings.vault_allowed_prefix}session",
                        alias="session",
                    ),
                    schema=SecretSchema(required_keys=("value",)),
                )
            )
```

This readiness probe expects a synthetic `value` key in the lab session secret. The runbook must write
that key for smoke evidence.

- [ ] **Step 6: Run tests and checks**

Run:

```bash
cd backend && .venv/bin/python -m pytest tests/test_config.py tests/test_api_health.py tests/secrets -q
cd backend && .venv/bin/python -m ruff check src/cloud_ui/config.py src/cloud_ui/health.py src/cloud_ui/secrets tests/test_config.py tests/test_api_health.py tests/secrets
cd backend && .venv/bin/python -m mypy src/cloud_ui/config.py src/cloud_ui/health.py src/cloud_ui/secrets
git diff --check
```

Expected: tests pass; Ruff passes; mypy passes; diff check is clean.

- [ ] **Step 7: Commit**

```bash
git add backend/src/cloud_ui/config.py backend/src/cloud_ui/health.py backend/src/cloud_ui/secrets backend/tests/test_config.py backend/tests/test_api_health.py backend/tests/secrets
git commit -m "feat: add vault readiness configuration"
```

### Task 4: Vault Policy, Runbook And Generated Evidence

**Files:**
- Create: `docs/generated/e08-vault-policy.hcl`
- Create: `docs/generated/e08-vault-lab-runbook.md`
- Create: `docs/generated/e08-vault-evidence-template.md`
- Modify: `docs/generated/secret-inventory.md`
- Modify: `docs/generated/tls-matrix.md`
- Modify: `docs/generated/integration-register.md`
- Modify: `docs/generated/risk-register.md`
- Modify: `docs/11_DKB_TRACEABILITY.md`

- [ ] **Step 1: Add Vault policy artifact**

Create `docs/generated/e08-vault-policy.hcl`:

```hcl
# E08 lab portal policy for synthetic Cloud UI secrets.
# This file contains no secret values.

path "kv/data/cloud-ui/local/*" {
  capabilities = ["read"]
}

path "kv/metadata/cloud-ui/local/*" {
  capabilities = ["read", "list"]
}
```

- [ ] **Step 2: Add lab runbook**

Create `docs/generated/e08-vault-lab-runbook.md` with these sections and exact commands:

````markdown
# E08 Vault/SecMan lab runbook

- Stage: E08
- Scope: permanent lab Vault on Ansible host `192.168.10.15`
- Rule: commands must not print root token, unseal keys, client token, private keys or real secret values.

## Precheck

Run on Ansible host:

```bash
hostname -f
ip addr
timedatectl status
swapon --show
ss -ltnp | grep ':8200\|:8201' || true
```

Expected evidence: host identity, time sync, swap state, and no conflicting Vault listener.

## Target layout

- user/group: `vault:vault`
- config: `/etc/vault.d/vault.hcl`
- data: `/opt/vault/data`
- TLS: `/etc/vault.d/tls/vault.crt`, `/etc/vault.d/tls/vault.key`
- audit: `/var/log/vault/audit.log`
- API address: `https://192.168.10.15:8200`
- cluster address: `https://192.168.10.15:8201`

## TLS

Preferred: corporate/test PKI certificate with IP SAN `192.168.10.15` and optional DNS SAN
`vault.lab.local`.

Fallback: lab CA stored outside Git. Record only CA fingerprint and expiration in evidence.

## Smoke without secret disclosure

```bash
vault status
vault secrets list
vault audit list
vault kv get -field=value kv/cloud-ui/local/session >/dev/null
vault kv get kv/other-service/local/test
```

Expected:

- status initialized and unsealed;
- KV v2 mounted at `kv/`;
- file audit enabled;
- allowed synthetic portal path read succeeds;
- unrelated path read fails for portal policy token.

## Rollback

```bash
sudo systemctl stop vault
sudo systemctl disable vault
```

Preserve `/opt/vault/data` unless destructive cleanup is explicitly approved.
````

- [ ] **Step 3: Add evidence template**

Create `docs/generated/e08-vault-evidence-template.md`:

```markdown
# E08 Vault/SecMan evidence template

- Date:
- Operator:
- Host: `192.168.10.15`
- Vault version:
- Install source:
- Binary/package checksum:
- TLS CA type: corporate/test PKI or lab CA
- CA fingerprint:
- Certificate SANs:
- TLS scan result:
- Vault initialized: yes/no
- Vault sealed: yes/no
- Raft storage path: `/opt/vault/data`
- Audit device: file `/var/log/vault/audit.log`
- KV mount: `kv/`
- Portal policy file: `docs/generated/e08-vault-policy.hcl`
- Positive read: `kv/cloud-ui/local/session` synthetic value, value not captured
- Negative read: unrelated path denied
- Notes:
- Residual gaps:
  - corporate PKI:
  - mTLS:
  - HA:
  - backup/restore:
  - auto-unseal/HSM:
  - Kolla/service secret rotation:
```

- [ ] **Step 4: Update generated docs and DKB traceability**

Make these exact content changes:

- `docs/generated/secret-inventory.md`: set stage to `E08`, add lifecycle notes for portal
  session/cursor/OpenStack/SIEM/Vault auth classes, and keep Kolla/MariaDB/RabbitMQ rotation pending.
- `docs/generated/tls-matrix.md`: update `Deploy/runtime -> Vault (SecMan)` evidence to
  `E08 server TLS contract, adapter CA verification tests, lab runbook; mTLS pending owner decision`.
- `docs/generated/integration-register.md`: update Vault row status to
  `E08 design and adapter contract planned/implemented; lab endpoint 192.168.10.15 runbook; production endpoint/auth pending`.
- `docs/generated/risk-register.md`: add E08 note under R-041 and R-043 that lab server TLS and
  adapter contract reduce integration uncertainty but production PKI/mTLS/full rotation remain open.
- `docs/11_DKB_TRACEABILITY.md`: add an E08 update section above the full matrix describing the
  Vault/SecMan contract, lab runbook and residual gaps for ДКБ-22.02/24/55/56.

- [ ] **Step 5: Run documentation checks**

Run:

```bash
rg -n "root token|unseal|private key|client token|BEGIN .*PRIVATE|DKB_CANARY" docs/generated/e08-vault-policy.hcl docs/generated/e08-vault-lab-runbook.md docs/generated/e08-vault-evidence-template.md docs/generated/secret-inventory.md docs/generated/tls-matrix.md docs/generated/integration-register.md docs/generated/risk-register.md docs/11_DKB_TRACEABILITY.md
git diff --check
make security
```

Expected: `rg` may find forbidden terms only in warning text, not values; `git diff --check` passes;
secret scan passes.

- [ ] **Step 6: Commit**

```bash
git add docs/generated/e08-vault-policy.hcl docs/generated/e08-vault-lab-runbook.md docs/generated/e08-vault-evidence-template.md docs/generated/secret-inventory.md docs/generated/tls-matrix.md docs/generated/integration-register.md docs/generated/risk-register.md docs/11_DKB_TRACEABILITY.md
git commit -m "docs: add E08 vault evidence runbook"
```

### Task 5: Optional Lab Inspection And Smoke Evidence

**Files:**
- Modify: `docs/generated/e08-vault-evidence-template.md` or create a dated sanitized evidence summary
  such as `docs/generated/e08-vault-lab-2026-06-22.md`

- [ ] **Step 1: Ask for explicit remote approval**

Before any SSH, ask the user:

```text
Подтверди, пожалуйста: можно подключиться к Ansible host 192.168.10.15 и только проверить наличие Vault/systemd/listeners без установки?
```

If the user approves inspection, use the existing approved SSH prefix and run non-mutating commands.

- [ ] **Step 2: Inspect current Vault state**

Run:

```bash
ssh -o StrictHostKeyChecking=no root@192.168.10.15 'command -v vault || true; systemctl is-active vault || true; ss -ltnp | grep ":8200\|:8201" || true; test -f /etc/vault.d/vault.hcl && sudo sed -n "1,160p" /etc/vault.d/vault.hcl || true'
```

Expected: command returns observed state. If Vault is absent, record `not installed` and stop unless
the user separately approves deployment.

- [ ] **Step 3: Ask for explicit deployment approval if Vault is absent**

Before installing packages, writing `/etc/vault.d`, generating lab CA or starting services, ask:

```text
Vault на 192.168.10.15 не найден. Подтверди отдельным сообщением, можно ли выполнить lab deployment по runbook: установить Vault, создать lab CA при отсутствии корпоративной PKI, включить systemd service, init/unseal, KV и file audit.
```

Without this approval, mark lab execution skipped in evidence.

- [ ] **Step 4: Save sanitized evidence**

Create `docs/generated/e08-vault-lab-2026-06-22.md` with:

```markdown
# E08 Vault lab evidence 2026-06-22

- Host: `192.168.10.15`
- Action: inspection only or deployment smoke
- Vault binary:
- Service state:
- Listener state:
- TLS state:
- KV state:
- Audit state:
- Positive synthetic read:
- Negative unrelated read:
- Secrets captured in this file: no
- Residual gaps:
```

- [ ] **Step 5: Run evidence checks and commit if a sanitized summary was created**

Run:

```bash
git diff --check
make security
git add docs/generated/e08-vault-lab-2026-06-22.md docs/execplans/E08-vault-secman.md
git commit -m "docs: add E08 vault lab evidence"
```

Expected: checks pass. If no remote action was approved, commit only the plan update that states lab
execution was skipped by approval gate.

### Task 6: Final Verification And Closeout

**Files:**
- Modify: `docs/execplans/E08-vault-secman.md`
- Modify if needed: `docs/superpowers/specs/2026-06-22-e08-vault-secman-design.md`

- [ ] **Step 1: Run targeted tests**

Run:

```bash
cd backend && .venv/bin/python -m pytest tests/secrets tests/test_config.py tests/test_api_health.py -q
```

Expected: all selected tests pass.

- [ ] **Step 2: Run stage gates**

Run:

```bash
make lint
make typecheck
make test
make test-integration
make security
git diff --check
```

Expected:

- Ruff, ESLint and secret scan pass;
- mypy and TypeScript pass;
- backend and frontend tests pass;
- integration tests pass or skip only tests already designed to skip without live config;
- diff check is clean.

- [ ] **Step 3: Self-review diff**

Run:

```bash
git diff main...HEAD --stat
git diff main...HEAD -- backend/src/cloud_ui/secrets backend/src/cloud_ui/config.py backend/src/cloud_ui/health.py backend/tests/secrets backend/tests/test_config.py backend/tests/test_api_health.py docs/generated docs/11_DKB_TRACEABILITY.md docs/execplans/E08-vault-secman.md
```

Review for:

- no real secrets;
- no raw token values in errors;
- no browser Vault access;
- no production compliance overclaim;
- no local provider allowed in production;
- no unbounded retry.

- [ ] **Step 4: Update ExecPlan progress and final risks**

Mark completed milestones with command results. Add any unexpected findings with evidence. Keep these
residual risks if still true:

- production SecMan endpoint/auth owner not approved;
- corporate PKI/mTLS not implemented;
- Kolla/service secret rotation remains external;
- Vault HA/backup/auto-unseal not proven;
- remote deployment skipped unless explicitly approved.

- [ ] **Step 5: Commit closeout**

```bash
git add docs/execplans/E08-vault-secman.md docs/superpowers/specs/2026-06-22-e08-vault-secman-design.md
git commit -m "docs: close E08 vault planning evidence"
```

If only progress entries changed and they were already committed in previous task commits, skip this
commit and state why in final response.

## Миграции и совместимость

No database migration is planned. The new secret provider is additive and disabled by default through
`CLOUD_UI_SECRETS_PROVIDER=local`. Production settings reject local provider so production deployment
must configure Vault explicitly.

Rolling update behavior:

- old backend ignores new Vault settings;
- new backend can start in local/test mode without Vault for CI;
- new backend with `secrets_provider=vault` reports readiness degraded when Vault is unavailable;
- no schema contract migration is needed.

Rollback:

- set `CLOUD_UI_SECRETS_PROVIDER=local` in local/test only;
- revert code commits for `cloud_ui.secrets`, settings and health wiring;
- remove generated E08 docs if the branch is abandoned;
- for lab host, stop/disable Vault service and preserve `/opt/vault/data` unless destructive cleanup is
  explicitly approved.

## Проверка

Targeted commands:

```bash
cd backend && .venv/bin/python -m pytest tests/secrets -q
cd backend && .venv/bin/python -m pytest tests/test_config.py tests/test_api_health.py -q
cd backend && .venv/bin/python -m ruff check src/cloud_ui/secrets src/cloud_ui/config.py src/cloud_ui/health.py tests/secrets tests/test_config.py tests/test_api_health.py
cd backend && .venv/bin/python -m mypy src/cloud_ui/secrets src/cloud_ui/config.py src/cloud_ui/health.py
```

Stage commands:

```bash
make lint
make typecheck
make test
make test-integration
make security
git diff --check
```

Expected results are all pass, with only pre-existing live-smoke skips allowed when external live
configuration is absent.

## Доказательства

Artifacts to create or update:

- `backend/tests/secrets/test_provider.py`;
- `backend/tests/secrets/test_vault_adapter.py`;
- `backend/tests/secrets/test_readiness.py`;
- `docs/generated/e08-vault-policy.hcl`;
- `docs/generated/e08-vault-lab-runbook.md`;
- `docs/generated/e08-vault-evidence-template.md`;
- optional `docs/generated/e08-vault-lab-2026-06-22.md` after explicit remote approval;
- `docs/generated/secret-inventory.md`;
- `docs/generated/tls-matrix.md`;
- `docs/generated/integration-register.md`;
- `docs/generated/risk-register.md`;
- `docs/11_DKB_TRACEABILITY.md`;
- command results recorded in this ExecPlan.

## Откат и восстановление

Code rollback:

```bash
git revert <E08-code-commit>
```

Config rollback for local/test:

```bash
export CLOUD_UI_SECRETS_PROVIDER=local
```

Lab Vault rollback:

```bash
sudo systemctl stop vault
sudo systemctl disable vault
```

Do not delete `/opt/vault/data`, unseal material, CA material or audit logs unless the user explicitly
approves destructive cleanup and the evidence has been sanitized.

## Итог и остаточные риски

Implementation not started in this plan document. Expected residual risks after the first E08
Vault/SecMan slice:

- production SecMan endpoint/auth remains owner-provided;
- corporate PKI and mTLS policy remain owner-provided;
- full Kolla/Ansible secret rotation remains E09/deployment-pipeline work;
- Vault HA, backup/restore, auto-unseal/HSM and break-glass remain production hardening work;
- ДКБ-55/56 are supported by portal contract/lab evidence, not fully closed.
