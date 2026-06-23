# TLS and mTLS matrix

- Stage: E00
- Status: draft
- Rule: no TLS/mTLS claim is accepted until test scan or negative certificate test exists.

| Flow | Minimum TLS | mTLS | CA/source | Identity check | Stage | Evidence |
|---|---|---|---|---|---|---|
| Browser -> external VIP | TLS 1.2 | no by default | corporate PKI | hostname verification | E08/E09 | TLS scan |
| HAProxy -> frontend | deployment decision | optional | internal PKI if TLS | service DNS/name | E09 | Kolla/HAProxy config and smoke |
| HAProxy -> API | deployment decision | optional | internal PKI if TLS | service DNS/name | E09 | Kolla/HAProxy config and smoke |
| API/worker -> Keystone | TLS 1.2 | decision pending | OpenStack/internal CA | endpoint hostname | E02/E03/E08 | contract smoke and TLS scan |
| API/worker -> Nova | TLS 1.2 | decision pending | OpenStack/internal CA | endpoint hostname | E03/E08 | contract smoke and TLS scan |
| API/worker -> Placement | TLS 1.2 | decision pending | OpenStack/internal CA | endpoint hostname | E03/E08 | contract smoke and TLS scan |
| API/worker -> Mistral | TLS 1.2 | decision pending | OpenStack/internal CA | endpoint hostname | E06/E08 | contract smoke and TLS scan |
| API/worker -> Watcher | TLS 1.2 | decision pending | OpenStack/internal CA | endpoint hostname | E06/E08 | contract smoke and TLS scan |
| API/worker -> Masakari | TLS 1.2 | decision pending | OpenStack/internal CA | endpoint hostname | E06/E08 | contract smoke and TLS scan |
| Masakari hostmonitor -> Consul | TLS 1.2 if Consul TLS enabled | decision pending | corporate/internal CA | Consul server identity | E10/P3/E08 | Consul ACL/TLS smoke and matrix recovery test |
| API/worker -> Prometheus datasource | TLS 1.2 | decision pending | OpenStack/internal or corporate CA | endpoint hostname | E10/P3/E08 | contract smoke, freshness test and TLS scan |
| Prometheus -> `openstack-exporter`/`node_exporter` | deployment decision | decision pending | internal or corporate CA | exporter endpoint identity | E10/P3/E08 | scrape auth/TLS smoke and cardinality review |
| Portal -> MariaDB | TLS if supported by Kolla baseline | optional/client cert decision pending | internal CA | DB endpoint | E09 | DB TLS config and negative test if mTLS |
| Portal -> RabbitMQ | TLS in production | optional/client cert decision pending | internal CA | broker endpoint | E09 | broker TLS config and negative test if mTLS |
| Audit worker -> SIEM | TLS 1.2 | likely yes, pending SIEM contract | corporate PKI | SIEM endpoint + client identity | E07/E08 | delivery test and cert rejection |
| Deploy/runtime -> Vault (SecMan) | TLS 1.2 | server TLS + Vault auth; mTLS pending owner decision | corporate/test PKI preferred; lab CA fallback is lab-only | Vault endpoint + auth method | E08 | E08 server TLS contract, adapter CA verification tests, lab runbook; mTLS pending owner decision |
| Deploy -> registry | TLS 1.2 | policy pending | corporate PKI | registry endpoint | E08/E09 | pull/push by digest and scan |

## Open decisions

- Exact flows requiring mTLS under ДКБ-22.02.
- Corporate CA chain injection into runtime containers.
- Certificate rotation process and emergency revoke.
- Whether backend TLS is required behind HAProxy in the target management zone.
- How certificate identity maps to service authorization for SIEM/Vault/RabbitMQ/MariaDB.

## Current observations

Lab update on 2026-06-19:

- Kolla internal and external TLS are enabled for the test VIP `192.168.10.250`.
- Kolla generated a test CA and HAProxy certificate. The HAProxy certificate issuer is `KollaTestCA`, includes SAN `IP Address:192.168.10.250`, and is valid from 2026-06-19 to 2027-06-19.
- The Kolla CA was installed into the Ansible and OpenStack host trust stores.
- Horizon responds over `https://192.168.10.250` with HTTP/2 302 to `/auth/login/`.
- Keystone version discovery over `https://192.168.10.250:5000/v3` returns `v3.14`.
- `openssl s_client` to `192.168.10.250:5000` with the Kolla CA reports TLSv1.3 and `Verification: OK`.
- `/etc/kolla/admin-openrc.sh` now exports `OS_AUTH_URL='https://192.168.10.250:5000'` and `OS_CACERT='/etc/pki/tls/certs/ca-bundle.crt'`.
- Horizon Python clients that rely on `requests/certifi` are configured through `/etc/kolla/config/horizon/_9999-custom-settings.py` to use the Kolla CA bundle. This fixes Mistral dashboard calls to `https://192.168.10.250:8989/v2/workbooks`.

Limits:

- This is lab TLS evidence only, using a Kolla-generated CA, not corporate PKI.
- mTLS, certificate rotation, revocation and production certificate policy remain E08/E09 gaps.
