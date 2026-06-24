# E09.3 Database/RabbitMQ Provisioning Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add tested E09.3 repository contracts and sanitized live evidence for Cloud UI Vault-backed MariaDB/RabbitMQ provisioning on the approved all-in-one test stand.

**Architecture:** Keep permanent container role behavior from E09.2 unchanged and add a separate `cloud_ui_provisioning` role for one-time dependency provisioning. Live work runs only from the controller session against `192.168.10.15` and `/etc/kolla/all-in-one`; subagents may edit repository files but must not run remote mutating commands.

**Tech Stack:** Python `pytest`, PyYAML, Ansible YAML, Kolla-Ansible all-in-one lab, HashiCorp Vault lab runbook, MariaDB and RabbitMQ Kolla containers.

---

## File Structure

- Create `tests/test_e09_db_rabbitmq_provisioning.py`: static contract tests for provisioning role, evidence and unique risk IDs.
- Create `deploy/kolla/ansible/roles/cloud_ui_provisioning/defaults/main.yml`: non-secret object names, Vault paths and provisioning policy shape.
- Create `deploy/kolla/ansible/roles/cloud_ui_provisioning/tasks/main.yml`: includes validation, Vault, database and RabbitMQ tasks.
- Create `deploy/kolla/ansible/roles/cloud_ui_provisioning/tasks/validate.yml`: fail-closed assertions for object names and path scope.
- Create `deploy/kolla/ansible/roles/cloud_ui_provisioning/tasks/vault.yml`: Vault KV reference/read task shape with `no_log: true`.
- Create `deploy/kolla/ansible/roles/cloud_ui_provisioning/tasks/database.yml`: MariaDB schema/user provisioning task shape with `no_log: true`.
- Create `deploy/kolla/ansible/roles/cloud_ui_provisioning/tasks/rabbitmq.yml`: RabbitMQ vhost/user/exchange/queue permission task shape with `no_log: true`.
- Create `docs/generated/e09-db-rabbitmq-provisioning.md`: sanitized E09.3 evidence.
- Modify `deploy/kolla/ansible/README.md`: link E09.3 provisioning role.
- Modify `docs/generated/risk-register.md`: add a unique E09.3 risk row.
- Modify `docs/11_DKB_TRACEABILITY.md`: add E09.3 DKB traceability update.
- Create and maintain `docs/execplans/E09-db-rabbitmq-provisioning.md`: active ExecPlan and verification record.

## Task 1: Add RED Contract Test and ExecPlan

**Files:**
- Create: `tests/test_e09_db_rabbitmq_provisioning.py`
- Create: `docs/execplans/E09-db-rabbitmq-provisioning.md`

- [ ] **Step 1: Create initial ExecPlan**

Create `docs/execplans/E09-db-rabbitmq-provisioning.md` from `PLANS.md` with:

```markdown
# ExecPlan: E09.3 DB/RabbitMQ provisioning

## Цель и наблюдаемый результат

E09.3 adds an approved test-stand path for Vault-backed Cloud UI MariaDB/RabbitMQ provisioning and
repository contracts that keep permanent service rollout separate from one-time dependency setup.

## Progress

- [x] 2026-06-24: AGENTS.md, tasks/E09_KOLLA_DEPLOY.md, docs/12_DEPLOY_ROCKY_KOLLA.md,
  docs/09_PERFORMANCE_HA.md, docs/10_SECURITY_DKB.md, docs/generated/e08-security-review.md,
  deploy/AGENTS.md and PLANS.md read.
- [x] 2026-06-24: E09.3 design approved and committed in
  docs/superpowers/specs/2026-06-24-e09-db-rabbitmq-provisioning-design.md.
- [x] 2026-06-24: Test stand selected: Ansible host 192.168.10.15 and inventory /etc/kolla/all-in-one.
- [x] 2026-06-24: Selected secret mechanism: lab Vault/SecMan on 192.168.10.15.
- [ ] Contract and RED tests.
- [ ] Provisioning role skeleton.
- [ ] Remote Vault bootstrap and sanitized evidence.
- [ ] Remote DB/RabbitMQ provisioning and least-privilege evidence.
- [ ] Traceability, risk register and final verification.
```

Fill every required ExecPlan section. Record that Vault precheck currently found `vault_cli_missing`, `inactive`, no `:8200/:8201` listener and health connection refused.

- [ ] **Step 2: Write the failing E09.3 test**

Create `tests/test_e09_db_rabbitmq_provisioning.py`:

```python
import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
ROLE_ROOT = ROOT / "deploy/kolla/ansible/roles/cloud_ui_provisioning"

EXPECTED_FILES = [
    "deploy/kolla/ansible/roles/cloud_ui_provisioning/defaults/main.yml",
    "deploy/kolla/ansible/roles/cloud_ui_provisioning/tasks/main.yml",
    "deploy/kolla/ansible/roles/cloud_ui_provisioning/tasks/validate.yml",
    "deploy/kolla/ansible/roles/cloud_ui_provisioning/tasks/vault.yml",
    "deploy/kolla/ansible/roles/cloud_ui_provisioning/tasks/database.yml",
    "deploy/kolla/ansible/roles/cloud_ui_provisioning/tasks/rabbitmq.yml",
    "docs/generated/e09-db-rabbitmq-provisioning.md",
]


def read_text(relative_path: str) -> str:
    return (ROOT / relative_path).read_text(encoding="utf-8")


def load_yaml(relative_path: str) -> object:
    return yaml.safe_load(read_text(relative_path))


def load_yaml_list(relative_path: str) -> list[dict]:
    loaded = load_yaml(relative_path)
    if not isinstance(loaded, list):
        return []
    return loaded


def role_text() -> str:
    if not ROLE_ROOT.exists():
        return ""
    return "\n".join(
        path.read_text(encoding="utf-8")
        for path in ROLE_ROOT.rglob("*")
        if path.is_file()
    )


def test_e09_db_rabbitmq_files_exist() -> None:
    for relative_path in EXPECTED_FILES:
        assert (ROOT / relative_path).exists(), relative_path


def test_provisioning_defaults_define_non_secret_scope() -> None:
    defaults = load_yaml(
        "deploy/kolla/ansible/roles/cloud_ui_provisioning/defaults/main.yml"
    )
    assert isinstance(defaults, dict)

    assert defaults["cloud_ui_provisioning_enabled"] is False
    assert defaults["cloud_ui_vault_addr"] == "https://192.168.10.15:8200"
    assert defaults["cloud_ui_vault_kv_mount"] == "kv"
    assert defaults["cloud_ui_vault_secret_paths"] == {
        "mariadb_runtime": "cloud-ui/local/mariadb/runtime",
        "mariadb_migration": "cloud-ui/local/mariadb/migration",
        "rabbitmq_runtime": "cloud-ui/local/rabbitmq/runtime",
    }

    assert defaults["cloud_ui_database_name"] == "cloud_ui"
    assert defaults["cloud_ui_database_runtime_user"] == "cloud_ui"
    assert defaults["cloud_ui_database_migration_user"] == "cloud_ui_migration"
    assert defaults["cloud_ui_rabbitmq_vhost"] == "/cloud-ui"
    assert defaults["cloud_ui_rabbitmq_user"] == "cloud_ui"
    assert set(defaults["cloud_ui_rabbitmq_exchanges"]) == {
        "cloud-ui.events",
        "cloud-ui.jobs",
        "cloud-ui.audit",
        "cloud-ui.dlx",
    }
    assert set(defaults["cloud_ui_rabbitmq_queues"]) == {
        "cloud-ui.events",
        "cloud-ui.jobs",
        "cloud-ui.audit",
        "cloud-ui.dead",
    }

    serialized = yaml.safe_dump(defaults).lower()
    for forbidden in ["password:", "token:", "private_key", "secret_key", "clouds.yaml"]:
        assert forbidden not in serialized


def test_provisioning_tasks_are_separate_and_secret_safe() -> None:
    main_tasks = load_yaml_list(
        "deploy/kolla/ansible/roles/cloud_ui_provisioning/tasks/main.yml"
    )
    actual_includes = []
    for task in main_tasks:
        assert isinstance(task, dict)
        include_value = task.get("ansible.builtin.include_tasks") or task.get("include_tasks")
        assert include_value is not None
        actual_includes.append(str(include_value).strip())

    assert actual_includes == ["validate.yml", "vault.yml", "database.yml", "rabbitmq.yml"]

    combined = role_text().lower()
    for required in [
        "community.hashi_vault.vault_kv2_get",
        "community.mysql.mysql_db",
        "community.mysql.mysql_user",
        "community.rabbitmq.rabbitmq_vhost",
        "community.rabbitmq.rabbitmq_user",
        "cloud-ui.dlx",
    ]:
        assert required in combined

    for task_file in ["vault.yml", "database.yml", "rabbitmq.yml"]:
        tasks = load_yaml_list(
            f"deploy/kolla/ansible/roles/cloud_ui_provisioning/tasks/{task_file}"
        )
        assert any(task.get("no_log") is True for task in tasks), task_file

    for forbidden in ["kolla_container:", "openstack rpc", "production approved"]:
        assert forbidden not in combined


def test_e09_db_rabbitmq_evidence_records_live_scope_and_limits() -> None:
    evidence = read_text("docs/generated/e09-db-rabbitmq-provisioning.md")

    for expected in [
        "Stage: E09.3 Database/RabbitMQ provisioning",
        "Test Ansible host: 192.168.10.15",
        "Kolla inventory: /etc/kolla/all-in-one",
        "Vault/SecMan lab path",
        "cloud_ui",
        "cloud_ui_migration",
        "/cloud-ui",
        "pending_external_evidence",
        "ДКБ-55/56",
        "ДКБ-76/77/80",
    ]:
        assert expected in evidence

    assert "production approved" not in evidence.lower()
    assert "root token" not in evidence.lower()
    assert "unseal key" not in evidence.lower()
    assert "client token" not in evidence.lower()


def test_risk_register_ids_are_unique_after_e09_3() -> None:
    risk_register = read_text("docs/generated/risk-register.md")
    risk_ids = re.findall(r"^\| (R-\d{3}) \|", risk_register, flags=re.MULTILINE)
    duplicate_ids = {risk_id for risk_id in risk_ids if risk_ids.count(risk_id) > 1}

    assert duplicate_ids == set()
```

- [ ] **Step 3: Run RED test**

Run:

```bash
/Users/dmitry/Desktop/dawn/backend/.venv/bin/python -m pytest tests/test_e09_db_rabbitmq_provisioning.py -q
```

Expected: fails because the provisioning role and evidence file do not exist yet.

- [ ] **Step 4: Commit RED test and ExecPlan**

Run:

```bash
git add tests/test_e09_db_rabbitmq_provisioning.py docs/execplans/E09-db-rabbitmq-provisioning.md
git commit -m "test: add E09 DB RabbitMQ contract"
```

## Task 2: Add Provisioning Role Skeleton

**Files:**
- Create: `deploy/kolla/ansible/roles/cloud_ui_provisioning/defaults/main.yml`
- Create: `deploy/kolla/ansible/roles/cloud_ui_provisioning/tasks/main.yml`
- Create: `deploy/kolla/ansible/roles/cloud_ui_provisioning/tasks/validate.yml`
- Create: `deploy/kolla/ansible/roles/cloud_ui_provisioning/tasks/vault.yml`
- Create: `deploy/kolla/ansible/roles/cloud_ui_provisioning/tasks/database.yml`
- Create: `deploy/kolla/ansible/roles/cloud_ui_provisioning/tasks/rabbitmq.yml`
- Modify: `deploy/kolla/ansible/README.md`

- [ ] **Step 1: Add defaults**

Create `deploy/kolla/ansible/roles/cloud_ui_provisioning/defaults/main.yml`:

```yaml
---
cloud_ui_provisioning_enabled: false

cloud_ui_vault_addr: "https://192.168.10.15:8200"
cloud_ui_vault_kv_mount: "kv"
cloud_ui_vault_validate_certs: true
cloud_ui_vault_secret_paths:
  mariadb_runtime: "cloud-ui/local/mariadb/runtime"
  mariadb_migration: "cloud-ui/local/mariadb/migration"
  rabbitmq_runtime: "cloud-ui/local/rabbitmq/runtime"

cloud_ui_database_name: "cloud_ui"
cloud_ui_database_runtime_user: "cloud_ui"
cloud_ui_database_migration_user: "cloud_ui_migration"

cloud_ui_rabbitmq_vhost: "/cloud-ui"
cloud_ui_rabbitmq_user: "cloud_ui"
cloud_ui_rabbitmq_exchanges:
  - "cloud-ui.events"
  - "cloud-ui.jobs"
  - "cloud-ui.audit"
  - "cloud-ui.dlx"
cloud_ui_rabbitmq_queues:
  - "cloud-ui.events"
  - "cloud-ui.jobs"
  - "cloud-ui.audit"
  - "cloud-ui.dead"
cloud_ui_rabbitmq_permission_configure: "^cloud-ui\\."
cloud_ui_rabbitmq_permission_write: "^cloud-ui\\."
cloud_ui_rabbitmq_permission_read: "^cloud-ui\\."
```

- [ ] **Step 2: Add main task includes**

Create `deploy/kolla/ansible/roles/cloud_ui_provisioning/tasks/main.yml`:

```yaml
---
- name: Validate Cloud UI provisioning inputs
  ansible.builtin.include_tasks: validate.yml

- name: Resolve Cloud UI Vault secret references
  ansible.builtin.include_tasks: vault.yml
  when: cloud_ui_provisioning_enabled | bool

- name: Provision Cloud UI MariaDB resources
  ansible.builtin.include_tasks: database.yml
  when: cloud_ui_provisioning_enabled | bool

- name: Provision Cloud UI RabbitMQ resources
  ansible.builtin.include_tasks: rabbitmq.yml
  when: cloud_ui_provisioning_enabled | bool
```

- [ ] **Step 3: Add validate task**

Create `deploy/kolla/ansible/roles/cloud_ui_provisioning/tasks/validate.yml`:

```yaml
---
- name: Validate Cloud UI provisioning names
  ansible.builtin.assert:
    that:
      - cloud_ui_database_name == 'cloud_ui'
      - cloud_ui_database_runtime_user == 'cloud_ui'
      - cloud_ui_database_migration_user == 'cloud_ui_migration'
      - cloud_ui_rabbitmq_vhost == '/cloud-ui'
      - cloud_ui_rabbitmq_user == 'cloud_ui'
    fail_msg: "Cloud UI provisioning names must stay scoped to cloud_ui and /cloud-ui."

- name: Validate Cloud UI Vault secret path scope
  ansible.builtin.assert:
    that:
      - cloud_ui_vault_kv_mount == 'kv'
      - cloud_ui_vault_secret_paths.mariadb_runtime == 'cloud-ui/local/mariadb/runtime'
      - cloud_ui_vault_secret_paths.mariadb_migration == 'cloud-ui/local/mariadb/migration'
      - cloud_ui_vault_secret_paths.rabbitmq_runtime == 'cloud-ui/local/rabbitmq/runtime'
    fail_msg: "Cloud UI Vault paths must stay under kv/cloud-ui/local."
```

- [ ] **Step 4: Add Vault task shape**

Create `deploy/kolla/ansible/roles/cloud_ui_provisioning/tasks/vault.yml`:

```yaml
---
- name: Read Cloud UI MariaDB runtime secret from Vault
  community.hashi_vault.vault_kv2_get:
    url: "{{ cloud_ui_vault_addr }}"
    engine_mount_point: "{{ cloud_ui_vault_kv_mount }}"
    path: "{{ cloud_ui_vault_secret_paths.mariadb_runtime }}"
    validate_certs: "{{ cloud_ui_vault_validate_certs }}"
  register: cloud_ui_mariadb_runtime_secret
  no_log: true

- name: Read Cloud UI MariaDB migration secret from Vault
  community.hashi_vault.vault_kv2_get:
    url: "{{ cloud_ui_vault_addr }}"
    engine_mount_point: "{{ cloud_ui_vault_kv_mount }}"
    path: "{{ cloud_ui_vault_secret_paths.mariadb_migration }}"
    validate_certs: "{{ cloud_ui_vault_validate_certs }}"
  register: cloud_ui_mariadb_migration_secret
  no_log: true

- name: Read Cloud UI RabbitMQ runtime secret from Vault
  community.hashi_vault.vault_kv2_get:
    url: "{{ cloud_ui_vault_addr }}"
    engine_mount_point: "{{ cloud_ui_vault_kv_mount }}"
    path: "{{ cloud_ui_vault_secret_paths.rabbitmq_runtime }}"
    validate_certs: "{{ cloud_ui_vault_validate_certs }}"
  register: cloud_ui_rabbitmq_runtime_secret
  no_log: true
```

- [ ] **Step 5: Add MariaDB task shape**

Create `deploy/kolla/ansible/roles/cloud_ui_provisioning/tasks/database.yml`:

```yaml
---
- name: Create Cloud UI database schema
  community.mysql.mysql_db:
    name: "{{ cloud_ui_database_name }}"
    state: present
    login_unix_socket: "{{ cloud_ui_mariadb_admin_socket | default(omit) }}"
    login_user: "{{ cloud_ui_mariadb_admin_user | default(omit) }}"
    login_password: "{{ cloud_ui_mariadb_admin_password | default(omit) }}"
  no_log: true

- name: Create Cloud UI runtime database user
  community.mysql.mysql_user:
    name: "{{ cloud_ui_database_runtime_user }}"
    host: "%"
    password: "{{ cloud_ui_mariadb_runtime_secret.secret.password }}"
    priv: "{{ cloud_ui_database_name }}.*:SELECT,INSERT,UPDATE,DELETE"
    state: present
    login_unix_socket: "{{ cloud_ui_mariadb_admin_socket | default(omit) }}"
    login_user: "{{ cloud_ui_mariadb_admin_user | default(omit) }}"
    login_password: "{{ cloud_ui_mariadb_admin_password | default(omit) }}"
  no_log: true

- name: Create Cloud UI migration database user
  community.mysql.mysql_user:
    name: "{{ cloud_ui_database_migration_user }}"
    host: "%"
    password: "{{ cloud_ui_mariadb_migration_secret.secret.password }}"
    priv: "{{ cloud_ui_database_name }}.*:ALL"
    state: present
    login_unix_socket: "{{ cloud_ui_mariadb_admin_socket | default(omit) }}"
    login_user: "{{ cloud_ui_mariadb_admin_user | default(omit) }}"
    login_password: "{{ cloud_ui_mariadb_admin_password | default(omit) }}"
  no_log: true
```

- [ ] **Step 6: Add RabbitMQ task shape**

Create `deploy/kolla/ansible/roles/cloud_ui_provisioning/tasks/rabbitmq.yml`:

```yaml
---
- name: Create Cloud UI RabbitMQ vhost
  community.rabbitmq.rabbitmq_vhost:
    name: "{{ cloud_ui_rabbitmq_vhost }}"
    state: present
  no_log: true

- name: Create Cloud UI RabbitMQ user
  community.rabbitmq.rabbitmq_user:
    user: "{{ cloud_ui_rabbitmq_user }}"
    password: "{{ cloud_ui_rabbitmq_runtime_secret.secret.password }}"
    vhost: "{{ cloud_ui_rabbitmq_vhost }}"
    configure_priv: "{{ cloud_ui_rabbitmq_permission_configure }}"
    write_priv: "{{ cloud_ui_rabbitmq_permission_write }}"
    read_priv: "{{ cloud_ui_rabbitmq_permission_read }}"
    state: present
  no_log: true

- name: Declare Cloud UI RabbitMQ exchanges
  community.rabbitmq.rabbitmq_exchange:
    name: "{{ item }}"
    vhost: "{{ cloud_ui_rabbitmq_vhost }}"
    type: direct
    durable: true
    state: present
  loop: "{{ cloud_ui_rabbitmq_exchanges }}"
  no_log: true

- name: Declare Cloud UI RabbitMQ queues
  community.rabbitmq.rabbitmq_queue:
    name: "{{ item }}"
    vhost: "{{ cloud_ui_rabbitmq_vhost }}"
    durable: true
    state: present
  loop: "{{ cloud_ui_rabbitmq_queues }}"
  no_log: true
```

- [ ] **Step 7: Update Ansible README**

Append to `deploy/kolla/ansible/README.md`:

```markdown
## E09.3 DB/RabbitMQ Provisioning

`roles/cloud_ui_provisioning` is the repository contract for one-time Cloud UI dependency
provisioning. It stores only object names and Vault secret references. It must not contain DB
passwords, RabbitMQ passwords, Vault tokens, openrc files or `clouds.yaml`.

Live E09.3 evidence is recorded in `docs/generated/e09-db-rabbitmq-provisioning.md`.
```

- [ ] **Step 8: Run role contract tests**

Run:

```bash
/Users/dmitry/Desktop/dawn/backend/.venv/bin/python -m pytest tests/test_e09_db_rabbitmq_provisioning.py tests/test_e09_kolla_ansible_role.py -q
```

Expected after Task 2: E09.3 test still fails only on missing `docs/generated/e09-db-rabbitmq-provisioning.md`; E09.2 role tests pass.

- [ ] **Step 9: Commit provisioning role skeleton**

Run:

```bash
git add deploy/kolla/ansible/README.md deploy/kolla/ansible/roles/cloud_ui_provisioning tests/test_e09_db_rabbitmq_provisioning.py
git commit -m "deploy: add E09 DB RabbitMQ provisioning role"
```

## Task 3: Remote Vault Bootstrap and Sanitized Evidence

**Files:**
- Modify: `docs/execplans/E09-db-rabbitmq-provisioning.md`
- Create or modify: `docs/generated/e09-db-rabbitmq-provisioning.md`

Remote commands must run only from the controller session. Do not delegate these steps to subagents.

- [ ] **Step 1: Remote precheck**

Run:

```bash
ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/tmp/dawn_known_hosts -o BatchMode=yes root@192.168.10.15 '
  set -eu
  hostname
  cat /etc/os-release | sed -n "1,6p"
  timedatectl status | sed -n "1,8p"
  swapon --show || true
  ss -ltn | awk "NR==1 || /:8200|:8201/"
  if command -v vault >/dev/null 2>&1; then echo vault_cli_present; else echo vault_cli_missing; fi
  systemctl is-active vault 2>/dev/null || true
'
```

Expected before bootstrap: host is `ansible.example.local`, no `:8200/:8201` listener, and Vault may be missing/inactive.

- [ ] **Step 2: Install Vault package only from an available package source**

Run:

```bash
ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/tmp/dawn_known_hosts -o BatchMode=yes root@192.168.10.15 '
  set -eu
  if command -v vault >/dev/null 2>&1; then
    vault version
    exit 0
  fi
  if dnf -q list available vault >/dev/null 2>&1; then
    dnf -y install vault
    vault version
    exit 0
  fi
  echo vault_package_unavailable
  exit 20
'
```

Expected: either `vault version` prints a version, or the command exits `20` with `vault_package_unavailable`. If it exits `20`, stop implementation and record the blocker in the ExecPlan.

- [ ] **Step 3: Create lab TLS and Vault config**

Run only if Vault is installed:

```bash
ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/tmp/dawn_known_hosts -o BatchMode=yes root@192.168.10.15 '
  set -eu
  getent group vault >/dev/null || groupadd --system vault
  id vault >/dev/null 2>&1 || useradd --system --home /etc/vault.d --shell /sbin/nologin --gid vault vault
  install -d -o vault -g vault -m 0700 /opt/vault/data
  install -d -o root -g vault -m 0750 /etc/vault.d/tls
  install -d -o vault -g vault -m 0750 /var/log/vault
  if [ ! -f /etc/vault.d/tls/vault.key ]; then
    openssl req -x509 -newkey rsa:3072 -sha256 -days 365 -nodes \
      -keyout /etc/vault.d/tls/vault.key \
      -out /etc/vault.d/tls/vault.crt \
      -subj "/CN=192.168.10.15" \
      -addext "subjectAltName=IP:192.168.10.15,DNS:vault.lab.local" >/dev/null 2>&1
    cp /etc/vault.d/tls/vault.crt /etc/vault.d/tls/ca.crt
  fi
  chown root:vault /etc/vault.d/tls/vault.crt /etc/vault.d/tls/ca.crt
  chown root:vault /etc/vault.d/tls/vault.key
  chmod 0644 /etc/vault.d/tls/vault.crt /etc/vault.d/tls/ca.crt
  chmod 0600 /etc/vault.d/tls/vault.key
  cat > /etc/vault.d/vault.hcl <<'"'"'EOF'"'"'
ui = false
api_addr = "https://192.168.10.15:8200"
cluster_addr = "https://192.168.10.15:8201"
disable_mlock = true

storage "raft" {
  path = "/opt/vault/data"
  node_id = "dawn-e09-lab"
}

listener "tcp" {
  address = "192.168.10.15:8200"
  cluster_address = "192.168.10.15:8201"
  tls_cert_file = "/etc/vault.d/tls/vault.crt"
  tls_key_file = "/etc/vault.d/tls/vault.key"
  tls_min_version = "tls12"
}
EOF
  chown root:vault /etc/vault.d/vault.hcl
  chmod 0640 /etc/vault.d/vault.hcl
  systemctl enable --now vault
  systemctl is-active vault
'
```

Expected: `active`.

- [ ] **Step 4: Initialize, unseal and configure Vault without printing secrets**

Run only if `/root/dawn-e09-vault-init.json` is absent or Vault reports uninitialized:

```bash
ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/tmp/dawn_known_hosts -o BatchMode=yes root@192.168.10.15 '
  set -eu
  export VAULT_ADDR=https://192.168.10.15:8200
  export VAULT_CACERT=/etc/vault.d/tls/ca.crt
  status_json="$(vault status -format=json 2>/dev/null || true)"
  initialized="$(printf "%s" "$status_json" | python3 -c "import json,sys; data=sys.stdin.read(); print(json.loads(data).get(\"initialized\", False) if data else False)")"
  if [ "$initialized" = "False" ]; then
    umask 077
    vault operator init -key-shares=1 -key-threshold=1 -format=json > /root/dawn-e09-vault-init.json
  fi
  if vault status -format=json | python3 -c "import json,sys; raise SystemExit(0 if json.load(sys.stdin).get(\"sealed\") else 1)"; then
    vault operator unseal "$(python3 -c "import json; print(json.load(open(\"/root/dawn-e09-vault-init.json\"))[\"unseal_keys_b64\"][0])")" >/dev/null
  fi
  export VAULT_TOKEN="$(python3 -c "import json; print(json.load(open(\"/root/dawn-e09-vault-init.json\"))[\"root_token\"])")"
  vault secrets enable -path=kv kv-v2 >/dev/null 2>&1 || true
  vault audit enable file file_path=/var/log/vault/audit.log >/dev/null 2>&1 || true
  cat > /root/dawn-e09-cloud-ui-policy.hcl <<'"'"'EOF'"'"'
path "kv/data/cloud-ui/local/*" {
  capabilities = ["create", "read", "update", "list"]
}

path "kv/metadata/cloud-ui/local/*" {
  capabilities = ["read", "list"]
}
EOF
  vault policy write cloud-ui-lab /root/dawn-e09-cloud-ui-policy.hcl >/dev/null
  vault token create -policy=cloud-ui-lab -period=24h -format=json > /root/dawn-e09-cloud-ui-token.json
  chmod 0600 /root/dawn-e09-vault-init.json /root/dawn-e09-cloud-ui-token.json
  vault status | sed -n "1,8p"
  vault secrets list | awk "NR==1 || /^kv\\//"
  vault audit list | awk "NR==1 || /^file\\//"
'
```

Expected output shows initialized/unsealed status, `kv/`, and `file/`. It must not print root token, unseal key, client token or secret values.

- [ ] **Step 5: Record sanitized Vault evidence**

Update `docs/generated/e09-db-rabbitmq-provisioning.md` with:

```markdown
# E09.3 Database/RabbitMQ Provisioning Evidence

- Stage: E09.3 Database/RabbitMQ provisioning
- Date: 2026-06-24
- Test Ansible host: 192.168.10.15
- Kolla inventory: /etc/kolla/all-in-one
- Secret mechanism: Vault/SecMan lab path
- Production action: none

## Vault Status

| Check | Sanitized result |
|---|---|
| Vault service | active after lab bootstrap |
| API listener | 192.168.10.15:8200 |
| Cluster listener | 192.168.10.15:8201 |
| KV mount | kv/ |
| Audit device | file audit enabled |
| Secret material captured in repository | no |
```

The evidence file must contain no token values, unseal values, private key content, `clouds.yaml`, openrc content or DB dumps.

- [ ] **Step 6: Run test and commit Vault evidence**

Run:

```bash
/Users/dmitry/Desktop/dawn/backend/.venv/bin/python -m pytest tests/test_e09_db_rabbitmq_provisioning.py -q
```

Expected at this point: evidence-related assertions pass if the role exists; DB/RabbitMQ live evidence rows may still be pending.

Commit:

```bash
git add docs/generated/e09-db-rabbitmq-provisioning.md docs/execplans/E09-db-rabbitmq-provisioning.md
git commit -m "docs: record E09 Vault lab evidence"
```

## Task 4: Remote DB/RabbitMQ Provisioning and Least-Privilege Evidence

**Files:**
- Modify: `docs/generated/e09-db-rabbitmq-provisioning.md`
- Modify: `docs/execplans/E09-db-rabbitmq-provisioning.md`

Remote commands must run only from the controller session. Do not delegate these steps to subagents.

- [ ] **Step 1: Generate Cloud UI secrets into Vault only**

Run:

```bash
ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/tmp/dawn_known_hosts -o BatchMode=yes root@192.168.10.15 '
  set -eu
  export VAULT_ADDR=https://192.168.10.15:8200
  export VAULT_CACERT=/etc/vault.d/tls/ca.crt
  export VAULT_TOKEN="$(python3 -c "import json; print(json.load(open(\"/root/dawn-e09-vault-init.json\"))[\"root_token\"])")"
  runtime_pw="$(openssl rand -hex 32)"
  migration_pw="$(openssl rand -hex 32)"
  rabbit_pw="$(openssl rand -hex 32)"
  vault kv put kv/cloud-ui/local/mariadb/runtime username=cloud_ui database=cloud_ui password="$runtime_pw" >/dev/null
  vault kv put kv/cloud-ui/local/mariadb/migration username=cloud_ui_migration database=cloud_ui password="$migration_pw" >/dev/null
  vault kv put kv/cloud-ui/local/rabbitmq/runtime username=cloud_ui vhost=/cloud-ui password="$rabbit_pw" >/dev/null
  echo cloud_ui_vault_secrets_written
'
```

Expected: `cloud_ui_vault_secrets_written` only.

- [ ] **Step 2: Provision MariaDB through Kolla container path**

Run a discovery command first:

```bash
ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/tmp/dawn_known_hosts -o BatchMode=yes root@192.168.10.15 '
  set -eu
  ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/tmp/dawn_known_hosts -o BatchMode=yes root@192.168.10.14 "docker ps --format \"{{.Names}}\" | egrep \"^(mariadb|rabbitmq)$\""
'
```

Expected: both `mariadb` and `rabbitmq` container names.

Then provision:

```bash
ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/tmp/dawn_known_hosts -o BatchMode=yes root@192.168.10.15 '
  set -eu
  export VAULT_ADDR=https://192.168.10.15:8200
  export VAULT_CACERT=/etc/vault.d/tls/ca.crt
  export VAULT_TOKEN="$(python3 -c "import json; print(json.load(open(\"/root/dawn-e09-vault-init.json\"))[\"root_token\"])")"
  runtime_pw="$(vault kv get -field=password kv/cloud-ui/local/mariadb/runtime)"
  migration_pw="$(vault kv get -field=password kv/cloud-ui/local/mariadb/migration)"
  db_admin_pw="$(python3 - <<'"'"'PY'"'"'
from pathlib import Path
for line in Path("/etc/kolla/passwords.yml").read_text().splitlines():
    if line.startswith("database_password:"):
        print(line.split(":", 1)[1].strip().strip("\"'"))
        break
PY
)"
  sql_file=/root/dawn-e09-cloud-ui-db.sql
  cat > "$sql_file" <<SQL
CREATE DATABASE IF NOT EXISTS cloud_ui CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER IF NOT EXISTS '"'"'cloud_ui'"'"'@'"'"'%'"'"' IDENTIFIED BY '"'"'$runtime_pw'"'"';
CREATE USER IF NOT EXISTS '"'"'cloud_ui_migration'"'"'@'"'"'%'"'"' IDENTIFIED BY '"'"'$migration_pw'"'"';
GRANT SELECT, INSERT, UPDATE, DELETE ON cloud_ui.* TO '"'"'cloud_ui'"'"'@'"'"'%'"'"';
GRANT ALL PRIVILEGES ON cloud_ui.* TO '"'"'cloud_ui_migration'"'"'@'"'"'%'"'"';
FLUSH PRIVILEGES;
SQL
  scp -o StrictHostKeyChecking=no -o UserKnownHostsFile=/tmp/dawn_known_hosts "$sql_file" root@192.168.10.14:/root/dawn-e09-cloud-ui-db.sql >/dev/null
  ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/tmp/dawn_known_hosts root@192.168.10.14 "docker exec -i mariadb mysql -uroot -p\"$db_admin_pw\" < /root/dawn-e09-cloud-ui-db.sql"
  rm -f "$sql_file"
  ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/tmp/dawn_known_hosts root@192.168.10.14 "rm -f /root/dawn-e09-cloud-ui-db.sql"
  echo cloud_ui_database_provisioned
'
```

Expected: `cloud_ui_database_provisioned`. If the SQL command prints a password or fails with shell tracing, stop and record a security finding.

- [ ] **Step 3: Verify MariaDB least privilege without dumping data**

Run:

```bash
ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/tmp/dawn_known_hosts -o BatchMode=yes root@192.168.10.15 '
  set -eu
  export VAULT_ADDR=https://192.168.10.15:8200
  export VAULT_CACERT=/etc/vault.d/tls/ca.crt
  export VAULT_TOKEN="$(python3 -c "import json; print(json.load(open(\"/root/dawn-e09-vault-init.json\"))[\"root_token\"])")"
  runtime_pw="$(vault kv get -field=password kv/cloud-ui/local/mariadb/runtime)"
  ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/tmp/dawn_known_hosts root@192.168.10.14 "docker exec mariadb mysql -ucloud_ui -p\"$runtime_pw\" -e \"SELECT 1\" cloud_ui >/dev/null && echo runtime_cloud_ui_schema_ok"
  if ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/tmp/dawn_known_hosts root@192.168.10.14 "docker exec mariadb mysql -ucloud_ui -p\"$runtime_pw\" -e \"SELECT 1\" mysql >/dev/null 2>&1"; then
    echo runtime_mysql_schema_unexpected_success
    exit 21
  else
    echo runtime_mysql_schema_denied
  fi
'
```

Expected:

```text
runtime_cloud_ui_schema_ok
runtime_mysql_schema_denied
```

- [ ] **Step 4: Provision RabbitMQ vhost/user and resource permissions**

Run:

```bash
ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/tmp/dawn_known_hosts -o BatchMode=yes root@192.168.10.15 '
  set -eu
  export VAULT_ADDR=https://192.168.10.15:8200
  export VAULT_CACERT=/etc/vault.d/tls/ca.crt
  export VAULT_TOKEN="$(python3 -c "import json; print(json.load(open(\"/root/dawn-e09-vault-init.json\"))[\"root_token\"])")"
  rabbit_pw="$(vault kv get -field=password kv/cloud-ui/local/rabbitmq/runtime)"
  ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/tmp/dawn_known_hosts root@192.168.10.14 "docker exec rabbitmq rabbitmqctl add_vhost /cloud-ui >/dev/null 2>&1 || true"
  ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/tmp/dawn_known_hosts root@192.168.10.14 "docker exec rabbitmq rabbitmqctl add_user cloud_ui \"$rabbit_pw\" >/dev/null 2>&1 || docker exec rabbitmq rabbitmqctl change_password cloud_ui \"$rabbit_pw\" >/dev/null"
  ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/tmp/dawn_known_hosts root@192.168.10.14 "docker exec rabbitmq rabbitmqctl set_permissions -p /cloud-ui cloud_ui \"^cloud-ui\\\\.\" \"^cloud-ui\\\\.\" \"^cloud-ui\\\\.\" >/dev/null"
  echo cloud_ui_rabbitmq_principal_provisioned
'
```

Expected: `cloud_ui_rabbitmq_principal_provisioned`.

- [ ] **Step 5: Declare queues/exchanges if safe tooling exists**

Run discovery:

```bash
ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/tmp/dawn_known_hosts -o BatchMode=yes root@192.168.10.15 '
  set -eu
  ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/tmp/dawn_known_hosts root@192.168.10.14 "docker exec rabbitmq sh -lc \"command -v rabbitmqadmin || python3 -c '\"'\"'import pika'\"'\"' 2>/dev/null && echo pika_present || true\""
'
```

If neither `rabbitmqadmin` nor `pika_present` is available, record queue/exchange declaration as a blocker and do not fake evidence. If one is available, declare only Cloud UI-owned exchanges and queues and record sanitized names.

- [ ] **Step 6: Verify RabbitMQ permissions**

Run:

```bash
ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/tmp/dawn_known_hosts -o BatchMode=yes root@192.168.10.15 '
  set -eu
  ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/tmp/dawn_known_hosts root@192.168.10.14 "docker exec rabbitmq rabbitmqctl list_vhosts --silent | grep -Fx /cloud-ui"
  ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/tmp/dawn_known_hosts root@192.168.10.14 "docker exec rabbitmq rabbitmqctl list_permissions -p /cloud-ui --silent | awk '\''$1 == \"cloud_ui\" {print \"cloud_ui_permissions_present\"}'\''"
  if ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/tmp/dawn_known_hosts root@192.168.10.14 "docker exec rabbitmq rabbitmqctl list_permissions -p / --silent | awk '\''$1 == \"cloud_ui\" {found=1} END {exit found ? 0 : 1}'\''"; then
    echo cloud_ui_root_vhost_unexpected_permission
    exit 22
  else
    echo cloud_ui_root_vhost_denied
  fi
'
```

Expected:

```text
/cloud-ui
cloud_ui_permissions_present
cloud_ui_root_vhost_denied
```

- [ ] **Step 7: Update evidence and commit live results**

Add sanitized DB/MQ sections to `docs/generated/e09-db-rabbitmq-provisioning.md`:

```markdown
## MariaDB Live Evidence

| Check | Sanitized result |
|---|---|
| Schema | `cloud_ui` present |
| Runtime user | `cloud_ui` present |
| Migration user | `cloud_ui_migration` present |
| Runtime schema access | allowed for `cloud_ui` |
| Runtime non-portal schema access | denied |

## RabbitMQ Live Evidence

| Check | Sanitized result |
|---|---|
| Vhost | `/cloud-ui` present |
| User | `cloud_ui` present |
| Root vhost access | denied |
| Queue/exchange declaration | recorded as completed or explicit blocker |
```

Commit:

```bash
git add docs/generated/e09-db-rabbitmq-provisioning.md docs/execplans/E09-db-rabbitmq-provisioning.md
git commit -m "docs: record E09 DB RabbitMQ live evidence"
```

## Task 5: Traceability, Risk Register and Final Verification

**Files:**
- Modify: `docs/11_DKB_TRACEABILITY.md`
- Modify: `docs/generated/risk-register.md`
- Modify: `docs/execplans/E09-db-rabbitmq-provisioning.md`

- [ ] **Step 1: Add risk row**

Add a unique row after `R-062`, using the next unused ID:

```markdown
| R-063 | E09.3 all-in-one DB/RabbitMQ evidence mistaken for HA production proof | E09.3 provisions Cloud UI-owned MariaDB/RabbitMQ resources only on the approved all-in-one test stand and records sanitized least-privilege checks. | Keep MariaDB HA, RabbitMQ quorum/HA, production SecMan, rotation, backup, network ACL and three-node rollout evidence as pending external gates. | E09 |
```

- [ ] **Step 2: Add DKB traceability update**

Append before `## Полная матрица` in `docs/11_DKB_TRACEABILITY.md`:

```markdown
## Обновление требований 2026-06-24: E09.3 DB/RabbitMQ provisioning

E09.3 adds live all-in-one lab evidence for Cloud UI-owned MariaDB/RabbitMQ provisioning with Vault
lab secret storage. This is not production SecMan or HA evidence.

- ДКБ-55/56: Cloud UI DB/RabbitMQ secret material is generated on the test host and stored in Vault
  lab paths, with no secret values committed to Git. Production SecMan endpoint/auth, HA, backup,
  auto-unseal, rotation and owner approval remain external.
- ДКБ-42-44/76/77/80: DB/MQ object boundaries and least-privilege checks are recorded for the lab.
  Network VLAN/ACL, unused-interface blocking and production management-zone proof remain external.
- ДКБ-82: repository rollback and live cleanup steps are documented, but full Kolla rollback/reconfigure
  evidence remains later E09 work.

Evidence: `tests/test_e09_db_rabbitmq_provisioning.py`,
`deploy/kolla/ansible/roles/cloud_ui_provisioning/*`,
`docs/generated/e09-db-rabbitmq-provisioning.md`, `docs/generated/risk-register.md` and ExecPlan
`docs/execplans/E09-db-rabbitmq-provisioning.md`.
```

- [ ] **Step 3: Run final verification**

Run from `/Users/dmitry/Desktop/dawn/.worktrees/e09-db-rabbitmq-provisioning`:

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

Expected:

- E09 targeted tests pass.
- Ruff/lint/typecheck/full tests/security pass.
- `git diff --check` passes.
- Grep output contains only forbidden-word policy text or negative assertions, not secret material.

- [ ] **Step 4: Request final review and commit**

Request code review for the full `main..HEAD` diff. Fix Critical and Important findings. Then commit:

```bash
git add docs/11_DKB_TRACEABILITY.md docs/generated/risk-register.md docs/execplans/E09-db-rabbitmq-provisioning.md
git commit -m "docs: trace E09 DB RabbitMQ provisioning"
```

