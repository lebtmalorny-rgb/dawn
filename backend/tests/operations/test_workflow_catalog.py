from __future__ import annotations

import pytest

from cloud_ui.operations.catalog import (
    WorkflowDefinitionNotFound,
    build_builtin_workflow_catalog,
    compute_definition_checksum,
)
from cloud_ui.operations.input_validation import InputValidationError, validate_json_input


def test_builtin_catalog_contains_maintenance_host_precheck_definition() -> None:
    catalog = build_builtin_workflow_catalog(environment="local")

    definition = catalog.get_definition("maintenance-host-precheck", "1.0.0")

    assert definition.workflow_key == "maintenance-host-precheck"
    assert definition.version == "1.0.0"
    assert definition.target_type == "host"
    assert definition.mistral_workflow_name == "portal.maintenance_host_precheck.v1"
    assert definition.required_capability == "workflow.execute.maintenance-host"
    assert definition.risk_level == "low"
    assert definition.approval_mode == "none"
    assert definition.cancel_policy == "best_effort"
    assert definition.enabled is True
    assert definition.enabled_environments == ("local", "test")
    assert definition.checksum == compute_definition_checksum(definition)
    assert len(definition.checksum) == 64
    assert "mistral_workflow_name" not in definition.input_schema_json["properties"]


def test_catalog_only_lists_enabled_definitions_for_current_environment() -> None:
    local_catalog = build_builtin_workflow_catalog(environment="local")
    production_catalog = build_builtin_workflow_catalog(environment="production")

    assert [item.workflow_key for item in local_catalog.list_definitions()] == [
        "maintenance-host-precheck"
    ]
    assert production_catalog.list_definitions() == []
    with pytest.raises(WorkflowDefinitionNotFound):
        production_catalog.get_definition("maintenance-host-precheck", "1.0.0")


def test_maintenance_precheck_input_schema_enforces_server_side_dry_run() -> None:
    catalog = build_builtin_workflow_catalog(environment="local")
    definition = catalog.get_definition("maintenance-host-precheck", "1.0.0")

    validated = validate_json_input(
        definition.input_schema_json,
        {"reason": "replace host firmware", "dry_run": True},
    )

    assert validated == {"reason": "replace host firmware", "dry_run": True}


def test_maintenance_precheck_input_rejects_arbitrary_workflow_fields() -> None:
    catalog = build_builtin_workflow_catalog(environment="local")
    definition = catalog.get_definition("maintenance-host-precheck", "1.0.0")

    with pytest.raises(InputValidationError) as exc_info:
        validate_json_input(
            definition.input_schema_json,
            {
                "reason": "replace host firmware",
                "dry_run": True,
                "mistral_workflow_name": "evil.workflow",
            },
        )

    assert exc_info.value.code == "additional_property"
    assert exc_info.value.path == "$.mistral_workflow_name"


def test_maintenance_precheck_input_requires_dry_run_true() -> None:
    catalog = build_builtin_workflow_catalog(environment="local")
    definition = catalog.get_definition("maintenance-host-precheck", "1.0.0")

    with pytest.raises(InputValidationError) as exc_info:
        validate_json_input(
            definition.input_schema_json,
            {"reason": "replace host firmware", "dry_run": False},
        )

    assert exc_info.value.code == "enum_mismatch"
    assert exc_info.value.path == "$.dry_run"
