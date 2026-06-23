# Secret inventory

- Stage: E08
- Status: E08 adds Vault/SecMan contract, adapter/readiness tests, CSRF bootstrap evidence and lab runbook for synthetic portal secrets; Kolla/MariaDB/RabbitMQ rotation remains pending
- Rule: no real secret value, token, private key, cookie or credential is stored here.

| Secret class | Used by | Proposed store | Injection | Rotation owner | Stage | Current status |
|---|---|---|---|---|---|---|
| UI session signing/encryption key | backend API | Vault (SecMan) in production; local dummy in P0 | mounted secret/reference | Vault/platform | E02/E08 | E08 defines portal path class `kv/data/cloud-ui/local/session`, server-side provider contract, lab synthetic read and E08.4 restored-session CSRF bootstrap evidence; rotation procedure still requires Vault owner approval |
| Inventory/operation/audit cursor signing keys | backend API | Vault (SecMan) in production; local dummy in P0 | mounted secret/reference | Vault/platform | E04/E06/E07/E08 | E08 defines `kv/data/cloud-ui/local/cursors`; production dummy-key rejection exists, but issue/rotate/revoke evidence remains pending |
| Human OpenStack session token | server-side session only | encrypted DB/session record | runtime only | IAM/OpenStack | E02 | pending ADR-001 |
| Service application credential | backend integrations | Vault (SecMan) | runtime secret reference | OpenStack/Vault | E03/E08 | E08 defines `kv/data/cloud-ui/local/openstack` for synthetic adapter tests only; real Keystone/application credential issue, rotation and revoke remain pending |
| MariaDB runtime password | API/worker/events | Kolla secret mechanism/Vault | config secret mount | DB/platform | E01/E09 | pending |
| MariaDB migration credential | migration job | Kolla secret mechanism/Vault | one-shot job secret | DB/platform | E01/E09 | pending |
| RabbitMQ producer/consumer password | API/worker/events | Kolla secret mechanism/Vault | config secret mount | messaging/platform | E01/E09 | pending |
| TLS private keys | HAProxy/API/clients | corporate PKI/Vault | mounted cert/key | PKI/platform | E08/E09 | pending |
| SIEM client credential | audit worker | Vault (SecMan) | runtime secret reference | SIEM/Vault | E07/E08 | E08 defines `kv/data/cloud-ui/local/siem` for lifecycle tracking; production Fluentd/SIEM auth/mTLS credential is still pending |
| Vault auth credential | backend/deploy | bootstrap mechanism defined by Vault | runtime/deploy identity | Vault/platform | E08 | E08 requires protected token file/auth role outside Git, server-side only; client token value must not appear in evidence |
| Mistral/OpenStack integration identity | worker | Keystone/Vault | runtime reference | OpenStack/Vault | E06/E08 | pending |
| Registry credential | deployment pipeline | CI/registry secret store | CI/deploy only | supply-chain owner | E08/E09 | pending |

## Forbidden handling

- No secrets in Git.
- No secrets in frontend assets.
- No secrets in image layers/history.
- No tokens/cookies/passwords in logs, metrics labels, audit payload or RabbitMQ messages.
- No production `clouds.yaml`, openrc, `.env`, private key or DB dump in workspace.

## E08 lifecycle notes

- Portal session key: stored under the portal Vault prefix, injected only into backend process memory through `SecretProvider`, never returned to browser; cache TTL, rotation window and break-glass owner remain to be approved.
- CSRF values: derived as per-session runtime values in the backend session manager and returned only through the authenticated same-origin BFF/API bootstrap path; they are not stored in browser `localStorage`/`sessionStorage`, not written to audit metadata and are not treated as Vault-managed long-lived secrets.
- Cursor signing keys: same store/injection model as session keys; rotation must preserve validation for active cursors or provide a controlled cursor invalidation plan.
- OpenStack integration credential: only synthetic lab path is documented in E08; real application credential issuance, least-privilege scope, revoke and audit evidence remain with IAM/OpenStack/Vault owners.
- SIEM credential: E08 tracks the path class and redaction rules; production SIEM endpoint, mTLS/auth method, rotation and retention evidence remain open.
- Vault auth credential: must be issued by Vault/SecMan bootstrap outside Git, delivered as a protected runtime/deploy identity and revoked in rollback; no root token, unseal keys or client token values are evidence artifacts.
- Kolla, MariaDB and RabbitMQ secret rotation remains pending for E09/deployment pipeline evidence and is not closed by the portal Vault adapter contract.

## Lifecycle fields still to complete

For each secret class:

- owner;
- store path/reference pattern;
- issue process;
- injection process;
- cache/retention policy;
- rotation procedure;
- revoke procedure;
- break-glass procedure;
- audit evidence;
- emergency rollback.
