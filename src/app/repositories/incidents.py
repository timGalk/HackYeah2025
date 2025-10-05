"""Data layer for incident persistence."""

from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import datetime
from typing import Any, Sequence

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

    async def get_recent_incidents(
        self,
        limit: int,
        routes: Sequence[str] | None = None,
    ) -> list[dict[str, Any]]:
        """Return the most recent incidents sorted by creation time (descending)."""

        size = max(limit, 0)
        if size == 0:
            return []
        filters = self._build_route_filters(routes)
        query = self._assemble_query(filters)
        response = await self._client.search(
            index=self._index_name,
            size=size,
            sort=[{"created_at": {"order": "desc"}}],
            query=query,
        )
        hits = response.get("hits", {}).get("hits", [])
        return [self._hydrate_hit(hit) for hit in hits]

    async def get_incidents_between(
        self,
        *,
        start: datetime,
        end: datetime,
        routes: Sequence[str] | None = None,
    ) -> list[dict[str, Any]]:
        """Return incidents created within the inclusive time interval."""

        filters = [
            {
                "range": {
                    "created_at": {
                        "gte": start.isoformat(),
                        "lte": end.isoformat(),
                    }
                }
            }
        ]
        filters.extend(self._build_route_filters(routes))
        query = self._assemble_query(filters)
        body = {
            "query": query,
            "sort": [{"created_at": {"order": "asc"}}],
        }
        return [item async for item in self._scan(body=body)]

    async def get_all_incidents(
        self,
        routes: Sequence[str] | None = None,
    ) -> list[dict[str, Any]]:
        """Return all persisted incidents sorted by creation time (ascending)."""

        filters = self._build_route_filters(routes)
        query = self._assemble_query(filters)
        body = {
            "query": query,
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

    async def approve_incident(self, incident_id: str, *, reward_points: float = 0.0) -> bool:
        """Mark an incident as approved, optionally rewarding the reporter."""

        try:
            document = await self._client.get(index=self._index_name, id=incident_id)
        except NotFoundError:
            return False

        source = dict(document.get("_source", {}))
        if bool(source.get("approved")):
            return True

        reward = max(float(reward_points), 0.0)
        current_score = self._coerce_social_score(source.get("reporter_social_score"))
        updated_score = current_score + reward if reward > 0 else current_score

        source["approved"] = True
        source["reporter_social_score"] = updated_score

        response = await self._client.index(
            index=self._index_name,
            id=incident_id,
            document=source,
            refresh="wait_for",
        )
        result = response.get("result")
        return result in {"updated", "created"}

    async def unapprove_incident(self, incident_id: str) -> bool:
        """Revoke approval for an incident if it exists."""

        return await self._set_incident_approval(incident_id=incident_id, approved=False)

    async def delete_incidents_all(self) -> int:
        """Remove every incident document from the index."""

        response = await self._client.delete_by_query(
            index=self._index_name,
            body={"query": {"match_all": {}}},
            conflicts="proceed",
            refresh=True,
        )
        return int(response.get("deleted", 0))

    async def delete_incidents_in_range(self, *, start: datetime, end: datetime) -> int:
        """Remove incidents whose timestamps fall within the provided interval."""

        response = await self._client.delete_by_query(
            index=self._index_name,
            body={
                "query": {
                    "range": {
                        "created_at": {
                            "gte": start.isoformat(),
                            "lte": end.isoformat(),
                        }
                    }
                }
            },
            conflicts="proceed",
            refresh=True,
        )
        return int(response.get("deleted", 0))

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
    def _coerce_social_score(raw: Any) -> float:
        """Convert stored social score values into a sanitized float."""

        if raw is None:
            return 0.0
        if isinstance(raw, (int, float)):
            candidate = float(raw)
        else:
            try:
                candidate = float(str(raw))
            except (TypeError, ValueError):
                return 0.0
        return candidate if candidate >= 0 else 0.0

    @staticmethod
    def _hydrate_hit(hit: dict[str, Any]) -> dict[str, Any]:
        """Merge hit metadata with the source payload for downstream layers."""

        source = dict(hit.get("_source", {}))
        source["id"] = str(hit.get("_id"))
        return source

    @staticmethod
    def _assemble_query(filters: list[dict[str, Any]]) -> dict[str, Any]:
        """Compose an Elasticsearch query that applies the provided filters."""

        if not filters:
            return {"match_all": {}}
        return {"bool": {"filter": filters}}

    @staticmethod
    def _build_route_filters(routes: Sequence[str] | None) -> list[dict[str, Any]]:
        """Create filter clauses constraining incidents to specific routes."""

        if not routes:
            return []
        unique_routes = {str(route_id) for route_id in routes if route_id}
        if not unique_routes:
            return []
        return [{"terms": {"impacted_routes": sorted(unique_routes)}}]
