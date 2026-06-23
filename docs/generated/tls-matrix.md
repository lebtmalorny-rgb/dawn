# TLS and mTLS matrix

- Stage: E08 threat/TLS review
- Status: expanded matrix; live production PKI/mTLS evidence remains pending.
- Rule: no TLS/mTLS claim is accepted until test scan or negative certificate test exists. Lab Kolla
  CA evidence is marked as lab-only and does not prove corporate PKI compliance.

| Flow | Minimum TLS | mTLS | CA/source | Server identity check | Client identity / authorization | Rotation owner | Negative test | Stage | Evidence | Residual gap |
|---|---|---|---|---|---|---|---|---|---|---|
| Browser -> external VIP | TLS 1.2 minimum; lab observed TLS 1.3 for Keystone VIP | no by default for browser users | corporate PKI required for production; lab Kolla CA observed | browser verifies portal hostname/SAN; lab VIP IP SAN `192.168.10.250` observed | user auth through portal session and IdP/Keystone; no browser OpenStack token | PKI/platform owner | TLS 1.0/1.1 rejected by scan; untrusted CA and wrong hostname rejected | E08/E09 | lab `openssl s_client` to Keystone VIP reported TLSv1.3 and verification OK with Kolla CA; production scan pending | corporate PKI, portal hostname certificate, revocation and production scan pending |
| HAProxy -> frontend | TLS 1.2 if backend TLS is enabled; otherwise internal HTTP only by deployment decision | optional; decision pending | internal/corporate PKI if TLS enabled | frontend service DNS/name or container network identity | HAProxy backend ACL and Kolla service placement | platform owner | backend connection with untrusted cert rejected if TLS selected | E09 | Kolla role/config evidence pending | backend TLS/mTLS and network ACL proof pending |
| HAProxy -> API | TLS 1.2 if backend TLS is enabled; otherwise internal HTTP only by deployment decision | optional; decision pending | internal/corporate PKI if TLS enabled | API service DNS/name or container network identity | HAProxy backend ACL, trusted proxy headers and health check path | platform owner | backend connection with untrusted cert rejected if TLS selected | E09 | Kolla role/config evidence pending | backend TLS/mTLS and trusted proxy evidence pending |
| API/worker -> Keystone | TLS 1.2 minimum; lab Keystone observed TLS 1.3 | mTLS decision pending | OpenStack internal CA for lab; corporate/internal CA for production | Keystone endpoint hostname/SAN from service catalog | Keystone token/application credential policy; OpenStack policy remains final authority | OpenStack/PKI owner | untrusted CA, wrong hostname and unauthorized credential rejected | E03/E08/E09 | E03 adapter contract; lab `https://192.168.10.250:5000/v3` verification OK with Kolla CA | production corporate CA, mTLS decision and least-privilege live credential evidence pending |
| API/worker -> Nova | TLS 1.2 minimum | mTLS decision pending | OpenStack internal or corporate CA | Nova endpoint hostname/SAN from service catalog | Keystone-scoped service/user credential; Nova policy final authority | OpenStack/PKI owner | untrusted CA, wrong hostname and OpenStack 403 preserved | E03/E08/E09 | E03 Nova adapter contract with microversion `2.96`; live TLS scan pending | live Nova TLS scan, mTLS decision and policy-negative evidence pending |
| API/worker -> Placement | TLS 1.2 minimum | mTLS decision pending | OpenStack internal or corporate CA | Placement endpoint hostname/SAN from service catalog | Keystone-scoped credential; Placement policy final authority | OpenStack/PKI owner | untrusted CA, wrong hostname and OpenStack 403 preserved | E03/E08/E09 | E03 Placement adapter contract with microversion `1.39`; live TLS scan pending | live Placement TLS scan, mTLS decision and policy-negative evidence pending |
| API/worker -> Mistral | TLS 1.2 minimum | mTLS decision pending | OpenStack internal or corporate CA | Mistral endpoint hostname/SAN from service catalog | allowlisted workflow catalog plus Keystone/Mistral policy | Workflow/OpenStack/PKI owner | untrusted CA, wrong hostname, unauthorized workflow and arbitrary workflow name rejected | E06/E08/E09 | E06 mock adapter and read-only smoke plan; live mutating evidence pending | approved workflow credential, live TLS scan and mTLS decision pending |
| API/worker -> Watcher | TLS 1.2 minimum | mTLS decision pending | OpenStack internal or corporate CA | Watcher endpoint hostname/SAN from service catalog | capability-gated portal access plus Watcher/OpenStack policy | OpenStack/PKI owner | untrusted CA, wrong hostname and unauthorized apply rejected | E06/E08/E10 | P0 Watcher status/risk UI contract; live adapter pending | live Watcher adapter/TLS scan and mTLS decision pending |
| API/worker -> Masakari | TLS 1.2 minimum | mTLS decision pending | OpenStack internal or corporate CA | Masakari endpoint hostname/SAN from service catalog | capability-gated portal access plus Masakari/Nova policy | OpenStack/PKI owner | untrusted CA, wrong hostname and risky recovery without approval rejected | E06/E08/E10 | P0 Masakari status/risk UI contract; live adapter pending | live Masakari adapter/TLS scan and mTLS decision pending |
| Masakari hostmonitor -> Consul | TLS 1.2 if Consul TLS is enabled | decision pending | corporate/internal CA for Consul | Consul server DNS/SAN | Consul ACL token and Masakari monitor config | OpenStack/platform owner | missing ACL, wrong cert or matrix rule without `recovery` action rejected | E10/P3/E08 | Masakari/Consul design notes and matrix requirement; no live Consul on current test node | Consul ACL/TLS deployment and monitor coverage evidence pending |
| API/worker -> Prometheus datasource | TLS 1.2 if Prometheus API is enabled | decision pending | corporate/internal CA | Prometheus endpoint hostname/SAN | backend-only allowlisted query API; no raw browser PromQL | Monitoring/PKI owner | untrusted CA, wrong hostname and raw/unauthorized query rejected | E10/P3/E08 | telemetry datasource selected as Prometheus path; endpoint pending | endpoint, retention, RBAC, TLS scan and mTLS decision pending |
| Prometheus -> openstack-exporter/node_exporter | TLS 1.2 if exporter TLS/auth is enabled | decision pending | internal or corporate CA | exporter endpoint identity/SAN | scrape auth token or mTLS identity with least privilege | Monitoring/platform owner | unauthenticated scrape and wrong cert rejected | E10/P3/E08 | exporter path selected; no live scrape evidence | exporter auth/TLS/cardinality evidence pending |
| Portal -> MariaDB | TLS if supported by Kolla baseline; production should use TLS | optional client cert decision pending | internal/corporate CA or Kolla DB TLS | DB endpoint hostname/SAN | dedicated `cloud_ui` DB user limited to portal schema | DB/platform owner | untrusted CA, wrong hostname and non-portal schema access rejected | E09/E08 | repository invariant forbids OpenStack service DB access; live DB TLS pending | MariaDB TLS, credential rotation, backup and HA evidence pending |
| Portal -> RabbitMQ | TLS in production | optional client cert decision pending | internal/corporate CA or Kolla broker TLS | RabbitMQ endpoint hostname/SAN | dedicated `/cloud-ui` vhost/user; no OpenStack RPC wildcard consumer | Messaging/platform owner | untrusted CA, wrong hostname, wrong vhost and RPC wildcard access rejected | E09/E08 | architecture invariant and integration register; live broker TLS pending | RabbitMQ TLS, vhost permissions and rotation evidence pending |
| Audit worker -> SIEM | TLS 1.2 minimum | likely yes; pending SIEM contract | corporate PKI | SIEM/Fluentd endpoint hostname/SAN | audit worker client identity authorized for audit ingest only | SIEM/PKI owner | missing or wrong client cert rejected; unauthenticated delivery rejected | E07/E08/E09 | E07 local sink and Fluentd HTTP payload contract; lab Fluentd present with OpenSearch disabled | production SIEM endpoint, mTLS/auth, retention and owner acceptance pending |
| Deploy/runtime -> Vault (SecMan) | TLS 1.2 minimum | server TLS + Vault auth; mTLS pending owner decision | corporate/test PKI preferred; lab CA fallback is lab-only | Vault endpoint hostname/IP SAN and CA chain | Vault policy token/auth role limited to `kv/data/cloud-ui/local/*` synthetic paths in lab | Vault/PKI owner | untrusted CA, wrong hostname, missing Vault auth and unrelated path access rejected | E08 | E08 Vault adapter CA verification tests, readiness tests, policy artifact and lab runbook | mTLS pending owner decision; production endpoint/auth, HA, backup, auto-unseal and rotation pending |
| Deploy -> registry | TLS 1.2 minimum | policy pending | corporate PKI | registry endpoint hostname/SAN | CI/deploy registry credential with push/pull by digest and signing policy | Supply-chain/PKI owner | untrusted CA, unsigned image, latest tag and unauthorized push rejected | E08/E09 | registry decision pending; SBOM/signing later E08/E09 | registry product, digest pinning, SBOM, scan and signature evidence pending |

## Open decisions

- Exact flows requiring mTLS under ДКБ-22.02.
- Corporate CA chain injection into runtime containers.
- Certificate rotation process, emergency revoke and evidence retention.
- Whether backend TLS is required behind HAProxy in the target management zone.
- How certificate identity maps to service authorization for SIEM, Vault, RabbitMQ and MariaDB.
- How production scans are executed and stored without leaking endpoints or credentials.

## Current observations

Lab update on 2026-06-19:

- Kolla internal and external TLS are enabled for the test VIP `192.168.10.250`.
- Kolla generated a test CA and HAProxy certificate. The HAProxy certificate issuer is `KollaTestCA`,
  includes SAN `IP Address:192.168.10.250`, and is valid from 2026-06-19 to 2027-06-19.
- The Kolla CA was installed into the Ansible and OpenStack host trust stores.
- Horizon responds over `https://192.168.10.250` with HTTP/2 302 to `/auth/login/`.
- Keystone version discovery over `https://192.168.10.250:5000/v3` returns `v3.14`.
- `openssl s_client` to `192.168.10.250:5000` with the Kolla CA reports TLSv1.3 and
  `Verification: OK`.
- `/etc/kolla/admin-openrc.sh` exports `OS_AUTH_URL='https://192.168.10.250:5000'` and
  `OS_CACERT='/etc/pki/tls/certs/ca-bundle.crt'`.
- Horizon Python clients that rely on `requests/certifi` are configured through
  `/etc/kolla/config/horizon/_9999-custom-settings.py` to use the Kolla CA bundle. This fixes
  Mistral dashboard calls to `https://192.168.10.250:8989/v2/workbooks`.

Limits:

- This is lab TLS evidence only, using a Kolla-generated CA, not corporate PKI.
- mTLS, certificate rotation, revocation, production certificate policy and negative certificate
  tests remain E08/E09 gaps.
