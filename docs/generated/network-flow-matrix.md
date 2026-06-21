# Network flow matrix

- Stage: E00
- Status: draft; actual CIDR/VLAN/ACL evidence pending

## Zones

| Zone | Description | Current status |
|---|---|---|
| User/external | browser access to portal VIP | observed `192.168.10.250` over HTTPS with Kolla CA in lab |
| Management/API | HAProxy, frontend, backend API | observed on all-in-one host/VIP; detailed ACL unknown |
| DB/messaging backend | MariaDB and RabbitMQ | unknown |
| OpenStack internal API | Keystone/Nova/Placement/Mistral/Watcher/Masakari/telemetry/etc | unknown |
| Audit/security | SIEM, Vault (SecMan), PKI | Vault product identified; endpoint/auth/path policy unknown |
| Registry/supply chain | image registry/scanner/signing | unknown |
| Storage/backup | storage and backup control plane | unknown |

## Planned flows

| Source | Destination | Protocol | Purpose | Stage | Required control | Status |
|---|---|---|---|---|---|---|
| Browser | HAProxy/VIP | HTTPS | portal UI/API same-origin | E09 | TLS >= 1.2, auth/session, WAF/rate policy if required | pending |
| HAProxy | Frontend containers | HTTP or HTTPS | static SPA | E09 | internal ACL, health check | pending |
| HAProxy | API containers | HTTP or HTTPS | `/api/v1` | E09 | trusted proxy headers, timeouts, request limits | pending |
| API | Keystone/IdP | HTTPS | auth, scope, service catalog | E02/E03 | TLS, optional mTLS by matrix, timeout/retry | pending |
| API/worker/events | MariaDB `cloud_ui` | TCP/TLS if enabled | sessions, read model, operations, audit index | E01/E09 | least privilege DB user, network ACL, backup | pending |
| API/worker/events | RabbitMQ `/cloud-ui` | AMQPS in production | jobs/outbox/events | E01/E09 | vhost/user ACL, DLX, no OpenStack RPC wildcard | pending |
| Worker/API | Nova | HTTPS | inventory/detail/refresh | E03/E04 | microversion, bounded concurrency | pending |
| Worker/API | Placement | HTTPS | capacity enrichment | E03/E04 | microversion, graceful degradation | pending |
| Worker | Mistral | HTTPS | workflow execution | E06 | allowlist, external correlation, no blind retry | pending |
| Worker/API | Watcher | HTTPS | audit/action status | E06+ | role/capability, contract tests | pending |
| Worker/API | Masakari | HTTPS | segments/notifications | E06+ | role/capability, contract tests | pending |
| Masakari hostmonitor | Consul | HTTPS/TCP by Consul deployment | network health checks for recovery matrix | E10/P3 | Consul ACL/TLS, monitor coverage, matrix review | pending; Consul not on current test node |
| Worker/API | Prometheus datasource | HTTPS | metrics for capacity/health/Watcher datasource/Masakari corroboration | E10/P3 | role/capability, contract tests, freshness and rate limits | pending |
| Prometheus | `openstack-exporter`/`node_exporter` | HTTP/HTTPS by deployment | scrape OpenStack and host metrics | E10/P3 | exporter auth/TLS/network ACL, scrape interval, cardinality limits | pending |
| Audit worker | SIEM/test sink | TLS/mTLS by matrix | audit delivery | E07/E08 | delivery ack, heartbeat, retry/DLQ | pending |
| API/deploy | Vault (SecMan) | TLS/mTLS by matrix | secret retrieval/lifecycle | E08 | no secrets in Git/image/log, rotation runbook | pending |
| Deploy | Registry | TLS/mTLS by policy | image push/pull | E08/E09 | digest, SBOM, scan, signature | pending |
| Platform admins | Hosts/Kolla | SSH via bastion/PAM | deployment/operations | E09/E12 | personal accounts, auditd/PAM/session recording | external pending |

## Explicitly forbidden flows

- Browser -> OpenStack service APIs.
- Browser -> MariaDB/RabbitMQ/SIEM/Vault.
- API/frontend -> OpenStack service databases.
- Portal consumers -> OpenStack RabbitMQ RPC exchanges as wildcard consumer.
- Frontend image/assets -> production endpoints or credentials.
- API -> user-supplied external URL without allowlist and SSRF controls.
- Portal -> Consul Events or Prometheus alerts as direct evacuation authority.

## Current observations

- `192.168.10.250` responds to ICMP from Ansible host.
- `https://192.168.10.250/` returns Horizon redirect to `/auth/login/` when verified with the Kolla CA.
- `https://192.168.10.250:5000/v3` returns Keystone version discovery `v3.14` when verified with the Kolla CA.
- `http://192.168.10.50:5000/v3` is unreachable from Ansible host.
- OpenStack host `192.168.10.14` has VIP `192.168.10.250/32` on `br0`.
- Current lab OpenStack API endpoints are HTTPS after Kolla TLS enablement. Production PKI, mTLS, rotation/revocation and portal-specific network ACL evidence remain E08/E09 gaps.
