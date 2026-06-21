# Integration register

- Stage: E00
- Status: draft

## Integration summary

| Integration | Purpose | Direction | Stage | Current status | Owner |
|---|---|---|---|---|---|
| Corporate IdP | human identity and MFA | portal API -> IdP/Keystone federation | E02/P1 | unknown | IAM owner |
| Keystone | token, scope, roles, service catalog | API/worker -> Keystone | E02/E03 | reachable at `https://192.168.10.250:5000` with Kolla CA | OpenStack owner |
| Nova | instances, hypervisors, services, aggregates | worker/API -> Nova | E03/E04 | reachable via HTTPS service catalog | OpenStack owner |
| Placement | resource provider inventory/usage | worker/API -> Placement | E03/E04 | reachable via HTTPS service catalog | OpenStack owner |
| Mistral | long-running workflow execution | worker -> Mistral | E06 | enabled; endpoint `https://192.168.10.250:8989/v2` | Workflow/platform owner |
| Watcher | goals, strategies, audits, continuous audits, action plans, actions, recommendations and optimization risk state | worker/API -> Watcher; operations may execute via Mistral | E06+ | enabled; endpoint `https://192.168.10.250:9322`; Prometheus exporter datasource selected first, contract pending | OpenStack owner |
| Masakari | failover segments, segment hosts, notifications, monitor events and recovery timeline | worker/API -> Masakari; recovery actions may execute via Mistral/Nova workflow; Masakari hostmonitor -> Consul for network health where enabled | E06+ | API/engine enabled; endpoint `https://192.168.10.250:15868`; monitors disabled for AIO lab; Consul not on current test node | OpenStack owner |
| Telemetry datasource | capacity/health metrics, Watcher datasource freshness and Masakari incident corroboration | worker/API -> Prometheus query API first; exporters `openstack-exporter` and `node_exporter`; Ceilometer/Gnocchi/Aetos later | E10/P3 | Prometheus exporter path selected; endpoints, retention and coverage pending | Monitoring owner |
| Heat | optional stacks/workflow module | worker/API -> Heat or via Mistral | after decision | reachable via HTTPS service catalog | Product owner |
| RabbitMQ `/cloud-ui` | jobs, outbox, events | API/worker/events -> RabbitMQ | E01+ | planned | Messaging owner |
| OpenStack notifications | read model acceleration | notification transport -> event consumer | E04/E07 | unknown | Messaging/OpenStack owner |
| MariaDB `cloud_ui` | portal state, sessions, read model | API/worker/events -> MariaDB | E01+ | planned | DB owner |
| SIEM/test sink | authoritative audit delivery | audit worker -> SIEM | E07 | unknown | SIEM owner |
| Vault (SecMan) | secret storage and lifecycle | backend/deploy -> Vault | E08 | product identified; endpoint/auth/path policy unknown | Vault owner |
| Corporate PKI | TLS/mTLS certificates | deploy/runtime -> PKI | E08/E09 | unknown | PKI owner |
| Corporate registry | image storage/signing/scanning | deploy -> registry | E08/E09 | unknown | Supply-chain owner |
| HAProxy/Kolla | same-origin routing/TLS | browser -> HAProxy -> frontend/API | E09 | lab TLS enabled on VIP `192.168.10.250`; live Keystone TLS verification OK with Kolla CA | Platform owner |
| PAM/auditd/FIM | host/admin audit controls | external | E12 | unknown | Security/platform owner |
| Backup/storage | backup RBAC and ДКБ-72 storage control | external | E12 | unknown | Storage/backup owner |

## Integration rules

- Browser uses only frontend and BFF/API.
- Service catalog endpoints are trusted configuration, not browser input.
- Each adapter needs timeout, retry policy, microversion, typed errors, metrics and contract tests.
- No OpenStack service DB is accessed.
- RabbitMQ RPC queues of OpenStack are not consumed directly.
- External integrations that are not available in test must be represented by interface, mock/contract and explicit pending evidence.

## Current deployment notes

- Ansible host `192.168.10.15` has Kolla-Ansible in `/root/venvs/kolla-epoxy`.
- OpenStack all-in-one host `192.168.10.14` runs Kolla containers tagged `2025.1-rocky-9`.
- Correct admin CLI source is `/etc/kolla/admin-openrc.sh`.
- `/etc/kolla/admin-openrc.sh` now uses `https://192.168.10.250:5000` and `OS_CACERT=/etc/pki/tls/certs/ca-bundle.crt`.
- Kolla build tooling is available in `/root/venvs/kolla-epoxy`: `kolla-build` `20.4.0`, Podman `5.2.2`, Python `podman` package `5.8.0`, and `/etc/kolla/kolla-build.conf`.
- `/root/openrc` and `/root/openrc.sh` reference unreachable `192.168.10.50` and should not be used for evidence until corrected.
- SecMan is Vault; treat it as one integration, not two separate secret managers.
