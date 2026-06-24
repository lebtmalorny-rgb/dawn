# E09.2 Ansible Role Skeleton Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a repository-only Kolla-Ansible role skeleton for Cloud UI that declares the frontend/API/worker/events container layout without running a live deployment.

**Architecture:** Keep the role under `deploy/kolla/ansible/roles/cloud_ui` next to the existing E09.1 Kolla Build artifacts. The role exposes defaults, validation tasks, config templates, handlers and container definition facts, while generated evidence explicitly keeps registry, DB/MQ, migration, HAProxy/TLS and live deployment proofs pending.

**Tech Stack:** Python `pytest`, PyYAML via the backend test environment, Kolla-Ansible-style role layout, Ansible YAML/Jinja templates, Markdown evidence.

---

## File Structure

- Create `tests/test_e09_kolla_ansible_role.py`: static contract tests for role structure, container definitions, scope boundaries and generated evidence.
- Create `deploy/kolla/ansible/README.md`: operator-facing repository contract and non-goals for E09.2.
- Create `deploy/kolla/ansible/roles/cloud_ui/defaults/main.yml`: service enable flags, image references, process commands, groups, ports, volumes and hardening dimensions.
- Create `deploy/kolla/ansible/roles/cloud_ui/tasks/main.yml`: imports validation, config and container definition tasks.
- Create `deploy/kolla/ansible/roles/cloud_ui/tasks/validate.yml`: fail-closed assertions for `latest`, missing image reference, missing config roots and invalid service definition shape.
- Create `deploy/kolla/ansible/roles/cloud_ui/tasks/config.yml`: config directory and non-secret template rendering skeleton.
- Create `deploy/kolla/ansible/roles/cloud_ui/tasks/containers.yml`: declares `cloud_ui_container_definitions` from `cloud_ui_services` for later Kolla deployment tasks.
- Create `deploy/kolla/ansible/roles/cloud_ui/handlers/main.yml`: restart handler names only; live restart remains later deployment scope.
- Create `deploy/kolla/ansible/roles/cloud_ui/templates/cloud-ui-backend.env.j2`: non-secret backend environment template.
- Create `deploy/kolla/ansible/roles/cloud_ui/templates/cloud-ui-frontend.conf.j2`: frontend nginx runtime template.
- Create `docs/generated/e09-kolla-ansible-role.md`: E09.2 evidence.
- Modify `deploy/kolla/README.md`: link E09.2 role skeleton.
- Modify `docs/generated/risk-register.md`: add E09.2 risk for skeleton-vs-live-deploy confusion.
- Modify `docs/11_DKB_TRACEABILITY.md`: add E09.2 traceability update.
- Create and maintain `docs/execplans/E09-kolla-ansible-role.md`: active ExecPlan and verification record.

## Task 1: Add RED Contract Test

**Files:**
- Create: `tests/test_e09_kolla_ansible_role.py`
- Create: `docs/execplans/E09-kolla-ansible-role.md`

- [ ] **Step 1: Create the initial ExecPlan**

Write `docs/execplans/E09-kolla-ansible-role.md` with the required sections from `PLANS.md`. The initial progress must record:

```markdown
- [x] 2026-06-24: AGENTS.md, tasks/E09_KOLLA_DEPLOY.md, docs/12_DEPLOY_ROCKY_KOLLA.md,
  docs/09_PERFORMANCE_HA.md, docs/10_SECURITY_DKB.md and docs/generated/e08-security-review.md read.
- [x] 2026-06-24: E09.2 design approved in
  docs/superpowers/specs/2026-06-24-e09-ansible-role-skeleton-design.md.
- [ ] Contract and RED tests.
- [ ] Minimal role skeleton.
- [ ] Evidence, DKB traceability and risk register.
- [ ] Final verification and review.
```

- [ ] **Step 2: Write the failing test**

Create `tests/test_e09_kolla_ansible_role.py`:

```python
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
ROLE_ROOT = ROOT / "deploy/kolla/ansible/roles/cloud_ui"

EXPECTED_ROLE_FILES = [
    "deploy/kolla/ansible/README.md",
    "deploy/kolla/ansible/roles/cloud_ui/defaults/main.yml",
    "deploy/kolla/ansible/roles/cloud_ui/handlers/main.yml",
    "deploy/kolla/ansible/roles/cloud_ui/tasks/main.yml",
    "deploy/kolla/ansible/roles/cloud_ui/tasks/validate.yml",
    "deploy/kolla/ansible/roles/cloud_ui/tasks/config.yml",
    "deploy/kolla/ansible/roles/cloud_ui/tasks/containers.yml",
    "deploy/kolla/ansible/roles/cloud_ui/templates/cloud-ui-backend.env.j2",
    "deploy/kolla/ansible/roles/cloud_ui/templates/cloud-ui-frontend.conf.j2",
    "docs/generated/e09-kolla-ansible-role.md",
]

EXPECTED_SERVICES = {
    "cloud_ui_frontend",
    "cloud_ui_api",
    "cloud_ui_worker",
    "cloud_ui_events",
}


def read_text(relative_path: str) -> str:
    return (ROOT / relative_path).read_text(encoding="utf-8")


def load_yaml(relative_path: str) -> dict:
    return yaml.safe_load(read_text(relative_path))


def load_yaml_list(relative_path: str) -> list[dict]:
    loaded = yaml.safe_load(read_text(relative_path))
    if not isinstance(loaded, list):
        return []
    return loaded


def role_texts() -> dict[str, str]:
    if not ROLE_ROOT.exists():
        return {}

    return {
        str(path.relative_to(ROLE_ROOT)): path.read_text(encoding="utf-8")
        for path in ROLE_ROOT.rglob("*")
        if path.is_file()
    }


def test_e09_ansible_role_files_exist() -> None:
    for relative_path in EXPECTED_ROLE_FILES:
        assert (ROOT / relative_path).exists(), relative_path


def test_defaults_declare_four_permanent_services_and_two_images() -> None:
    defaults = load_yaml("deploy/kolla/ansible/roles/cloud_ui/defaults/main.yml")
    services = defaults["cloud_ui_services"]

    assert set(services) == EXPECTED_SERVICES
    assert defaults["cloud_ui_backend_image"] == "cloud-ui-backend"
    assert defaults["cloud_ui_frontend_image"] == "cloud-ui-frontend"
    assert defaults["cloud_ui_backend_image_tag"] != "latest"
    assert defaults["cloud_ui_frontend_image_tag"] != "latest"
    assert defaults["cloud_ui_permanent_container_count_per_node"] == 4

    assert services["cloud_ui_frontend"]["image"] == "{{ cloud_ui_frontend_image_full }}"
    for service_name in ["cloud_ui_api", "cloud_ui_worker", "cloud_ui_events"]:
        assert services[service_name]["image"] == "{{ cloud_ui_backend_image_full }}"

    assert services["cloud_ui_api"]["command"] == "cloud-ui api"
    assert services["cloud_ui_worker"]["command"] == "cloud-ui worker"
    assert services["cloud_ui_events"]["command"] == "cloud-ui events"
    assert "cloud-ui db-upgrade" not in {
        service["command"] for service in services.values()
    }


def test_tasks_are_skeleton_only_and_import_expected_steps() -> None:
    main_tasks = load_yaml_list("deploy/kolla/ansible/roles/cloud_ui/tasks/main.yml")
    containers_tasks = load_yaml_list(
        "deploy/kolla/ansible/roles/cloud_ui/tasks/containers.yml"
    )
    containers_tasks_text = read_text(
        "deploy/kolla/ansible/roles/cloud_ui/tasks/containers.yml"
    )
    validate_tasks = load_yaml_list(
        "deploy/kolla/ansible/roles/cloud_ui/tasks/validate.yml"
    )
    assert isinstance(main_tasks, list)
    actual_imports: list[str] = []
    for task in main_tasks:
        assert isinstance(task, dict)
        assert (
            "include_tasks" in task or "ansible.builtin.include_tasks" in task
        ), "Only include_tasks entries are allowed in main.yml"
        if "include_tasks" in task:
            actual_imports.append(str(task["include_tasks"]).strip())
        elif "ansible.builtin.include_tasks" in task:
            actual_imports.append(str(task["ansible.builtin.include_tasks"]).strip())

    assert len(main_tasks) == len(actual_imports)
    assert actual_imports == ["validate.yml", "config.yml", "containers.yml"]

    assert isinstance(containers_tasks, list)
    set_fact_value = None
    for task in containers_tasks:
        assert isinstance(task, dict)
        fact_task = task.get("ansible.builtin.set_fact") or task.get("set_fact")
        if isinstance(fact_task, dict) and "cloud_ui_container_definitions" in fact_task:
            set_fact_value = fact_task["cloud_ui_container_definitions"]
            break

    assert set_fact_value is not None
    assert set_fact_value == "{{ cloud_ui_services }}"

    assert isinstance(validate_tasks, list)
    validate_thats = []
    for task in validate_tasks:
        assert isinstance(task, dict)
        assert_block = task.get("ansible.builtin.assert") or task.get("assert")
        assert isinstance(assert_block, dict)
        that = assert_block.get("that")
        assert isinstance(that, list)
        validate_thats.extend([str(item) for item in that])

    for expected in [
        "cloud_ui_backend_image_tag != 'latest'",
        "cloud_ui_frontend_image_tag != 'latest'",
    ]:
        assert expected in validate_thats

    assert "kolla_container:" not in containers_tasks_text


def test_role_templates_contain_only_non_secret_config() -> None:
    backend_template = read_text(
        "deploy/kolla/ansible/roles/cloud_ui/templates/cloud-ui-backend.env.j2"
    )
    frontend_template = read_text(
        "deploy/kolla/ansible/roles/cloud_ui/templates/cloud-ui-frontend.conf.j2"
    )

    for expected in [
        "CLOUD_UI_CONFIG_VERSION",
        "CLOUD_UI_PUBLIC_BASE_URL",
        "CLOUD_UI_LOG_LEVEL",
        "CLOUD_UI_BACKEND_ROLE",
    ]:
        assert expected in backend_template

    assert "listen {{ cloud_ui_frontend_listen_port }};" in frontend_template

    combined_templates = f"{backend_template}\n{frontend_template}".lower()
    for forbidden in ["password", "token", "private_key", "secret_key"]:
        assert forbidden not in combined_templates


def test_role_scope_excludes_later_e09_work() -> None:
    assert ROLE_ROOT.exists(), ROLE_ROOT
    combined_role = "\n".join(role_texts().values()).lower()

    for forbidden in [
        "mariadb",
        "rabbitmq",
        "db-upgrade",
        "haproxy",
        "tls_private",
        "production",
        "inventory.ini",
        "kolla_container:",
    ]:
        assert forbidden not in combined_role

    assert "pending_external_evidence" in read_text(
        "docs/generated/e09-kolla-ansible-role.md"
    )


def test_e09_role_evidence_records_limits_and_dkb_scope() -> None:
    evidence = read_text("docs/generated/e09-kolla-ansible-role.md")

    for expected in [
        "Stage: E09.2 Ansible role skeleton",
        "cloud_ui_frontend",
        "cloud_ui_api",
        "cloud_ui_worker",
        "cloud_ui_events",
        "repository-side role skeleton",
        "pending_external_evidence",
        "ДКБ-69",
        "ДКБ-70",
        "ДКБ-76/77/80",
    ]:
        assert expected in evidence

    assert "12 live containers proven" not in evidence
    assert "production approved" not in evidence.lower()
```

- [ ] **Step 3: Run the RED test**

Run:

```bash
backend/.venv/bin/python -m pytest tests/test_e09_kolla_ansible_role.py -q
```

Expected: fail because `deploy/kolla/ansible/README.md`, role files and evidence do not exist.

- [ ] **Step 4: Commit the RED test and initial ExecPlan**

Run:

```bash
git add tests/test_e09_kolla_ansible_role.py docs/execplans/E09-kolla-ansible-role.md
git commit -m "test: add E09 Ansible role contract"
```

## Task 2: Add Minimal Role Skeleton

**Files:**
- Create: `deploy/kolla/ansible/README.md`
- Create: `deploy/kolla/ansible/roles/cloud_ui/defaults/main.yml`
- Create: `deploy/kolla/ansible/roles/cloud_ui/handlers/main.yml`
- Create: `deploy/kolla/ansible/roles/cloud_ui/tasks/main.yml`
- Create: `deploy/kolla/ansible/roles/cloud_ui/tasks/validate.yml`
- Create: `deploy/kolla/ansible/roles/cloud_ui/tasks/config.yml`
- Create: `deploy/kolla/ansible/roles/cloud_ui/tasks/containers.yml`
- Create: `deploy/kolla/ansible/roles/cloud_ui/templates/cloud-ui-backend.env.j2`
- Create: `deploy/kolla/ansible/roles/cloud_ui/templates/cloud-ui-frontend.conf.j2`
- Modify: `docs/execplans/E09-kolla-ansible-role.md`

- [ ] **Step 1: Add Ansible README**

Create `deploy/kolla/ansible/README.md`:

```markdown
# Cloud UI Kolla-Ansible Role

This directory contains the E09.2 repository-side Kolla-Ansible role skeleton for Cloud UI.

The role declares four permanent services per control/UI node:

- `cloud_ui_frontend`
- `cloud_ui_api`
- `cloud_ui_worker`
- `cloud_ui_events`

The role preserves the E09.1 two-image contract:

- `cloud-ui-frontend` for `cloud_ui_frontend`
- `cloud-ui-backend` for `cloud_ui_api`, `cloud_ui_worker` and `cloud_ui_events`

## Scope

E09.2 does not run a deployment. It provides defaults, validation, config templates, handler names and
container definition data for later Kolla-Ansible integration.

Database provisioning, message broker provisioning, one-shot migration, HAProxy/TLS, live container
inspection, SELinux proof, registry digest evidence, rollback and three-node smoke remain later E09
slices.
```

- [ ] **Step 2: Add defaults**

Create `deploy/kolla/ansible/roles/cloud_ui/defaults/main.yml`:

```yaml
---
cloud_ui_enabled: false

cloud_ui_config_version: "e09.2-role-skeleton"
cloud_ui_public_base_url: "/"
cloud_ui_log_level: "INFO"

cloud_ui_permanent_container_count_per_node: 4

cloud_ui_frontend_group: "cloud-ui-frontend"
cloud_ui_api_group: "cloud-ui-api"
cloud_ui_worker_group: "cloud-ui-worker"
cloud_ui_events_group: "cloud-ui-events"

cloud_ui_registry: "{{ kolla_internal_fqdn | default('registry.test.example.invalid/cloud-ui') }}"
cloud_ui_backend_image: "cloud-ui-backend"
cloud_ui_frontend_image: "cloud-ui-frontend"
cloud_ui_backend_image_tag: "{{ openstack_tag | default('2025.1-rocky-9') }}"
cloud_ui_frontend_image_tag: "{{ openstack_tag | default('2025.1-rocky-9') }}"
cloud_ui_backend_image_digest: ""
cloud_ui_frontend_image_digest: ""
cloud_ui_backend_image_full: "{{ cloud_ui_registry }}/{{ cloud_ui_backend_image }}{% if cloud_ui_backend_image_digest | length > 0 %}@{{ cloud_ui_backend_image_digest }}{% else %}:{{ cloud_ui_backend_image_tag }}{% endif %}"
cloud_ui_frontend_image_full: "{{ cloud_ui_registry }}/{{ cloud_ui_frontend_image }}{% if cloud_ui_frontend_image_digest | length > 0 %}@{{ cloud_ui_frontend_image_digest }}{% else %}:{{ cloud_ui_frontend_image_tag }}{% endif %}"

cloud_ui_config_root: "{{ node_config_directory | default('/etc/kolla') }}"
cloud_ui_container_config_directory: "{{ container_config_directory | default('/var/lib/kolla/config_files') }}"
cloud_ui_log_volume: "kolla_logs"

cloud_ui_backend_listen_port: 8080
cloud_ui_frontend_listen_port: 8080

cloud_ui_backend_dimensions:
  cap_drop:
    - ALL
  read_only: true
  pids_limit: 512
  ulimits:
    nofile:
      soft: 65536
      hard: 65536

cloud_ui_frontend_dimensions:
  cap_drop:
    - ALL
  read_only: true
  pids_limit: 256
  ulimits:
    nofile:
      soft: 65536
      hard: 65536

cloud_ui_services:
  cloud_ui_frontend:
    container_name: "cloud_ui_frontend"
    group: "{{ cloud_ui_frontend_group }}"
    enabled: "{{ cloud_ui_enabled }}"
    image: "{{ cloud_ui_frontend_image_full }}"
    command: "nginx -g 'daemon off;'"
    listen_port: "{{ cloud_ui_frontend_listen_port }}"
    config_dir: "cloud-ui-frontend"
    dimensions: "{{ cloud_ui_frontend_dimensions }}"
    volumes:
      - "{{ cloud_ui_config_root }}/cloud-ui-frontend/:{{ cloud_ui_container_config_directory }}/:ro"
      - "{{ cloud_ui_log_volume }}:/var/log/kolla/"
  cloud_ui_api:
    container_name: "cloud_ui_api"
    group: "{{ cloud_ui_api_group }}"
    enabled: "{{ cloud_ui_enabled }}"
    image: "{{ cloud_ui_backend_image_full }}"
    command: "cloud-ui api"
    listen_port: "{{ cloud_ui_backend_listen_port }}"
    config_dir: "cloud-ui-backend"
    dimensions: "{{ cloud_ui_backend_dimensions }}"
    volumes:
      - "{{ cloud_ui_config_root }}/cloud-ui-backend/:{{ cloud_ui_container_config_directory }}/:ro"
      - "{{ cloud_ui_log_volume }}:/var/log/kolla/"
  cloud_ui_worker:
    container_name: "cloud_ui_worker"
    group: "{{ cloud_ui_worker_group }}"
    enabled: "{{ cloud_ui_enabled }}"
    image: "{{ cloud_ui_backend_image_full }}"
    command: "cloud-ui worker"
    config_dir: "cloud-ui-backend"
    dimensions: "{{ cloud_ui_backend_dimensions }}"
    volumes:
      - "{{ cloud_ui_config_root }}/cloud-ui-backend/:{{ cloud_ui_container_config_directory }}/:ro"
      - "{{ cloud_ui_log_volume }}:/var/log/kolla/"
  cloud_ui_events:
    container_name: "cloud_ui_events"
    group: "{{ cloud_ui_events_group }}"
    enabled: "{{ cloud_ui_enabled }}"
    image: "{{ cloud_ui_backend_image_full }}"
    command: "cloud-ui events"
    config_dir: "cloud-ui-backend"
    dimensions: "{{ cloud_ui_backend_dimensions }}"
    volumes:
      - "{{ cloud_ui_config_root }}/cloud-ui-backend/:{{ cloud_ui_container_config_directory }}/:ro"
      - "{{ cloud_ui_log_volume }}:/var/log/kolla/"
```

- [ ] **Step 3: Add task files**

Create `deploy/kolla/ansible/roles/cloud_ui/tasks/main.yml`:

```yaml
---
- name: Validate Cloud UI role inputs
  ansible.builtin.import_tasks: validate.yml

- name: Prepare Cloud UI config templates
  ansible.builtin.import_tasks: config.yml
  when: cloud_ui_enabled | bool

- name: Define Cloud UI container data
  ansible.builtin.import_tasks: containers.yml
  when: cloud_ui_enabled | bool
```

Create `deploy/kolla/ansible/roles/cloud_ui/tasks/validate.yml`:

```yaml
---
- name: Reject mutable Cloud UI image tags
  ansible.builtin.assert:
    that:
      - cloud_ui_backend_image_tag != 'latest'
      - cloud_ui_frontend_image_tag != 'latest'
    fail_msg: "Cloud UI images must not use the latest tag."

- name: Validate Cloud UI service count
  ansible.builtin.assert:
    that:
      - cloud_ui_services | length == cloud_ui_permanent_container_count_per_node
      - cloud_ui_permanent_container_count_per_node == 4
    fail_msg: "Cloud UI must declare exactly four permanent services per node."

- name: Validate Cloud UI image names
  ansible.builtin.assert:
    that:
      - cloud_ui_backend_image == 'cloud-ui-backend'
      - cloud_ui_frontend_image == 'cloud-ui-frontend'
    fail_msg: "Cloud UI must keep the E09 two-image contract."
```

Create `deploy/kolla/ansible/roles/cloud_ui/tasks/config.yml`:

```yaml
---
- name: Ensure Cloud UI config directories exist
  ansible.builtin.file:
    path: "{{ cloud_ui_config_root }}/{{ item }}"
    state: directory
    mode: "0750"
  loop:
    - cloud-ui-backend
    - cloud-ui-frontend

- name: Render Cloud UI backend non-secret environment
  ansible.builtin.template:
    src: cloud-ui-backend.env.j2
    dest: "{{ cloud_ui_config_root }}/cloud-ui-backend/cloud-ui-backend.env"
    mode: "0640"
  notify:
    - Restart Cloud UI containers

- name: Render Cloud UI frontend runtime config
  ansible.builtin.template:
    src: cloud-ui-frontend.conf.j2
    dest: "{{ cloud_ui_config_root }}/cloud-ui-frontend/nginx.conf"
    mode: "0640"
  notify:
    - Restart Cloud UI containers
```

Create `deploy/kolla/ansible/roles/cloud_ui/tasks/containers.yml`:

```yaml
---
- name: Publish Cloud UI container definitions for later Kolla deployment tasks
  ansible.builtin.set_fact:
    cloud_ui_container_definitions: "{{ cloud_ui_services }}"
```

- [ ] **Step 4: Add handlers and templates**

Create `deploy/kolla/ansible/roles/cloud_ui/handlers/main.yml`:

```yaml
---
- name: Restart Cloud UI containers
  ansible.builtin.debug:
    msg: "Cloud UI restart is a later E09 live-deploy action."
```

Create `deploy/kolla/ansible/roles/cloud_ui/templates/cloud-ui-backend.env.j2`:

```jinja
CLOUD_UI_CONFIG_VERSION={{ cloud_ui_config_version }}
CLOUD_UI_PUBLIC_BASE_URL={{ cloud_ui_public_base_url }}
CLOUD_UI_LOG_LEVEL={{ cloud_ui_log_level }}
CLOUD_UI_BACKEND_ROLE={{ item.key | default('cloud_ui_backend') }}
```

Create `deploy/kolla/ansible/roles/cloud_ui/templates/cloud-ui-frontend.conf.j2`:

```jinja
worker_processes auto;
pid /tmp/nginx.pid;

events {
    worker_connections 1024;
}

http {
    include /etc/nginx/mime.types;
    default_type application/octet-stream;

    server {
        listen {{ cloud_ui_frontend_listen_port }};
        server_name _;

        root /usr/share/nginx/html;
        index index.html;

        location / {
            try_files $uri $uri/ /index.html;
        }
    }
}
```

- [ ] **Step 5: Run the targeted test**

Run:

```bash
backend/.venv/bin/python -m pytest tests/test_e09_kolla_ansible_role.py -q
```

Expected after role files exist but before evidence exists: failures only for missing `docs/generated/e09-kolla-ansible-role.md` and evidence assertions.

- [ ] **Step 6: Commit minimal role skeleton**

Run:

```bash
git add deploy/kolla/ansible docs/execplans/E09-kolla-ansible-role.md
git commit -m "deploy: add E09 Kolla Ansible role skeleton"
```

## Task 3: Add Evidence and Traceability

**Files:**
- Create: `docs/generated/e09-kolla-ansible-role.md`
- Modify: `deploy/kolla/README.md`
- Modify: `docs/generated/risk-register.md`
- Modify: `docs/11_DKB_TRACEABILITY.md`
- Modify: `docs/execplans/E09-kolla-ansible-role.md`

- [ ] **Step 1: Add generated evidence**

Create `docs/generated/e09-kolla-ansible-role.md`:

```markdown
# E09.2 Kolla-Ansible Role Evidence

- Stage: E09.2 Ansible role skeleton
- Date: 2026-06-24
- Scope: repository-side role skeleton and dry-run contract
- Live deployment: not executed in this slice
- Production action: none

## Role Contract

The role path is `deploy/kolla/ansible/roles/cloud_ui`.

Permanent services declared per node:

| Service | Image | Command |
|---|---|---|
| `cloud_ui_frontend` | `cloud-ui-frontend` | `nginx -g 'daemon off;'` |
| `cloud_ui_api` | `cloud-ui-backend` | `cloud-ui api` |
| `cloud_ui_worker` | `cloud-ui-backend` | `cloud-ui worker` |
| `cloud_ui_events` | `cloud-ui-backend` | `cloud-ui events` |

This preserves the two-image contract from E09.1.

## External Evidence Status

| Evidence | Status | Reason |
|---|---|---|
| live Kolla-Ansible syntax/render on test inventory | pending_external_evidence | Requires approved test inventory and image digests. |
| three-node 12 live containers | pending_external_evidence | E09.5/E09.8 own rollout and inspection. |
| DB/RabbitMQ least privilege | pending_external_evidence | E09.3 owns provisioning. |
| one-shot migration execution | pending_external_evidence | E09.4 owns migration job. |
| HAProxy/TLS route | pending_external_evidence | E09.6 owns proxy and TLS evidence. |
| rollback/reconfigure proof | pending_external_evidence | E09.7 owns rollback. |
| registry digest, SBOM, scan and signature | pending_external_evidence | Requires approved test registry and scanner/signing flow. |

## DKB Impact

- ДКБ-55/56: no runtime secret values are stored in this role skeleton. Secret material, rotation and
  test evidence remain E09.3+.
- ДКБ-69/70: image references preserve the two-image contract and reject `latest`, but scanner,
  signature and Python interpreter waiver evidence remain pending.
- ДКБ-76/77/80: role placement and container definition interfaces are documented. Runtime network
  ACLs, disabled unused interfaces and management-zone evidence remain pending.
- ДКБ-22.02/23.02/24/42-44/65/82: TLS/mTLS, firewall, SELinux, backup and rollback evidence remain
  external to this slice.

## Rollback

Revert the E09.2 commits. This slice changes only repository files and does not modify remote hosts,
database schema, queues, registry contents, Vault paths, Kolla inventory or production credentials.
```

- [ ] **Step 2: Update Kolla README**

Append this section to `deploy/kolla/README.md`:

```markdown
## Kolla-Ansible Role Skeleton

`deploy/kolla/ansible/roles/cloud_ui` contains the E09.2 repository-side role skeleton. It declares
four permanent services per control/UI node while preserving two images:

- `cloud_ui_frontend` uses `cloud-ui-frontend`;
- `cloud_ui_api`, `cloud_ui_worker` and `cloud_ui_events` use `cloud-ui-backend`.

This role skeleton is not live deployment evidence. DB/RabbitMQ provisioning, one-shot migration,
HAProxy/TLS, container inspection, SELinux proof, rolling update and rollback remain later E09 slices.
```

- [ ] **Step 3: Update risk register**

Add this E09 risk row in `docs/generated/risk-register.md` near the E09 Kolla deployment risks:

```markdown
| R-061 | E09.2 role skeleton mistaken for live deployment proof | E09.2 adds repository-side Kolla-Ansible role files and contract tests only. No inventory, host, registry, DB, RabbitMQ, HAProxy/TLS, SELinux or rollback proof is produced in this slice. | Keep live deployment rows as `pending_external_evidence` until E09.3-E09.8 execute on the approved test stand. | E09 |
```

- [ ] **Step 4: Update DKB traceability**

Add a section to `docs/11_DKB_TRACEABILITY.md` after the E09.1 update:

```markdown
## Обновление требований 2026-06-24: E09.2 Kolla-Ansible role skeleton

E09.2 добавляет repository-side Kolla-Ansible role skeleton без live deployment:

- ДКБ-55/56: role skeleton does not store runtime secret values. DB/RabbitMQ credentials, Vault/SecMan
  references and rotation evidence remain E09.3+.
- ДКБ-69/70: role defaults preserve two image names and reject `latest`; scanner/signing/registry
  digest evidence and the Python backend interpreter waiver remain pending.
- ДКБ-76/77/80: role declares service placement and four permanent service definitions per node.
  Runtime Kolla-Ansible execution, management-zone ACLs and disabled-interface proof remain E09.5+.
- ДКБ-22.02/23.02/24/42-44/65/82: TLS/mTLS, firewall, SELinux, backup/restore and rollback evidence
  are explicitly out of scope for this repository-only slice.

Evidence: `tests/test_e09_kolla_ansible_role.py`,
`deploy/kolla/ansible/roles/cloud_ui/defaults/main.yml`,
`deploy/kolla/ansible/roles/cloud_ui/tasks/*.yml`,
`deploy/kolla/ansible/roles/cloud_ui/templates/*.j2`,
`docs/generated/e09-kolla-ansible-role.md` and ExecPlan
`docs/execplans/E09-kolla-ansible-role.md`.
```

- [ ] **Step 5: Run targeted test**

Run:

```bash
backend/.venv/bin/python -m pytest tests/test_e09_kolla_ansible_role.py -q
```

Expected: pass.

- [ ] **Step 6: Commit evidence and traceability**

Run:

```bash
git add deploy/kolla/README.md docs/generated/e09-kolla-ansible-role.md docs/generated/risk-register.md docs/11_DKB_TRACEABILITY.md docs/execplans/E09-kolla-ansible-role.md
git commit -m "docs: add E09 Ansible role evidence"
```

## Task 4: Final Verification and Review

**Files:**
- Modify: `docs/execplans/E09-kolla-ansible-role.md`

- [ ] **Step 1: Run final checks**

Run from `/Users/dmitry/Desktop/dawn/.worktrees/e09-ansible-role-skeleton`:

```bash
backend/.venv/bin/python -m pytest tests/test_e09_kolla_ansible_role.py -q
backend/.venv/bin/python -m pytest tests/test_e09_kolla_image_build.py tests/test_e09_kolla_ansible_role.py -q
cd backend && .venv/bin/python -m ruff check ../tests/test_e09_kolla_ansible_role.py
make lint
make typecheck
make test
make security
git diff --check
rg -n "password|token|private key|BEGIN|latest|production approved|12 live containers proven" deploy/kolla docs/generated/e09-kolla-ansible-role.md docs/11_DKB_TRACEABILITY.md docs/generated/risk-register.md tests/test_e09_kolla_ansible_role.py
```

Expected:

- targeted E09.2 test passes;
- combined E09.1/E09.2 tests pass;
- ruff passes;
- backend/frontend lint passes;
- backend/frontend typecheck passes;
- backend 326+ tests pass with the existing skipped test count, frontend 35 tests pass;
- secret scan passes;
- diff check passes;
- self-review grep contains only negative assertions, explanatory documentation or existing traceability text.

- [ ] **Step 2: Update ExecPlan with final results**

Record exact command results in `docs/execplans/E09-kolla-ansible-role.md`, including residual risks:

- no live stand;
- no registry digest/SBOM/scan/signing;
- no DB/RabbitMQ provisioning;
- no migration execution;
- no HAProxy/TLS;
- no 12 live container proof;
- no rollback proof.

- [ ] **Step 3: Commit final verification record**

Run:

```bash
git add docs/execplans/E09-kolla-ansible-role.md
git commit -m "docs: record E09 Ansible role verification"
```

- [ ] **Step 4: Request review**

Ask for a final code review focused on:

- role skeleton overclaiming live deployment;
- accidental secret/live inventory inclusion;
- breaking E09.1 two-image contract;
- missing negative tests for later E09 scopes.

Address any findings with tests first.

## Execution Notes

- Do not run Kolla-Ansible against hosts in this slice.
- Do not add production inventory, hostnames, credentials, registry credentials or secret values.
- Do not add DB/RabbitMQ provisioning, migration job execution, HAProxy/TLS or rollback tasks in E09.2.
- Keep generated evidence explicit about `pending_external_evidence`.
