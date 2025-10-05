"""Business logic for ingesting and moderating Facebook posts."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any, Sequence

from app.repositories.facebook_posts import FacebookPostRepository
from app.schemas.facebook_posts import (
    FacebookPostDocument,
    FacebookPostRead,
    FacebookPostSource,
    FacebookPostListResponse,
    FacebookPostsUploadResponse,
)
from app.services.transport import TransportGraphService


class FacebookPostService:
    """Coordinate Facebook post ingestion workflows."""

    APPROVED_WEIGHT_MULTIPLIER = 2.0

    def __init__(
        self,
        *,
        repository: FacebookPostRepository,
        mock_data_path: Path,
        transport_service: TransportGraphService,
    ) -> None:
        self._repository = repository
        self._mock_data_path = mock_data_path
        self._transport_service = transport_service

    async def list_posts(self) -> FacebookPostListResponse:
        """Return Facebook posts ordered by scraping timestamp descending."""

        posts = await self._repository.list_posts()
        return FacebookPostListResponse(posts=self._to_models(posts))

    async def get_post(self, post_id: str) -> FacebookPostRead | None:
        """Return a single Facebook post by its identifier when it exists."""

        payload = await self._repository.get_post(post_id)
        if payload is None:
            return None
        return FacebookPostRead.model_validate(payload)

    async def posts_exist(self) -> bool:
        """Return ``True`` when at least one Facebook post has been ingested."""

        count = await self._repository.count_posts()
        return count > 0

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

    async def approve_post(self, post_id: str) -> bool:
        """Mark a post as approved and apply its impact to the nearest transit edge."""

        payload = await self._repository.get_post(post_id)
        if payload is None:
            return False

        latitude = payload.get("latitude")
        longitude = payload.get("longitude")
        if latitude is None or longitude is None:
            return False

        try:
            edge = self._transport_service.get_closest_transit_edge(
                latitude=float(latitude),
                longitude=float(longitude),
            )
        except ValueError:
            return False

        mode = edge.get("mode")
        source = edge.get("source")
        target = edge.get("target")
        if mode is None or source is None or target is None:
            return False

        baseline_weight = float(edge.get("weight", 0.0))
        if baseline_weight <= 0:
            return False

        applied_weight = baseline_weight * self.APPROVED_WEIGHT_MULTIPLIER

        self._transport_service.update_edge(
            mode=str(mode),
            source=str(source),
            target=str(target),
            key=edge.get("key"),
            weight=applied_weight,
            speed_kmh=None,
            event_context={"facebook_post_id": post_id},
        )

        update_payload = {
            "approved": True,
            "edge_mode": str(mode),
            "edge_source": str(source),
            "edge_target": str(target),
            "edge_key": str(edge.get("key")) if edge.get("key") is not None else None,
            "edge_weight_before": baseline_weight,
            "edge_weight_applied": applied_weight,
        }

        updated = await self._repository.update_post(post_id, update_payload)
        return updated

    async def revoke_post(self, post_id: str) -> bool:
        """Revert an approved post impact and mark it as unapproved."""

        payload = await self._repository.get_post(post_id)
        if payload is None:
            return False

        baseline_weight_raw = payload.get("edge_weight_before")
        mode = payload.get("edge_mode")
        source = payload.get("edge_source")
        target = payload.get("edge_target")
        key = payload.get("edge_key")

        try:
            baseline_weight = float(baseline_weight_raw) if baseline_weight_raw is not None else None
        except (TypeError, ValueError):
            baseline_weight = None

        if (
            baseline_weight is not None
            and baseline_weight > 0
            and mode is not None
            and source is not None
            and target is not None
        ):
            try:
                self._transport_service.update_edge(
                    mode=str(mode),
                    source=str(source),
                    target=str(target),
                    key=key,
                    weight=float(baseline_weight),
                    speed_kmh=None,
                    event_context={"facebook_post_id": post_id, "reverted": True},
                )
            except (KeyError, ValueError):
                # If the edge metadata is no longer valid we still proceed with the status change.
                pass

        update_payload = {
            "approved": False,
            "edge_weight_applied": None,
        }
        return await self._repository.update_post(post_id, update_payload)

    def _to_models(self, data: Sequence[dict[str, Any]]) -> list[FacebookPostRead]:
        """Convert raw payloads into typed Facebook post models."""

        return [FacebookPostRead.model_validate(item) for item in data]

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
