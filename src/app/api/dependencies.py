"""Dependency wiring for API routes."""

from pathlib import Path

from fastapi import Depends
from elasticsearch import AsyncElasticsearch

from app.core.config import Settings
from app.core.dependencies import (
    get_app_settings,
    get_elasticsearch_client,
    get_transport_service,
)
from app.repositories.facebook_posts import FacebookPostRepository
from app.repositories.incidents import IncidentRepository
from app.repositories.route_preferences import RoutePreferenceRepository
from app.services.facebook_posts import FacebookPostService
from app.services.incidents import IncidentService
from app.services.route_preferences import RoutePreferenceService
from app.services.transport import TransportGraphService


def get_incident_repository(
    client: AsyncElasticsearch = Depends(get_elasticsearch_client),
    settings: Settings = Depends(get_app_settings),
) -> IncidentRepository:
    """Provide an incident repository instance per request."""

    return IncidentRepository(client=client, index_name=settings.elasticsearch_index)


def get_incident_service(
    repository: IncidentRepository = Depends(get_incident_repository),
    transport_service: TransportGraphService = Depends(get_transport_service),
) -> IncidentService:
    """Provide an incident service instance per request."""

    return IncidentService(repository=repository, transport_service=transport_service)


def get_facebook_post_repository(
    client: AsyncElasticsearch = Depends(get_elasticsearch_client),
    settings: Settings = Depends(get_app_settings),
) -> FacebookPostRepository:
    """Provide a Facebook post repository instance per request."""

    return FacebookPostRepository(client=client, index_name=settings.facebook_posts_index)


def get_facebook_post_service(
    repository: FacebookPostRepository = Depends(get_facebook_post_repository),
    settings: Settings = Depends(get_app_settings),
) -> FacebookPostService:
    """Provide a Facebook post service instance per request."""

    mock_path = Path(settings.facebook_posts_mock_path)
    return FacebookPostService(repository=repository, mock_data_path=mock_path)


def get_route_preference_repository(
    client: AsyncElasticsearch = Depends(get_elasticsearch_client),
    settings: Settings = Depends(get_app_settings),
) -> RoutePreferenceRepository:
    """Provide a route preference repository instance per request."""

    return RoutePreferenceRepository(client=client, index_name=settings.user_routes_index)


def get_route_preference_service(
    repository: RoutePreferenceRepository = Depends(get_route_preference_repository),
) -> RoutePreferenceService:
    """Provide a route preference service instance per request."""

    return RoutePreferenceService(repository=repository)


def get_transport_graph_service(
    service: TransportGraphService = Depends(get_transport_service),
) -> TransportGraphService:
    """Provide the transport graph service instance for request scoped dependencies."""

    return service
