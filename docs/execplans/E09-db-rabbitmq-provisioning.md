# ExecPlan: E09.3 DB/RabbitMQ provisioning

## Цель и наблюдаемый результат

E09.3 adds a verified test-stand path for Cloud UI-owned MariaDB/RabbitMQ provisioning with Vault-backed
secret storage. After this plan, an operator can point to repository contracts, sanitized live evidence
and DKB traceability showing that the all-in-one lab has a `cloud_ui` database scope, `/cloud-ui`
RabbitMQ scope and lab Vault secret paths for Cloud UI DB/MQ material.

Before this plan, E09.1/E09.2 defined image and role structure only. There was no Cloud UI-specific
DB/MQ provisioning role, live lab DB/MQ least-privilege evidence or E09.3 generated evidence.

## Контекст и текущее состояние

- Branch/worktree: `e09-db-rabbitmq-provisioning` at
  `/Users/dmitry/Desktop/dawn/.worktrees/e09-db-rabbitmq-provisioning`.
- Base: `03ce31a test: guard E09 risk evidence`.
- E09.1 evidence exists in `docs/generated/e09-kolla-image-build.md`.
- E09.2 evidence exists in `docs/generated/e09-kolla-ansible-role.md`.
- Current permanent service role: `deploy/kolla/ansible/roles/cloud_ui`.
- E09.3 design is committed in
  `docs/superpowers/specs/2026-06-24-e09-db-rabbitmq-provisioning-design.md`.
- Test stand selected by the user:
  - Ansible host: `192.168.10.15`;
  - Kolla inventory: `/etc/kolla/all-in-one`;
  - Kolla venv: `/root/venvs/kolla-epoxy`;
  - OpenStack all-in-one host: `192.168.10.14`.
- Safe read-only precheck on `192.168.10.15` found:
  - hostname `ansible.example.local`;
  - `/root/venvs/kolla-epoxy/bin/kolla-ansible` exists;
  - inventories `/etc/kolla/all-in-one`, `/root/all-in-one` and `/root/multinode` exist;
  - `/etc/kolla/passwords.yml` exists and was not read into the repository.
- Vault precheck found:
  - `vault_cli_missing`;
  - `systemctl is-active vault` -> inactive;
  - no `:8200` or `:8201` listener;
  - `https://127.0.0.1:8200/v1/sys/health` refused connection.

## Scope

- Add static E09.3 contract tests.
- Add a separate repository role `deploy/kolla/ansible/roles/cloud_ui_provisioning`.
- Bootstrap lab Vault on `192.168.10.15` only if a verified package source is available.
- Generate Cloud UI DB/MQ passwords on the remote host and store them in Vault KV paths.
- Provision test all-in-one MariaDB schema/users for `cloud_ui`.
- Provision test all-in-one RabbitMQ vhost/user/permissions for `/cloud-ui`.
- Record sanitized evidence without secret material.
- Update DKB traceability and risk register.

## Non-goals

- No production deployment.
- No production Vault/SecMan claim.
- No corporate PKI claim if a lab CA is used.
- No three-node rollout or 12-container proof.
- No migration execution; E09.4 owns `cloud-ui db-upgrade`.
- No HAProxy/TLS portal route work.
- No MariaDB HA, RabbitMQ HA/quorum or backup/failover proof.
- No storage of `clouds.yaml`, openrc, `.env`, tokens, passwords, private keys or DB dumps in Git.

## Требования и ограничения

- Browser remains isolated from DB/RabbitMQ/OpenStack internals.
- Portal uses MariaDB only for its own data, server-side sessions, operations and read model.
- RabbitMQ uses separate credentials, vhost, exchange and queues; no OpenStack RPC queue consumption.
- Secrets must come from a protected runtime mechanism and must not be logged, committed or displayed.
- Remote commands must disable shell tracing before reading Kolla passwords, Vault init material or
  generated Cloud UI secret values.
- All live commands are test-stand-only and must be idempotent where practical.
- If a command would require production credentials or affect non-Cloud UI resources, stop and record
  a blocker instead of proceeding.

## Связь с ДКБ

- ДКБ-55/56: this plan creates lab Vault-backed Cloud UI DB/MQ secret storage evidence. Production
  SecMan endpoint/auth, HA, backup, auto-unseal, rotation and owner approval remain external.
- ДКБ-42-44/76/77/80: this plan records DB/MQ object boundaries and least-privilege checks in the lab.
  Network VLAN/ACL, unused-interface blocking and management-zone proof remain external.
- ДКБ-69/70: this plan does not change image interpreter, signing, scanner or registry status.
- ДКБ-82: this plan documents repository rollback and Cloud UI-only live cleanup. Full Kolla
  rollback/reconfigure evidence remains later E09.

## Milestones

1. RED E09.3 contract test and ExecPlan committed.
2. Provisioning role skeleton makes repository structure checks pass.
3. Lab Vault bootstrap succeeds or records a blocking package/source finding.
4. DB/RabbitMQ provisioning succeeds or records a blocking live-tooling finding.
5. Sanitized evidence, DKB traceability, risk register and final gates pass.

## Progress

- [x] 2026-06-24: AGENTS.md, tasks/E09_KOLLA_DEPLOY.md, docs/12_DEPLOY_ROCKY_KOLLA.md,
  docs/09_PERFORMANCE_HA.md, docs/10_SECURITY_DKB.md, docs/generated/e08-security-review.md,
  deploy/AGENTS.md and PLANS.md read.
- [x] 2026-06-24: E09.3 design approved and committed in
  `docs/superpowers/specs/2026-06-24-e09-db-rabbitmq-provisioning-design.md`.
- [x] 2026-06-24: Test stand selected: Ansible host `192.168.10.15` and inventory
  `/etc/kolla/all-in-one`.
- [x] 2026-06-24: Selected secret mechanism: lab Vault/SecMan on `192.168.10.15`.
- [x] 2026-06-24: Vault precheck found no active Vault service or listener.
- [x] 2026-06-25: Contract and RED tests complete. Added
  `tests/test_e09_db_rabbitmq_provisioning.py`. RED command
  `/Users/dmitry/Desktop/dawn/backend/.venv/bin/python -m pytest tests/test_e09_db_rabbitmq_provisioning.py -q`
  exited 1 with expected missing-artifact failures: 4 failed, 1 passed because
  `deploy/kolla/ansible/roles/cloud_ui_provisioning/defaults/main.yml`,
  `deploy/kolla/ansible/roles/cloud_ui_provisioning/tasks/main.yml` and
  `docs/generated/e09-db-rabbitmq-provisioning.md` do not exist yet. Ruff command
  `cd backend && /Users/dmitry/Desktop/dawn/backend/.venv/bin/python -m ruff check ../tests/test_e09_db_rabbitmq_provisioning.py`
  exited 0 with `All checks passed!`.
- [x] 2026-06-25: Provisioning role skeleton added with disabled defaults, fail-closed object/path
  validation, Vault KV reads, MariaDB schema/users, RabbitMQ vhost/user/exchange/queue tasks and
  README scope notes. Contract command
  `/Users/dmitry/Desktop/dawn/backend/.venv/bin/python -m pytest tests/test_e09_db_rabbitmq_provisioning.py tests/test_e09_kolla_ansible_role.py -q`
  exited 1 with expected Task 3-only missing evidence failures: 2 failed, 10 passed. Ruff command
  `cd backend && /Users/dmitry/Desktop/dawn/backend/.venv/bin/python -m ruff check ../tests/test_e09_db_rabbitmq_provisioning.py`
  exited 0 with `All checks passed!`.
- [ ] Remote Vault bootstrap and sanitized evidence.
  - 2026-06-25: Read-only precheck confirmed host `ansible.example.local`, Kolla-Ansible and
    `/etc/kolla/all-in-one` present, Vault CLI missing, Vault service inactive and no `:8200/:8201`
    listeners.
  - 2026-06-25: Approved package-source check
    `ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/tmp/dawn_known_hosts -o BatchMode=yes root@192.168.10.15 ...`
    exited 20 with `vault_package_unavailable`. Per plan, live Vault bootstrap stopped and sanitized
    blocker evidence was recorded in `docs/generated/e09-db-rabbitmq-provisioning.md`.
- [ ] Remote DB/RabbitMQ provisioning and least-privilege evidence.
  - 2026-06-25: Not executed because the protected secret mechanism is unavailable on the selected
    test host.
- [ ] Traceability, risk register and final verification.
  - 2026-06-25: Added `docs/generated/e09-db-rabbitmq-provisioning.md`, DKB traceability update and
    risk `R-063` to record the external blocker without claiming live DB/MQ proof.
  - 2026-06-25: `make lint` initially failed because the secret scanner flagged safe Ansible
    Vault-backed template references in `cloud_ui_provisioning` tasks. Added a narrow regression test
    and allowlist for those exact no-log role paths; direct scanner run then passed.
  - 2026-06-25: Verification passed:
    `backend/.venv/bin/python -m pytest backend/tests/test_secret_scan_script.py -q` -> 3 passed;
    `/Users/dmitry/Desktop/dawn/backend/.venv/bin/python -m pytest tests/test_e09_kolla_image_build.py tests/test_e09_kolla_ansible_role.py tests/test_e09_db_rabbitmq_provisioning.py -q` -> 19 passed;
    `make lint` -> backend Ruff, frontend ESLint and secret scan passed;
    `make typecheck` -> backend mypy and frontend TypeScript passed;
    `make test` -> backend 327 passed, 1 skipped; frontend 35 passed;
    `make security` -> secret scan passed;
    `git diff --check` -> passed.

## Неожиданные открытия

- Vault is not installed/active on the selected Ansible host even though E09.3 selected Vault/SecMan as
  the secret mechanism. The plan therefore has to bootstrap lab Vault before DB/MQ provisioning.
- The selected test host does not currently expose an approved Vault package through `dnf`; the remote
  check returned `vault_package_unavailable`. E09.3 cannot safely proceed to DB/MQ mutation until an
  approved Vault/SecMan source or pre-installed approved lab Vault is available.
- The repository secret scanner intentionally flags password-like YAML keys. E09.3 Ansible modules
  need those module argument names for Vault-derived values, so `scripts/secret-scan.sh` now has a
  narrow path-and-expression allowlist plus `backend/tests/test_secret_scan_script.py` regression
  coverage.

## Журнал решений

- 2026-06-24: Use a separate `cloud_ui_provisioning` role rather than adding DB/MQ tasks to the E09.2
  `cloud_ui` permanent service role. Alternative: extend `cloud_ui`. Reason: E09.3 is one-time
  dependency provisioning and must not alter the permanent container role semantics. Consequence:
  later E09 rollout can compose both roles explicitly.
- 2026-06-24: Keep live remote mutating commands in the controller session, not subagents. Reason:
  Vault/DB/MQ mutation requires serial execution and careful secret-output handling. Consequence:
  subagents may review/edit repository files only.
- 2026-06-24: Fail closed if Vault package source or safe RabbitMQ queue declaration tooling is absent.
  Alternative: hand-roll ad hoc install/queue commands. Reason: E09 evidence must not fake production
  integration or leak credentials. Consequence: a blocker may be recorded instead of full live proof.
- 2026-06-25: Do not install Vault outside the approved package-source path after `dnf` returned
  `vault_package_unavailable`. Alternative: download/install Vault through an ad hoc path. Reason:
  E09.3 requires an approved secret mechanism and package provenance before live DB/MQ mutation.
  Consequence: E09.3 is blocked with repository contract and blocker evidence only.
- 2026-06-25: Allowlist only exact Cloud UI provisioning Ansible template references in the secret
  scanner. Alternative: weaken the generic password-key pattern. Reason: the role needs Ansible module
  argument names, but arbitrary literal secret values must remain blocked. Consequence: `make lint`
  passes while the scanner regression still reports ordinary secret literals.

## Детальный план реализации

The detailed TDD plan is
`docs/superpowers/plans/2026-06-24-e09-db-rabbitmq-provisioning.md`.

Implementation order:

1. Add RED test `tests/test_e09_db_rabbitmq_provisioning.py`.
2. Add `deploy/kolla/ansible/roles/cloud_ui_provisioning`.
3. Add generated evidence file.
4. Run Vault bootstrap on `192.168.10.15` if package source is available.
5. Generate Cloud UI DB/MQ secrets into Vault only.
6. Provision MariaDB and RabbitMQ on the test all-in-one.
7. Record sanitized evidence, traceability and risk register.
8. Run full repository verification and final review.

## Миграции и совместимость

No application DB schema migration is executed. The `cloud_ui` database is created as an empty portal
schema for later migrations. E09.4 owns one-shot migration ordering and rollback-window behavior.

Provisioning commands are designed to be idempotent:

- `CREATE DATABASE IF NOT EXISTS`;
- `CREATE USER IF NOT EXISTS` or equivalent user update;
- RabbitMQ vhost add is allowed to already exist;
- RabbitMQ user password can be changed from Vault material;
- permissions are overwritten to the scoped Cloud UI regex.

The permanent service role remains disabled by default. No API/worker/events container rollout occurs
in this plan.

## Проверка

Repository verification:

```bash
/Users/dmitry/Desktop/dawn/backend/.venv/bin/python -m pytest tests/test_e09_kolla_image_build.py tests/test_e09_kolla_ansible_role.py tests/test_e09_db_rabbitmq_provisioning.py -q
cd backend && /Users/dmitry/Desktop/dawn/backend/.venv/bin/python -m ruff check ../tests/test_e09_db_rabbitmq_provisioning.py
make lint
make typecheck
make test
make security
git diff --check
rg -n "root token|unseal key|client token|private key|BEGIN|password:|production approved|clouds.yaml|openrc" deploy/kolla docs/generated/e09-db-rabbitmq-provisioning.md docs/11_DKB_TRACEABILITY.md docs/generated/risk-register.md tests/test_e09_db_rabbitmq_provisioning.py
```

Remote verification:

- Vault initialized/unsealed status without secret values.
- KV mount and audit device visible.
- MariaDB runtime user can connect to `cloud_ui` and cannot connect to the `mysql` schema.
- RabbitMQ `/cloud-ui` vhost exists, user permissions exist, and root vhost permission is absent.
- Queue/exchange declaration either succeeds with safe tooling or is recorded as a live blocker.

## Доказательства

- `tests/test_e09_db_rabbitmq_provisioning.py`;
- `backend/tests/test_secret_scan_script.py`;
- `scripts/secret-scan.sh`;
- `deploy/kolla/ansible/roles/cloud_ui_provisioning/*`;
- `docs/generated/e09-db-rabbitmq-provisioning.md`;
- `docs/generated/risk-register.md`;
- `docs/11_DKB_TRACEABILITY.md`;
- this ExecPlan.

Evidence must not contain Vault root token, unseal key, client token, private key, DB/MQ password,
`passwords.yml`, `clouds.yaml`, openrc content or DB dumps.

## Откат и восстановление

Repository rollback is a Git revert of E09.3 commits.

Live cleanup, only if explicitly approved:

- revoke Cloud UI lab Vault token and delete `kv/cloud-ui/local/*` paths;
- drop MariaDB users `cloud_ui` and `cloud_ui_migration`;
- drop MariaDB schema `cloud_ui` after confirming no required test data remains;
- delete RabbitMQ user `cloud_ui`;
- delete RabbitMQ vhost `/cloud-ui` and Cloud UI-owned exchanges/queues.

Vault service rollback follows the E08 runbook:

```bash
sudo systemctl stop vault
sudo systemctl disable vault
```

Preserve `/opt/vault/data` unless destructive cleanup is explicitly approved.

## Итог и остаточные риски

Current status: blocked before live DB/RabbitMQ mutation. The repository contract and sanitized
external blocker evidence are present, but E09.3 live provisioning is not complete because the
selected test host has no approved Vault package source.

- approved Vault/SecMan package source or pre-installed approved lab Vault is required before DB/MQ
  provisioning can run;
- live MariaDB schema/users and RabbitMQ vhost/user/permissions were not created;
- least-privilege negative DB/MQ checks were not executed;
- lab all-in-one evidence is not HA production evidence;
- corporate PKI, Vault HA/backup/auto-unseal and production owner approval remain external;
- MariaDB backup/failover and RabbitMQ quorum/HA remain E10/external;
- full three-node Kolla rollout, HAProxy/TLS and rollback remain later E09 work.
