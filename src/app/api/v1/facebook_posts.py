"""Facebook post ingestion API routes."""

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.dependencies import get_facebook_post_service
from app.schemas.facebook_posts import (
    FacebookPostsUploadRequest,
    FacebookPostsUploadResponse,
)
from app.services.facebook_posts import FacebookPostService

router = APIRouter(prefix="/facebook-posts", tags=["facebook_posts"])


@router.post(
    "/upload",
    status_code=status.HTTP_200_OK,
    response_model=FacebookPostsUploadResponse,
    summary="Upload Facebook posts into Elasticsearch",
)
async def upload_facebook_posts(
    payload: FacebookPostsUploadRequest,
    service: FacebookPostService = Depends(get_facebook_post_service),
) -> FacebookPostsUploadResponse:
    """Ingest Facebook posts from mock data or trigger a live scrape (not yet implemented)."""

    try:
        return await service.upload_posts(source=payload.source)
    except FileNotFoundError as exc:
        msg = str(exc)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=msg) from exc
    except ValueError as exc:
        msg = str(exc)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=msg) from exc
