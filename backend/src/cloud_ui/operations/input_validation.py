from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class InputValidationError(Exception):
    code: str
    path: str

    def __str__(self) -> str:
        return f"{self.code} at {self.path}"


_SUPPORTED_SCHEMA_KEYS = frozenset(
    {
        "type",
        "additionalProperties",
        "required",
        "properties",
        "enum",
        "minLength",
        "maxLength",
        "minimum",
        "maximum",
    }
)


def validate_json_input(schema: dict[str, Any], payload: Any) -> dict[str, Any]:
    _validate_schema_keywords(schema, "$")
    _validate_value(schema, payload, "$")
    if not isinstance(payload, dict):
        raise InputValidationError(code="type_mismatch", path="$")
    return payload


def _validate_schema_keywords(schema: Any, path: str) -> None:
    if not isinstance(schema, dict):
        raise InputValidationError(code="invalid_schema", path=path)
    for key, value in schema.items():
        if key not in _SUPPORTED_SCHEMA_KEYS:
            raise InputValidationError(code="unsupported_schema_keyword", path=f"{path}.{key}")
        if key == "properties":
            if not isinstance(value, dict):
                raise InputValidationError(code="invalid_schema", path=f"{path}.{key}")
            for property_name, property_schema in value.items():
                _validate_schema_keywords(property_schema, f"{path}.{property_name}")


def _validate_value(schema: dict[str, Any], value: Any, path: str) -> None:
    expected_type = schema.get("type")
    if expected_type == "object":
        _validate_object(schema, value, path)
    elif expected_type == "string":
        _validate_string(schema, value, path)
    elif expected_type == "boolean":
        _validate_boolean(value, path)
    elif expected_type == "integer":
        _validate_integer(schema, value, path)
    else:
        raise InputValidationError(code="unsupported_schema_type", path=f"{path}.type")

    enum_values = schema.get("enum")
    if enum_values is not None and value not in enum_values:
        raise InputValidationError(code="enum_mismatch", path=path)


def _validate_object(schema: dict[str, Any], value: Any, path: str) -> None:
    if not isinstance(value, dict):
        raise InputValidationError(code="type_mismatch", path=path)
    properties = schema.get("properties", {})
    if not isinstance(properties, dict):
        raise InputValidationError(code="invalid_schema", path=f"{path}.properties")
    required = schema.get("required", [])
    if not isinstance(required, list) or not all(isinstance(item, str) for item in required):
        raise InputValidationError(code="invalid_schema", path=f"{path}.required")
    for property_name in required:
        if property_name not in value:
            raise InputValidationError(code="required", path=f"{path}.{property_name}")
    if schema.get("additionalProperties") is False:
        extra_keys = sorted(set(value) - set(properties))
        if extra_keys:
            raise InputValidationError(code="additional_property", path=f"{path}.{extra_keys[0]}")
    for property_name, property_value in value.items():
        property_schema = properties.get(property_name)
        if property_schema is not None:
            _validate_value(property_schema, property_value, f"{path}.{property_name}")


def _validate_string(schema: dict[str, Any], value: Any, path: str) -> None:
    if not isinstance(value, str):
        raise InputValidationError(code="type_mismatch", path=path)
    min_length = schema.get("minLength")
    if min_length is not None and len(value) < int(min_length):
        raise InputValidationError(code="min_length", path=path)
    max_length = schema.get("maxLength")
    if max_length is not None and len(value) > int(max_length):
        raise InputValidationError(code="max_length", path=path)


def _validate_boolean(value: Any, path: str) -> None:
    if not isinstance(value, bool):
        raise InputValidationError(code="type_mismatch", path=path)


def _validate_integer(schema: dict[str, Any], value: Any, path: str) -> None:
    if not isinstance(value, int) or isinstance(value, bool):
        raise InputValidationError(code="type_mismatch", path=path)
    minimum = schema.get("minimum")
    if minimum is not None and value < int(minimum):
        raise InputValidationError(code="minimum", path=path)
    maximum = schema.get("maximum")
    if maximum is not None and value > int(maximum):
        raise InputValidationError(code="maximum", path=path)
