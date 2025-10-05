"""Background polling service for ingesting Facebook posts."""

from __future__ import annotations

import asyncio
import logging
from contextlib import suppress

from app.schemas.facebook_posts import FacebookPostSource
from app.services.facebook_posts import FacebookPostService


class FacebookPostPollingService:
    """Periodically ingest Facebook posts into Elasticsearch."""

    def __init__(
        self,
        *,
        service: FacebookPostService,
        interval_seconds: float,
    ) -> None:
        self._service = service
        self._interval_seconds = max(interval_seconds, 1.0)
        self._logger = logging.getLogger(__name__)
        self._task: asyncio.Task[None] | None = None

    def start(self) -> None:
        """Start the background polling task if it is not already running."""

        if self._task is None:
            self._task = asyncio.create_task(self._run())

    async def stop(self) -> None:
        """Stop the background polling task."""

        if self._task is None:
            return
        self._task.cancel()
        with suppress(asyncio.CancelledError):
            await self._task
        self._task = None

    async def _run(self) -> None:
        while True:
            try:
                await self._poll_once()
            except Exception:  # noqa: BLE001 - log and continue polling
                self._logger.exception("Failed to poll Facebook posts for ingestion")
            await asyncio.sleep(self._interval_seconds)

    async def _poll_once(self) -> None:
        """Ingest Facebook posts from the mock source when none are present."""

        if await self._service.posts_exist():
            return

        response = await self._service.upload_posts(source=FacebookPostSource.MOCK)
        if response.uploaded > 0:
            self._logger.info("Uploaded %s mock Facebook posts", response.uploaded)
