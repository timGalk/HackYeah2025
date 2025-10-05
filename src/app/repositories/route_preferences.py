"""Repository for user route preference persistence."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Sequence

from elasticsearch import AsyncElasticsearch, NotFoundError

from app.schemas.route_preferences import RoutePreferenceDocument, RoutePreferenceKind


class RoutePreferenceRepository:
    """Persist and query user route preferences in Elasticsearch."""

    def __init__(self, client: AsyncElasticsearch, index_name: str) -> None:
        self._client = client
        self._index_name = index_name

    async def upsert_preference(self, document: RoutePreferenceDocument) -> str:
        """Create or replace a preference using a deterministic identifier."""

        document_id = self._compose_id(
            user_id=document.user_id,
            route_id=document.route_id,
            kind=document.kind,
        )
        payload = document.model_copy(update={"updated_at": datetime.utcnow()})
        await self._client.index(
            index=self._index_name,
            id=document_id,
            document=payload.model_dump(mode="json"),
            refresh="wait_for",
        )
        return document_id

    async def delete_preference(self, *, user_id: str, route_id: str, kind: RoutePreferenceKind) -> bool:
        """Remove a stored preference if it exists."""

        document_id = self._compose_id(user_id=user_id, route_id=route_id, kind=kind)
        try:
            await self._client.delete(index=self._index_name, id=document_id, refresh="wait_for")
            return True
        except NotFoundError:
            return False

    async def list_preferences(
        self,
        *,
        user_id: str,
        kinds: Sequence[RoutePreferenceKind] | None = None,
    ) -> list[dict[str, Any]]:
        """Return all preferences for a user, optionally filtering by preference kind."""

        filters: list[dict[str, Any]] = [
            {"term": {"user_id.keyword": user_id}},
        ]
        if kinds:
            filters.append({"terms": {"kind.keyword": list(dict.fromkeys(kinds))}})
        query = {"bool": {"filter": filters}}
        response = await self._client.search(index=self._index_name, query=query, size=500)
        hits = response.get("hits", {}).get("hits", [])
        return [self._hydrate_hit(hit) for hit in hits]

    @staticmethod
    def _compose_id(*, user_id: str, route_id: str, kind: RoutePreferenceKind) -> str:
        """Create a deterministic document identifier."""

        return f"{user_id}::{route_id}::{kind}"

    @staticmethod
    def _hydrate_hit(hit: dict[str, Any]) -> dict[str, Any]:
        """Merge the Elasticsearch hit metadata with the source payload."""

        source = dict(hit.get("_source", {}))
        source["id"] = str(hit.get("_id"))
        return source
