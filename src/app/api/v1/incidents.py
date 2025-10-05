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
    coordinates: list[str] | None = Query(
        default=None,
        description="Filter incidents to routes near the provided coordinates (format: 'lat,lng').",
    ),
    max_distance_km: float = Query(
        default=1.0,
        ge=0.1,
        le=10.0,
        description="Maximum distance in kilometers from coordinates to consider routes.",
    ),
) -> IncidentListResponse:
    """Return all incidents stored in the system."""

    # Parse coordinates from strings to tuples
    parsed_coordinates = None
    if coordinates:
        try:
            parsed_coordinates = [
                tuple(float(coord.strip()) for coord in coord_str.split(","))
                for coord_str in coordinates
                if coord_str.strip()
            ]
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid coordinate format. Expected 'lat,lng' but got: {coordinates}. Error: {str(e)}",
            ) from e

    return await service.get_all_incidents(coordinates=parsed_coordinates, max_distance_km=max_distance_km)


@router.get(
    "/latest",
    response_model=IncidentListResponse,
    summary="Fetch the most recent incidents",
)
async def latest_incidents(
    limit: int = Query(10, gt=0, le=1000, description="Maximum number of incidents to return."),
    coordinates: list[str] | None = Query(
        default=None,
        description="Filter incidents to routes near the provided coordinates (format: 'lat,lng').",
    ),
    max_distance_km: float = Query(
        default=1.0,
        ge=0.1,
        le=10.0,
        description="Maximum distance in kilometers from coordinates to consider routes.",
    ),
    service: IncidentService = Depends(get_incident_service),
) -> IncidentListResponse:
    """Return the last N incidents ordered by creation time descending."""

    # Parse coordinates from strings to tuples
    parsed_coordinates = None
    if coordinates:
        try:
            parsed_coordinates = [
                tuple(float(coord.strip()) for coord in coord_str.split(","))
                for coord_str in coordinates
                if coord_str.strip()
            ]
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid coordinate format. Expected 'lat,lng' but got: {coordinates}. Error: {str(e)}",
            ) from e

    return await service.get_recent_incidents(limit, coordinates=parsed_coordinates, max_distance_km=max_distance_km)


@router.get(
    "/range",
    response_model=IncidentListResponse,
    summary="Fetch incidents within a time interval",
)
async def incidents_in_range(
    start: datetime = Query(..., description="Start of the interval (inclusive)."),
    end: datetime = Query(..., description="End of the interval (inclusive)."),
    coordinates: list[str] | None = Query(
        default=None,
        description="Filter incidents to routes near the provided coordinates (format: 'lat,lng').",
    ),
    max_distance_km: float = Query(
        default=1.0,
        ge=0.1,
        le=10.0,
        description="Maximum distance in kilometers from coordinates to consider routes.",
    ),
    service: IncidentService = Depends(get_incident_service),
) -> IncidentListResponse:
    """Return incidents created within the specified time interval."""

    if end < start:
        msg = "Parameter 'end' must be greater than or equal to 'start'."
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=msg)

    # Parse coordinates from strings to tuples
    parsed_coordinates = None
    if coordinates:
        try:
            parsed_coordinates = [
                tuple(float(coord.strip()) for coord in coord_str.split(","))
                for coord_str in coordinates
                if coord_str.strip()
            ]
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid coordinate format. Expected 'lat,lng' but got: {coordinates}. Error: {str(e)}",
            ) from e

    try:
        return await service.get_incidents_between(
            start=start,
            end=end,
            coordinates=parsed_coordinates,
            max_distance_km=max_distance_km,
        )
    except ValueError as exc:  # pragma: no cover - maps to HTTP error response
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
