"""Business logic for incident workflows."""

import math
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
from app.services.transport import TransportGraphService


class IncidentService:
    """Coordinate incident ingestion workflows."""

    def __init__(
        self,
        *,
        repository: IncidentRepository,
        transport_service: TransportGraphService,
    ) -> None:
        self._repository = repository
        self._transport_service = transport_service

    async def report_incident(self, payload: IncidentCreate) -> IncidentCreatedResponse:
        """Validate and persist an incident, returning its identifier."""

        document = self._build_document(payload)
        incident_id = await self._repository.create_incident(document)
        return IncidentCreatedResponse(incident_id=incident_id)

    async def get_recent_incidents(
        self,
        limit: int,
        routes: Sequence[str] | None = None,
    ) -> IncidentListResponse:
        """Return the most recent incidents limited by the requested count."""

        incidents = await self._repository.get_recent_incidents(limit, routes=routes)
        return IncidentListResponse(incidents=self._to_models(incidents))

    async def get_incidents_between(
        self,
        *,
        start: datetime,
        end: datetime,
        routes: Sequence[str] | None = None,
    ) -> IncidentListResponse:
        """Return incidents created within the provided time interval."""

        if end < start:
            msg = "Parameter 'end' must be greater than or equal to 'start'."
            raise ValueError(msg)
        incidents = await self._repository.get_incidents_between(
            start=start,
            end=end,
            routes=routes,
        )
        return IncidentListResponse(incidents=self._to_models(incidents))

    async def get_all_incidents(
        self,
        routes: Sequence[str] | None = None,
    ) -> IncidentListResponse:
        """Return all incidents stored in the repository."""

        incidents = await self._repository.get_all_incidents(routes=routes)
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

    async def delete_incidents_all(self) -> int:
        """Delete every incident document. Returns the count of removed records."""

        return await self._repository.delete_incidents_all()

    async def delete_incidents_in_range(self, *, start: datetime, end: datetime) -> int:
        """Delete incidents within the inclusive time interval. Returns deleted count."""

        if end < start:
            msg = "Parameter 'end' must be greater than or equal to 'start'."
            raise ValueError(msg)
        return await self._repository.delete_incidents_in_range(start=start, end=end)

    def _to_models(self, payload: Sequence[dict[str, Any]]) -> list[IncidentRead]:
        """Convert raw repository documents into typed models."""

        return [IncidentRead.model_validate(item) for item in payload]

    def _build_document(self, payload: IncidentCreate) -> IncidentDocument:
        """Augment the incoming payload with edge metadata before persistence."""

        base_data = payload.model_dump()
        edge = self._resolve_edge_context(latitude=payload.latitude, longitude=payload.longitude)

        if edge is None:
            return IncidentDocument(**base_data)

        edge_key = self._normalize_optional_string(edge.get("key"))
        route_id = self._normalize_optional_string(edge.get("route_id"))
        impacted_routes = [route_id] if isinstance(route_id, str) and route_id else []

        trip_id = self._normalize_optional_string(edge.get("trip_id"))
        route_short_name = self._normalize_optional_string(edge.get("route_short_name"))
        route_long_name = self._normalize_optional_string(edge.get("route_long_name"))

        return IncidentDocument(
            **base_data,
            edge_mode=edge.get("mode"),
            edge_source=edge.get("source"),
            edge_target=edge.get("target"),
            edge_key=edge_key,
            trip_id=trip_id,
            route_id=route_id,
            route_short_name=route_short_name,
            route_long_name=route_long_name,
            impacted_routes=impacted_routes,
        )

    def _resolve_edge_context(self, *, latitude: float, longitude: float) -> dict[str, Any] | None:
        """Lookup the closest transit edge and return its metadata, if any."""

        try:
            return self._transport_service.get_closest_transit_edge(
                latitude=latitude,
                longitude=longitude,
            )
        except ValueError:
            return None

    @staticmethod
    def _normalize_optional_string(value: Any) -> str | None:
        """Return a clean string representation or ``None`` when not available."""

        if value is None:
            return None
        if isinstance(value, str):
            return value
        if isinstance(value, float) and math.isnan(value):
            return None
        return str(value)
