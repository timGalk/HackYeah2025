"""Schemas for transport network endpoints."""

from __future__ import annotations

from typing import Any, Dict, List

from pydantic import BaseModel, Field, model_validator


class AvailableModesResponse(BaseModel):
    """List of transport graph modes exposed by the API."""

    modes: list[str] = Field(..., description="Transport modes available in the network.")


class EdgeUpdatePayload(BaseModel):
    """Payload describing the adjustments to apply to a graph edge."""

    key: str | int | None = Field(
        default=None,
        description="Specific edge key in a MultiDiGraph. Defaults to the first matching edge.",
    )
    weight: float | None = Field(
        default=None,
        ge=0,
        description="Explicit weight (seconds) to assign to the edge.",
    )
    speed_kmh: float | None = Field(
        default=None,
        gt=0,
        description="Speed in km/h used to recompute the edge weight when distance metadata exists.",
    )

    @model_validator(mode="after")
    def ensure_modification(self) -> "EdgeUpdatePayload":
        """Ensure at least one modifiable attribute has been provided."""

        if self.weight is None and self.speed_kmh is None:
            msg = "Supply either 'weight' or 'speed_kmh' to modify an edge."
            raise ValueError(msg)
        return self


class EdgeDetail(BaseModel):
    """Representation of a transport graph edge after modification."""

    mode: str = Field(..., description="Transport mode identifier.")
    source: str = Field(..., description="Edge source node identifier.")
    target: str = Field(..., description="Edge target node identifier.")
    key: str | int = Field(..., description="Unique key for the MultiDiGraph edge.")
    weight: float = Field(..., description="Edge weight expressed in seconds.")
    speed_kmh: float | None = Field(
        default=None, description="Speed in km/h associated with this edge, if applicable."
    )
    distance_km: float | None = Field(
        default=None, description="Great-circle distance between nodes in kilometres."
    )
    connector: bool | None = Field(
        default=None, description="Indicates if the edge was injected to ensure connectivity."
    )

    model_config = {
        "extra": "allow",
        "json_schema_extra": {
            "examples": [
                {
                    "mode": "walking",
                    "source": "stop_a",
                    "target": "stop_b",
                    "key": "walk-stop_a-stop_b",
                    "weight": 180.0,
                    "speed_kmh": 5.0,
                    "distance_km": 0.25,
                }
            ]
        },
    }


class EdgeUpdateResponse(BaseModel):
    """Response returned after applying updates to an edge."""

    edge: EdgeDetail


class EdgeErrorResponse(BaseModel):
    """Error payload used when edge manipulation fails."""

    detail: str
    context: dict[str, Any] | None = None


class ClosestEdgeUpdatePayload(BaseModel):
    """Payload for updating the nearest non-walking/non-bike edge."""

    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    weight: float = Field(
        ..., gt=0, description="New weight (seconds) that should be applied to the edge."
    )


class ClosestEdgeUpdateResponse(BaseModel):
    """Response returned after the nearest edge has been updated."""

    edge: EdgeDetail


class ClosestEdgeLookupPayload(BaseModel):
    """Payload for querying the closest transit edge."""

    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)


class ClosestEdgeLookupResponse(BaseModel):
    """Response containing details about the closest transit edge."""

    edge: EdgeDetail


class GraphNode(BaseModel):
    """Node representation used in transport graph snapshots."""

    id: str = Field(..., description="Unique node identifier.")
    latitude: float | None = Field(
        default=None, description="Latitude associated with the node, when available."
    )
    longitude: float | None = Field(
        default=None, description="Longitude associated with the node, when available."
    )
    bike_accessible: bool | None = Field(
        default=None, description="Flag indicating whether bikes can access this node."
    )
    metadata: Dict[str, Any] | None = Field(
        default=None, description="Additional attributes attached to the node."
    )


class GraphEdge(BaseModel):
    """Edge representation used in transport graph snapshots."""

    source: str = Field(..., description="Source node identifier.")
    target: str = Field(..., description="Target node identifier.")
    key: str | int = Field(..., description="Unique multigraph key for the edge.")
    weight: float | None = Field(
        default=None, description="Weight of the edge expressed in seconds."
    )
    mode: str | None = Field(
        default=None, description="Mode the edge belongs to if it differs from the graph label."
    )
    distance_km: float | None = Field(
        default=None, description="Great-circle distance covered by the edge."
    )
    speed_kmh: float | None = Field(
        default=None, description="Traversal speed for the edge, when available."
    )
    connector: bool | None = Field(
        default=None, description="True when the edge was injected to ensure connectivity."
    )
    metadata: Dict[str, Any] | None = Field(
        default=None, description="Additional edge attributes preserved for visualization."
    )


class GraphPayload(BaseModel):
    """Snapshot of a transport graph with node and edge collections."""

    mode: str | None = Field(default=None, description="Transport mode identifier.")
    nodes: List[GraphNode]
    edges: List[GraphEdge]


class GraphSnapshotResponse(BaseModel):
    """Response containing serialized transport graphs for visualization."""

    graphs: Dict[str, GraphPayload]
