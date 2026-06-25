# E09.7 Reconfigure/upgrade/rollback evidence

- Stage: E09.7 Reconfigure/upgrade/rollback
- Status: repository-side lifecycle contract; not a live Kolla reconfigure.
- Scope: clean deploy/reconfigure ordering, rolling upgrade ordering, failed update rollback,
  disable/uninstall policy and evidence gates.
- Live execution status: `pending_external_evidence`.

## Lifecycle contract

The Cloud UI role publishes dry-run lifecycle facts for later test-inventory execution tooling:

- `cloud_ui_lifecycle_plan`;
- `cloud_ui_reconfigure_plan`;
- `cloud_ui_rolling_upgrade_plan`;
- `cloud_ui_failed_update_rollback_plan`;
- `cloud_ui_disable_uninstall_plan`.

The role does not run `kolla-ansible deploy`, `kolla-ansible reconfigure`, `kolla-ansible destroy`
or shell/command tasks in this slice.

## Clean deploy/reconfigure

The repository contract orders clean deploy/reconfigure as:

1. precheck;
2. confirm backup and rollback window;
3. pull images by digest;
4. migration precheck;
5. one-shot migration;
6. render config;
7. apply permanent containers;
8. apply HAProxy route;
9. smoke;
10. idempotency check;
11. record evidence.

## Rolling upgrade

Rolling upgrade requires digest-pinned image pull and migration before backend rollout. Backend API,
worker and events roll before frontend. HAProxy health and compatibility smoke follow service rollout.
The contract migration is held until the rollback window closes; contract migration is held by default.

## Failed update rollback

Failed update rollback restores the previous config commit and previous frontend/backend image digests,
reruns reconfigure in the test inventory, smokes the previous version and preserves:

- operations;
- audit events;
- read model;
- queued messages.

If a contract migration has already been applied, repository rollback is not enough; the required
action is restore from approved backup or forward fix.

## Disable/uninstall

Disable/uninstall is data-preserving by default:

- set `cloud_ui_enabled=false`;
- remove HAProxy route;
- stop frontend, API, worker and events;
- preserve database, RabbitMQ vhost, Vault paths and logs;
- destructive cleanup requires explicit external approval.

## ДКБ scope

- ДКБ-55/56: no deployment secrets are stored in Git; full SecMan rotation remains external.
- ДКБ-69/70: lifecycle requires digest-pinned images before rollout, but live registry pull,
  scanner/signature/SBOM and ДКБ-69 waiver remain pending.
- ДКБ-76/77/80: lifecycle interfaces are documented for test inventory execution, but firewall/ACL,
  network-zone and unused-interface blocking proof remain external.
- ДКБ-82: operational lifecycle and rollback path are documented; live rolling update and failed
  rollback execution remain pending.
