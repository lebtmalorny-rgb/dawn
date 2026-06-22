from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

ResourceType = Literal["vm", "host", "mixed"]
MembershipMode = Literal["explicit", "dynamic", "imported"]
ScopeType = Literal["project", "domain", "system"]


class ResourceGroup(BaseModel):
    model_config = ConfigDict(frozen=True)

    group_id: str
    name: str
    description: str | None
    resource_type: str
    scope_type: str
    scope_id: str
    membership_mode: str
    rule_version: int
    rule_body_json: dict[str, Any] | None
    owner_subject_id: str
    revision: int
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None


class GroupMember(BaseModel):
    model_config = ConfigDict(frozen=True)

    group_id: str
    resource_type: str
    cloud_id: str
    region_id: str
    resource_id: str
    source: str
    added_by: str
    added_at: datetime
    expires_at: datetime | None


class GroupCreate(BaseModel):
    model_config = ConfigDict(frozen=True)

    actor_id: str
    scope_type: ScopeType | str
    scope_id: str | None
    name: str
    description: str | None
    resource_type: ResourceType | str
    membership_mode: MembershipMode | str
    rule_version: int = 1
    rule_body_json: dict[str, Any] | None = None


class GroupUpdate(BaseModel):
    model_config = ConfigDict(frozen=True)

    group_id: str
    actor_id: str
    expected_revision: int
    name: str
    description: str | None


class GroupPage(BaseModel):
    model_config = ConfigDict(frozen=True)

    items: list[ResourceGroup] = Field(default_factory=list)
    next_cursor: str | None = None


class GroupRepositoryError(Exception):
    code = "group_repository_error"

    def __init__(self, message: str | None = None) -> None:
        super().__init__(message or self.code)


class GroupRevisionConflict(GroupRepositoryError):
    code = "group_revision_conflict"


class GroupNotFound(GroupRepositoryError):
    code = "group_not_found"
