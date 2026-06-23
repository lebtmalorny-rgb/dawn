from __future__ import annotations

import re
import tomllib
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
PINNED_FROM_PATTERN = re.compile(
    r"^FROM\s+[\w./:-]+@sha256:[0-9a-f]{64}(?:\s+AS\s+[\w-]+)?$",
    re.IGNORECASE,
)


def _read(relative_path: str) -> str:
    return (REPO_ROOT / relative_path).read_text(encoding="utf-8")


def _from_lines(relative_path: str) -> list[str]:
    return [
        line.strip()
        for line in _read(relative_path).splitlines()
        if line.strip().upper().startswith("FROM ")
    ]


def test_makefile_exposes_reproducible_sbom_gate() -> None:
    makefile = _read("Makefile")

    assert re.search(r"^\.PHONY:.*\bsbom\b", makefile, re.MULTILINE)
    assert re.search(r"^sbom:\s+build\b", makefile, re.MULTILINE)
    assert "./scripts/generate-sbom.sh" in makefile


def test_runtime_dockerfiles_pin_base_images_by_digest() -> None:
    for dockerfile in ("backend/Dockerfile", "frontend/Dockerfile"):
        from_lines = _from_lines(dockerfile)
        assert from_lines, dockerfile
        for line in from_lines:
            assert PINNED_FROM_PATTERN.match(line), line


def test_dependency_manifests_are_locked_or_exactly_pinned() -> None:
    frontend_lock = REPO_ROOT / "frontend" / "package-lock.json"
    assert frontend_lock.exists()
    assert '"lockfileVersion"' in frontend_lock.read_text(encoding="utf-8")

    pyproject = tomllib.loads(_read("backend/pyproject.toml"))
    for dependency in pyproject["project"]["dependencies"]:
        assert "==" in dependency, dependency
    for dependency in pyproject["project"]["optional-dependencies"]["dev"]:
        assert "==" in dependency, dependency


def test_supply_chain_evidence_records_scope_and_residual_gaps() -> None:
    evidence_path = REPO_ROOT / "docs" / "generated" / "e08-supply-chain.md"
    assert evidence_path.exists()

    evidence = evidence_path.read_text(encoding="utf-8")
    assert "Docker SBOM" in evidence
    assert "cloud-ui-backend:dev" in evidence
    assert "cloud-ui-frontend:dev" in evidence
    assert "ДКБ-69" in evidence
    assert "ДКБ-70" in evidence
    assert "not claim" in evidence
    assert "registry push" in evidence
    assert "image signing" in evidence
