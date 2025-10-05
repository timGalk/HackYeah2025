"""Business logic for ingesting Facebook posts."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any

from app.repositories.facebook_posts import FacebookPostRepository
from app.schemas.facebook_posts import (
    FacebookPostDocument,
    FacebookPostSource,
    FacebookPostsUploadResponse,
)


class FacebookPostService:
    """Coordinate Facebook post ingestion workflows."""

    def __init__(self, *, repository: FacebookPostRepository, mock_data_path: Path) -> None:
        self._repository = repository
        self._mock_data_path = mock_data_path

    async def upload_posts(self, *, source: FacebookPostSource) -> FacebookPostsUploadResponse:
        """Upload Facebook posts into Elasticsearch depending on the requested source."""

        if source is FacebookPostSource.SCRAPE:
            warning = "Live scraping is not implemented yet. Returning without ingestion."
            return FacebookPostsUploadResponse(uploaded=0, source=source, warning=warning)

        documents = await self._load_mock_posts(source)
        stored = await self._repository.store_posts(documents)
        warning: str | None = None
        if stored == 0:
            warning = "No posts were ingested from the mock dataset."
        return FacebookPostsUploadResponse(uploaded=stored, source=source, warning=warning)

    async def _load_mock_posts(self, source: FacebookPostSource) -> list[FacebookPostDocument]:
        """Load Facebook post payloads from the configured mock dataset."""

        if not self._mock_data_path.exists():
            msg = f"Mock data file not found at {self._mock_data_path}"
            raise FileNotFoundError(msg)

        raw_payload = await asyncio.to_thread(self._mock_data_path.read_text, "utf-8")
        data = json.loads(raw_payload)
        records = self._extract_records(data)
        documents: list[FacebookPostDocument] = []
        for record in records:
            try:
                documents.append(
                    FacebookPostDocument(
                        post_id=int(record["post_id"]),
                        description=str(record["description"]),
                        category=str(record["category"]),
                        stop_name=self._normalize_optional_string(record.get("stop_name")),
                        latitude=float(record["lat"]),
                        longitude=float(record["lon"]),
                        source=source,
                    )
                )
            except (KeyError, TypeError, ValueError) as exc:
                raise ValueError("Invalid record encountered in mock dataset.") from exc
        return documents

    @staticmethod
    def _extract_records(payload: Any) -> list[dict[str, Any]]:
        """Extract record dictionaries from the raw JSON payload."""

        if isinstance(payload, dict):
            results = payload.get("results")
            if isinstance(results, list):
                return [item for item in results if isinstance(item, dict)]
            raise ValueError("Mock dataset is missing the 'results' list.")
        if isinstance(payload, list):
            return [item for item in payload if isinstance(item, dict)]
        raise ValueError("Unsupported mock dataset structure.")

    @staticmethod
    def _normalize_optional_string(value: Any) -> str | None:
        """Convert optional values to clean strings where available."""

        if value is None:
            return None
        if isinstance(value, str):
            return value
        return str(value)
