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

    model_config = {
        "extra": "forbid",
    }


class IncidentDocument(IncidentCreate):
    """Data representation persisted into Elasticsearch."""

    created_at: datetime = Field(default_factory=datetime.utcnow)


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
