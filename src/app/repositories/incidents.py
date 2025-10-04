"""Data layer for incident persistence."""

from elasticsearch import AsyncElasticsearch

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
