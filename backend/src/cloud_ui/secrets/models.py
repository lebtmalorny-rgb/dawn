from __future__ import annotations

from typing import TypeAlias

from pydantic import BaseModel, ConfigDict, Field

SecretScalar: TypeAlias = str | int | float | bool


class SecretReference(BaseModel):
    model_config = ConfigDict(frozen=True)

    path: str = Field(min_length=1)
    alias: str = Field(min_length=1)

    def is_allowed(self, allowed_prefix: str) -> bool:
        return self.path.startswith(allowed_prefix)


class SecretSchema(BaseModel):
    model_config = ConfigDict(frozen=True)

    required_keys: tuple[str, ...]

    def validate_data(self, data: dict[str, SecretScalar]) -> dict[str, SecretScalar]:
        missing = [key for key in self.required_keys if key not in data]
        if missing:
            raise ValueError("secret document is missing required keys")
        return data


class SecretDocument(BaseModel):
    model_config = ConfigDict(frozen=True)

    alias: str
    data: dict[str, SecretScalar]
