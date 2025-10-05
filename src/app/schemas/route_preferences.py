"""Schemas describing user route preference persistence."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

RoutePreferenceKind = Literal["planned", "frequent"]


class RoutePreferenceBase(BaseModel):
    """Common fields shared across route preference models."""

    user_id: str = Field(..., min_length=1, max_length=255)
    route_id: str = Field(..., min_length=1, max_length=255)
    route_short_name: str | None = Field(default=None, max_length=255)
    route_long_name: str | None = Field(default=None, max_length=512)
    kind: RoutePreferenceKind = Field(..., description="Preference category (planned or frequent).")

    model_config = {
        "extra": "forbid",
    }


class RoutePreferenceCreate(RoutePreferenceBase):
    """Payload accepted when creating or updating a route preference."""

    notes: str | None = Field(default=None, max_length=2000)


class RoutePreferenceDocument(RoutePreferenceCreate):
    """Representation persisted in Elasticsearch."""

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class RoutePreferenceRead(RoutePreferenceDocument):
    """Route preference record returned by query endpoints."""

    id: str = Field(..., description="Unique identifier composed of user, route, and preference kind.")


class RoutePreferenceListResponse(BaseModel):
    """Container for collections of route preference records."""

    preferences: list[RoutePreferenceRead] = Field(default_factory=list)


class RoutePreferenceDeleteResponse(BaseModel):
    """Response returned when a preference is removed."""

    deleted: bool = Field(..., description="True when the record existed and was removed.")
