"""Schemas for Facebook post ingestion endpoints."""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class FacebookPostSource(str, Enum):
    """Possible sources for Facebook posts provided to the API."""

    MOCK = "mock"
    SCRAPE = "scrape"


class FacebookPostDocument(BaseModel):
    """Representation of a Facebook post persisted to Elasticsearch."""

    post_id: int = Field(..., ge=0, description="Identifier of the scraped Facebook post.")
    description: str = Field(..., min_length=1, max_length=4000, description="Text content of the post.")
    category: str = Field(..., min_length=1, max_length=100, description="Assigned category for the post.")
    stop_name: str | None = Field(
        default=None,
        min_length=1,
        max_length=255,
        description="Optional stop name mentioned in the post.",
    )
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    source: FacebookPostSource = Field(
        default=FacebookPostSource.MOCK,
        description="Origin of the post payload ingested into the system.",
    )
    scraped_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Timestamp describing when the post payload was captured.",
    )
    approved: bool = Field(
        default=False,
        description="Whether the post has been approved by an administrator.",
    )
    edge_mode: str | None = Field(
        default=None,
        description="Transport mode of the closest edge affected by this post.",
    )
    edge_source: str | None = Field(
        default=None,
        description="Source node identifier of the impacted edge.",
    )
    edge_target: str | None = Field(
        default=None,
        description="Target node identifier of the impacted edge.",
    )
    edge_key: str | None = Field(
        default=None,
        description="Edge key within the transport graph corresponding to the impact.",
    )
    edge_weight_before: float | None = Field(
        default=None,
        gt=0,
        description="Baseline edge weight captured prior to applying the approval impact.",
    )
    edge_weight_applied: float | None = Field(
        default=None,
        gt=0,
        description="Edge weight applied when the post was approved.",
    )

    model_config = {
        "extra": "forbid",
    }


class FacebookPostRead(FacebookPostDocument):
    """Representation of a Facebook post retrieved from Elasticsearch."""

    id: str = Field(..., description="Elasticsearch document identifier assigned to the post.")


class FacebookPostListResponse(BaseModel):
    """Container for collections of Facebook posts."""

    posts: list[FacebookPostRead]


class FacebookPostsUploadRequest(BaseModel):
    """Payload accepted by the upload endpoint to select the ingestion source."""

    source: FacebookPostSource = Field(
        default=FacebookPostSource.MOCK,
        description="Select whether to load posts from mock data or perform live scraping.",
    )

    model_config = {
        "extra": "forbid",
    }


class FacebookPostsUploadResponse(BaseModel):
    """Response returned after attempting to ingest Facebook posts."""

    uploaded: int = Field(..., ge=0, description="Number of posts written to Elasticsearch.")
    source: FacebookPostSource = Field(..., description="Source that supplied the ingested posts.")
    warning: str | None = Field(
        default=None,
        description="Optional warning message providing additional ingestion details.",
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "uploaded": 10,
                    "source": "mock",
                    "warning": None,
                }
            ]
        }
    }
