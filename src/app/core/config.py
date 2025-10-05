"""Application configuration helpers."""

import os
from dataclasses import dataclass, field
from functools import lru_cache


@dataclass(frozen=True)
class Settings:
    """Runtime configuration for the FastAPI application."""

    app_name: str = "Incident API"
    app_version: str = os.getenv("APP_VERSION", "0.1.1")
    elasticsearch_url: str = field(
        default_factory=lambda: os.getenv(
            "ELASTICSEARCH_URL", "http://elasticsearch:9200"
        )
    )
    elasticsearch_index: str = field(
        default_factory=lambda: os.getenv("ELASTICSEARCH_INDEX", "incidents")
    )
    gtfs_feed_path: str = field(
        default_factory=lambda: os.getenv("GTFS_FEED_PATH", "otp_data/GTFS_KRK_A.zip")
    )
    walking_speed_kmh: float = field(
        default_factory=lambda: float(os.getenv("WALKING_SPEED_KMH", "5.0"))
    )
    bike_speed_kmh: float = field(
        default_factory=lambda: float(os.getenv("BIKE_SPEED_KMH", "20.0"))
    )
    bike_access_radius_m: float = field(
        default_factory=lambda: float(os.getenv("BIKE_ACCESS_RADIUS_M", "150"))
    )
    bike_parkings_path: str | None = field(
        default_factory=lambda: os.getenv("BIKE_PARKINGS_PATH")
    )

    def elasticsearch_hosts(self) -> list[str]:
        """Return the configured Elasticsearch hosts list for the async client."""

        return [self.elasticsearch_url]


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Provide a cached Settings instance."""

    return Settings()
