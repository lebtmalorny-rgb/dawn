from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict

EnvironmentName = Literal["local", "test", "production"]


class WorkflowDefinition(BaseModel):
    model_config = ConfigDict(frozen=True)

    workflow_key: str
    version: str
    title: str
    description: str
    target_type: str
    input_schema_json: dict[str, Any]
    ui_schema_json: dict[str, Any] | None
    mistral_workflow_name: str
    required_capability: str
    required_scope_type: str
    risk_level: str
    approval_mode: str
    cancel_policy: str
    enabled_environments: tuple[EnvironmentName, ...]
    checksum: str
    enabled: bool

    def enabled_for(self, environment: EnvironmentName) -> bool:
        return self.enabled and environment in self.enabled_environments


@dataclass
class WorkflowDefinitionNotFound(Exception):
    workflow_key: str
    version: str

    def __str__(self) -> str:
        return f"workflow definition not found: {self.workflow_key}@{self.version}"


class WorkflowCatalog:
    def __init__(
        self,
        *,
        environment: EnvironmentName,
        definitions: tuple[WorkflowDefinition, ...],
    ) -> None:
        self._environment = environment
        self._definitions = definitions

    def list_definitions(self) -> list[WorkflowDefinition]:
        return [
            definition
            for definition in self._definitions
            if definition.enabled_for(self._environment)
        ]

    def get_definition(self, workflow_key: str, version: str) -> WorkflowDefinition:
        for definition in self.list_definitions():
            if definition.workflow_key == workflow_key and definition.version == version:
                return definition
        raise WorkflowDefinitionNotFound(workflow_key=workflow_key, version=version)


def build_builtin_workflow_catalog(*, environment: EnvironmentName) -> WorkflowCatalog:
    definition = _with_checksum(
        WorkflowDefinition(
            workflow_key="maintenance-host-precheck",
            version="1.0.0",
            title="Host maintenance precheck",
            description="Dry-run host maintenance readiness check",
            target_type="host",
            input_schema_json={
                "type": "object",
                "additionalProperties": False,
                "required": ["reason", "dry_run"],
                "properties": {
                    "reason": {"type": "string", "minLength": 1, "maxLength": 256},
                    "dry_run": {"type": "boolean", "enum": [True]},
                },
            },
            ui_schema_json=None,
            mistral_workflow_name="portal.maintenance_host_precheck.v1",
            required_capability="workflow.execute.maintenance-host",
            required_scope_type="system",
            risk_level="low",
            approval_mode="none",
            cancel_policy="best_effort",
            enabled_environments=("local", "test"),
            checksum="",
            enabled=True,
        )
    )
    return WorkflowCatalog(environment=environment, definitions=(definition,))


def compute_definition_checksum(definition: WorkflowDefinition) -> str:
    payload = definition.model_dump(mode="json")
    payload["checksum"] = ""
    raw_payload = json.dumps(
        payload,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return hashlib.sha256(raw_payload).hexdigest()


def _with_checksum(definition: WorkflowDefinition) -> WorkflowDefinition:
    return definition.model_copy(update={"checksum": compute_definition_checksum(definition)})
