from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class PlacementResourceProvider(BaseModel):
    model_config = ConfigDict(frozen=True)

    provider_uuid: str
    name: str
    generation: int


class PlacementInventory(BaseModel):
    model_config = ConfigDict(frozen=True)

    total: int
    reserved: int
    allocation_ratio: float
