from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
TLS_MATRIX = REPO_ROOT / "docs" / "generated" / "tls-matrix.md"
THREAT_MODEL = REPO_ROOT / "docs" / "generated" / "e08-threat-model.md"

REQUIRED_TLS_COLUMNS = [
    "Flow",
    "Minimum TLS",
    "mTLS",
    "CA/source",
    "Server identity check",
    "Client identity / authorization",
    "Rotation owner",
    "Negative test",
    "Stage",
    "Evidence",
    "Residual gap",
]

REQUIRED_TLS_FLOWS = [
    "Browser -> external VIP",
    "HAProxy -> frontend",
    "HAProxy -> API",
    "API/worker -> Keystone",
    "API/worker -> Nova",
    "API/worker -> Placement",
    "API/worker -> Mistral",
    "API/worker -> Watcher",
    "API/worker -> Masakari",
    "Masakari hostmonitor -> Consul",
    "API/worker -> Prometheus datasource",
    "Prometheus -> openstack-exporter/node_exporter",
    "Portal -> MariaDB",
    "Portal -> RabbitMQ",
    "Audit worker -> SIEM",
    "Deploy/runtime -> Vault (SecMan)",
    "Deploy -> registry",
]


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _parse_first_markdown_table(markdown: str) -> list[dict[str, str]]:
    table_lines = [line.strip() for line in markdown.splitlines() if line.strip().startswith("|")]
    assert len(table_lines) >= 3
    header = [cell.strip() for cell in table_lines[0].strip("|").split("|")]
    rows: list[dict[str, str]] = []
    for line in table_lines[2:]:
        values = [cell.strip() for cell in line.strip("|").split("|")]
        if len(values) == len(header):
            rows.append(dict(zip(header, values, strict=True)))
    return rows


def test_tls_matrix_has_required_e08_columns_and_flows() -> None:
    rows = _parse_first_markdown_table(_read(TLS_MATRIX))
    assert rows
    assert list(rows[0].keys()) == REQUIRED_TLS_COLUMNS

    by_flow = {row["Flow"]: row for row in rows}
    for flow in REQUIRED_TLS_FLOWS:
        assert flow in by_flow
        row = by_flow[flow]
        for column in REQUIRED_TLS_COLUMNS:
            assert row[column], f"{flow} has empty {column}"

    assert "corporate PKI" in by_flow["Browser -> external VIP"]["CA/source"]
    assert "client cert" in by_flow["Audit worker -> SIEM"]["Negative test"].lower()
    assert "mTLS pending" in by_flow["Deploy/runtime -> Vault (SecMan)"]["Residual gap"]


def test_e08_threat_model_records_required_sections_and_residual_risks() -> None:
    text = _read(THREAT_MODEL)

    for heading in [
        "## Assets",
        "## Trust Boundaries",
        "## Threats, Controls And Evidence",
        "## High Residual Risks",
    ]:
        assert heading in text

    for required in [
        "browser -> HAProxy/frontend/API",
        "API/worker -> Keystone/Nova/Placement/Mistral/Watcher/Masakari",
        "Audit worker -> SIEM",
        "Deploy/runtime -> Vault (SecMan)",
        "ДКБ-22.02",
        "ДКБ-69",
    ]:
        assert required in text


def test_e08_security_docs_do_not_contain_secret_canary_values() -> None:
    for path in [TLS_MATRIX, THREAT_MODEL]:
        assert "DKB_CANARY" not in _read(path)
