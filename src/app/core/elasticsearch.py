"""Elasticsearch client management helpers."""

from typing import Any

from elasticsearch import AsyncElasticsearch

from app.core.config import Settings


async def create_elasticsearch_client(settings: Settings) -> AsyncElasticsearch:
    """Instantiate an AsyncElasticsearch client using provided settings."""

    return AsyncElasticsearch(hosts=settings.elasticsearch_hosts())


async def close_elasticsearch_client(client: AsyncElasticsearch) -> None:
    """Gracefully close the AsyncElasticsearch client."""

    await client.close()


async def ensure_index(
    client: AsyncElasticsearch,
    index_name: str,
    *,
    mappings: dict[str, Any] | None = None,
) -> None:
    """Ensure the target index exists in Elasticsearch with the provided mappings."""

    index_exists = await client.indices.exists(index=index_name)
    if not index_exists:
        mapping_payload = mappings or {
            "properties": {
                "latitude": {"type": "float"},
                "longitude": {"type": "float"},
                "description": {"type": "text"},
                "category": {"type": "keyword"},
                "username": {"type": "keyword"},
                "approved": {"type": "boolean"},
                "reporter_social_score": {"type": "float"},
                "created_at": {"type": "date"},
            }
        }
        await client.indices.create(index=index_name, mappings=mapping_payload)


def facebook_posts_index_mappings() -> dict[str, Any]:
    """Return mappings tailored for the Facebook posts index."""

    return {
        "properties": {
            "post_id": {"type": "integer"},
            "description": {"type": "text"},
            "category": {"type": "keyword"},
            "stop_name": {"type": "keyword"},
            "latitude": {"type": "float"},
            "longitude": {"type": "float"},
            "source": {"type": "keyword"},
            "scraped_at": {"type": "date"},
            "approved": {"type": "boolean"},
            "edge_mode": {"type": "keyword"},
            "edge_source": {"type": "keyword"},
            "edge_target": {"type": "keyword"},
            "edge_key": {"type": "keyword"},
            "edge_weight_before": {"type": "float"},
            "edge_weight_applied": {"type": "float"},
        }
    }
