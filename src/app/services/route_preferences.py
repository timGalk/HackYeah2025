"""Business logic around user route preferences."""

from __future__ import annotations

from typing import Sequence

from app.repositories.route_preferences import RoutePreferenceRepository
from app.schemas.route_preferences import (
    RoutePreferenceCreate,
    RoutePreferenceDeleteResponse,
    RoutePreferenceDocument,
    RoutePreferenceKind,
    RoutePreferenceListResponse,
    RoutePreferenceRead,
)


class RoutePreferenceService:
    """Coordinate route preference persistence workflows."""

    def __init__(self, repository: RoutePreferenceRepository) -> None:
        self._repository = repository

    async def add_or_update(self, payload: RoutePreferenceCreate) -> RoutePreferenceRead:
        """Store a new preference or update an existing one."""

        document = RoutePreferenceDocument(**payload.model_dump())
        preference_id = await self._repository.upsert_preference(document)
        return RoutePreferenceRead(id=preference_id, **document.model_dump())

    async def remove(self, *, user_id: str, route_id: str, kind: RoutePreferenceKind) -> RoutePreferenceDeleteResponse:
        """Delete a stored preference, returning whether it previously existed."""

        deleted = await self._repository.delete_preference(
            user_id=user_id,
            route_id=route_id,
            kind=kind,
        )
        return RoutePreferenceDeleteResponse(deleted=deleted)

    async def list_preferences(
        self,
        *,
        user_id: str,
        kinds: Sequence[RoutePreferenceKind] | None = None,
    ) -> RoutePreferenceListResponse:
        """Return all preferences for a user, optionally filtered by kind."""

        raw = await self._repository.list_preferences(user_id=user_id, kinds=kinds)
        preferences = [RoutePreferenceRead.model_validate(item) for item in raw]
        return RoutePreferenceListResponse(preferences=preferences)
