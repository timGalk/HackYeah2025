"""Repository for Facebook post persistence."""

from __future__ import annotations

from typing import Any, Iterable

from elasticsearch import AsyncElasticsearch, NotFoundError
from elasticsearch.helpers import async_bulk

from app.schemas.facebook_posts import FacebookPostDocument


class FacebookPostRepository:
    """Persist Facebook posts into the configured Elasticsearch index."""

    def __init__(self, client: AsyncElasticsearch, index_name: str) -> None:
        self._client = client
        self._index_name = index_name

    async def store_posts(self, posts: Iterable[FacebookPostDocument]) -> int:
        """Write the provided posts to Elasticsearch and return the stored count."""

        documents = list(posts)
        if not documents:
            return 0

        actions = (
            {
                "_op_type": "index",
                "_index": self._index_name,
                "_id": str(document.post_id),
                "_source": document.model_dump(mode="json"),
            }
            for document in documents
        )

        success, _ = await async_bulk(
            client=self._client,
            actions=actions,
            refresh=True,
        )
        return int(success)

    async def list_posts(self) -> list[dict[str, Any]]:
        """Return all Facebook posts sorted by scraping time descending."""

        response = await self._client.search(
            index=self._index_name,
            size=500,
            sort=[{"scraped_at": {"order": "desc"}}],
            query={"match_all": {}},
        )
        hits = response.get("hits", {}).get("hits", [])
        return [self._hydrate_hit(hit) for hit in hits]

    async def get_post(self, post_id: str) -> dict[str, Any] | None:
        """Fetch a single post by its identifier or return ``None`` when missing."""

        try:
            response = await self._client.get(index=self._index_name, id=post_id)
        except NotFoundError:
            return None
        return self._hydrate_hit(response)

    async def update_post(self, post_id: str, document: dict[str, Any]) -> bool:
        """Partially update a post document. Returns True when the post exists."""

        try:
            await self._client.update(
                index=self._index_name,
                id=post_id,
                doc=document,
                refresh="wait_for",
                retry_on_conflict=2,
            )
        except NotFoundError:
            return False
        return True

    async def count_posts(self) -> int:
        """Return the number of Facebook posts stored in the index."""

        response = await self._client.count(index=self._index_name)
        return int(response.get("count", 0))

    @staticmethod
    def _hydrate_hit(hit: dict[str, Any]) -> dict[str, Any]:
        """Merge Elasticsearch metadata with the persisted payload."""

        source = dict(hit.get("_source", {}))
        source["id"] = str(hit.get("_id"))
        return source
