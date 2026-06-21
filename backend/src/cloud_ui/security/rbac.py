from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from cloud_ui.security.identity import Subject

SubjectType = Literal["human", "service"]


class AuthorizationDenied(Exception):
    def __init__(self, code: str = "forbidden") -> None:
        self.code = code
        super().__init__(code)


class OpenStackForbidden(Exception):
    """Raised when OpenStack policy denies an action allowed by portal policy."""


@dataclass(frozen=True)
class RoleBindingRequest:
    subject_id: str
    subject_type: SubjectType
    role: str


class PolicyService:
    policy_revision = "p0-mock-policy-v1"

    def require_capability(self, subject: Subject, capability: str) -> None:
        if capability not in subject.capabilities:
            raise AuthorizationDenied()

    def validate_role_binding(self, actor: Subject, request: RoleBindingRequest) -> None:
        self.require_capability(actor, "role.manage")
        if request.subject_type == "human" and request.role == "service":
            raise AuthorizationDenied("service_role_for_human")

    def ensure_openstack_allowed(self, *, openstack_allowed: bool) -> None:
        if not openstack_allowed:
            raise OpenStackForbidden("OpenStack policy denied the operation")
