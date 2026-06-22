from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import pytest
import sqlalchemy as sa

from cloud_ui.groups.rules import GroupRuleCompiler, GroupRuleError


def test_valid_vm_rule_compiles_to_project_scoped_conditions() -> None:
    compiler = GroupRuleCompiler()
    compiled = compiler.compile(
        resource_type="vm",
        scope_type="project",
        scope_id="project-a",
        rule={
            "all": [
                {"field": "project_id", "op": "eq", "value": "project-a"},
                {"field": "status", "op": "in", "value": ["ACTIVE", "SHUTOFF"]},
            ]
        },
    )

    assert compiled.explain == [
        "project_id eq project-a",
        "status in 2 values",
    ]
    sql = str(compiled.condition.compile(compile_kwargs={"literal_binds": True}))
    assert "instances.project_id = 'project-a'" in sql
    assert "instances.status IN ('ACTIVE', 'SHUTOFF')" in sql


def test_vm_rule_requires_project_scope() -> None:
    compiler = GroupRuleCompiler()

    _assert_rule_error(
        compiler,
        resource_type="vm",
        scope_type="system",
        scope_id=None,
        rule={"field": "status", "op": "eq", "value": "ACTIVE"},
        code="invalid_scope",
    )
    _assert_rule_error(
        compiler,
        resource_type="vm",
        scope_type="domain",
        scope_id="domain-a",
        rule={"field": "status", "op": "eq", "value": "ACTIVE"},
        code="invalid_scope",
    )


def test_unknown_field_operator_and_extra_properties_are_rejected() -> None:
    compiler = GroupRuleCompiler()

    _assert_rule_error(
        compiler,
        rule={"field": "name", "op": "eq", "value": "vm-a"},
        code="unknown_field",
    )
    _assert_rule_error(
        compiler,
        rule={"field": "status", "op": "regex", "value": "ACTIVE"},
        code="unknown_operator",
    )
    _assert_rule_error(
        compiler,
        rule={"field": "status", "op": "eq", "value": "ACTIVE", "raw_sql": "1=1"},
        code="extra_properties",
    )
    _assert_rule_error(
        compiler,
        rule={"all": [{"field": "status", "op": "eq", "value": "ACTIVE"}], "sql": "1=1"},
        code="extra_properties",
    )
    _assert_rule_error(
        compiler,
        rule={"not": {"field": "status", "op": "exists", "value": "unexpected"}},
        code="invalid_value",
    )

    unsafe = compiler.compile(
        resource_type="vm",
        scope_type="project",
        scope_id="project-a",
        rule={"field": "status", "op": "eq", "value": "x' OR 1=1 --"},
    )
    compiled = unsafe.condition.compile()
    assert "x' OR 1=1 --" in compiled.params.values()
    assert str(compiled).count("OR 1=1") == 0


def test_string_fields_reject_non_string_values() -> None:
    compiler = GroupRuleCompiler()

    _assert_rule_error(
        compiler,
        rule={"field": "status", "op": "eq", "value": True},
        code="invalid_value",
    )
    _assert_rule_error(
        compiler,
        rule={"field": "status", "op": "eq", "value": float("nan")},
        code="invalid_value",
    )
    _assert_rule_error(
        compiler,
        rule={"field": "status", "op": "in", "value": ["ACTIVE", True]},
        code="invalid_value",
    )
    _assert_rule_error(
        compiler,
        rule={"field": "status", "op": "prefix", "value": 1},
        code="invalid_value",
    )


def test_depth_node_and_in_value_limits_are_enforced() -> None:
    _assert_rule_error(
        GroupRuleCompiler(max_depth=2),
        rule={"not": {"not": {"field": "status", "op": "eq", "value": "ACTIVE"}}},
        code="max_depth_exceeded",
    )
    _assert_rule_error(
        GroupRuleCompiler(max_nodes=2),
        rule={
            "all": [
                {"field": "project_id", "op": "eq", "value": "project-a"},
                {"field": "status", "op": "eq", "value": "ACTIVE"},
            ]
        },
        code="max_nodes_exceeded",
    )
    _assert_rule_error(
        GroupRuleCompiler(max_in_values=2),
        rule={"field": "status", "op": "in", "value": ["ACTIVE", "SHUTOFF", "ERROR"]},
        code="too_many_values",
    )


def test_sqlalchemy_expression_values_are_rejected() -> None:
    compiler = GroupRuleCompiler()

    _assert_rule_error(
        compiler,
        rule={"field": "status", "op": "eq", "value": sa.text("CURRENT_USER")},
        code="invalid_value",
    )
    _assert_rule_error(
        compiler,
        rule={"field": "status", "op": "in", "value": [sa.literal_column("CURRENT_USER")]},
        code="invalid_value",
    )


def test_exists_rule_uses_no_value_payload() -> None:
    compiler = GroupRuleCompiler()
    compiled = compiler.compile(
        resource_type="host",
        scope_type="system",
        scope_id=None,
        rule={"field": "maintenance_status", "op": "exists"},
    )

    assert compiled.explain == ["maintenance_status exists"]
    sql = str(compiled.condition.compile(compile_kwargs={"literal_binds": True}))
    assert "hypervisors.maintenance_status IS NOT NULL" in sql

    _assert_rule_error(
        compiler,
        resource_type="host",
        scope_type="system",
        scope_id=None,
        rule={"field": "maintenance_status", "op": "exists", "value": True},
        code="invalid_value",
    )


def test_any_rule_compiles_with_clear_explain() -> None:
    compiler = GroupRuleCompiler()
    compiled = compiler.compile(
        resource_type="vm",
        scope_type="project",
        scope_id="project-a",
        rule={
            "any": [
                {"field": "status", "op": "eq", "value": "ACTIVE"},
                {"field": "status", "op": "eq", "value": "SHUTOFF"},
            ]
        },
    )

    assert compiled.explain == ["any (status eq ACTIVE; status eq SHUTOFF)"]
    sql = str(compiled.condition.compile(compile_kwargs={"literal_binds": True}))
    assert "instances.project_id = 'project-a'" in sql
    assert "instances.status = 'ACTIVE'" in sql
    assert "instances.status = 'SHUTOFF'" in sql
    assert " OR " in sql


def test_not_rule_compiles_with_clear_group_explain() -> None:
    compiler = GroupRuleCompiler()
    compiled = compiler.compile(
        resource_type="vm",
        scope_type="project",
        scope_id="project-a",
        rule={
            "not": {
                "all": [
                    {"field": "status", "op": "eq", "value": "ERROR"},
                    {"field": "host_name", "op": "prefix", "value": "compute-"},
                ]
            }
        },
    )

    assert compiled.explain == ["not (all (status eq ERROR; host_name prefix compute-))"]
    sql = str(compiled.condition.compile(compile_kwargs={"literal_binds": True}))
    assert "instances.project_id = 'project-a'" in sql
    assert "NOT" in sql
    assert "instances.status = 'ERROR'" in sql
    assert "instances.host_name LIKE 'compute-' || '%' ESCAPE '/'" in sql


def test_host_rule_uses_host_allowlist_only() -> None:
    compiler = GroupRuleCompiler()
    compiled = compiler.compile(
        resource_type="host",
        scope_type="system",
        scope_id=None,
        rule={
            "all": [
                {"field": "host_name", "op": "prefix", "value": "compute_%"},
                {"field": "service_status", "op": "eq", "value": "enabled"},
            ]
        },
    )

    assert compiled.explain == [
        "host_name prefix compute_%",
        "service_status eq enabled",
    ]
    sql = str(compiled.condition.compile(compile_kwargs={"literal_binds": True}))
    assert "hypervisors.host_name LIKE 'compute/_/%' || '%' ESCAPE '/'" in sql
    assert "hypervisors.service_status = 'enabled'" in sql
    assert "instances." not in sql

    _assert_rule_error(
        compiler,
        resource_type="host",
        scope_type="system",
        scope_id=None,
        rule={"field": "project_id", "op": "eq", "value": "project-a"},
        code="unknown_field",
    )


def _assert_rule_error(
    compiler: GroupRuleCompiler,
    *,
    rule: Mapping[str, Any],
    code: str,
    resource_type: str = "vm",
    scope_type: str = "project",
    scope_id: str | None = "project-a",
) -> None:
    with pytest.raises(GroupRuleError) as error:
        compiler.compile(
            resource_type=resource_type,
            scope_type=scope_type,
            scope_id=scope_id,
            rule=rule,
        )

    assert error.value.code == code
