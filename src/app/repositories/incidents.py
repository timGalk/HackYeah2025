"""Data layer for incident persistence."""

from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import datetime
from typing import Any

from elasticsearch import AsyncElasticsearch, NotFoundError
from elasticsearch.helpers import async_scan

from app.schemas.incidents import IncidentDocument


class IncidentRepository:
    """Repository responsible for persisting incidents to Elasticsearch."""

    def __init__(self, client: AsyncElasticsearch, index_name: str) -> None:
        self._client = client
        self._index_name = index_name

    async def create_incident(self, document: IncidentDocument) -> str:
        """Persist an incident document and return its identifier."""

        response = await self._client.index(
            index=self._index_name,
            document=document.model_dump(mode="json"),
            refresh="wait_for",
        )
        return str(response["_id"])

    async def get_recent_incidents(self, limit: int) -> list[dict[str, Any]]:
        """Return the most recent incidents sorted by creation time (descending)."""

        size = max(limit, 0)
        if size == 0:
            return []
        response = await self._client.search(
            index=self._index_name,
            size=size,
            sort=[{"created_at": {"order": "desc"}}],
            query={"match_all": {}},
        )
        hits = response.get("hits", {}).get("hits", [])
        return [self._hydrate_hit(hit) for hit in hits]

    async def get_incidents_between(
        self,
        *,
        start: datetime,
        end: datetime,
    ) -> list[dict[str, Any]]:
        """Return incidents created within the inclusive time interval."""

        query = {
            "range": {
                "created_at": {
                    "gte": start.isoformat(),
                    "lte": end.isoformat(),
                }
            }
        }
        body = {
            "query": query,
            "sort": [{"created_at": {"order": "asc"}}],
        }
        return [item async for item in self._scan(body=body)]

    async def get_all_incidents(self) -> list[dict[str, Any]]:
        """Return all persisted incidents sorted by creation time (ascending)."""

        body = {
            "query": {"match_all": {}},
            "sort": [{"created_at": {"order": "asc"}}],
        }
        return [item async for item in self._scan(body=body)]

    async def get_unapproved_incidents(self) -> list[dict[str, Any]]:
        """Return incidents that still await manual approval."""

        body = {
            "query": {
                "bool": {
                    "must_not": [
                        {"term": {"approved": True}},
                    ]
                }
            },
            "sort": [{"created_at": {"order": "asc"}}],
        }
        return [item async for item in self._scan(body=body)]

    async def approve_incident(self, incident_id: str) -> bool:
        """Mark an incident as approved. Returns False if it was not found."""

        return await self._set_incident_approval(incident_id=incident_id, approved=True)

    async def unapprove_incident(self, incident_id: str) -> bool:
        """Revoke approval for an incident if it exists."""

        return await self._set_incident_approval(incident_id=incident_id, approved=False)

    async def _set_incident_approval(self, *, incident_id: str, approved: bool) -> bool:
        """Toggle the approval flag for the given incident document."""

        try:
            response = await self._client.update(
                index=self._index_name,
                id=incident_id,
                doc={"approved": approved},
                refresh="wait_for",
                retry_on_conflict=2,
            )
        except NotFoundError:
            return False
        result = response.get("result")
        return result in {"updated", "noop"}

    async def _scan(
        self,
        *,
        body: dict[str, Any],
    ) -> AsyncIterator[dict[str, Any]]:
        """Iterate over incidents using the Elasticsearch scroll helper."""

        async for hit in async_scan(
            client=self._client,
            index=self._index_name,
            query=body,
            preserve_order=True,
        ):
            yield self._hydrate_hit(hit)

    @staticmethod
    def _hydrate_hit(hit: dict[str, Any]) -> dict[str, Any]:
        """Merge hit metadata with the source payload for downstream layers."""

        source = dict(hit.get("_source", {}))
        source["id"] = str(hit.get("_id"))
        return source
