from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
SECURITY_REVIEW = REPO_ROOT / "docs" / "generated" / "e08-security-review.md"

REQUIRED_HEADINGS = [
    "# Security review: E08 hardening",
    "## Архитектурное изменение",
    "## Проверенные угрозы",
    "## Findings",
    "## Проверки",
    "## External controls/gaps",
    "## Решение review",
]

REQUIRED_THREATS = [
    "Auth bypass/IDOR",
    "Session/CSRF/XSS",
    "Secret/token leakage",
    "Injection/SSRF",
    "Workflow/code execution",
    "Retry/idempotency",
    "Audit tampering/loss",
    "Container/host boundary",
    "Supply chain",
    "Availability/DoS",
]

REQUIRED_CHECKS = [
    "Negative RBAC/IDOR",
    "CSRF/session",
    "Canary secret redaction",
    "No credentials in browser/image/log",
    "Workflow allowlist/schema",
    "Retry/idempotency/lost response",
    "Audit delivery/heartbeat",
    "Dependency/image scan",
    "SELinux/container privileges",
    "DKB traceability updated",
]


def _read_review() -> str:
    assert SECURITY_REVIEW.exists(), f"missing E08.8 security review: {SECURITY_REVIEW}"
    return SECURITY_REVIEW.read_text(encoding="utf-8")


def test_e08_security_review_uses_required_template_sections() -> None:
    text = _read_review()

    for heading in REQUIRED_HEADINGS:
        assert heading in text
    for threat in REQUIRED_THREATS:
        assert threat in text
    for check in REQUIRED_CHECKS:
        assert f"- [x] {check}" in text


def test_e08_security_review_records_release_decision_and_no_unresolved_highs() -> None:
    text = _read_review()

    assert "Decision: Approved with conditions" in text
    assert "Codex is not the final compliance approval authority" in text
    assert "Unresolved critical/high findings: 0" in text
    assert "Critical" in text
    assert "High" in text
    assert "ДКБ-69" in text
    assert "not closed" in text

    forbidden_overclaims = [
        "fully compliant",
        "formal approval granted",
        "ДКБ-69 closed",
    ]
    for phrase in forbidden_overclaims:
        assert phrase not in text


def test_e08_security_review_links_evidence_and_external_gaps() -> None:
    text = _read_review()

    for required in [
        "docs/generated/e08-threat-model.md",
        "docs/generated/tls-matrix.md",
        "docs/generated/e08-vault-lab-runbook.md",
        "docs/generated/e08-session-token-protection.md",
        "docs/generated/e08-container-hardening.md",
        "docs/generated/e08-supply-chain.md",
        "docs/generated/e08-dkb-gaps-waivers.md",
        "docs/generated/risk-register.md",
    ]:
        assert required in text

    for gap in ["IAM/PAM", "PKI/mTLS", "SIEM", "SecMan", "SELinux", "registry/signing", "storage"]:
        assert gap in text
