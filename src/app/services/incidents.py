"""Business logic for incident workflows."""

from datetime import datetime
from typing import Any, Sequence

from app.repositories.incidents import IncidentRepository
from app.schemas.incidents import (
    IncidentCreate,
    IncidentCreatedResponse,
    IncidentDocument,
    IncidentListResponse,
    IncidentRead,
)


class IncidentService:
    """Coordinate incident ingestion workflows."""

    def __init__(self, repository: IncidentRepository) -> None:
        self._repository = repository

    async def report_incident(self, payload: IncidentCreate) -> IncidentCreatedResponse:
        """Validate and persist an incident, returning its identifier."""

        document = IncidentDocument(**payload.model_dump())
        incident_id = await self._repository.create_incident(document)
        return IncidentCreatedResponse(incident_id=incident_id)

    async def get_recent_incidents(self, limit: int) -> IncidentListResponse:
        """Return the most recent incidents limited by the requested count."""

        incidents = await self._repository.get_recent_incidents(limit)
        return IncidentListResponse(incidents=self._to_models(incidents))

    async def get_incidents_between(
        self,
        *,
        start: datetime,
        end: datetime,
    ) -> IncidentListResponse:
        """Return incidents created within the provided time interval."""

        if end < start:
            msg = "Parameter 'end' must be greater than or equal to 'start'."
            raise ValueError(msg)
        incidents = await self._repository.get_incidents_between(start=start, end=end)
        return IncidentListResponse(incidents=self._to_models(incidents))

    async def get_all_incidents(self) -> IncidentListResponse:
        """Return all incidents stored in the repository."""

        incidents = await self._repository.get_all_incidents()
        return IncidentListResponse(incidents=self._to_models(incidents))

    async def get_unapproved_incidents(self) -> IncidentListResponse:
        """Return incidents that still await administrative approval."""

        incidents = await self._repository.get_unapproved_incidents()
        return IncidentListResponse(incidents=self._to_models(incidents))

    async def approve_incident(self, incident_id: str) -> bool:
        """Mark the incident identified by the given id as approved."""

        return await self._repository.approve_incident(incident_id)

    async def revoke_incident_approval(self, incident_id: str) -> bool:
        """Remove approval from the incident identified by the given id."""

        return await self._repository.unapprove_incident(incident_id)

    def _to_models(self, payload: Sequence[dict[str, Any]]) -> list[IncidentRead]:
        """Convert raw repository documents into typed models."""

        return [IncidentRead.model_validate(item) for item in payload]
