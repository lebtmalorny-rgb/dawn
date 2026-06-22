from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Literal, cast

import sqlalchemy as sa

from cloud_ui.inventory import schema as inventory_schema

_ALLOWED_OPERATORS = frozenset({"eq", "in", "prefix", "exists"})
_LOGICAL_KEYS = frozenset({"all", "any", "not"})
_EXISTS_LEAF_KEYS = frozenset({"field", "op"})
_VALUE_LEAF_KEYS = frozenset({"field", "op", "value"})
_SCOPE_TYPES = frozenset({"project", "domain", "system"})

_VM_FIELDS: Mapping[str, sa.Column[Any]] = {
    "project_id": inventory_schema.instances.c.project_id,
    "status": inventory_schema.instances.c.status,
    "host_name": inventory_schema.instances.c.host_name,
    "availability_zone": inventory_schema.instances.c.availability_zone,
    "flavor_id": inventory_schema.instances.c.flavor_id,
}

_HOST_FIELDS: Mapping[str, sa.Column[Any]] = {
    "host_name": inventory_schema.hypervisors.c.host_name,
    "service_status": inventory_schema.hypervisors.c.service_status,
    "service_state": inventory_schema.hypervisors.c.service_state,
    "availability_zone": inventory_schema.hypervisors.c.availability_zone,
    "maintenance_status": inventory_schema.hypervisors.c.maintenance_status,
}


class GroupRuleError(ValueError):
    def __init__(self, code: str, message: str | None = None) -> None:
        self.code = code
        super().__init__(message or code)


@dataclass(frozen=True)
class CompiledGroupRule:
    condition: sa.ColumnElement[bool]
    explain: list[str]


@dataclass(frozen=True)
class _CompiledNode:
    condition: sa.ColumnElement[bool]
    explain: list[str]
    summary: str
    node_count: int


class GroupRuleCompiler:
    def __init__(self, max_depth: int = 4, max_nodes: int = 32, max_in_values: int = 20) -> None:
        if max_depth < 1:
            raise ValueError("max_depth must be at least 1")
        if max_nodes < 1:
            raise ValueError("max_nodes must be at least 1")
        if max_in_values < 1:
            raise ValueError("max_in_values must be at least 1")

        self._max_depth = max_depth
        self._max_nodes = max_nodes
        self._max_in_values = max_in_values

    def compile(
        self,
        *,
        resource_type: str,
        scope_type: str,
        scope_id: str | None,
        rule: Mapping[str, Any],
    ) -> CompiledGroupRule:
        fields = _fields_for_resource_type(resource_type)
        self._validate_scope(scope_type=scope_type, scope_id=scope_id)
        if resource_type == "vm" and (scope_type != "project" or scope_id is None):
            raise GroupRuleError("invalid_scope", "VM group rules require project scope")

        compiled = self._compile_node(
            rule,
            fields=fields,
            depth=1,
            node_count=0,
        )
        condition = compiled.condition

        if resource_type == "vm":
            condition = sa.and_(inventory_schema.instances.c.project_id == scope_id, condition)

        return CompiledGroupRule(condition=condition, explain=compiled.explain)

    def _compile_node(
        self,
        node: object,
        *,
        fields: Mapping[str, sa.Column[Any]],
        depth: int,
        node_count: int,
    ) -> _CompiledNode:
        if depth > self._max_depth:
            raise GroupRuleError("max_depth_exceeded")
        node_count += 1
        if node_count > self._max_nodes:
            raise GroupRuleError("max_nodes_exceeded")
        if not isinstance(node, Mapping):
            raise GroupRuleError("invalid_node")

        rule_node = cast(Mapping[str, Any], node)
        keys = frozenset(rule_node.keys())
        if _has_extra_logical_keys(keys):
            raise GroupRuleError("extra_properties")
        if _has_extra_leaf_keys(keys):
            raise GroupRuleError("extra_properties")

        if keys == {"all"}:
            return self._compile_group(
                rule_node["all"],
                fields=fields,
                depth=depth,
                node_count=node_count,
                combinator=sa.and_,
                label="all",
            )
        if keys == {"any"}:
            return self._compile_group(
                rule_node["any"],
                fields=fields,
                depth=depth,
                node_count=node_count,
                combinator=sa.or_,
                label="any",
            )
        if keys == {"not"}:
            child = self._compile_node(
                rule_node["not"],
                fields=fields,
                depth=depth + 1,
                node_count=node_count,
            )
            summary = f"not ({child.summary})"
            return _CompiledNode(
                condition=sa.not_(child.condition),
                explain=[summary],
                summary=summary,
                node_count=child.node_count,
            )
        if keys == _VALUE_LEAF_KEYS:
            condition, summary = self._compile_leaf(rule_node, fields=fields, has_value=True)
            return _CompiledNode(
                condition=condition,
                explain=[summary],
                summary=summary,
                node_count=node_count,
            )
        if keys == _EXISTS_LEAF_KEYS:
            condition, summary = self._compile_leaf(rule_node, fields=fields, has_value=False)
            return _CompiledNode(
                condition=condition,
                explain=[summary],
                summary=summary,
                node_count=node_count,
            )

        raise GroupRuleError("invalid_node")

    def _compile_group(
        self,
        raw_children: object,
        *,
        fields: Mapping[str, sa.Column[Any]],
        depth: int,
        node_count: int,
        combinator: Any,
        label: Literal["all", "any"],
    ) -> _CompiledNode:
        if not isinstance(raw_children, list) or len(raw_children) == 0:
            raise GroupRuleError("invalid_value")

        children: list[_CompiledNode] = []
        for child in raw_children:
            compiled_child = self._compile_node(
                child,
                fields=fields,
                depth=depth + 1,
                node_count=node_count,
            )
            children.append(compiled_child)
            node_count = compiled_child.node_count

        conditions = [child.condition for child in children]
        child_summaries = _join_summaries(children)
        if label == "any":
            summary = f"any ({child_summaries})"
            explain = [summary]
        else:
            summary = f"all ({child_summaries})"
            explain = [item for child in children for item in child.explain]

        return _CompiledNode(
            condition=combinator(*conditions),
            explain=explain,
            summary=summary,
            node_count=node_count,
        )

    def _compile_leaf(
        self,
        node: Mapping[str, Any],
        *,
        fields: Mapping[str, sa.Column[Any]],
        has_value: bool,
    ) -> tuple[sa.ColumnElement[bool], str]:
        field = node["field"]
        operator = node["op"]
        if not isinstance(field, str) or not isinstance(operator, str):
            raise GroupRuleError("invalid_value")
        if field not in fields:
            raise GroupRuleError("unknown_field")
        if operator not in _ALLOWED_OPERATORS:
            raise GroupRuleError("unknown_operator")

        column = fields[field]
        if operator == "exists":
            if has_value:
                raise GroupRuleError("invalid_value")
            return column.is_not(None), f"{field} exists"
        if not has_value:
            raise GroupRuleError("invalid_node")

        value = node["value"]
        if operator == "eq":
            scalar = _validate_string_value(value)
            return column == scalar, f"{field} eq {_format_value(scalar)}"
        if operator == "in":
            values = _validate_in_values(value, max_values=self._max_in_values)
            return column.in_(values), f"{field} in {len(values)} values"
        if operator == "prefix":
            prefix = _validate_string_value(value)
            return column.startswith(prefix, autoescape=True), f"{field} prefix {prefix}"

        raise GroupRuleError("unknown_operator")

    @staticmethod
    def _validate_scope(*, scope_type: str, scope_id: str | None) -> None:
        if scope_type not in _SCOPE_TYPES:
            raise GroupRuleError("invalid_scope")
        if scope_type in {"project", "domain"} and not scope_id:
            raise GroupRuleError("invalid_scope")
        if scope_type == "system" and scope_id is not None:
            raise GroupRuleError("invalid_scope")


def _fields_for_resource_type(resource_type: str) -> Mapping[str, sa.Column[Any]]:
    if resource_type == "vm":
        return _VM_FIELDS
    if resource_type == "host":
        return _HOST_FIELDS
    raise GroupRuleError("unknown_resource_type")


def _has_extra_logical_keys(keys: frozenset[str]) -> bool:
    return bool(keys & _LOGICAL_KEYS) and keys not in ({"all"}, {"any"}, {"not"})


def _has_extra_leaf_keys(keys: frozenset[str]) -> bool:
    return bool(keys & _EXISTS_LEAF_KEYS) and not keys <= _VALUE_LEAF_KEYS


def _validate_in_values(value: object, *, max_values: int) -> list[str]:
    if not isinstance(value, list) or len(value) == 0:
        raise GroupRuleError("invalid_value")
    if len(value) > max_values:
        raise GroupRuleError("too_many_values")

    return [_validate_string_value(item) for item in value]


def _validate_string_value(value: object) -> str:
    if isinstance(value, str):
        return value
    raise GroupRuleError("invalid_value")


def _format_value(value: str) -> str:
    return value


def _join_summaries(children: list[_CompiledNode]) -> str:
    return "; ".join(child.summary for child in children)
