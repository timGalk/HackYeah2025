"""Repository for Facebook post persistence."""

from __future__ import annotations

from typing import Iterable

from elasticsearch import AsyncElasticsearch
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
