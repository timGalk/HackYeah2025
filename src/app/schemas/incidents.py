"""Schemas for incident reporting endpoints."""

from datetime import datetime

from pydantic import BaseModel, Field


class IncidentCreate(BaseModel):
    """Payload accepted by the incident reporting endpoint."""

    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    description: str = Field(..., min_length=1, max_length=2000)
    category: str = Field(..., min_length=1, max_length=100)
    username: str = Field(..., min_length=1, max_length=100)
    approved: bool = Field(default=False)

    model_config = {
        "extra": "forbid",
    }


class IncidentDocument(IncidentCreate):
    """Data representation persisted into Elasticsearch."""

    created_at: datetime = Field(default_factory=datetime.utcnow)
    edge_mode: str | None = Field(default=None, description="Transport mode of the impacted edge.")
    edge_source: str | None = Field(default=None, description="Source node identifier of the impacted edge.")
    edge_target: str | None = Field(default=None, description="Target node identifier of the impacted edge.")
    edge_key: str | None = Field(default=None, description="Key of the impacted edge within the transport graph.")
    trip_id: str | None = Field(default=None, description="Transit trip identifier associated with the impacted edge.")
    route_id: str | None = Field(default=None, description="GTFS route identifier touched by the incident.")
    route_short_name: str | None = Field(default=None, description="Short name of the impacted route, if available.")
    route_long_name: str | None = Field(default=None, description="Long name of the impacted route, if available.")
    impacted_routes: list[str] = Field(
        default_factory=list,
        description="Collection of route identifiers affected by this incident.",
    )


class IncidentCreatedResponse(BaseModel):
    """Response returned when an incident has been stored."""

    incident_id: str = Field(..., description="Identifier assigned by Elasticsearch.")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {"incident_id": "abc123"},
            ]
        }
    }


class IncidentRead(IncidentDocument):
    """Representation of an incident retrieved from persistence."""

    id: str = Field(..., description="Elasticsearch document identifier.")


class IncidentListResponse(BaseModel):
    """Container for collections of incidents returned by query endpoints."""

    incidents: list[IncidentRead]
