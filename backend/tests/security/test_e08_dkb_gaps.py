from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
GAP_REGISTER = REPO_ROOT / "docs" / "generated" / "e08-dkb-gaps-waivers.md"

REQUIRED_COLUMNS = [
    "DKB code",
    "Gap status",
    "Reason",
    "Existing portal evidence",
    "Compensating controls",
    "Owner role",
    "Review/expiry",
    "Evidence required to close",
    "Release gate",
]

REQUIRED_DKB_CODES = [
    "ДКБ-07",
    "ДКБ-22.02",
    "ДКБ-48",
    "ДКБ-50",
    "ДКБ-55",
    "ДКБ-56",
    "ДКБ-65",
    "ДКБ-69",
    "ДКБ-72",
]

FORBIDDEN_STATUSES = {"closed", "compliant", "approved", "done", "accepted"}


def _read_gap_register() -> str:
    assert GAP_REGISTER.exists(), f"missing E08.7 gap register: {GAP_REGISTER}"
    return GAP_REGISTER.read_text(encoding="utf-8")


def _parse_first_markdown_table(markdown: str) -> list[dict[str, str]]:
    table_lines = [line.strip() for line in markdown.splitlines() if line.strip().startswith("|")]
    assert len(table_lines) >= 3, "gap register must contain a markdown table"
    header = [cell.strip() for cell in table_lines[0].strip("|").split("|")]
    assert header == REQUIRED_COLUMNS

    rows: list[dict[str, str]] = []
    for line in table_lines[2:]:
        values = [cell.strip() for cell in line.strip("|").split("|")]
        if len(values) == len(header):
            rows.append(dict(zip(header, values, strict=True)))
    return rows


def test_e08_gap_register_has_required_dkb_rows_and_fields() -> None:
    rows = _parse_first_markdown_table(_read_gap_register())
    assert rows

    by_code = {row["DKB code"]: row for row in rows}
    for code in REQUIRED_DKB_CODES:
        assert code in by_code
        row = by_code[code]
        for column in REQUIRED_COLUMNS:
            assert row[column], f"{code} has empty {column}"

        assert "owner" not in row["Owner role"].lower()
        assert "2026-" in row["Review/expiry"]


def test_e08_gap_register_keeps_external_gaps_unapproved() -> None:
    rows = _parse_first_markdown_table(_read_gap_register())

    for row in rows:
        status_words = set(row["Gap status"].lower().replace("/", " ").split())
        assert status_words.isdisjoint(FORBIDDEN_STATUSES), row

    dkb69 = next(row for row in rows if row["DKB code"] == "ДКБ-69")
    combined = " ".join(dkb69.values())
    assert "formal waiver" in combined
    assert "Python" in combined
    assert "not closed" in combined
    assert "interpreter" in combined


def test_e08_gap_register_links_to_existing_security_evidence() -> None:
    text = _read_gap_register()

    for required in [
        "docs/generated/tls-matrix.md",
        "docs/generated/audit-source-map.md",
        "docs/generated/secret-inventory.md",
        "docs/generated/e08-container-hardening.md",
        "docs/generated/e08-supply-chain.md",
        "docs/generated/risk-register.md",
    ]:
        assert required in text

    assert "This draft is not an approval" in text
