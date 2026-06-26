# E09 Live Reconfigure Bundle Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a repository-side E09 live reconfigure preflight bundle that validates test-stand inputs without executing a live Kolla deploy/reconfigure.

**Architecture:** The bundle is static and fail-closed: a localhost Ansible preflight playbook validates marker, rollback window, image digest shape and runtime DB/MQ inputs, then imports only `cloud_ui` role validation. Example vars use placeholders/env lookups only. Tests enforce that the bundle does not run shell, `kolla-ansible`, `kolla_container`, DB/MQ mutations or commit secrets.

**Tech Stack:** Python `pytest` + `PyYAML` static contract tests; Ansible YAML playbook and example vars; Markdown evidence/docs.

---

## Files

- Create: `tests/test_e09_live_reconfigure_bundle.py`
- Create: `deploy/kolla/ansible/playbooks/cloud-ui-preflight.yml`
- Create: `deploy/kolla/ansible/examples/cloud-ui-vars.yml.example`
- Create: `docs/generated/e09-live-reconfigure-bundle.md`
- Create: `docs/execplans/E09-live-reconfigure-bundle.md`
- Modify: `deploy/kolla/ansible/README.md`
- Modify: `docs/11_DKB_TRACEABILITY.md`
- Modify: `docs/generated/risk-register.md`

## Task 1: RED Contract Tests

**Files:**
- Create: `tests/test_e09_live_reconfigure_bundle.py`

- [ ] **Step 1: Write the failing test file**

Create `tests/test_e09_live_reconfigure_bundle.py`:

```python
import re
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]

PLAYBOOK = "deploy/kolla/ansible/playbooks/cloud-ui-preflight.yml"
VALIDATE_TASKS = "deploy/kolla/ansible/roles/cloud_ui/tasks/validate.yml"
EXAMPLE_VARS = "deploy/kolla/ansible/examples/cloud-ui-vars.yml.example"
EVIDENCE = "docs/generated/e09-live-reconfigure-bundle.md"
EXECPLAN = "docs/execplans/E09-live-reconfigure-bundle.md"
README = "deploy/kolla/ansible/README.md"
TRACEABILITY = "docs/11_DKB_TRACEABILITY.md"
RISK_REGISTER = "docs/generated/risk-register.md"
TASK1_NEW_ARTIFACTS = [
    PLAYBOOK,
    VALIDATE_TASKS,
    EXAMPLE_VARS,
    EVIDENCE,
    EXECPLAN,
]
PREFLIGHT_SECTION_HEADING = "E09 live reconfigure preflight bundle"
RISK_ID = "R-069"
PREFLIGHT_ASSERTIONS = {
    "cloud_ui_test_stand | bool",
    "cloud_ui_rollback_window_open | bool",
    "cloud_ui_backend_image_digest is match('^sha256:[0-9a-f]{64}$')",
    "cloud_ui_frontend_image_digest is match('^sha256:[0-9a-f]{64}$')",
    "cloud_ui_database_url | length > 0",
    "cloud_ui_rabbitmq_url | length > 0",
}
SECRET_REFERENCE_MARKERS = {
    "cloud_ui_database_url",
    "cloud_ui_rabbitmq_url",
    "CLOUD_UI_DATABASE_URL",
    "CLOUD_UI_RABBITMQ_URL",
}
ZERO_SHA256_DIGEST = "sha256:0000000000000000000000000000000000000000000000000000000000000000"


def fixture_value(*parts: str) -> str:
    return "".join(parts)


def read_text(relative_path: str) -> str:
    return (ROOT / relative_path).read_text(encoding="utf-8")


def load_yaml(relative_path: str) -> Any:
    return yaml.safe_load(read_text(relative_path))


def load_task_list(relative_path: str) -> list[dict[str, Any]]:
    tasks = load_yaml(relative_path)
    assert isinstance(tasks, list)
    validated_tasks = []
    for task in tasks:
        assert isinstance(task, dict)
        validated_tasks.append(task)
    return validated_tasks


def load_play() -> dict[str, Any]:
    playbook = load_yaml(PLAYBOOK)
    assert isinstance(playbook, list)
    assert len(playbook) == 1
    play = playbook[0]
    assert isinstance(play, dict)
    return play


def load_tasks() -> list[dict[str, Any]]:
    tasks = load_play()["tasks"]
    assert isinstance(tasks, list)
    validated_tasks = []
    for task in tasks:
        assert isinstance(task, dict)
        validated_tasks.append(task)
    return validated_tasks


def playbook_assert_conditions() -> set[str]:
    conditions = set()
    for task in load_tasks():
        assert_args = task.get("ansible.builtin.assert")
        if not isinstance(assert_args, dict):
            continue
        task_conditions = assert_args.get("that", [])
        assert isinstance(task_conditions, list)
        for condition in task_conditions:
            assert isinstance(condition, str)
            conditions.add(condition)
    return conditions


def extract_markdown_section(relative_path: str, heading_text: str) -> str:
    lines = read_text(relative_path).splitlines()
    for start, line in enumerate(lines):
        match = re.match(r"^(#{1,6})\s+(.+?)\s*$", line)
        if not match or match.group(2).strip().lower() != heading_text.lower():
            continue

        heading_level = len(match.group(1))
        end = len(lines)
        for next_index in range(start + 1, len(lines)):
            next_match = re.match(r"^(#{1,6})\s+", lines[next_index])
            if next_match and len(next_match.group(1)) <= heading_level:
                end = next_index
                break
        return "\n".join(lines[start:end])

    raise AssertionError(f"{relative_path} missing section: {heading_text}")


def extract_risk_row(risk_id: str) -> str:
    for line in read_text(RISK_REGISTER).splitlines():
        if line.startswith(f"| {risk_id} |"):
            return line
    raise AssertionError(f"{RISK_REGISTER} missing row: {risk_id}")


def task1_contract_text_blocks() -> dict[str, str]:
    return {
        **{relative_path: read_text(relative_path) for relative_path in TASK1_NEW_ARTIFACTS},
        f"{README}#{PREFLIGHT_SECTION_HEADING}": extract_markdown_section(
            README,
            PREFLIGHT_SECTION_HEADING,
        ),
        f"{TRACEABILITY}#{PREFLIGHT_SECTION_HEADING}": extract_markdown_section(
            TRACEABILITY,
            PREFLIGHT_SECTION_HEADING,
        ),
        f"{RISK_REGISTER}#{RISK_ID}": extract_risk_row(RISK_ID),
    }


def nested_strings(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        strings = []
        for item_key, item_value in value.items():
            strings.extend(nested_strings(item_key))
            strings.extend(nested_strings(item_value))
        return strings
    if isinstance(value, list):
        strings = []
        for item in value:
            strings.extend(nested_strings(item))
        return strings
    return []


def task_references_secret_input(task: dict[str, Any]) -> bool:
    task_references = "\n".join(nested_strings(task))
    return any(marker in task_references for marker in SECRET_REFERENCE_MARKERS)


def test_e09_live_reconfigure_bundle_files_exist() -> None:
    for relative_path in [
        PLAYBOOK,
        VALIDATE_TASKS,
        EXAMPLE_VARS,
        EVIDENCE,
        EXECPLAN,
    ]:
        assert (ROOT / relative_path).exists(), relative_path


def test_preflight_playbook_is_local_and_imports_only_validation() -> None:
    play = load_play()
    allowed_play_keys = {"name", "hosts", "connection", "gather_facts", "vars", "tasks"}
    unsafe_play_keys = {
        "become",
        "collections",
        "environment",
        "handlers",
        "import_playbook",
        "post_tasks",
        "pre_tasks",
        "roles",
        "strategy",
        "vars_files",
    }

    assert set(play) <= allowed_play_keys
    assert unsafe_play_keys.isdisjoint(play)
    assert play["hosts"] == "localhost"
    assert play["connection"] == "local"
    assert play["gather_facts"] is False
    assert play["vars"] == {"cloud_ui_enabled": True}

    tasks = load_tasks()
    conditions = playbook_assert_conditions()
    assert conditions == PREFLIGHT_ASSERTIONS

    import_tasks = [task for task in tasks if "ansible.builtin.import_role" in task]
    assert len(import_tasks) == 1
    import_args = import_tasks[0]["ansible.builtin.import_role"]
    assert import_args == {"name": "cloud_ui", "tasks_from": "validate"}


def test_preflight_playbook_tasks_are_validation_only_modules() -> None:
    tasks = load_tasks()
    allowed_task_keys = {
        "name",
        "no_log",
        "ansible.builtin.assert",
        "ansible.builtin.import_role",
    }
    allowed_action_keys = {"ansible.builtin.assert", "ansible.builtin.import_role"}

    import_tasks = []
    for task in tasks:
        assert set(task) <= allowed_task_keys
        action_keys = [key for key in task if key in allowed_action_keys]
        assert len(action_keys) == 1
        if action_keys[0] == "ansible.builtin.import_role":
            import_tasks.append(task)

    assert len(import_tasks) == 1
    assert import_tasks[0]["ansible.builtin.import_role"] == {
        "name": "cloud_ui",
        "tasks_from": "validate",
    }


def test_preflight_runtime_secret_assertion_is_no_log() -> None:
    tasks = load_tasks()
    secret_assertions = {
        "cloud_ui_database_url | length > 0",
        "cloud_ui_rabbitmq_url | length > 0",
    }
    secret_assert_tasks = []
    for task in tasks:
        assert_args = task.get("ansible.builtin.assert")
        if not isinstance(assert_args, dict):
            continue
        assertions = assert_args.get("that", [])
        if isinstance(assertions, list) and secret_assertions.issubset(assertions):
            secret_assert_tasks.append(task)

    assert len(secret_assert_tasks) == 1
    assert secret_assert_tasks[0].get("no_log") is True

    for task in tasks:
        if task_references_secret_input(task):
            assert task.get("no_log") is True


def test_imported_role_validation_tasks_are_assert_only_and_secret_safe() -> None:
    tasks = load_task_list(VALIDATE_TASKS)
    assert tasks

    allowed_task_keys = {"name", "no_log", "ansible.builtin.assert"}
    for task in tasks:
        assert set(task) <= allowed_task_keys
        action_keys = [key for key in task if key == "ansible.builtin.assert"]
        assert action_keys == ["ansible.builtin.assert"]
        if task_references_secret_input(task):
            assert task.get("no_log") is True


def test_preflight_bundle_does_not_execute_live_or_mutating_commands() -> None:
    forbidden_patterns = [
        r"(?im)^\s*(?:[-*]\s+)?(?:`|\$|sudo\s+)?kolla-ansible"
        r"(?:\s+(?!deploy\b|reconfigure\b|destroy\b|upgrade\b)\S+)*"
        r"\s+(?:deploy|reconfigure|destroy|upgrade)\b",
        r"(?im)^\s*(?:[-*]\s+)?(?:ansible\.builtin\.)?shell\s*:",
        r"(?im)^\s*(?:[-*]\s+)?(?:ansible\.builtin\.)?command\s*:",
        r"(?im)^\s*(?:[-*]\s+)?kolla_container\s*:",
        r"(?im)^\s*(?:[-*]\s+)?community\.mysql(?:\.[A-Za-z_]+)?\s*:",
        r"(?im)^\s*(?:[-*]\s+)?community\.rabbitmq(?:\.[A-Za-z_]+)?\s*:",
    ]

    for label, text in task1_contract_text_blocks().items():
        for pattern in forbidden_patterns:
            assert re.search(pattern, text) is None, label


def test_task1_artifacts_do_not_contain_secret_canaries_or_credential_urls() -> None:
    credential_url_patterns = [
        r"mysql\+pymysql://[^\s'\"/@:]+:[^\s'\"/@]+@",
        r"amqps?://[^\s'\"/@:]+:[^\s'\"/@]+@",
    ]

    for label, text in task1_contract_text_blocks().items():
        for forbidden in [
            fixture_value("admin", "123"),
            fixture_value("mysql+pymysql://", "cloud_ui", ":"),
            fixture_value("amqp://", "cloud_ui", ":"),
            fixture_value("BEGIN", " "),
            "clouds.yaml",
            "openrc",
        ]:
            assert forbidden not in text, label
        for pattern in credential_url_patterns:
            assert re.search(pattern, text) is None, label


def test_example_vars_are_placeholders_and_secret_safe() -> None:
    example = read_text(EXAMPLE_VARS)
    example_vars = load_yaml(EXAMPLE_VARS)
    assert isinstance(example_vars, dict)

    assert example_vars["cloud_ui_test_stand"] is True
    assert example_vars["cloud_ui_rollback_window_open"] is False
    assert example_vars["cloud_ui_enabled"] is True
    assert example_vars["cloud_ui_backend_image_digest"] == ZERO_SHA256_DIGEST
    assert example_vars["cloud_ui_frontend_image_digest"] == ZERO_SHA256_DIGEST
    assert re.match(
        r"^sha256:[0-9a-f]{64}$",
        example_vars["cloud_ui_backend_image_digest"],
    )
    assert re.match(
        r"^sha256:[0-9a-f]{64}$",
        example_vars["cloud_ui_frontend_image_digest"],
    )
    assert (
        example_vars["cloud_ui_database_url"]
        == "{{ lookup('ansible.builtin.env', 'CLOUD_UI_DATABASE_URL') }}"
    )
    assert (
        example_vars["cloud_ui_rabbitmq_url"]
        == "{{ lookup('ansible.builtin.env', 'CLOUD_UI_RABBITMQ_URL') }}"
    )

    for expected in [
        "cloud_ui_test_stand: true",
        "cloud_ui_rollback_window_open: false",
        "cloud_ui_enabled: true",
        "cloud_ui_backend_image_digest: \"sha256:",
        "cloud_ui_frontend_image_digest: \"sha256:",
        "lookup('ansible.builtin.env', 'CLOUD_UI_DATABASE_URL')",
        "lookup('ansible.builtin.env', 'CLOUD_UI_RABBITMQ_URL')",
    ]:
        assert expected in example

    for forbidden in [
        fixture_value("admin", "123"),
        fixture_value("mysql+pymysql://", "cloud_ui", ":"),
        fixture_value("amqp://", "cloud_ui", ":"),
        "BEGIN ",
        "clouds.yaml",
        "openrc",
        "production",
    ]:
        assert forbidden not in example


def test_docs_record_preflight_scope_and_pending_live_evidence() -> None:
    evidence = read_text(EVIDENCE)
    readme = extract_markdown_section(README, PREFLIGHT_SECTION_HEADING)
    traceability = extract_markdown_section(TRACEABILITY, PREFLIGHT_SECTION_HEADING)
    risk_row = extract_risk_row(RISK_ID)

    for text in (evidence, readme, traceability):
        assert "E09 live reconfigure preflight bundle" in text
        assert "preflight only" in text.lower()
        assert "runtime secret value" in text

    for text in (evidence, traceability):
        assert "pending_external_evidence" in text

    assert RISK_ID in risk_row
    assert "preflight bundle mistaken for deployment acceptance" in risk_row

    risk_ids = re.findall(r"^\| (R-\d{3}) \|", read_text(RISK_REGISTER), flags=re.MULTILINE)
    duplicate_ids = {risk_id for risk_id in risk_ids if risk_ids.count(risk_id) > 1}
    assert duplicate_ids == set()
```

- [ ] **Step 2: Run RED test**

Run:

```bash
UV_CACHE_DIR=/tmp/dawn-uv-cache UV_PYTHON_INSTALL_DIR=/tmp/dawn-uv-python UV_PROJECT_ENVIRONMENT=/tmp/dawn-e09-live-bundle-venv uv run --python 3.11 --project backend --extra dev pytest tests/test_e09_live_reconfigure_bundle.py -q
```

Expected: fails because the playbook, example vars and evidence do not exist.

## Task 2: Preflight Bundle Artifacts

**Files:**
- Create: `deploy/kolla/ansible/playbooks/cloud-ui-preflight.yml`
- Create: `deploy/kolla/ansible/examples/cloud-ui-vars.yml.example`

- [ ] **Step 1: Create playbook directory and example directory**

Run:

```bash
mkdir -p deploy/kolla/ansible/playbooks deploy/kolla/ansible/examples
```

- [ ] **Step 2: Add the preflight playbook**

Create `deploy/kolla/ansible/playbooks/cloud-ui-preflight.yml`:

```yaml
---
- name: Cloud UI live reconfigure preflight
  hosts: localhost
  connection: local
  gather_facts: false
  vars:
    cloud_ui_enabled: true
  tasks:
    - name: Validate Cloud UI test stand marker and rollback window
      ansible.builtin.assert:
        that:
          - cloud_ui_test_stand | bool
          - cloud_ui_rollback_window_open | bool
        fail_msg: "Cloud UI preflight requires approved test stand marker and open rollback window."

    - name: Validate Cloud UI digest-pinned images
      ansible.builtin.assert:
        that:
          - cloud_ui_backend_image_digest is match('^sha256:[0-9a-f]{64}$')
          - cloud_ui_frontend_image_digest is match('^sha256:[0-9a-f]{64}$')
        fail_msg: "Cloud UI preflight requires backend/frontend sha256 image digests."

    - name: Validate Cloud UI runtime secret inputs are present
      ansible.builtin.assert:
        that:
          - cloud_ui_database_url | length > 0
          - cloud_ui_rabbitmq_url | length > 0
        fail_msg: "Cloud UI preflight requires runtime DB/MQ URLs from the approved secret mechanism."
      no_log: true

    - name: Import Cloud UI role validation only
      ansible.builtin.import_role:
        name: cloud_ui
        tasks_from: validate
```

- [ ] **Step 3: Add example vars**

Create `deploy/kolla/ansible/examples/cloud-ui-vars.yml.example`:

```yaml
---
# Copy this file outside Git before live test-stand use.
# Do not commit the copied file if it contains real runtime URLs, credentials or host-specific data.

cloud_ui_test_stand: true
cloud_ui_rollback_window_open: false
cloud_ui_enabled: true

cloud_ui_backend_image_digest: "sha256:0000000000000000000000000000000000000000000000000000000000000000"
cloud_ui_frontend_image_digest: "sha256:0000000000000000000000000000000000000000000000000000000000000000"

cloud_ui_database_url: "{{ lookup('ansible.builtin.env', 'CLOUD_UI_DATABASE_URL') }}"
cloud_ui_rabbitmq_url: "{{ lookup('ansible.builtin.env', 'CLOUD_UI_RABBITMQ_URL') }}"
```

- [ ] **Step 4: Run bundle tests**

Run:

```bash
UV_CACHE_DIR=/tmp/dawn-uv-cache UV_PYTHON_INSTALL_DIR=/tmp/dawn-uv-python UV_PROJECT_ENVIRONMENT=/tmp/dawn-e09-live-bundle-venv uv run --python 3.11 --project backend --extra dev pytest tests/test_e09_live_reconfigure_bundle.py -q
```

Expected: only documentation/evidence assertions still fail.

## Task 3: Evidence And Traceability

**Files:**
- Create: `docs/generated/e09-live-reconfigure-bundle.md`
- Create: `docs/execplans/E09-live-reconfigure-bundle.md`
- Modify: `deploy/kolla/ansible/README.md`
- Modify: `docs/11_DKB_TRACEABILITY.md`
- Modify: `docs/generated/risk-register.md`

- [ ] **Step 1: Add generated evidence**

Create `docs/generated/e09-live-reconfigure-bundle.md`:

```markdown
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

The preflight imports only the role validation task path. It does not run `kolla-ansible`, create
containers, render runtime config, mutate MariaDB/RabbitMQ/Vault, execute migration, apply HAProxy or
perform rollback.

## Required live follow-up

Full E09 acceptance remains blocked until an explicitly approved test-stand run provides:

- copied bundle path and sanitized preflight output;
- approved non-committed vars file or environment injection for runtime secret values;
- Kolla role/config installation evidence on `192.168.10.15`;
- one-shot migration evidence;
- Kolla deploy/reconfigure/idempotency evidence;
- three-node/twelve-container inspection;
- HAProxy/TLS smoke;
- hardening inspection for non-root/read-only/caps/SELinux;
- rollback execution evidence.

## DKB scope

- ДКБ-55/56: the bundle validates that DB/MQ runtime inputs are supplied, but stores no runtime secret
  value. Rotation, owner approval and production SecMan evidence remain pending.
- ДКБ-65/69/70: no new image or container inspection evidence is created by preflight only.
- ДКБ-76/77/80: network/API registry evidence remains pending until live Kolla run and inspection.
- ДКБ-82: this adds operator documentation, not live rollback/deployment acceptance.
```

- [ ] **Step 2: Add ExecPlan**

Create `docs/execplans/E09-live-reconfigure-bundle.md`:

```markdown
# ExecPlan: E09 Live Reconfigure Preflight Bundle

## Goal

Create a repository-side preflight bundle for approved E09 test-stand live reconfigure preparation.

## Scope

This plan creates static Ansible/operator artifacts and tests. It does not run live Kolla deploy or
reconfigure.

## Progress

- [x] 2026-06-26: Design approved in
  `docs/superpowers/specs/2026-06-26-e09-live-reconfigure-bundle-design.md`.
- [ ] RED tests.
- [ ] Bundle artifacts.
- [ ] Evidence and traceability.
- [ ] Verification and review.

## Verification

- `UV_CACHE_DIR=/tmp/dawn-uv-cache UV_PYTHON_INSTALL_DIR=/tmp/dawn-uv-python UV_PROJECT_ENVIRONMENT=/tmp/dawn-e09-live-bundle-venv uv run --python 3.11 --project backend --extra dev pytest tests/test_e09_live_reconfigure_bundle.py tests/test_e09_reconfigure_rollback.py tests/test_e09_kolla_ansible_role.py -q`
- `UV_CACHE_DIR=/tmp/dawn-uv-cache UV_PYTHON_INSTALL_DIR=/tmp/dawn-uv-python UV_PROJECT_ENVIRONMENT=/tmp/dawn-e09-live-bundle-venv uv run --python 3.11 --project backend --extra dev ruff check tests/test_e09_live_reconfigure_bundle.py`
- `./scripts/secret-scan.sh`
- `git diff --check`

## Rollback

Revert this repository commit. No remote host, registry, database, queue, Vault path or production
credential is changed by this slice.
```

- [ ] **Step 3: Update README**

Append this section to `deploy/kolla/ansible/README.md`:

```markdown
## E09 live reconfigure preflight bundle

`playbooks/cloud-ui-preflight.yml` is an E09 live reconfigure preflight bundle for approved test
stand preparation. It is preflight only: it validates the test marker, rollback window, image digest
inputs and runtime DB/MQ secret inputs, then imports `cloud_ui` role validation with
`tasks_from: validate`.

The preflight does not run live `kolla-ansible` deploy/reconfigure, start containers, render runtime
config files, run migrations, mutate DB/MQ/Vault or claim E09 acceptance. A non-committed vars file
must be created from `examples/cloud-ui-vars.yml.example`, and runtime secret values must come from
the approved secret mechanism. No runtime secret value belongs in Git.

Evidence: `docs/generated/e09-live-reconfigure-bundle.md`.
```

- [ ] **Step 4: Update DKB traceability**

Add a short section to `docs/11_DKB_TRACEABILITY.md` after the E09.8 section:

```markdown
## Обновление требований 2026-06-26: E09 live reconfigure preflight bundle

The E09 live reconfigure preflight bundle adds a repository-side operator path for approved test
stand validation before any live mutation. It is preflight only and keeps live deploy/reconfigure,
migration, 12-container inspection, HAProxy/TLS smoke and rollback as `pending_external_evidence`.

- ДКБ-55/56: validates that runtime DB/MQ inputs are supplied by the approved secret mechanism without
  committing any runtime secret value. Rotation and production SecMan evidence remain open.
- ДКБ-65/69/70/76/77/80/82: no live container, registry, network, SELinux or rollback proof is created
  by this slice.

Evidence: `tests/test_e09_live_reconfigure_bundle.py`,
`deploy/kolla/ansible/playbooks/cloud-ui-preflight.yml`,
`deploy/kolla/ansible/examples/cloud-ui-vars.yml.example` and
`docs/generated/e09-live-reconfigure-bundle.md`.
```

- [ ] **Step 5: Update risk register**

Append a new row to `docs/generated/risk-register.md` with ID `R-069`:

```markdown
| R-069 | E09 live preflight bundle mistaken for deployment acceptance | The preflight bundle validates inputs and role validation locally, but does not install the custom role on the Ansible host, run Kolla deploy/reconfigure, execute migration, inspect twelve live containers, validate HAProxy/TLS or test rollback. | Keep E09.8 live evidence rows pending until user-approved test-stand commands produce sanitized evidence. | E09 |
```

- [ ] **Step 6: Run tests**

Run:

```bash
UV_CACHE_DIR=/tmp/dawn-uv-cache UV_PYTHON_INSTALL_DIR=/tmp/dawn-uv-python UV_PROJECT_ENVIRONMENT=/tmp/dawn-e09-live-bundle-venv uv run --python 3.11 --project backend --extra dev pytest tests/test_e09_live_reconfigure_bundle.py -q
```

Expected: all tests in the new file pass.

## Task 4: Verification And Commit

**Files:**
- Verify all changed files.

- [ ] **Step 1: Run relevant tests**

Run:

```bash
UV_CACHE_DIR=/tmp/dawn-uv-cache UV_PYTHON_INSTALL_DIR=/tmp/dawn-uv-python UV_PROJECT_ENVIRONMENT=/tmp/dawn-e09-live-bundle-venv uv run --python 3.11 --project backend --extra dev pytest tests/test_e09_live_reconfigure_bundle.py tests/test_e09_reconfigure_rollback.py tests/test_e09_kolla_ansible_role.py -q
```

Expected: all selected tests pass.

- [ ] **Step 2: Run Ruff**

Run:

```bash
UV_CACHE_DIR=/tmp/dawn-uv-cache UV_PYTHON_INSTALL_DIR=/tmp/dawn-uv-python UV_PROJECT_ENVIRONMENT=/tmp/dawn-e09-live-bundle-venv uv run --python 3.11 --project backend --extra dev ruff check tests/test_e09_live_reconfigure_bundle.py
```

Expected: `All checks passed!`

- [ ] **Step 3: Run secret scan**

Run:

```bash
./scripts/secret-scan.sh
```

Expected: exit 0, no findings.

- [ ] **Step 4: Run diff check**

Run:

```bash
git diff --check
```

Expected: exit 0.

- [ ] **Step 5: Self-review diff**

Run:

```bash
git diff --stat
git diff -- deploy/kolla/ansible/playbooks/cloud-ui-preflight.yml deploy/kolla/ansible/examples/cloud-ui-vars.yml.example tests/test_e09_live_reconfigure_bundle.py docs/generated/e09-live-reconfigure-bundle.md
```

Confirm the diff contains no runtime secret value, no production approval claim, no live mutation command and no E09 acceptance claim.

- [ ] **Step 6: Commit**

Run:

```bash
git add deploy/kolla/ansible/playbooks/cloud-ui-preflight.yml deploy/kolla/ansible/examples/cloud-ui-vars.yml.example tests/test_e09_live_reconfigure_bundle.py docs/generated/e09-live-reconfigure-bundle.md docs/execplans/E09-live-reconfigure-bundle.md deploy/kolla/ansible/README.md docs/11_DKB_TRACEABILITY.md docs/generated/risk-register.md
git commit -m "deploy: add E09 live reconfigure preflight bundle"
```

Expected: one commit with only the planned files.
