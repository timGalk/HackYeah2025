"""Incident reporting API routes."""

from fastapi import APIRouter, Depends, status

from app.api.dependencies import get_incident_service
from app.schemas.incidents import IncidentCreate, IncidentCreatedResponse
from app.services.incidents import IncidentService

router = APIRouter(prefix="/incidents", tags=["incidents"])


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=IncidentCreatedResponse,
    summary="Report a new incident",
)
async def report_incident(
    payload: IncidentCreate,
    service: IncidentService = Depends(get_incident_service),
) -> IncidentCreatedResponse:
    """Persist an incident using the configured Elasticsearch repository."""

    return await service.report_incident(payload)
