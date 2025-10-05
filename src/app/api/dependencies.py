"""Dependency wiring for API routes."""

from fastapi import Depends, Request
from elasticsearch import AsyncElasticsearch

from app.core.config import Settings
from app.core.dependencies import (
    get_app_settings,
    get_elasticsearch_client,
    get_transport_service,
)
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


def get_facebook_post_service(request: Request) -> FacebookPostService:
    """Return the shared Facebook post service stored on application state."""

    service = getattr(request.app.state, "facebook_post_service", None)
    if service is None:
        msg = "Facebook post service is not configured on application state."
        raise RuntimeError(msg)
    return service


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
