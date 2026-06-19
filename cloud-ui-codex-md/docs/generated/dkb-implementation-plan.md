# DKB implementation plan

- Stage: E00
- Source: `docs/11_DKB_TRACEABILITY.md`
- Count: 73 unique DKB codes verified by local `rg` command.
- Status: planning only, no compliance claim.

## Gates

| Gate | Meaning |
|---|---|
| P1 | Integrated read-only PoC evidence for portal scope |
| P2 | Integrated mutating PoC evidence for portal scope |
| P3 | Production pilot or external control evidence |

## Implementation matrix

| Code | Primary stage | Gate | Owner contour | E00 evidence plan |
|---|---|---|---|---|
| ДКБ-01 | E02 | P1 | Portal + Keystone + IAM | role matrix, capability tests, backend 403, audit denial |
| ДКБ-01.01 | E02 | P1 | Portal + Keystone + IAM | least privilege roles and negative tests |
| ДКБ-01.02 | E02 | P2 | Portal + DB/PAM external | DB least privilege plus external DBA/root controls |
| ДКБ-01.03 | E02 | P2 | Portal + OpenStack + external controls | policy coverage and host/storage boundary evidence |
| ДКБ-01.04 | E02 | P1 | Portal + Keystone | role-based access tests |
| ДКБ-01.05 | E02 | P1 | Portal + IAM | functional role matrix and owner approval |
| ДКБ-01.06 | E02 | P2 | Portal + OpenStack + external controls | data access scope tests and external boundary |
| ДКБ-02 | E02 | P1 | IAM + portal checks | SoD matrix, conflict tests, IAM evidence pending |
| ДКБ-02.01 | E02 | P1 | IAM + Keystone | admin role group mapping evidence |
| ДКБ-02.02 | E02 | P1 | Keystone/service identities | service role separation and non-interactive account evidence |
| ДКБ-02.03 | E02 | P1 | IAM + network | internal user group and network access evidence |
| ДКБ-03 | E02 | P2 | Portal + OpenStack + PAM/storage | API RBAC plus external direct-access controls |
| ДКБ-04 | E02 | P2 | IAM | SoD enforcement evidence from IAM |
| ДКБ-05 | E02 | P2 | IAM/PAM/auditd | personalized admin/sudo/session recording evidence |
| ДКБ-06 | E02 | P1 | IAM + Keystone | centralized auth/federation evidence |
| ДКБ-07 | E02/E12 | P2 | IAM + OpenStack + waiver owner | service account exception and compensating controls |
| ДКБ-12 | E02 | P1 | Portal + OpenStack | UI hide plus backend deny tests |
| ДКБ-13 | E02/E08 | P2 | Portal + Vault(SecMan)/PAM | no password display plus host/root secret controls |
| ДКБ-15 | E02 | P1 | Keystone/IdP | auth policy/federation decision evidence |
| ДКБ-17 | E12 | P3 | Nova/libvirt/storage/guest OS | storage isolation evidence or gap |
| ДКБ-18 | E12 | P3 | Backup/IAM/PAM | backup RBAC and audit evidence |
| ДКБ-20 | E02 | P1 | Portal + IdP/Keystone | session limit tests and CLI token policy gap |
| ДКБ-21 | E02 | P1 | Portal + IdP/Keystone | idle timeout, absolute lifetime, revoke tests |
| ДКБ-22.02 | E08/E09 | P2/P3 | PKI/platform | TLS/mTLS matrix, positive/negative tests |
| ДКБ-23.02 | E08/E09 | P2 | PKI/platform | corporate CA/SCEP/NDES process evidence |
| ДКБ-24 | E08/E09 | P1 | Portal/Kolla/PKI | external TLS scan |
| ДКБ-25 | E08/E09 | P2 | Portal/Kolla/PKI | certificate lifecycle evidence |
| ДКБ-42 | E09 | P3 | Network/platform | management zone and ACL evidence |
| ДКБ-43 | E09 | P3 | Network/platform | backend network segmentation evidence |
| ДКБ-44 | E09 | P3 | Network/platform | firewall/route evidence |
| ДКБ-46 | E07 | P1 | Portal + SIEM | audit event schema and delivery tests |
| ДКБ-47 | E07/E10 | P2/P3 | Portal + monitoring/SIEM | audit availability, heartbeat, failover evidence |
| ДКБ-48 | E07/E12 | P3 | SIEM/FIM/auditd/platform | anti-disable controls and heartbeat alerts |
| ДКБ-49 | E07 | P1 | Portal + SIEM | mandatory audit fields |
| ДКБ-49.01 | E07 | P1 | Portal + SIEM | actor field evidence |
| ДКБ-49.02 | E07 | P1 | Portal + SIEM | action/event field evidence |
| ДКБ-49.03 | E07 | P1 | Portal + SIEM | target/scope field evidence |
| ДКБ-49.04 | E07 | P1 | Portal + SIEM | timestamp UTC evidence |
| ДКБ-49.05 | E07 | P1 | Portal + SIEM | outcome evidence |
| ДКБ-49.08 | E07 | P1 | Portal + SIEM | source/correlation/session evidence |
| ДКБ-50 | E07/E12 | P3 | Portal + OpenStack + SIEM + host/storage/IdP | audit source map and external evidence |
| ДКБ-50.01 | E07/E12 | P3 | Keystone/IdP/SIEM | user/role change event sources |
| ДКБ-50.02 | E07/E12 | P3 | Keystone/IdP/guest OS | auth success/failure and VM user boundary |
| ДКБ-50.03 | E07/E12 | P3 | Kolla/IaC/FIM/SIEM | config change evidence |
| ДКБ-50.04 | E07/E12 | P3 | SIEM/PAM/auditd | admin action evidence |
| ДКБ-50.06 | E07/E12 | P3 | API logs/PAM/network | component access evidence |
| ДКБ-50.07 | E07/E10 | P3 | Monitoring/SIEM/platform | unavailable component events |
| ДКБ-50.08 | E07/E12 | P3 | Keystone/IdP/SIEM | auth mechanism change events |
| ДКБ-50.10 | E07/E12 | P3 | OpenStack/SIEM | system object create/delete events |
| ДКБ-50.11 | E07/E12 | P3 | Neutron/host/network/SIEM | virtual network setting changes |
| ДКБ-50.12 | E07/E12 | P3 | Nova/SIEM/host audit | VM lifecycle events |
| ДКБ-50.13 | E07/E12 | P3 | Glance/storage/SIEM | image lifecycle events |
| ДКБ-50.14 | E07/E12 | P3 | Nova/Cinder/Glance/storage | image copy/snapshot controls |
| ДКБ-50.15 | E07/E12 | P3 | Keystone/PAM/SIEM | logical access changes |
| ДКБ-50.16 | E07/E12 | P3 | Kolla/IaC/FIM/SIEM | server component config changes |
| ДКБ-50.17 | E07/E12 | P3 | systemd/container runtime/auditd | service start/stop events |
| ДКБ-50.19 | E07/E12 | P3 | Storage/backup/SIEM | current image copy controls |
| ДКБ-51 | E07 | P1 | Portal + SIEM | redaction canary tests |
| ДКБ-52 | E07 | P1 | Portal + protected logs/SIEM | safe audit error plus protected full detail |
| ДКБ-53 | E07 | P1 | Portal + SIEM/platform | audit read/export RBAC and no direct access controls |
| ДКБ-55 | E08/E09 | P2 | Vault (SecMan) + Kolla + portal | Vault contract and Kolla secret boundary |
| ДКБ-56 | E08/E09/E12 | P2 | Vault (SecMan) + deployment pipeline | all-secret lifecycle, rotation runbook, gap/waiver |
| ДКБ-60 | E05 | P2 | Portal + Nova | group CRUD, dynamic rule, DKB-60 demo |
| ДКБ-62 | E12 | P3 | Vendor/operations | update SLA/advisory evidence or gap |
| ДКБ-65 | E08/E09/E12 | P3 | Rocky/Kolla/platform | SELinux/AppArmor host evidence |
| ДКБ-66 | E10 | P3 | Kolla/OpenStack/storage/network | failover/load/recovery reports |
| ДКБ-69 | E08/E09/E12 | P3 | Kolla/supply chain/security owner | image hardening plus interpreter waiver |
| ДКБ-70 | E08/E09 | P2 | Registry/supply chain | corporate registry digest/SBOM/scan evidence |
| ДКБ-72 | E12 | P3 | Nova/Cinder/Ceph/storage | storage path evidence or waiver |
| ДКБ-76 | E08/E09/E12 | P3 | Container platform/security owner | requirement clarification for 76.x |
| ДКБ-77 | E03/E08/E09 | P1/P3 | Portal + OpenStack/Kolla/network | API register plus technical blocking |
| ДКБ-80 | E09 | P3 | Kolla/Rocky/network | management zone evidence |
| ДКБ-82 | E11 | P1 | Product/operations | technical and operational documentation |

## High-risk gap handling

| Code | Required E00 action |
|---|---|
| ДКБ-07 | Assign IAM/security owner for service account exception. |
| ДКБ-22.02 | Require mTLS scope decision in ADR/security review. |
| ДКБ-48/50 | Create audit source map in E07 and external evidence matrix in E12. |
| ДКБ-55/56 | Require Vault owner and rotation runbook. |
| ДКБ-65 | Require Rocky SELinux/AppArmor evidence on actual host. |
| ДКБ-69 | Require explicit waiver for Python backend interpreter. |
| ДКБ-72 | Require storage architecture evidence, not UI setting. |
| ДКБ-76 | Request full DKB-76.x text before claiming status. |

## Verification

The source matrix contains 73 unique codes:

```bash
rg -o "ДКБ-[0-9]+(?:\\.[0-9]+)?" cloud-ui-codex-md/docs/11_DKB_TRACEABILITY.md | sort -u | wc -l
```

Expected result:

```text
73
```

## Current environment delta from assumptions

- Current test service catalog includes Mistral, Watcher and Masakari after the 2026-06-19 Kolla update. Service-specific contract tests and production policy decisions remain pending.
- Current observed API endpoints use HTTP on `192.168.10.250`. ДКБ-24 and ДКБ-22.02 evidence remains blocked until TLS/mTLS configuration and scans are available.
- `/root/openrc` points to unreachable `192.168.10.50`; `/etc/kolla/admin-openrc.sh` is the working test admin source. Do not use stale openrc files as evidence.
