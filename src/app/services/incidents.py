"""Business logic for incident workflows."""

from app.repositories.incidents import IncidentRepository
from app.schemas.incidents import (
    IncidentCreate,
    IncidentCreatedResponse,
    IncidentDocument,
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
