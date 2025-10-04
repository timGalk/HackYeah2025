"""FastAPI application factory."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.incidents import router as incidents_router
from app.core.config import Settings, get_settings
from app.core.elasticsearch import (
    close_elasticsearch_client,
    create_elasticsearch_client,
    ensure_index,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage startup and shutdown resources for the FastAPI application."""

    settings: Settings = get_settings()
    app.state.settings = settings
    client = await create_elasticsearch_client(settings)
    app.state.elasticsearch = client
    await ensure_index(client, settings.elasticsearch_index)
    try:
        yield
    finally:
        await close_elasticsearch_client(client)


def create_app() -> FastAPI:
    """Create and configure the FastAPI application instance."""

    settings = get_settings()
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(incidents_router, prefix="/api/v1")
    return app


app = create_app()
