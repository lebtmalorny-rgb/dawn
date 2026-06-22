# E08 Vault SecMan Lab Design

Дата: 2026-06-22
Статус: design approved, written-spec review pending
Ветка/worktree: `e08-vault-secman-design` / `.worktrees/e08-vault-secman-design`

## Цель

Этот spec фиксирует Vault/SecMan-срез E08: постоянный тестовый Vault на Ansible host,
контракт чтения секретов для портала, локальный/test adapter и runbook/evidence для lab deployment.
Он нужен, чтобы E08 мог проверять secret lifecycle, TLS evidence, redaction and access-denial cases
без подключения production Vault и без хранения реальных секретов в Git.

Выбранный стенд:

- Ansible host: `192.168.10.15`;
- all-in-one OpenStack/Kolla host: `192.168.10.14`;
- Vault service: native systemd на Ansible host;
- storage: single-node integrated Raft;
- TLS включен сразу. Corporate PKI preferred; если ее нет на стенде, используется отдельная lab CA
  с явной пометкой, что это не production PKI evidence.

## Утвержденные решения

- Разворачивать постоянный Vault на Ansible host, а не `vault server -dev`.
- Не добавлять Vault container в portal runtime и не менять правило двух custom runtime images
  (`cloud-ui-frontend`, `cloud-ui-backend`).
- Использовать native systemd service, системного пользователя `vault` и отдельные директории:
  `/etc/vault.d`, `/opt/vault/data`, `/var/log/vault`.
- Использовать integrated Raft для хранения данных Vault. Даже в single-node режиме это ближе к
  будущему HA path, чем filesystem dev storage.
- Установку фиксировать exact Vault version/checksum в evidence. Для upgrades применять правило
  latest supported fix release, но не оставлять floating version в runbook.
- Включить TCP listener только с TLS. Минимум `tls_min_version = "tls12"`.
- Если management interface на Ansible host подтвержден, bind выполняется на `192.168.10.15:8200`
  и `192.168.10.15:8201`, а не wildcard. Если bind только на wildcard временно необходим,
  runbook обязан зафиксировать firewall restriction и gap.
- `api_addr = "https://192.168.10.15:8200"` и
  `cluster_addr = "https://192.168.10.15:8201"` для lab.
- Если DNS/hosts можно закрепить, дополнительное имя `vault.lab.local` включается в SAN сертификата.
  IP SAN `192.168.10.15` обязателен для воспроизводимого smoke без внешнего DNS.
- Lab default для Shamir init: 3 key shares / threshold 2. Production требует отдельного решения по
  owners, HSM/auto-unseal, backup and break-glass.
- Root token и unseal keys не попадают в Git, shell history, `.env`, screenshots or evidence logs.
- Vault audit включается через file audit device на `/var/log/vault/audit.log`, с logrotate and
  `SIGHUP` после rotation.
- Portal adapter читает только разрешенные test paths. Browser никогда не обращается к Vault и не
  получает Vault token, secret value или certificate private key.
- Деплой на стенд остается отдельным явно одобряемым действием. Этот spec сам по себе не мутирует
  remote host.

## Scope

E08 Vault/SecMan slice включает:

- design spec и будущий ExecPlan;
- lab Vault deployment runbook для Ansible host;
- TLS/lab CA evidence template;
- Vault policy/path contract для портала;
- secret inventory lifecycle update для E08.3;
- DKB traceability/gap update для ДКБ-22.02, 24, 55, 56 and related secret/audit controls;
- backend `SecretProvider` contract and local fake adapter;
- Vault HTTP adapter contract tests with no live secrets;
- optional manual lab smoke, only after explicit approval to deploy or use the test stand.

## Non-goals

- Не подключать production Vault/SecMan.
- Не заявлять закрытие ДКБ-55/56 для всех Kolla/OpenStack/service secrets.
- Не хранить Vault root token, client token, unseal key, private key, real `clouds.yaml`, openrc or
  production URL with credentials в репозитории.
- Не добавлять прямой browser access к Vault.
- Не считать lab CA доказательством корпоративной PKI.
- Не считать single-node Raft доказательством HA.
- Не автоматизировать full Kolla secrets rotation в этом slice.
- Не заявлять, что mTLS matrix всего стенда закрыта только Vault listener TLS.

## Vault Host Layout

Runbook должен создать или проверить:

- user/group: `vault:vault`;
- config: `/etc/vault.d/vault.hcl`, owned by `root:vault`, mode `0640`;
- data: `/opt/vault/data`, owned by `vault:vault`, mode `0700`;
- TLS material: `/etc/vault.d/tls`, private key mode `0600`;
- audit log: `/var/log/vault/audit.log`, writable by Vault and readable only by approved operators;
- systemd unit with restart policy and no dev mode;
- swap disabled or explicitly documented as a lab gap, because integrated Raft guidance recommends
  `disable_mlock = true` together with disabled swap.

Target `vault.hcl` shape:

```hcl
ui = true
disable_mlock = true
api_addr = "https://192.168.10.15:8200"
cluster_addr = "https://192.168.10.15:8201"

storage "raft" {
  path = "/opt/vault/data"
  node_id = "ansible-vault-01"
}

listener "tcp" {
  address = "192.168.10.15:8200"
  cluster_address = "192.168.10.15:8201"
  tls_cert_file = "/etc/vault.d/tls/vault.crt"
  tls_key_file = "/etc/vault.d/tls/vault.key"
  tls_min_version = "tls12"
  redact_addresses = "true"
  redact_cluster_name = "true"
  redact_version = "true"
}
```

The runbook records deviations from this shape with reason, owner and expiry.

## PKI And TLS

Preferred path:

- use corporate/test PKI if available;
- issue server certificate for `192.168.10.15` and optional `vault.lab.local`;
- install CA bundle only on hosts that need Vault access;
- verify hostname/IP SAN, certificate chain and TLS minimum version.

Fallback path:

- create a separate lab CA on the Ansible host;
- protect CA private key outside Git and exclude it from evidence;
- document the lab CA fingerprint and expiration;
- mark the result as lab-only evidence for ДКБ-22.02/24, not corporate PKI compliance.

Negative evidence:

- TLS 1.0/1.1 connection attempt fails;
- connection with untrusted CA fails;
- connection with wrong hostname/SAN fails;
- Vault token with no policy cannot read portal paths;
- portal policy cannot read unrelated paths.

mTLS is not enabled by default in this lab design. If corporate SecMan requires client certificate
authentication, the implementation plan must add `tls_require_and_verify_client_cert` and
`tls_client_ca_file`, plus negative tests for missing/wrong client certificate. Until then, the
Vault row in `docs/generated/tls-matrix.md` must state "server TLS + Vault auth; mTLS pending owner
decision" rather than claiming full ДКБ-22.02 closure.

## Logical Vault Layout

Lab secret engine:

- enable KV v2 at `kv/`;
- store only synthetic values and canary strings;
- no production tokens, passwords or private keys.

Portal-owned lab paths:

- `kv/data/cloud-ui/local/session`;
- `kv/data/cloud-ui/local/cursors`;
- `kv/data/cloud-ui/local/openstack`;
- `kv/data/cloud-ui/local/siem`.

Metadata/list paths may be allowed only under `kv/metadata/cloud-ui/local/*` when a contract test
requires listing. Broad `kv/*` access is forbidden.

Initial portal lab policy:

```hcl
path "kv/data/cloud-ui/local/*" {
  capabilities = ["read"]
}

path "kv/metadata/cloud-ui/local/*" {
  capabilities = ["read", "list"]
}
```

Everything outside this prefix is denied by absence of policy. The negative test suite must include
at least `kv/data/other-service/local/test`, `sys/mounts` and a missing portal key.

## Portal Secret Provider Contract

Backend introduces a narrow interface before any live Vault dependency:

```text
SecretProvider.get(path, schema, correlation_id) -> SecretDocument
```

Contract rules:

- path comes from trusted server-side configuration, not from browser input;
- values are returned only inside backend process memory;
- response schema is explicit per secret class;
- timeout is bounded;
- retry is limited to temporary network/5xx failures;
- forbidden/not found/sealed/uninitialized/malformed/TLS errors are typed separately;
- logs, audit metadata and API errors contain path class and safe error code, not secret values;
- no secret value is emitted to frontend, audit event, metrics label or exception text;
- optional in-memory cache respects explicit TTL and can be disabled for tests.

Adapters:

- `LocalSecretProvider` for unit/contract tests with deterministic fixtures;
- `VaultSecretProvider` using Vault HTTP API and injected trust bundle;
- no direct dependency from frontend to either adapter.

The first code slice should fail closed: if Vault config is enabled but unavailable or unauthorized,
startup/smoke reports the dependency as unhealthy instead of silently falling back to local secrets.

## Runbook And Evidence

The lab runbook must cover:

- precheck: OS, hostname/IP, time sync, free disk, firewall, swap, existing Vault process/package;
- install: exact version, checksum, package/binary source, systemd unit;
- TLS: corporate CA or lab CA path, SAN verification, trust bundle;
- initialize/unseal: sanitized command transcript with no key material;
- enable KV v2 and write synthetic canary secrets;
- create portal policy and non-root lab token/auth role;
- enable file audit device;
- configure logrotate and `SIGHUP`;
- health smoke: `vault status`, `/v1/sys/health`, Raft peer list, audit list, policy positive/negative;
- TLS smoke: accepted TLS 1.2/1.3 and rejected TLS 1.0/1.1 where tooling supports it;
- rollback: stop service, revoke lab token, remove trust entry, disable firewall rule and preserve
  `/opt/vault/data` unless destructive deletion is explicitly approved.

Evidence files must be sanitized summaries under `docs/generated/` or referenced external artifacts.
Raw logs with tokens, unseal keys, private keys or real secret values are not committed.

## Testing Strategy

Mandatory tests for implementation plan:

- unit tests for secret schema validation and redaction canaries;
- adapter contract tests for successful read;
- forbidden path returns typed permanent error;
- missing secret returns typed not-found error;
- sealed/uninitialized Vault status maps to dependency unavailable;
- temporary 5xx/timeout retries within bound and then fails safe;
- malformed Vault response is rejected without leaking body;
- TLS/CA verification negative case using mock transport or local test server;
- backend API/status does not expose secret values;
- `make lint`, `make typecheck`, `make test` for code slice.

Optional live smoke after explicit stand approval:

- read synthetic `kv/cloud-ui/local/session` through Vault API from Ansible host;
- deny unrelated path;
- verify file audit contains sanitized access record;
- capture TLS and policy evidence without secret values.

## DKB Impact

- ДКБ-22.02/24: adds Vault server TLS evidence and explicit mTLS gap if client cert auth is not enabled.
- ДКБ-13/51: secret/token/private key redaction is extended to Vault adapter and evidence.
- ДКБ-46-53: Vault audit file proves lab access logging for the secret store, but not full SIEM/FIM coverage.
- ДКБ-55: creates a Vault/SecMan contract and lab service for portal secrets.
- ДКБ-56: documents lifecycle fields for portal secret classes and exposes remaining Kolla/service
  rotation gap.
- ДКБ-69/70: no new portal image dependency is added; Vault host package evidence is separate from
  portal container hardening.
- ДКБ-77: Vault endpoint and allowed paths must be added to integration/API registers and unused
  interfaces must remain denied.

Residual gaps:

- production SecMan owner and endpoint not approved;
- corporate PKI flow unavailable until owner provides it;
- full Kolla/Ansible password and certificate rotation pipeline is not implemented;
- Vault HA, backup restore test, HSM/auto-unseal and break-glass are not production-ready;
- mTLS for portal-to-Vault remains pending unless explicitly selected;
- firewall/management VLAN evidence belongs to E09/network owner.

## Official References

- HashiCorp Vault install and version guidance: <https://developer.hashicorp.com/vault/docs/get-vault>
- Vault integrated Raft storage: <https://developer.hashicorp.com/vault/docs/configuration/storage/raft>
- Vault TCP listener TLS settings: <https://developer.hashicorp.com/vault/docs/configuration/listener/tcp>
- Vault file audit device: <https://developer.hashicorp.com/vault/docs/audit/file>
