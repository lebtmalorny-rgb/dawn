# E09.6 HAProxy/TLS/network evidence

- Stage: E09.6 HAProxy/TLS/network
- Status: repository-side route contract; not a live HAProxy deployment.
- Scope: same-origin route, health checks, trusted proxy headers, timeout/body limits, TLS/backend TLS
  policy defaults and management network/ACL documentation.
- Evidence status: `pending_external_evidence` for live VIP, corporate PKI, mTLS, ACL and negative
  certificate/network tests.

## Route contract

| External path | Backend service | Health check | Purpose |
|---|---|---|---|
| `/api/v1/` -> `cloud_ui_api` | `cloud_ui_api` group | `/api/v1/health/ready` | BFF/API only, no browser OpenStack API exposure |
| `/` -> `cloud_ui_frontend` | `cloud_ui_frontend` group | `/` | Static SPA fallback |

The route is same-origin: browser traffic reaches Cloud UI through the portal VIP/HAProxy only. The
frontend still does not call OpenStack APIs, MariaDB, RabbitMQ, Vault or SIEM directly.

## TLS and proxy policy

- External scheme default is `https`.
- Placeholder public FQDN is `cloud-ui.example.invalid`; deploy inventory must override it before
  enabling the route.
- TLS minimum default is `TLSv1.2`.
- Backend TLS mode default is `internal_http`; `backend_tls` and `backend_mtls` are explicit matrix
  options for deployments that enable internal TLS/mTLS.
- Trusted proxy headers are `X-Forwarded-For`, `X-Forwarded-Proto`, `X-Forwarded-Host` and
  `X-Request-ID`.
- Security headers are `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY` and
  `Referrer-Policy: no-referrer`.
- Request body limit is 16777216 bytes.

## Network and ACL status

Management network ACL enforcement remains `pending_external_evidence`. The repository contract
records forbidden flows:

- browser to OpenStack service APIs;
- browser to MariaDB, RabbitMQ, Vault or SIEM;
- frontend to OpenStack service databases;
- portal consumer to OpenStack RabbitMQ RPC wildcard.

Live E09.7/E09.8 evidence must prove concrete CIDR/VLAN/port rules and negative rejects before this
can be treated as deployment acceptance.

## ДКБ scope

- ДКБ-22.02/23.02/24: TLS route policy and backend TLS/mTLS decision points are documented, but
  corporate PKI, mTLS authorization, revocation/rotation and negative certificate tests remain external.
- ДКБ-65/66: management network/ACL requirements are documented, but not enforced by this repository
  change alone.
- ДКБ-69/70: no certificates, private keys, passwords or tokens are added to images/templates.
- ДКБ-76/77/80: route, health, timeout, header and public-path deployment interface is tested.
- ДКБ-82: rollback is repository revert before live rollout; live failed-update rollback remains E09.7.
