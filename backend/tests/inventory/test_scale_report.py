from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType


def test_generated_scale_report_contains_counts_success_and_bounded_queries() -> None:
    from cloud_ui.inventory.scale_report import ScaleProfile, generate_scale_report

    report = generate_scale_report(
        ScaleProfile(
            instance_count=60,
            hypervisor_count=8,
            page_size=10,
            max_page_size=20,
            sample_iterations=3,
        )
    )

    assert report.success is True
    assert report.dataset.instance_count == 60
    assert report.dataset.hypervisor_count == 8
    assert report.sync.status == "success"
    assert report.sync.instance_count == 60
    assert report.sync.hypervisor_count == 8
    assert report.sync.elapsed_seconds >= 0

    scenario_names = {scenario.name for scenario in report.scenarios}
    assert scenario_names == {
        "instances_default_page",
        "instances_filtered_project_status",
        "hypervisors_default_page",
        "hypervisors_filtered_service_status_az",
    }
    assert all(scenario.page_size == 10 for scenario in report.scenarios)
    assert all(scenario.returned_count <= 10 for scenario in report.scenarios)
    assert all(scenario.p95_seconds >= 0 for scenario in report.scenarios)
    assert all(scenario.query_count_max <= 6 for scenario in report.scenarios)
    assert all(scenario.query_count_p95 <= 6 for scenario in report.scenarios)
    assert report.peak_memory_mib > 0


def test_scale_report_contains_explain_summaries() -> None:
    from cloud_ui.inventory.scale_report import ScaleProfile, generate_scale_report

    report = generate_scale_report(
        ScaleProfile(
            instance_count=30,
            hypervisor_count=5,
            page_size=5,
            max_page_size=20,
            sample_iterations=2,
        )
    )

    assert all(scenario.explain_summary for scenario in report.scenarios)
    assert all(
        any("instances" in line or "hypervisors" in line for line in scenario.explain_summary)
        for scenario in report.scenarios
    )


def test_markdown_report_is_sanitized_and_marks_scope(tmp_path: Path) -> None:
    from cloud_ui.inventory.scale_report import ScaleProfile, generate_scale_report

    output_path = tmp_path / "scale-report.md"
    report = generate_scale_report(
        ScaleProfile(
            instance_count=20,
            hypervisor_count=4,
            page_size=5,
            max_page_size=20,
            sample_iterations=2,
        ),
        output_path=output_path,
    )

    text = output_path.read_text(encoding="utf-8")
    assert report.success is True
    assert "E04.6 Synthetic scale report" in text
    assert "not production MariaDB/HA evidence" in text
    assert "synthetic/local evidence only" in text
    assert "instances: 20" in text
    assert "hypervisors: 4" in text

    forbidden_markers = (
        "OS_" + "PASSWORD",
        "auth_" + "token",
        "application_credential_" + "secret",
        "X-Auth-" + "Token",
        "BEGIN " + "PRIVATE KEY",
        "clouds.yaml",
        "openrc",
        "mysql+pymysql://",
        "amqp://",
        "https://",
    )
    for marker in forbidden_markers:
        assert marker not in text


def test_scale_report_cli_writes_tiny_profile(tmp_path: Path) -> None:
    module = _load_scale_report_script()
    output_path = tmp_path / "cli-scale-report.md"

    exit_code = module.main(
        [
            "--instances",
            "12",
            "--hypervisors",
            "3",
            "--page-size",
            "4",
            "--max-page-size",
            "20",
            "--iterations",
            "2",
            "--output",
            str(output_path),
        ]
    )

    assert exit_code == 0
    assert output_path.exists()
    assert "instances: 12" in output_path.read_text(encoding="utf-8")


def _load_scale_report_script() -> ModuleType:
    script_path = Path(__file__).resolve().parents[3] / "scripts" / "e04_scale_report.py"
    spec = importlib.util.spec_from_file_location("e04_scale_report", script_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
