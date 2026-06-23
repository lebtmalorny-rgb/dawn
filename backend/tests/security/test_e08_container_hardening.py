from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[3]
APP_SERVICES = ("api", "worker", "events", "frontend")
FORBIDDEN_MOUNT_TARGETS = {
    "/",
    "/var/run/docker.sock",
    "/run/podman/podman.sock",
}


def _read(relative_path: str) -> str:
    return (REPO_ROOT / relative_path).read_text(encoding="utf-8")


def _compose() -> dict[str, Any]:
    payload = yaml.safe_load(_read("compose.yaml"))
    assert isinstance(payload, dict)
    return payload


def _service(name: str) -> dict[str, Any]:
    services = _compose()["services"]
    service = services[name]
    assert isinstance(service, dict)
    return service


def _stage_lines(dockerfile: str, stage_name: str) -> list[str]:
    lines = dockerfile.splitlines()
    stage_start = next(
        index
        for index, line in enumerate(lines)
        if line.upper().startswith("FROM ") and line.rstrip().endswith(f" AS {stage_name}")
    )
    next_stage = next(
        (
            index
            for index, line in enumerate(lines[stage_start + 1 :], start=stage_start + 1)
            if line.upper().startswith("FROM ")
        ),
        len(lines),
    )
    return lines[stage_start:next_stage]


def _tmpfs_options(entry: str) -> set[str]:
    _, separator, option_string = entry.partition(":")
    assert separator, entry
    return set(option_string.split(","))


def test_portal_app_services_drop_privileges_and_use_read_only_rootfs() -> None:
    for name in APP_SERVICES:
        service = _service(name)

        assert service.get("read_only") is True, name
        assert service.get("cap_drop") == ["ALL"], name
        assert "no-new-privileges:true" in service.get("security_opt", []), name
        assert service.get("privileged") is not True, name


def test_portal_app_services_have_only_controlled_writable_paths() -> None:
    for name in APP_SERVICES:
        service = _service(name)
        tmpfs = service.get("tmpfs")
        assert isinstance(tmpfs, list) and tmpfs, name
        assert all(isinstance(path, str) and path.startswith("/") for path in tmpfs), name

        for volume in service.get("volumes", []):
            assert isinstance(volume, str)
            source, _, target = volume.partition(":")
            assert source not in FORBIDDEN_MOUNT_TARGETS
            assert target not in FORBIDDEN_MOUNT_TARGETS


def test_frontend_writable_tmpfs_paths_are_owned_by_nginx_runtime_user() -> None:
    tmpfs = _service("frontend")["tmpfs"]
    assert isinstance(tmpfs, list)
    entries_by_path = {entry.split(":", 1)[0]: entry for entry in tmpfs}

    for path in ("/var/cache/nginx", "/var/run"):
        options = _tmpfs_options(entries_by_path[path])
        assert "uid=101" in options, path
        assert "gid=101" in options, path


def test_backend_runtime_dockerfile_is_non_root_and_installs_only_wheels() -> None:
    dockerfile = _read("backend/Dockerfile")
    runtime = "\n".join(_stage_lines(dockerfile, "runtime"))

    assert "FROM python:3.11-slim AS builder" in dockerfile
    assert "FROM python:3.11-slim AS runtime" in dockerfile
    assert "python -m pip wheel --no-cache-dir --wheel-dir /wheels ." in dockerfile
    assert "COPY --from=builder /wheels /wheels" in runtime
    assert "USER cloudui" in runtime

    for forbidden in (".env", "tests", ".venv", "node_modules"):
        assert forbidden not in runtime


def test_frontend_runtime_dockerfile_excludes_node_toolchain() -> None:
    dockerfile = _read("frontend/Dockerfile")
    runtime = "\n".join(_stage_lines(dockerfile, "runtime"))
    normalized_runtime = runtime.lower()

    assert "FROM node:24-alpine AS build" in dockerfile
    assert "FROM nginxinc/nginx-unprivileged:1.27-alpine AS runtime" in dockerfile
    assert "COPY --from=build /app/dist /usr/share/nginx/html" in runtime
    assert "nginx-unprivileged" in normalized_runtime or "USER 101" in runtime
    assert "npm " not in normalized_runtime
    assert "node " not in normalized_runtime
    assert "node_modules" not in normalized_runtime
