"""Dependency wiring for API routes."""

from fastapi import Depends
from elasticsearch import AsyncElasticsearch

from app.core.config import Settings
from app.core.dependencies import get_app_settings, get_elasticsearch_client
from app.repositories.incidents import IncidentRepository
from app.services.incidents import IncidentService


def get_incident_repository(
    client: AsyncElasticsearch = Depends(get_elasticsearch_client),
    settings: Settings = Depends(get_app_settings),
) -> IncidentRepository:
    """Provide an incident repository instance per request."""

    return IncidentRepository(client=client, index_name=settings.elasticsearch_index)


def get_incident_service(
    repository: IncidentRepository = Depends(get_incident_repository),
) -> IncidentService:
    """Provide an incident service instance per request."""

    return IncidentService(repository=repository)
