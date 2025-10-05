"""FastAPI application factory."""

from __future__ import annotations

import json
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Iterable

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.incidents import router as incidents_router
from app.api.v1.transport import router as transport_router
from app.core.config import Settings, get_settings
from app.core.elasticsearch import (
    close_elasticsearch_client,
    create_elasticsearch_client,
    ensure_index,
)
from app.services.transport import BikeParkingLocation, TransportGraphService


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage startup and shutdown resources for the FastAPI application."""

    settings: Settings = get_settings()
    app.state.settings = settings
    client = await create_elasticsearch_client(settings)
    app.state.elasticsearch = client
    await ensure_index(client, settings.elasticsearch_index)

    transport_service = TransportGraphService(
        feed_path=Path(settings.gtfs_feed_path),
        walker_speed_kmh=settings.walking_speed_kmh,
        bike_speed_kmh=settings.bike_speed_kmh,
        bike_access_radius_m=settings.bike_access_radius_m,
    )
    await transport_service.build_graphs()

    bike_parkings = _load_bike_parking_file(settings.bike_parkings_path)
    if bike_parkings:
        transport_service.load_bike_parkings(bike_parkings)

    app.state.transport_service = transport_service
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
    app.include_router(transport_router, prefix="/api/v1")
    return app


app = create_app()


def _load_bike_parking_file(path_str: str | None) -> list[BikeParkingLocation]:
    """Load bike parking coordinates from a JSON payload, if provided."""

    if not path_str:
        return []

    path = Path(path_str)
    if not path.exists():
        return []

    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)

    if isinstance(payload, dict) and "features" in payload:
        return _parse_geojson_features(payload["features"])
    if isinstance(payload, list):
        return _parse_simple_locations(payload)

    msg = "Unsupported bike parking file format. Expected list or GeoJSON FeatureCollection."
    raise ValueError(msg)


def _parse_simple_locations(payload: Iterable[dict[str, object]]) -> list[BikeParkingLocation]:
    """Parse a simple JSON list of objects with latitude and longitude keys."""

    locations: list[BikeParkingLocation] = []
    for item in payload:
        latitude = item.get("latitude") if isinstance(item, dict) else None
        longitude = item.get("longitude") if isinstance(item, dict) else None
        name = item.get("name") if isinstance(item, dict) else None
        if latitude is None or longitude is None:
            continue
        locations.append(
            BikeParkingLocation(
                latitude=float(latitude),
                longitude=float(longitude),
                name=str(name) if name is not None else None,
            )
        )
    return locations


def _parse_geojson_features(features: Iterable[dict[str, object]]) -> list[BikeParkingLocation]:
    """Parse bike parking locations from GeoJSON features."""

    locations: list[BikeParkingLocation] = []
    for feature in features:
        if not isinstance(feature, dict):
            continue
        geometry = feature.get("geometry")
        if not isinstance(geometry, dict):
            continue
        coordinates = geometry.get("coordinates")
        if (
            not isinstance(coordinates, (list, tuple))
            or len(coordinates) < 2
            or coordinates[0] is None
            or coordinates[1] is None
        ):
            continue
        properties = feature.get("properties")
        name = properties.get("name") if isinstance(properties, dict) else None
        longitude, latitude = float(coordinates[0]), float(coordinates[1])
        locations.append(BikeParkingLocation(latitude=latitude, longitude=longitude, name=name))
    return locations
