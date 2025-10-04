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

    def elasticsearch_hosts(self) -> list[str]:
        """Return the configured Elasticsearch hosts list for the async client."""

        return [self.elasticsearch_url]


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Provide a cached Settings instance."""

    return Settings()
