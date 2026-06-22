# Secret inventory

- Stage: E07
- Status: draft; E07 adds audit cursor signing key and SIEM credential placeholder only, with no real secret value committed
- Rule: no real secret value, token, private key, cookie or credential is stored here.

| Secret class | Used by | Proposed store | Injection | Rotation owner | Stage | Current status |
|---|---|---|---|---|---|---|
| UI session signing/encryption key | backend API | Vault (SecMan) in production; local dummy in P0 | mounted secret/reference | Vault/platform | E02/E08 | pending |
| Inventory/operation/audit cursor signing keys | backend API | Vault (SecMan) in production; local dummy in P0 | mounted secret/reference | Vault/platform | E04/E06/E07/E08 | E07 adds audit cursor key; production dummy-key rejection implemented for production settings |
| Human OpenStack session token | server-side session only | encrypted DB/session record | runtime only | IAM/OpenStack | E02 | pending ADR-001 |
| Service application credential | backend integrations | Vault (SecMan) | runtime secret reference | OpenStack/Vault | E03/E08 | pending |
| MariaDB runtime password | API/worker/events | Kolla secret mechanism/Vault | config secret mount | DB/platform | E01/E09 | pending |
| MariaDB migration credential | migration job | Kolla secret mechanism/Vault | one-shot job secret | DB/platform | E01/E09 | pending |
| RabbitMQ producer/consumer password | API/worker/events | Kolla secret mechanism/Vault | config secret mount | messaging/platform | E01/E09 | pending |
| TLS private keys | HAProxy/API/clients | corporate PKI/Vault | mounted cert/key | PKI/platform | E08/E09 | pending |
| SIEM client credential | audit worker | Vault (SecMan) | runtime secret reference | SIEM/Vault | E07/E08 | not used by E07 local test sink; required for production Fluentd/SIEM auth/mTLS |
| Vault auth credential | backend/deploy | bootstrap mechanism defined by Vault | runtime/deploy identity | Vault/platform | E08 | pending |
| Mistral/OpenStack integration identity | worker | Keystone/Vault | runtime reference | OpenStack/Vault | E06/E08 | pending |
| Registry credential | deployment pipeline | CI/registry secret store | CI/deploy only | supply-chain owner | E08/E09 | pending |

## Forbidden handling

- No secrets in Git.
- No secrets in frontend assets.
- No secrets in image layers/history.
- No tokens/cookies/passwords in logs, metrics labels, audit payload or RabbitMQ messages.
- No production `clouds.yaml`, openrc, `.env`, private key or DB dump in workspace.

## Lifecycle fields to complete in E08

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
