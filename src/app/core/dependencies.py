"""Shared FastAPI dependency providers."""

from fastapi import Request
from elasticsearch import AsyncElasticsearch

from app.core.config import Settings, get_settings
from app.services.transport import TransportGraphService


def get_app_settings() -> Settings:
    """Return application settings for request scope dependencies."""

    return get_settings()


def get_elasticsearch_client(request: Request) -> AsyncElasticsearch:
    """Return the Elasticsearch client stored on the FastAPI application state."""

    client = getattr(request.app.state, "elasticsearch", None)
    if client is None:
        msg = "Elasticsearch client is not configured on application state."
        raise RuntimeError(msg)
    return client


def get_transport_service(request: Request) -> TransportGraphService:
    """Return the transport graph service stored on the FastAPI application state."""

    service = getattr(request.app.state, "transport_service", None)
    if service is None:
        msg = "Transport graph service is not configured on application state."
        raise RuntimeError(msg)
    return service
