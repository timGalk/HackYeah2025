"""Incident reporting API routes."""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.dependencies import get_incident_service
from app.schemas.incidents import (
    IncidentCreate,
    IncidentCreatedResponse,
    IncidentListResponse,
)
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


@router.get(
    "",
    response_model=IncidentListResponse,
    summary="List all incidents",
)
async def list_incidents(
    service: IncidentService = Depends(get_incident_service),
) -> IncidentListResponse:
    """Return all incidents stored in the system."""

    return await service.get_all_incidents()


@router.get(
    "/latest",
    response_model=IncidentListResponse,
    summary="Fetch the most recent incidents",
)
async def latest_incidents(
    limit: int = Query(10, gt=0, le=1000, description="Maximum number of incidents to return."),
    service: IncidentService = Depends(get_incident_service),
) -> IncidentListResponse:
    """Return the last N incidents ordered by creation time descending."""

    return await service.get_recent_incidents(limit)


@router.get(
    "/range",
    response_model=IncidentListResponse,
    summary="Fetch incidents within a time interval",
)
async def incidents_in_range(
    start: datetime = Query(..., description="Start of the interval (inclusive)."),
    end: datetime = Query(..., description="End of the interval (inclusive)."),
    service: IncidentService = Depends(get_incident_service),
) -> IncidentListResponse:
    """Return incidents created within the specified time interval."""

    if end < start:
        msg = "Parameter 'end' must be greater than or equal to 'start'."
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=msg)
    try:
        return await service.get_incidents_between(start=start, end=end)
    except ValueError as exc:  # pragma: no cover - maps to HTTP error response
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
