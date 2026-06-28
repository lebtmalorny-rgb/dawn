# E09 live reconfigure preflight bundle

- Stage: E09 live reconfigure preflight bundle
- Status: preflight only; live deploy/reconfigure remains `pending_external_evidence`
- Scope: repository-side operator bundle for approved test inventory validation
- Production action: none

## Bundle

| Artifact | Purpose |
|---|---|
| `deploy/kolla/ansible/playbooks/cloud-ui-preflight.yml` | Validates approved test marker, rollback window, digest-pinned images and runtime DB/MQ secret inputs. |
| `deploy/kolla/ansible/examples/cloud-ui-vars.yml.example` | Placeholder-only variables for a non-committed test-stand vars file. |
| `deploy/kolla/ansible/roles/cloud_ui` | Existing Cloud UI role validation imported with `tasks_from: validate`. |

The preflight imports only the role validation task path. It does not run live mutating Kolla actions, create containers, render runtime config, mutate MariaDB/RabbitMQ/Vault, execute migration, apply HAProxy or perform rollback.

Role resolution note: when invoking the preflight playbook from this repository, provide the Cloud UI role path through `ANSIBLE_ROLES_PATH=deploy/kolla/ansible/roles` or an equivalent Ansible roles path configuration.

## Subsequent AIO lab evidence

On 2026-06-28 the preflight bundle was synchronized to the Ansible host and executed against the
approved all-in-one inventory. The preflight completed with `localhost : ok=10 changed=0 failed=0`.
A separate bounded AIO reconfigure playbook then converged the current lab UI; that evidence is
recorded in `docs/generated/e09-deployment-smoke-evidence.md`.

This document remains scoped to the preflight bundle. Full E09 acceptance still requires the
three-node/twelve-container, HAProxy/VIP/TLS, SELinux and rollback evidence listed below.

## Required live follow-up

Full E09 acceptance remains blocked until an explicitly approved test-stand run provides:

- copied bundle path and sanitized preflight output;
- approved non-committed vars file or environment injection for runtime secret values;
- Kolla role/config installation evidence on the approved test stand;
- one-shot migration evidence;
- Kolla lifecycle idempotency evidence;
- three-node/twelve-container inspection;
- HAProxy/TLS smoke;
- hardening inspection for non-root/read-only/caps/SELinux;
- rollback execution evidence.

## DKB scope

- ДКБ-55/56: the bundle validates that DB/MQ runtime inputs are supplied, but stores no runtime secret value. Rotation, owner approval and SecMan evidence remain pending.
- ДКБ-65/69/70: no new image or container inspection evidence is created by preflight only.
- ДКБ-76/77/80: network/API registry evidence remains pending until live Kolla run and inspection.
- ДКБ-82: this adds operator documentation, not live rollback/deployment acceptance.
