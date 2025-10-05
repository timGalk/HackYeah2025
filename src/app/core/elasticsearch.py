"""Elasticsearch client management helpers."""

from elasticsearch import AsyncElasticsearch

from app.core.config import Settings


async def create_elasticsearch_client(settings: Settings) -> AsyncElasticsearch:
    """Instantiate an AsyncElasticsearch client using provided settings."""

    return AsyncElasticsearch(hosts=settings.elasticsearch_hosts())


async def close_elasticsearch_client(client: AsyncElasticsearch) -> None:
    """Gracefully close the AsyncElasticsearch client."""

    await client.close()


async def ensure_index(client: AsyncElasticsearch, index_name: str) -> None:
    """Ensure the target index exists in Elasticsearch with proper mappings."""

    index_exists = await client.indices.exists(index=index_name)
    if not index_exists:
        mappings = {
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
        await client.indices.create(index=index_name, mappings=mappings)
