"""Background service adjusting transport graphs based on incidents."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Iterable
from contextlib import suppress
from typing import Any

from fastapi import FastAPI
from httpx import AsyncClient

from app.services.transport import TransportGraphService

EdgeKey = tuple[str, str, str, str | int]


class IncidentImpactService:
    """Poll incidents and update transport graphs according to delay factors."""

    INCIDENT_DELAY_MAPPING: dict[str, float] = {}

    def __init__(
        self,
        *,
        app: FastAPI,
        transport_service: TransportGraphService,
        interval_seconds: float,
    ) -> None:
        self._app = app
        self._transport_service = transport_service
        self._interval_seconds = max(interval_seconds, 1.0)
        self._logger = logging.getLogger(__name__)
        self._task: asyncio.Task[None] | None = None
        self._edge_baselines: dict[EdgeKey, float] = {}
        self._current_multipliers: dict[EdgeKey, float] = {}
        self._modified_edges: list[EdgeKey] = []

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

    @property
    def modified_edges(self) -> list[EdgeKey]:
        """Return the list of edges currently impacted by incidents."""

        return list(self._modified_edges)

    async def _run(self) -> None:
        async with AsyncClient(app=self._app, base_url="http://internal.app") as client:
            while True:
                try:
                    incidents = await self._fetch_incidents(client)
                    await self._apply_incident_impacts(incidents)
                except Exception:  # noqa: BLE001 - log and keep running
                    self._logger.exception("Failed to apply incident impacts to transport graph")
                await asyncio.sleep(self._interval_seconds)

    async def _fetch_incidents(self, client: AsyncClient) -> list[dict[str, Any]]:
        """Retrieve incidents via the public API endpoint."""

        response = await client.get("/api/v1/incidents")
        response.raise_for_status()
        payload = response.json()
        incidents = payload.get("incidents", [])
        if not isinstance(incidents, list):
            return []
        return incidents

    async def _apply_incident_impacts(self, incidents: Iterable[dict[str, Any]]) -> None:
        """Apply delay factors derived from incidents to the transport network."""

        target_multipliers: dict[EdgeKey, float] = {}

        for incident in incidents:
            category = incident.get("category")
            multiplier = self.INCIDENT_DELAY_MAPPING.get(str(category))
            if multiplier is None:
                continue
            if multiplier <= 0:
                continue

            latitude = incident.get("latitude")
            longitude = incident.get("longitude")
            if latitude is None or longitude is None:
                continue

            try:
                edge = self._transport_service.get_closest_transit_edge(
                    latitude=float(latitude),
                    longitude=float(longitude),
                )
            except ValueError:
                continue

            edge_key = (edge["mode"], edge["source"], edge["target"], edge["key"])
            baseline = self._edge_baselines.get(edge_key)
            current_multiplier = self._current_multipliers.get(edge_key, 1.0)
            if baseline is None:
                baseline = float(edge.get("weight", 0.0))
                if current_multiplier != 0:
                    baseline /= current_multiplier
                self._edge_baselines[edge_key] = baseline

            previous_best = target_multipliers.get(edge_key, 1.0)
            if multiplier > previous_best:
                target_multipliers[edge_key] = multiplier

        await self._apply_multipliers(target_multipliers)

    async def _apply_multipliers(self, target_multipliers: dict[EdgeKey, float]) -> None:
        """Update edges to match the target multipliers without compounding effects."""

        # Apply or update affected edges.
        for edge_key, multiplier in target_multipliers.items():
            baseline = self._edge_baselines.get(edge_key)
            if baseline is None:
                continue
            current = self._current_multipliers.get(edge_key, 1.0)
            if multiplier == current:
                continue
            desired_weight = baseline * multiplier
            self._transport_service.update_edge(
                mode=edge_key[0],
                source=edge_key[1],
                target=edge_key[2],
                key=edge_key[3],
                weight=desired_weight,
                speed_kmh=None,
                event_context={"multiplier": multiplier},
            )
            self._current_multipliers[edge_key] = multiplier

        # Revert edges no longer impacted.
        for edge_key, current_multiplier in list(self._current_multipliers.items()):
            if edge_key in target_multipliers:
                continue
            if current_multiplier == 1.0:
                continue
            baseline = self._edge_baselines.get(edge_key)
            if baseline is None:
                continue
            self._transport_service.update_edge(
                mode=edge_key[0],
                source=edge_key[1],
                target=edge_key[2],
                key=edge_key[3],
                weight=baseline,
                speed_kmh=None,
                event_context={"multiplier": 1.0},
            )
            self._current_multipliers[edge_key] = 1.0

        self._modified_edges = [
            edge_key
            for edge_key, multiplier in self._current_multipliers.items()
            if multiplier != 1.0
        ]
