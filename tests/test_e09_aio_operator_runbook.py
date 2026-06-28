from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNBOOK = ROOT / "docs/generated/e09-aio-operator-runbook.md"


def test_aio_operator_runbook_records_safe_baseline_scope() -> None:
    assert RUNBOOK.exists()
    runbook = RUNBOOK.read_text(encoding="utf-8")
    normalized = runbook.lower()

    for expected in [
        "Stage: E09 AIO operator baseline",
        "all-in-one",
        "not full E09 acceptance",
        "three-node rollout is paused",
        "/etc/kolla/all-in-one",
        "192.168.10.15",
        "openstack-aio",
        "run-cloud-ui-aio-kolla.py preflight",
        "run-cloud-ui-aio-kolla.py reconfigure",
        "run-cloud-ui-aio-kolla.py reconfigure-no-migration",
        "cloud-ui db-upgrade --check",
        "cloud-ui db-upgrade",
        "curl -4",
        "/api/v1/health/ready",
        "/api/v1/session",
        "/root/cloud-ui-aio-rollback-20260628T122556Z",
        "digest availability",
        "no runtime secret value",
    ]:
        assert expected in runbook

    for forbidden in [
        "mysql+pymysql://",
        "amqp://",
        "admin" + "123",
        "password:",
        "private_key",
        "token:",
    ]:
        assert forbidden not in normalized


def test_aio_operator_runbook_is_linked_from_dkb_and_risk_register() -> None:
    traceability = (ROOT / "docs/11_DKB_TRACEABILITY.md").read_text(encoding="utf-8")
    risk_register = (ROOT / "docs/generated/risk-register.md").read_text(encoding="utf-8")
    current_state = (ROOT / "docs/generated/current-state.md").read_text(encoding="utf-8")

    for document in (traceability, risk_register, current_state):
        assert "docs/generated/e09-aio-operator-runbook.md" in document

    assert "AIO operator baseline" in traceability
    assert "AIO operator baseline mistaken for full E09 acceptance" in risk_register
