from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def copy_secret_scan(tmp_path: Path) -> Path:
    scripts_dir = tmp_path / "scripts"
    scripts_dir.mkdir()
    script_path = scripts_dir / "secret-scan.sh"
    shutil.copy2(ROOT / "scripts" / "secret-scan.sh", script_path)
    return script_path


def run_secret_scan(tmp_path: Path) -> subprocess.CompletedProcess[str]:
    bash_path = shutil.which("bash")
    assert bash_path is not None
    return subprocess.run(  # noqa: S603 - test executes a copied repository script with no user input.
        [bash_path, "scripts/secret-scan.sh"],
        capture_output=True,
        cwd=tmp_path,
        text=True,
        check=False,
    )


def test_secret_scan_ignores_local_worktrees(tmp_path: Path) -> None:
    copy_secret_scan(tmp_path)
    password_key = "MYSQL_" + "PASSWORD"
    worktree_dir = tmp_path / ".worktrees" / "local-copy"
    worktree_dir.mkdir(parents=True)
    (worktree_dir / "compose.yaml").write_text(
        "services:\n"
        "  db:\n"
        "    environment:\n"
        f"      {password_key}: ${{{password_key}:-cloud_ui_dev}}\n",
        encoding="utf-8",
    )

    result = run_secret_scan(tmp_path)

    assert result.returncode == 0, result.stdout + result.stderr


def test_secret_scan_still_reports_regular_secret(tmp_path: Path) -> None:
    copy_secret_scan(tmp_path)
    password_key = "MYSQL_" + "PASSWORD"
    Path(tmp_path / "unsafe.env").write_text(f"{password_key}=not_allowed\n", encoding="utf-8")

    result = run_secret_scan(tmp_path)

    assert result.returncode == 1
    assert "unsafe.env" in result.stdout


def test_secret_scan_allows_cloud_ui_ansible_vault_references(tmp_path: Path) -> None:
    copy_secret_scan(tmp_path)
    task_dir = (
        tmp_path
        / "deploy"
        / "kolla"
        / "ansible"
        / "roles"
        / "cloud_ui_provisioning"
        / "tasks"
    )
    task_dir.mkdir(parents=True)
    (task_dir / "database.yml").write_text(
        "---\n"
        "- name: Create Cloud UI runtime database user\n"
        "  community.mysql.mysql_user:\n"
        "    login_password: \"{{ cloud_ui_mariadb_admin_password | default(omit) }}\"\n"
        "    password: \"{{ cloud_ui_mariadb_runtime_secret.secret.password }}\"\n"
        "  no_log: true\n",
        encoding="utf-8",
    )
    (task_dir / "rabbitmq.yml").write_text(
        "---\n"
        "- name: Create Cloud UI RabbitMQ user\n"
        "  community.rabbitmq.rabbitmq_user:\n"
        "    password: \"{{ cloud_ui_rabbitmq_runtime_secret.secret.password }}\"\n"
        "    update_password: always\n"
        "  no_log: true\n",
        encoding="utf-8",
    )

    result = run_secret_scan(tmp_path)

    assert result.returncode == 0, result.stdout + result.stderr
