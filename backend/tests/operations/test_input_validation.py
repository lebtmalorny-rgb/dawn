from __future__ import annotations

import pytest

from cloud_ui.operations.input_validation import InputValidationError, validate_json_input


def test_json_input_validator_rejects_missing_required_field() -> None:
    with pytest.raises(InputValidationError) as exc_info:
        validate_json_input(_SCHEMA, {"dry_run": True})

    assert exc_info.value.code == "required"
    assert exc_info.value.path == "$.reason"


def test_json_input_validator_rejects_wrong_scalar_type() -> None:
    with pytest.raises(InputValidationError) as exc_info:
        validate_json_input(_SCHEMA, {"reason": 123, "dry_run": True})

    assert exc_info.value.code == "type_mismatch"
    assert exc_info.value.path == "$.reason"


def test_json_input_validator_rejects_string_length_bounds() -> None:
    with pytest.raises(InputValidationError) as exc_info:
        validate_json_input(_SCHEMA, {"reason": "", "dry_run": True})

    assert exc_info.value.code == "min_length"
    assert exc_info.value.path == "$.reason"


def test_json_input_validator_rejects_number_bounds() -> None:
    schema = {
        "type": "object",
        "additionalProperties": False,
        "required": ["attempts"],
        "properties": {"attempts": {"type": "integer", "minimum": 1, "maximum": 3}},
    }

    with pytest.raises(InputValidationError) as exc_info:
        validate_json_input(schema, {"attempts": 4})

    assert exc_info.value.code == "maximum"
    assert exc_info.value.path == "$.attempts"


def test_json_input_validator_fails_closed_for_unsupported_schema_keyword() -> None:
    schema = {
        "type": "object",
        "additionalProperties": False,
        "required": ["reason"],
        "properties": {"reason": {"type": "string", "pattern": ".*"}},
    }

    with pytest.raises(InputValidationError) as exc_info:
        validate_json_input(schema, {"reason": "safe"})

    assert exc_info.value.code == "unsupported_schema_keyword"
    assert exc_info.value.path == "$.reason.pattern"


_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["reason", "dry_run"],
    "properties": {
        "reason": {"type": "string", "minLength": 1, "maxLength": 256},
        "dry_run": {"type": "boolean", "enum": [True]},
    },
}
