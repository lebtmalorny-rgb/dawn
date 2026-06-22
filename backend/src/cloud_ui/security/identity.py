from __future__ import annotations

from typing import Literal, Protocol

from pydantic import BaseModel, ConfigDict

SubjectType = Literal["human", "service"]


class AuthenticationFailed(Exception):
    """Raised when identity provider cannot authenticate the login request."""


class LoginRequest(BaseModel):
    login: str
    credential: str


class Subject(BaseModel):
    model_config = ConfigDict(frozen=True)

    subject_id: str
    display_name: str
    subject_type: SubjectType
    scope_type: Literal["project", "system"] = "system"
    scope_id: str | None = None
    roles: frozenset[str]
    capabilities: frozenset[str]


class LoginResult(BaseModel):
    subject: Subject
    authentication_method: str


class IdentityProvider(Protocol):
    def authenticate(self, request: LoginRequest) -> LoginResult:
        """Authenticate user input and return a sanitized subject result."""
