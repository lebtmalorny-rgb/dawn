# E01.5 Kolla Lab Prototype Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a lab-only Kolla-shaped packaging and single-node deployment prototype for the existing Dawn E01 application.

**Architecture:** Keep `dawn` as the source application repository and add a `deploy/kolla/` layer for Kolla Build templates, lab registry/build automation and reversible single-node AIO deployment playbooks. The prototype produces exactly two custom images, pushes them to `192.168.10.15:5000`, deploys four long-running containers on `192.168.10.14`, runs one migration command, verifies smoke, and rolls back without touching unrelated OpenStack/Kolla services.

**Tech Stack:** Kolla Build 20.4.x, Rocky 9, Podman registry/build host on `192.168.10.15`, Docker runtime on `192.168.10.14`, Ansible built-in modules plus container CLI commands, Python static tests with pytest, existing Dawn backend/frontend packages.

---

## References

- Design spec: `docs/superpowers/specs/2026-06-21-e015-kolla-lab-prototype-design.md`
- Kolla docs: `https://docs.openstack.org/kolla/2025.1/admin/image-building.html`
- Kolla custom templates use `--docker-dir` for external non-built-in project images; custom users need explicit user config sections.
- Lab Kolla baseline observed on `192.168.10.15`: `kolla-build 20.4.0`, `engine = podman`, `base = rocky`, `base_tag = 9`, `openstack_release = 2025.1`, `tag = 2025.1-rocky-9`.

## File Structure

Create or modify:

```text
tests/test_e015_kolla_layout.py
deploy/kolla/README.md
deploy/kolla/kolla-build.conf.example
deploy/kolla/docker/cloud-ui-backend/Dockerfile.j2
deploy/kolla/docker/cloud-ui-frontend/Dockerfile.j2
deploy/kolla/scripts/build-images.sh
deploy/kolla/lab/inventory.ini.example
deploy/kolla/lab/group_vars/all.yml.example
deploy/kolla/lab/playbooks/bootstrap-registry.yml
deploy/kolla/lab/playbooks/deploy.yml
deploy/kolla/lab/playbooks/smoke.yml
deploy/kolla/lab/playbooks/rollback.yml
docs/execplans/E015-kolla-lab-prototype.md
docs/generated/current-state.md
FILE_INDEX.md
```

No real credential file is committed. Lab secrets are supplied through environment variables or an untracked operator file on the Ansible host.

---

### Task 1: Static Contract Tests For E01.5 Layout

**Files:**
- Create: `tests/test_e015_kolla_layout.py`

- [ ] **Step 1: Write the failing layout tests**

Create `tests/test_e015_kolla_layout.py`:

```python
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read_text(relative_path: str) -> str:
    return (ROOT / relative_path).read_text(encoding="utf-8")


def test_kolla_build_files_exist() -> None:
    expected_files = [
        "deploy/kolla/README.md",
        "deploy/kolla/kolla-build.conf.example",
        "deploy/kolla/docker/cloud-ui-backend/Dockerfile.j2",
        "deploy/kolla/docker/cloud-ui-frontend/Dockerfile.j2",
        "deploy/kolla/scripts/build-images.sh",
    ]

    for relative_path in expected_files:
        assert (ROOT / relative_path).is_file(), relative_path


def test_kolla_build_config_defines_two_custom_images() -> None:
    config = read_text("deploy/kolla/kolla-build.conf.example")

    assert "engine = podman" in config
    assert "base = rocky" in config
    assert "base_tag = 9" in config
    assert "openstack_release = 2025.1" in config
    assert "tag = 2025.1-rocky-9" in config
    assert "cloud-ui-backend = cloud-ui-backend" in config
    assert "cloud-ui-frontend = cloud-ui-frontend" in config
    assert "[cloud-ui-backend]" in config
    assert "[cloud-ui-frontend]" in config
    assert "[cloudui-user]" in config
    assert "latest" not in config.lower()


def test_backend_template_keeps_one_backend_image_for_all_commands() -> None:
    template = read_text("deploy/kolla/docker/cloud-ui-backend/Dockerfile.j2")

    assert "FROM {{ namespace }}/{{ image_prefix }}openstack-base:{{ tag }}" in template
    assert "cloud-ui-backend-source" in template
    assert "cloud-ui api" in template
    assert "cloud-ui worker" in template
    assert "cloud-ui events" in template
    assert "cloud-ui db-upgrade" in template
    assert "cloud-ui smoke" in template
    assert "cloud-ui-api" not in template
    assert "cloud-ui-worker" not in template
    assert "cloud-ui-events" not in template


def test_frontend_template_uses_prebuilt_dist_without_node_runtime() -> None:
    template = read_text("deploy/kolla/docker/cloud-ui-frontend/Dockerfile.j2")

    assert "FROM {{ namespace }}/{{ image_prefix }}base:{{ tag }}" in template
    assert "cloud-ui-frontend-source/frontend/dist" in template
    assert "nginx" in template
    assert "node" not in template.lower()
    assert "npm" not in template.lower()


def test_lab_playbooks_are_reversible_and_use_no_committed_secrets() -> None:
    expected_files = [
        "deploy/kolla/lab/inventory.ini.example",
        "deploy/kolla/lab/group_vars/all.yml.example",
        "deploy/kolla/lab/playbooks/bootstrap-registry.yml",
        "deploy/kolla/lab/playbooks/deploy.yml",
        "deploy/kolla/lab/playbooks/smoke.yml",
        "deploy/kolla/lab/playbooks/rollback.yml",
    ]

    for relative_path in expected_files:
        assert (ROOT / relative_path).is_file(), relative_path

    deploy = read_text("deploy/kolla/lab/playbooks/deploy.yml")
    rollback = read_text("deploy/kolla/lab/playbooks/rollback.yml")
    group_vars = read_text("deploy/kolla/lab/group_vars/all.yml.example")

    for name in ("cloud_ui_api", "cloud_ui_worker", "cloud_ui_events", "cloud_ui_frontend"):
        assert name in deploy
        assert name in rollback

    assert "cloud-ui" in deploy
    assert "cloud-ui-backend" in deploy
    assert "cloud-ui-frontend" in deploy
    assert "cloud_ui_database_url" in group_vars
    assert "cloud_ui_rabbitmq_url" in group_vars
    assert "cloud_ui_dev" not in group_vars
    assert "admin123" not in group_vars
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
backend/.venv/bin/python -m pytest -q tests/test_e015_kolla_layout.py
```

Expected: FAIL with missing `deploy/kolla/...` files.

- [ ] **Step 3: Commit the failing contract tests**

Run:

```bash
git add tests/test_e015_kolla_layout.py
git commit -m "test: add E01.5 Kolla layout contracts"
```

Expected: commit succeeds with only the new test file.

---

### Task 2: Kolla Build Templates And Build Config

**Files:**
- Create: `deploy/kolla/README.md`
- Create: `deploy/kolla/kolla-build.conf.example`
- Create: `deploy/kolla/docker/cloud-ui-backend/Dockerfile.j2`
- Create: `deploy/kolla/docker/cloud-ui-frontend/Dockerfile.j2`

- [ ] **Step 1: Create Kolla build README**

Create `deploy/kolla/README.md`:

```markdown
# Dawn Kolla lab prototype

This directory contains the lab-only E01.5 Kolla Build and single-node deployment prototype.

It is not the final E09 production Kolla-Ansible role. It exists to prove that Dawn can be packaged as two custom images and deployed safely in the test lab.

## Images

- `cloud-ui-backend`
- `cloud-ui-frontend`

The backend image is shared by API, worker, events, migration and smoke commands:

```text
cloud-ui api
cloud-ui worker
cloud-ui events
cloud-ui db-upgrade
cloud-ui smoke
```

## Lab topology

- build/control host: `192.168.10.15`
- test registry: `192.168.10.15:5000`
- deploy target: `192.168.10.14`

## Required operator inputs

Real database and RabbitMQ connection strings are never committed. Supply them on the Ansible host through environment variables or an untracked vars file.

Required variables:

- `cloud_ui_database_url`
- `cloud_ui_rabbitmq_url`

## Kolla Build checks

```bash
kolla-build --config-file deploy/kolla/kolla-build.conf.example \
  --docker-dir deploy/kolla/docker \
  --list-images '^cloud-ui-(backend|frontend)$'

kolla-build --config-file deploy/kolla/kolla-build.conf.example \
  --docker-dir deploy/kolla/docker \
  --template-only '^cloud-ui-(backend|frontend)$'
```

Use `deploy/kolla/scripts/build-images.sh` on the Ansible host for the lab build and push flow.

## Safety

- no production inventory;
- no real secrets in Git;
- no `latest` tag;
- no OpenStack service DB changes;
- rollback removes only Dawn custom containers and generated Dawn config.
```

- [ ] **Step 2: Create Kolla build config example**

Create `deploy/kolla/kolla-build.conf.example`:

```ini
[DEFAULT]
engine = podman
base = rocky
base_tag = 9
openstack_release = 2025.1
namespace = kolla
tag = 2025.1-rocky-9
registry = 192.168.10.15:5000
push = False
template_only = False
logs_dir = /tmp/dawn-kolla-build/logs
work_dir = /tmp/dawn-kolla-build/work

[profiles]
cloud-ui-backend = cloud-ui-backend
cloud-ui-frontend = cloud-ui-frontend
cloud-ui = cloud-ui-backend,cloud-ui-frontend

[cloud-ui-backend]
type = local
location = /opt/dawn/source

[cloud-ui-frontend]
type = local
location = /opt/dawn/source

[cloudui-user]
uid = 42480
gid = 42480
```

- [ ] **Step 3: Create backend Kolla Dockerfile template**

Create `deploy/kolla/docker/cloud-ui-backend/Dockerfile.j2`:

```jinja
FROM {{ namespace }}/{{ image_prefix }}openstack-base:{{ tag }}

{% block labels %}
LABEL maintainer="{{ maintainer }}" name="{{ image_name }}" build-date="{{ build_date }}"
LABEL org.opencontainers.image.title="Dawn cloud UI backend"
LABEL org.opencontainers.image.description="Dawn API, worker, events, migration and smoke runtime"
{% endblock %}

{% block cloud_ui_backend_header %}{% endblock %}

{% import "macros.j2" as macros with context %}

{{ macros.configure_user(name='cloudui') }}

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

COPY cloud-ui-backend-source /tmp/cloud-ui-source

RUN {{ macros.install_pip(['/tmp/cloud-ui-source/backend'] | customizable("pip_packages")) }} \
    && mkdir -p /etc/cloud-ui /var/lib/cloud-ui /var/log/cloud-ui \
    && chown -R cloudui: /etc/cloud-ui /var/lib/cloud-ui /var/log/cloud-ui \
    && rm -rf /tmp/cloud-ui-source

USER cloudui
WORKDIR /var/lib/cloud-ui
EXPOSE 8080

# Supported commands from the single backend image:
# - cloud-ui api
# - cloud-ui worker
# - cloud-ui events
# - cloud-ui db-upgrade
# - cloud-ui smoke

CMD ["cloud-ui", "api"]

{% block cloud_ui_backend_footer %}{% endblock %}
{% block footer %}{% endblock %}
```

- [ ] **Step 4: Create frontend Kolla Dockerfile template**

Create `deploy/kolla/docker/cloud-ui-frontend/Dockerfile.j2`:

```jinja
FROM {{ namespace }}/{{ image_prefix }}base:{{ tag }}

{% block labels %}
LABEL maintainer="{{ maintainer }}" name="{{ image_name }}" build-date="{{ build_date }}"
LABEL org.opencontainers.image.title="Dawn cloud UI frontend"
LABEL org.opencontainers.image.description="Dawn static frontend served by nginx"
{% endblock %}

{% block cloud_ui_frontend_header %}{% endblock %}

{% import "macros.j2" as macros with context %}

{% set cloud_ui_frontend_packages = ['nginx'] %}
{{ macros.install_packages(cloud_ui_frontend_packages | customizable("packages")) }}
{{ macros.configure_user(name='cloudui') }}

COPY cloud-ui-frontend-source/frontend/dist /usr/share/nginx/html
COPY cloud-ui-frontend-source/frontend/nginx.conf /etc/nginx/nginx.conf

RUN mkdir -p /var/cache/nginx /var/log/nginx /run \
    && chown -R cloudui: /usr/share/nginx/html /var/cache/nginx /var/log/nginx /run \
    && chmod -R g=u /var/cache/nginx /var/log/nginx /run

USER cloudui
EXPOSE 8080

CMD ["nginx", "-g", "daemon off;"]

{% block cloud_ui_frontend_footer %}{% endblock %}
{% block footer %}{% endblock %}
```

- [ ] **Step 5: Run static tests**

Run:

```bash
backend/.venv/bin/python -m pytest -q tests/test_e015_kolla_layout.py
```

Expected: layout tests still fail because lab playbooks and scripts are not present yet, but build layout tests pass.

- [ ] **Step 6: Commit build layout**

Run:

```bash
git add deploy/kolla/README.md deploy/kolla/kolla-build.conf.example deploy/kolla/docker
git commit -m "feat: add Kolla build templates"
```

Expected: commit succeeds with Kolla build files only.

---

### Task 3: Lab Build And Registry Automation

**Files:**
- Create: `deploy/kolla/scripts/build-images.sh`
- Create: `deploy/kolla/lab/inventory.ini.example`
- Create: `deploy/kolla/lab/group_vars/all.yml.example`
- Create: `deploy/kolla/lab/playbooks/bootstrap-registry.yml`

- [ ] **Step 1: Create build-and-push script**

Create executable `deploy/kolla/scripts/build-images.sh`:

```bash
#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"

KOLLA_BUILD="${KOLLA_BUILD:-kolla-build}"
KOLLA_CONFIG="${KOLLA_CONFIG:-${repo_root}/deploy/kolla/kolla-build.conf.example}"
KOLLA_DOCKER_DIR="${KOLLA_DOCKER_DIR:-${repo_root}/deploy/kolla/docker}"
CLOUD_UI_REGISTRY="${CLOUD_UI_REGISTRY:-192.168.10.15:5000}"
CLOUD_UI_TAG="${CLOUD_UI_TAG:-2025.1-rocky-9}"
CLOUD_UI_SOURCE="${CLOUD_UI_SOURCE:-/opt/dawn/source}"
CLOUD_UI_IMAGES_REGEX="${CLOUD_UI_IMAGES_REGEX:-^cloud-ui-(backend|frontend)$}"

if [ ! -d "${CLOUD_UI_SOURCE}" ]; then
  printf 'source directory not found: %s\n' "${CLOUD_UI_SOURCE}" >&2
  printf 'sync this repository to the build host first, for example /opt/dawn/source\n' >&2
  exit 2
fi

if [ ! -d "${CLOUD_UI_SOURCE}/frontend/dist" ]; then
  printf 'frontend/dist not found under %s; run npm ci && npm run build before kolla-build\n' "${CLOUD_UI_SOURCE}" >&2
  exit 2
fi

exec "${KOLLA_BUILD}" \
  --config-file "${KOLLA_CONFIG}" \
  --docker-dir "${KOLLA_DOCKER_DIR}" \
  --registry "${CLOUD_UI_REGISTRY}" \
  --tag "${CLOUD_UI_TAG}" \
  --push \
  "${CLOUD_UI_IMAGES_REGEX}"
```

- [ ] **Step 2: Create example lab inventory**

Create `deploy/kolla/lab/inventory.ini.example`:

```ini
[registry]
ansible-host ansible_host=192.168.10.15 ansible_user=root

[cloud_ui_aio]
openstack-aio ansible_host=192.168.10.14 ansible_user=root
```

- [ ] **Step 3: Create example group vars**

Create `deploy/kolla/lab/group_vars/all.yml.example`:

```yaml
cloud_ui_registry_host: "192.168.10.15:5000"
cloud_ui_image_tag: "2025.1-rocky-9"
cloud_ui_backend_image: "{{ cloud_ui_registry_host }}/kolla/cloud-ui-backend:{{ cloud_ui_image_tag }}"
cloud_ui_frontend_image: "{{ cloud_ui_registry_host }}/kolla/cloud-ui-frontend:{{ cloud_ui_image_tag }}"

cloud_ui_network_name: "cloud-ui"
cloud_ui_api_port: 18080
cloud_ui_frontend_port: 13080
cloud_ui_config_dir: "/etc/cloud-ui"
cloud_ui_env_file: "{{ cloud_ui_config_dir }}/cloud-ui.env"

cloud_ui_registry_engine: "podman"
cloud_ui_aio_engine: "docker"

# Supply these through an untracked vars file or environment-specific secret store.
cloud_ui_database_url: "{{ lookup('env', 'CLOUD_UI_DATABASE_URL') }}"
cloud_ui_rabbitmq_url: "{{ lookup('env', 'CLOUD_UI_RABBITMQ_URL') }}"
```

- [ ] **Step 4: Create registry bootstrap playbook**

Create `deploy/kolla/lab/playbooks/bootstrap-registry.yml`:

```yaml
---
- name: Bootstrap Dawn lab registry
  hosts: registry
  gather_facts: false
  vars:
    registry_container_name: dawn_registry
    registry_bind: "0.0.0.0:5000"
    registry_image: "registry:2"
  tasks:
    - name: Check registry container
      ansible.builtin.command:
        argv:
          - "{{ cloud_ui_registry_engine }}"
          - ps
          - --filter
          - "name={{ registry_container_name }}"
          - --format
          - "{{ '{{' }}.Names{{ '}}' }}"
      register: registry_ps
      changed_when: false

    - name: Start registry container
      ansible.builtin.command:
        argv:
          - "{{ cloud_ui_registry_engine }}"
          - run
          - -d
          - --restart=always
          - -p
          - "{{ registry_bind }}:5000"
          - --name
          - "{{ registry_container_name }}"
          - "{{ registry_image }}"
      when: registry_container_name not in registry_ps.stdout_lines
```

- [ ] **Step 5: Mark build script executable**

Run:

```bash
chmod +x deploy/kolla/scripts/build-images.sh
```

Expected: `git ls-files -s deploy/kolla/scripts/build-images.sh` later shows `100755`.

- [ ] **Step 6: Run static tests**

Run:

```bash
backend/.venv/bin/python -m pytest -q tests/test_e015_kolla_layout.py
```

Expected: tests still fail because deploy/smoke/rollback playbooks are not present yet; registry/build checks pass.

- [ ] **Step 7: Commit lab build automation**

Run:

```bash
git add deploy/kolla/scripts deploy/kolla/lab/inventory.ini.example deploy/kolla/lab/group_vars deploy/kolla/lab/playbooks/bootstrap-registry.yml
git commit -m "feat: add Kolla lab build automation"
```

Expected: commit succeeds.

---

### Task 4: Single-Node Deploy, Smoke And Rollback Playbooks

**Files:**
- Create: `deploy/kolla/lab/playbooks/deploy.yml`
- Create: `deploy/kolla/lab/playbooks/smoke.yml`
- Create: `deploy/kolla/lab/playbooks/rollback.yml`

- [ ] **Step 1: Create deploy playbook**

Create `deploy/kolla/lab/playbooks/deploy.yml`:

```yaml
---
- name: Deploy Dawn lab containers on single-node AIO
  hosts: cloud_ui_aio
  gather_facts: false
  tasks:
    - name: Require database URL
      ansible.builtin.assert:
        that:
          - cloud_ui_database_url | length > 0
          - cloud_ui_database_url is search('://')
        fail_msg: "cloud_ui_database_url must be supplied outside Git"
      no_log: true

    - name: Require RabbitMQ URL
      ansible.builtin.assert:
        that:
          - cloud_ui_rabbitmq_url | length > 0
          - cloud_ui_rabbitmq_url is search('://')
        fail_msg: "cloud_ui_rabbitmq_url must be supplied outside Git"
      no_log: true

    - name: Create Dawn config directory
      ansible.builtin.file:
        path: "{{ cloud_ui_config_dir }}"
        state: directory
        owner: root
        group: root
        mode: "0750"

    - name: Write Dawn runtime environment file
      ansible.builtin.copy:
        dest: "{{ cloud_ui_env_file }}"
        owner: root
        group: root
        mode: "0640"
        content: |
          CLOUD_UI_DATABASE_URL={{ cloud_ui_database_url }}
          CLOUD_UI_RABBITMQ_URL={{ cloud_ui_rabbitmq_url }}
          CLOUD_UI_API_BIND_HOST=0.0.0.0
          CLOUD_UI_API_PORT=8080
          CLOUD_UI_LOG_LEVEL=INFO
          CLOUD_UI_CONFIG_VERSION=e015-lab
      no_log: true

    - name: Create Dawn Docker network
      ansible.builtin.command:
        argv:
          - "{{ cloud_ui_aio_engine }}"
          - network
          - create
          - "{{ cloud_ui_network_name }}"
      register: network_create
      failed_when: network_create.rc not in [0, 1]
      changed_when: network_create.rc == 0

    - name: Pull backend image
      ansible.builtin.command:
        argv:
          - "{{ cloud_ui_aio_engine }}"
          - pull
          - "{{ cloud_ui_backend_image }}"
      changed_when: true

    - name: Pull frontend image
      ansible.builtin.command:
        argv:
          - "{{ cloud_ui_aio_engine }}"
          - pull
          - "{{ cloud_ui_frontend_image }}"
      changed_when: true

    - name: Remove previous Dawn containers
      ansible.builtin.command:
        argv:
          - "{{ cloud_ui_aio_engine }}"
          - rm
          - -f
          - "{{ item }}"
      register: remove_result
      failed_when: remove_result.rc not in [0, 1]
      changed_when: remove_result.rc == 0
      loop:
        - cloud_ui_frontend
        - cloud_ui_api
        - cloud_ui_worker
        - cloud_ui_events

    - name: Run database migration once
      ansible.builtin.command:
        argv:
          - "{{ cloud_ui_aio_engine }}"
          - run
          - --rm
          - --name
          - cloud_ui_db_migrate
          - --env-file
          - "{{ cloud_ui_env_file }}"
          - --network
          - "{{ cloud_ui_network_name }}"
          - "{{ cloud_ui_backend_image }}"
          - cloud-ui
          - db-upgrade
      no_log: true

    - name: Start API container
      ansible.builtin.command:
        argv:
          - "{{ cloud_ui_aio_engine }}"
          - run
          - -d
          - --restart
          - unless-stopped
          - --name
          - cloud_ui_api
          - --env-file
          - "{{ cloud_ui_env_file }}"
          - --network
          - "{{ cloud_ui_network_name }}"
          - --network-alias
          - api
          - -p
          - "{{ cloud_ui_api_port }}:8080"
          - "{{ cloud_ui_backend_image }}"
          - cloud-ui
          - api
      no_log: true

    - name: Start worker container
      ansible.builtin.command:
        argv:
          - "{{ cloud_ui_aio_engine }}"
          - run
          - -d
          - --restart
          - unless-stopped
          - --name
          - cloud_ui_worker
          - --env-file
          - "{{ cloud_ui_env_file }}"
          - --network
          - "{{ cloud_ui_network_name }}"
          - "{{ cloud_ui_backend_image }}"
          - cloud-ui
          - worker
      no_log: true

    - name: Start events container
      ansible.builtin.command:
        argv:
          - "{{ cloud_ui_aio_engine }}"
          - run
          - -d
          - --restart
          - unless-stopped
          - --name
          - cloud_ui_events
          - --env-file
          - "{{ cloud_ui_env_file }}"
          - --network
          - "{{ cloud_ui_network_name }}"
          - "{{ cloud_ui_backend_image }}"
          - cloud-ui
          - events
      no_log: true

    - name: Start frontend container
      ansible.builtin.command:
        argv:
          - "{{ cloud_ui_aio_engine }}"
          - run
          - -d
          - --restart
          - unless-stopped
          - --name
          - cloud_ui_frontend
          - --network
          - "{{ cloud_ui_network_name }}"
          - -p
          - "{{ cloud_ui_frontend_port }}:8080"
          - "{{ cloud_ui_frontend_image }}"
```

- [ ] **Step 2: Create smoke playbook**

Create `deploy/kolla/lab/playbooks/smoke.yml`:

```yaml
---
- name: Smoke Dawn lab containers
  hosts: cloud_ui_aio
  gather_facts: false
  tasks:
    - name: Wait for API liveness
      ansible.builtin.uri:
        url: "http://127.0.0.1:{{ cloud_ui_api_port }}/health/live"
        method: GET
        status_code: 200
        return_content: true
      register: api_live
      retries: 30
      delay: 2
      until: api_live.status == 200 and api_live.json.status == "ok"

    - name: Wait for API readiness
      ansible.builtin.uri:
        url: "http://127.0.0.1:{{ cloud_ui_api_port }}/api/v1/health/ready"
        method: GET
        status_code: 200
        return_content: true
      register: api_ready
      retries: 30
      delay: 2
      until: api_ready.status == 200 and api_ready.json.status == "ok"

    - name: Wait for frontend response
      ansible.builtin.uri:
        url: "http://127.0.0.1:{{ cloud_ui_frontend_port }}/"
        method: GET
        status_code: 200
      register: frontend_response
      retries: 30
      delay: 2
      until: frontend_response.status == 200

    - name: List Dawn containers
      ansible.builtin.command:
        argv:
          - "{{ cloud_ui_aio_engine }}"
          - ps
          - --filter
          - name=cloud_ui_
          - --format
          - "{{ '{{' }}.Names{{ '}}' }} {{ '{{' }}.Image{{ '}}' }} {{ '{{' }}.Status{{ '}}' }}"
      register: cloud_ui_ps
      changed_when: false

    - name: Require all long-running containers
      ansible.builtin.assert:
        that:
          - "'cloud_ui_api' in cloud_ui_ps.stdout"
          - "'cloud_ui_worker' in cloud_ui_ps.stdout"
          - "'cloud_ui_events' in cloud_ui_ps.stdout"
          - "'cloud_ui_frontend' in cloud_ui_ps.stdout"
          - "cloud_ui_backend_image in cloud_ui_ps.stdout"
          - "cloud_ui_frontend_image in cloud_ui_ps.stdout"
```

- [ ] **Step 3: Create rollback playbook**

Create `deploy/kolla/lab/playbooks/rollback.yml`:

```yaml
---
- name: Roll back Dawn lab containers
  hosts: cloud_ui_aio
  gather_facts: false
  tasks:
    - name: Remove Dawn containers
      ansible.builtin.command:
        argv:
          - "{{ cloud_ui_aio_engine }}"
          - rm
          - -f
          - "{{ item }}"
      register: remove_result
      failed_when: remove_result.rc not in [0, 1]
      changed_when: remove_result.rc == 0
      loop:
        - cloud_ui_frontend
        - cloud_ui_api
        - cloud_ui_worker
        - cloud_ui_events
        - cloud_ui_db_migrate

    - name: Remove Dawn config directory
      ansible.builtin.file:
        path: "{{ cloud_ui_config_dir }}"
        state: absent

    - name: Remove Dawn Docker network
      ansible.builtin.command:
        argv:
          - "{{ cloud_ui_aio_engine }}"
          - network
          - rm
          - "{{ cloud_ui_network_name }}"
      register: network_remove
      failed_when: network_remove.rc not in [0, 1]
      changed_when: network_remove.rc == 0

    - name: Verify Dawn containers are gone
      ansible.builtin.command:
        argv:
          - "{{ cloud_ui_aio_engine }}"
          - ps
          - -a
          - --filter
          - name=cloud_ui_
          - --format
          - "{{ '{{' }}.Names{{ '}}' }}"
      register: remaining_containers
      changed_when: false

    - name: Assert rollback removed custom containers
      ansible.builtin.assert:
        that:
          - remaining_containers.stdout | trim == ""
```

- [ ] **Step 4: Run static layout tests**

Run:

```bash
backend/.venv/bin/python -m pytest -q tests/test_e015_kolla_layout.py
```

Expected: PASS.

- [ ] **Step 5: Run YAML syntax checks if ansible is available**

Run:

```bash
ansible-playbook --syntax-check -i deploy/kolla/lab/inventory.ini.example deploy/kolla/lab/playbooks/bootstrap-registry.yml
ansible-playbook --syntax-check -i deploy/kolla/lab/inventory.ini.example deploy/kolla/lab/playbooks/deploy.yml
ansible-playbook --syntax-check -i deploy/kolla/lab/inventory.ini.example deploy/kolla/lab/playbooks/smoke.yml
ansible-playbook --syntax-check -i deploy/kolla/lab/inventory.ini.example deploy/kolla/lab/playbooks/rollback.yml
```

Expected: each command reports `playbook: ...`.

- [ ] **Step 6: Run repository safety checks**

Run:

```bash
./scripts/secret-scan.sh
git diff --check
```

Expected: both pass with exit 0.

- [ ] **Step 7: Commit lab deploy playbooks**

Run:

```bash
git add deploy/kolla/lab/playbooks/deploy.yml deploy/kolla/lab/playbooks/smoke.yml deploy/kolla/lab/playbooks/rollback.yml tests/test_e015_kolla_layout.py
git commit -m "feat: add Kolla lab deployment playbooks"
```

Expected: commit succeeds.

---

### Task 5: Lab Build, Push, Deploy, Smoke And Rollback Evidence

**Files:**
- Modify if evidence requires: `deploy/kolla/README.md`
- Create: `docs/execplans/E015-kolla-lab-prototype.md`

- [ ] **Step 1: Sync repo to Ansible host source path**

Run from local worktree:

```bash
rsync -a --delete \
  --exclude=.git \
  --exclude=.worktrees \
  --exclude=.serena \
  --exclude=.agents \
  --exclude=backend/.venv \
  --exclude=frontend/node_modules \
  --exclude=frontend/dist \
  /Users/dmitry/Desktop/dawn/.worktrees/e015-kolla-prototype/ \
  root@192.168.10.15:/opt/dawn/source/
```

Expected: rsync exits 0.

- [ ] **Step 2: Build frontend dist on Ansible host**

Run:

```bash
ssh -o StrictHostKeyChecking=no root@192.168.10.15 \
  'cd /opt/dawn/source/frontend && npm ci && npm run build'
```

Expected: `npm ci` exits 0 and `npm run build` exits 0, creating `/opt/dawn/source/frontend/dist`.

- [ ] **Step 3: Bootstrap lab registry**

Run:

```bash
ssh -o StrictHostKeyChecking=no root@192.168.10.15 \
  'cd /opt/dawn/source && /root/venvs/kolla-epoxy/bin/ansible-playbook -i deploy/kolla/lab/inventory.ini.example deploy/kolla/lab/playbooks/bootstrap-registry.yml'
```

Expected: play recap has `failed=0`; `podman ps --filter name=dawn_registry` shows registry on port 5000.

- [ ] **Step 4: Verify Kolla sees custom images**

Run:

```bash
ssh -o StrictHostKeyChecking=no root@192.168.10.15 \
  'cd /opt/dawn/source && /root/venvs/kolla-epoxy/bin/kolla-build --config-file deploy/kolla/kolla-build.conf.example --docker-dir deploy/kolla/docker --list-images "^cloud-ui-(backend|frontend)$"'
```

Expected: output includes `cloud-ui-backend` and `cloud-ui-frontend`.

- [ ] **Step 5: Render templates**

Run:

```bash
ssh -o StrictHostKeyChecking=no root@192.168.10.15 \
  'cd /opt/dawn/source && rm -rf /tmp/dawn-kolla-template-only && /root/venvs/kolla-epoxy/bin/kolla-build --config-file deploy/kolla/kolla-build.conf.example --docker-dir deploy/kolla/docker --template-only --work-dir /tmp/dawn-kolla-template-only "^cloud-ui-(backend|frontend)$"'
```

Expected: command exits 0 and generated Dockerfiles exist under `/tmp/dawn-kolla-template-only`.

- [ ] **Step 6: Build and push images**

Run:

```bash
ssh -o StrictHostKeyChecking=no root@192.168.10.15 \
  'cd /opt/dawn/source && KOLLA_BUILD=/root/venvs/kolla-epoxy/bin/kolla-build CLOUD_UI_SOURCE=/opt/dawn/source ./deploy/kolla/scripts/build-images.sh'
```

Expected: command exits 0 and pushes exactly two images tagged `192.168.10.15:5000/kolla/cloud-ui-backend:2025.1-rocky-9` and `192.168.10.15:5000/kolla/cloud-ui-frontend:2025.1-rocky-9`.

- [ ] **Step 7: Verify pushed image names**

Run:

```bash
ssh -o StrictHostKeyChecking=no root@192.168.10.15 \
  'podman images --format "{{.Repository}}:{{.Tag}}" | grep "192.168.10.15:5000/kolla/cloud-ui-" | sort'
```

Expected output:

```text
192.168.10.15:5000/kolla/cloud-ui-backend:2025.1-rocky-9
192.168.10.15:5000/kolla/cloud-ui-frontend:2025.1-rocky-9
```

- [ ] **Step 8: Prepare untracked lab secret vars on Ansible host**

Create `/root/dawn-cloud-ui-lab-secrets.yml` on `192.168.10.15` with lab-only generated credentials. Do not copy this file into Git.

Example shape:

```yaml
cloud_ui_database_url: "mysql+pymysql://cloud_ui:<lab-password>@<lab-db-host>:3306/cloud_ui"
cloud_ui_rabbitmq_url: "amqp://cloud_ui:<lab-password>@<lab-rabbit-host>:5672/%2Fcloud-ui"
```

Expected: file exists only on the Ansible host and `./scripts/secret-scan.sh` in the repo still returns no matches.

- [ ] **Step 9: Deploy to single-node AIO**

Run:

```bash
ssh -o StrictHostKeyChecking=no root@192.168.10.15 \
  'cd /opt/dawn/source && /root/venvs/kolla-epoxy/bin/ansible-playbook -i deploy/kolla/lab/inventory.ini.example -e @/root/dawn-cloud-ui-lab-secrets.yml deploy/kolla/lab/playbooks/deploy.yml'
```

Expected: play recap has `failed=0`; Docker on `192.168.10.14` shows `cloud_ui_api`, `cloud_ui_worker`, `cloud_ui_events`, `cloud_ui_frontend`.

- [ ] **Step 10: Run lab smoke**

Run:

```bash
ssh -o StrictHostKeyChecking=no root@192.168.10.15 \
  'cd /opt/dawn/source && /root/venvs/kolla-epoxy/bin/ansible-playbook -i deploy/kolla/lab/inventory.ini.example -e @/root/dawn-cloud-ui-lab-secrets.yml deploy/kolla/lab/playbooks/smoke.yml'
```

Expected: play recap has `failed=0`; smoke confirms API liveness, API readiness, frontend response and four long-running containers.

- [ ] **Step 11: Run rollback**

Run:

```bash
ssh -o StrictHostKeyChecking=no root@192.168.10.15 \
  'cd /opt/dawn/source && /root/venvs/kolla-epoxy/bin/ansible-playbook -i deploy/kolla/lab/inventory.ini.example -e @/root/dawn-cloud-ui-lab-secrets.yml deploy/kolla/lab/playbooks/rollback.yml'
```

Expected: play recap has `failed=0`; `docker ps -a --filter name=cloud_ui_` on `192.168.10.14` returns no containers.

- [ ] **Step 12: Write E01.5 evidence document**

Create `docs/execplans/E015-kolla-lab-prototype.md`:

```markdown
# ExecPlan: E01.5 Kolla lab prototype

## Result

E01.5 adds a lab-only Kolla Build and single-node deployment prototype for Dawn. It builds two custom images, publishes them to the test registry on `192.168.10.15:5000`, deploys the custom containers on AIO `192.168.10.14`, verifies smoke and rolls back the custom containers.

## Verification

- `backend/.venv/bin/python -m pytest -q tests/test_e015_kolla_layout.py`
- `ansible-playbook --syntax-check` for registry, deploy, smoke and rollback playbooks
- `kolla-build --docker-dir deploy/kolla/docker --list-images "^cloud-ui-(backend|frontend)$"`
- `kolla-build --docker-dir deploy/kolla/docker --template-only "^cloud-ui-(backend|frontend)$"`
- `deploy/kolla/scripts/build-images.sh`
- registry image inspection for exactly two custom images
- lab deploy playbook on `192.168.10.14`
- lab smoke playbook on `192.168.10.14`
- lab rollback playbook on `192.168.10.14`
- `./scripts/secret-scan.sh`

## Scope Limits

- Lab-only single-node prototype.
- No production inventory.
- No three-node HA rollout.
- No production HAProxy/TLS claim.
- No SBOM, vulnerability scan or digest-pinning claim.
- No DKB closure claim.

## Rollback

Run:

```bash
ansible-playbook -i deploy/kolla/lab/inventory.ini.example \
  -e @/root/dawn-cloud-ui-lab-secrets.yml \
  deploy/kolla/lab/playbooks/rollback.yml
```

Rollback removes only custom Dawn containers, the Dawn Docker network and generated Dawn config on the lab AIO host.
```

- [ ] **Step 13: Commit lab evidence**

Run:

```bash
git add docs/execplans/E015-kolla-lab-prototype.md deploy/kolla/README.md
git commit -m "docs: record E01.5 Kolla lab evidence"
```

Expected: commit succeeds after successful lab verification.

---

### Task 6: Index, Current State And Final Checks

**Files:**
- Modify: `FILE_INDEX.md`
- Modify: `docs/generated/current-state.md`

- [ ] **Step 1: Add E01.5 entries to FILE_INDEX**

Add this section to `FILE_INDEX.md` near the E01 artifacts:

```markdown
## Артефакты E01.5

| Файл | Назначение |
|---|---|
| [docs/superpowers/specs/2026-06-21-e015-kolla-lab-prototype-design.md](docs/superpowers/specs/2026-06-21-e015-kolla-lab-prototype-design.md) | Дизайн lab-only Kolla prototype. |
| [docs/execplans/E015-kolla-lab-prototype.md](docs/execplans/E015-kolla-lab-prototype.md) | Evidence по build/push/deploy/smoke/rollback E01.5. |
| [deploy/kolla/](deploy/kolla/) | Kolla Build templates and lab deployment prototype. |
| [tests/test_e015_kolla_layout.py](tests/test_e015_kolla_layout.py) | Static contract tests for E01.5 layout and safety boundaries. |
```

- [ ] **Step 2: Update current-state**

Add a concise E01.5 section to `docs/generated/current-state.md`:

```markdown
## E01.5 Kolla lab prototype state

E01.5 adds a lab-only Kolla-shaped build and deployment prototype:

- custom Kolla Build templates under `deploy/kolla/docker/`;
- test registry flow targeting `192.168.10.15:5000`;
- single-node AIO deploy, smoke and rollback playbooks for `192.168.10.14`;
- exactly two Dawn custom images: `cloud-ui-backend` and `cloud-ui-frontend`.

This is not full E09 acceptance. Three-node HA rollout, production HAProxy/TLS, SBOM/scan/digest evidence and hardening remain deferred to E09.
```

- [ ] **Step 3: Run final local checks**

Run:

```bash
backend/.venv/bin/python -m pytest -q tests/test_e015_kolla_layout.py
make lint
make typecheck
make test
./scripts/secret-scan.sh
git diff --check
```

Expected:

- E01.5 layout tests pass;
- existing backend/frontend lint/typecheck/test pass;
- secret scan has no findings;
- whitespace check has no findings.

- [ ] **Step 4: Commit docs index and current state**

Run:

```bash
git add FILE_INDEX.md docs/generated/current-state.md
git commit -m "docs: update E01.5 project index"
```

Expected: commit succeeds.

- [ ] **Step 5: Push branch**

Run:

```bash
git push origin feature/e015-kolla-prototype
```

Expected: branch updates on GitHub.

---

## Final Review Checklist

- [ ] Only test inventory paths and example vars are committed.
- [ ] No real passwords, tokens, private keys, `clouds.yaml`, openrc or production URLs are committed.
- [ ] `cloud-ui-backend` and `cloud-ui-frontend` are the only custom Dawn images.
- [ ] API, worker, events and migration use the backend image.
- [ ] Rollback removes custom containers and does not remove OpenStack/Kolla service containers.
- [ ] E01.5 docs avoid claiming full E09, HA, hardening, SBOM, scan or DKB closure.
- [ ] Final branch is pushed to GitHub.
