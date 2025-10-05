"""API routes for managing user route preferences."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query, status

from app.api.dependencies import get_route_preference_service
from app.schemas.route_preferences import (
    RoutePreferenceCreate,
    RoutePreferenceDeleteResponse,
    RoutePreferenceKind,
    RoutePreferenceListResponse,
    RoutePreferenceRead,
)
from app.services.route_preferences import RoutePreferenceService

router = APIRouter(prefix="/users/{user_id}/routes", tags=["route-preferences"])

UserIdPath = Annotated[str, Path(..., min_length=1, max_length=255, description="Identifier of the user.")]
RouteIdPath = Annotated[str, Path(..., min_length=1, max_length=255, description="GTFS route identifier.")]
KindPath = Annotated[
    RoutePreferenceKind,
    Path(..., description="Preference type to manipulate (planned or frequent)."),
]


@router.get(
    "",
    response_model=RoutePreferenceListResponse,
    summary="List stored route preferences",
)
async def list_route_preferences(
    user_id: UserIdPath,
    kinds: list[RoutePreferenceKind] | None = Query(
        default=None,
        description="Optional filter restricting the result to selected preference kinds.",
    ),
    service: RoutePreferenceService = Depends(get_route_preference_service),
) -> RoutePreferenceListResponse:
    """Return all saved preferences for a user."""

    return await service.list_preferences(user_id=user_id, kinds=kinds)


@router.put(
    "",
    response_model=RoutePreferenceRead,
    status_code=status.HTTP_201_CREATED,
    summary="Add or update a route preference",
)
async def upsert_route_preference(
    user_id: UserIdPath,
    payload: RoutePreferenceCreate,
    service: RoutePreferenceService = Depends(get_route_preference_service),
) -> RoutePreferenceRead:
    """Persist a planned or frequent route for the user."""

    preference = payload.model_copy(update={"user_id": user_id})
    return await service.add_or_update(preference)


@router.delete(
    "/{kind}/{route_id}",
    response_model=RoutePreferenceDeleteResponse,
    summary="Remove a stored route preference",
)
async def delete_route_preference(
    user_id: UserIdPath,
    kind: KindPath,
    route_id: RouteIdPath,
    service: RoutePreferenceService = Depends(get_route_preference_service),
) -> RoutePreferenceDeleteResponse:
    """Delete the stored preference for a route, if any."""

    return await service.remove(user_id=user_id, route_id=route_id, kind=kind)
