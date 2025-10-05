"""Multimodal transport network construction and manipulation services."""

from __future__ import annotations

import asyncio
from asyncio import Queue, QueueEmpty, QueueFull
from contextlib import suppress
from dataclasses import dataclass
from math import asin, cos, radians, sin, sqrt
from pathlib import Path
from threading import Lock
from typing import Any, Iterable, Sequence

import gtfs_kit as gk
import networkx as nx
import pandas as pd

from app.core.node_mapping import get_node_name


WEIGHT_EPSILON = 1e-6
EDGE_METADATA_EXCLUDE = {
    "weight",
    "default_weight",
    "mode",
    "distance_km",
    "speed_kmh",
    "connector",
}


class MultimodalDiGraph(nx.MultiDiGraph):
    """Thin wrapper around :class:`networkx.MultiDiGraph` for clarity."""


@dataclass(frozen=True)
class BikeParkingLocation:
    """Geographical representation of a bike parking facility."""

    latitude: float
    longitude: float
    name: str | None = None


class TransportGraphService:
    """Construct and manage multimodal transport graphs from GTFS sources."""

    _ROUTE_TYPE_LABELS: dict[int, str] = {
        0: "tram",
        1: "subway",
        2: "rail",
        3: "bus",
        4: "ferry",
        5: "cable_tram",
        6: "aerial_lift",
        7: "funicular",
        11: "trolleybus",
        12: "monorail",
    }

    def __init__(
        self,
        *,
        feed_path: Path,
        walker_speed_kmh: float = 5.0,
        bike_speed_kmh: float = 20.0,
        bike_access_radius_m: float = 150.0,
    ) -> None:
        self._feed_path = feed_path
        self._walker_speed_kmh = walker_speed_kmh
        self._bike_speed_kmh = bike_speed_kmh
        self._bike_access_radius_km = bike_access_radius_m / 1000
        self._graphs: dict[str, MultimodalDiGraph] = {}
        self._bike_parkings: list[BikeParkingLocation] = []
        self._subscribers: set[Queue[dict[str, Any]]] = set()
        self._subscribers_lock = Lock()

    async def build_graphs(self) -> None:
        """Load the GTFS feed and populate transport graphs."""

        await asyncio.to_thread(self._build_graphs_sync)
        self._broadcast_snapshot()

    def get_graph(self, mode: str) -> MultimodalDiGraph:
        """Return the graph for a specific transport mode."""

        graph = self._graphs.get(mode)
        if graph is None:
            msg = f"Transport graph for mode '{mode}' is not available."
            raise KeyError(msg)
        return graph

    def available_modes(self) -> list[str]:
        """List the transport modes with constructed graphs."""

        return sorted(self._graphs.keys())

    def load_bike_parkings(
        self, locations: Iterable[BikeParkingLocation], *, proximity_override_m: float | None = None
    ) -> None:
        """Register bike parking locations and refresh bike accessibility metadata."""

        self._bike_parkings = list(locations)
        if proximity_override_m is not None:
            self._bike_access_radius_km = proximity_override_m / 1000
        self._annotate_bike_accessible_nodes()
        self._refresh_bike_graph()
        self._broadcast_snapshot()

    def update_edge(
        self,
        *,
        mode: str,
        source: str,
        target: str,
        key: str | int | None,
        weight: float | None = None,
        speed_kmh: float | None = None,
        event_context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Update edge attributes for a selected edge and return the new state."""

        graph = self.get_graph(mode)
        try:
            candidate_edges = graph.get_edge_data(source, target)
        except KeyError as exc:  # pragma: no cover - networkx raises KeyError
            raise KeyError(f"Edge {source}->{target} not found in mode '{mode}'.") from exc

        if not candidate_edges:
            msg = f"Edge {source}->{target} not found in mode '{mode}'."
            raise KeyError(msg)

        resolved_key: str | int
        edge_payload: dict[str, Any]

        if key is None:
            resolved_key, edge_payload = next(iter(candidate_edges.items()))
        else:
            try:
                resolved_key = key
                edge_payload = candidate_edges[key]
            except KeyError as exc:
                formatted = ", ".join(str(existing_key) for existing_key in candidate_edges)
                msg = (
                    f"Edge key '{key}' does not exist for {source}->{target} in mode '{mode}'. "
                    f"Known keys: [{formatted}]"
                )
                raise KeyError(msg) from exc

        distance_km = edge_payload.get("distance_km")
        if speed_kmh is not None:
            if distance_km is None:
                msg = "Edge does not contain distance metadata required to derive weight from speed."
                raise ValueError(msg)
            weight = self._travel_time_seconds(distance_km, speed_kmh)
            edge_payload["speed_kmh"] = speed_kmh

        if weight is not None:
            if weight <= 0:
                msg = "Edge weight must be strictly positive."
                raise ValueError(msg)
            edge_payload["weight"] = weight

        # Update edge attributes using NetworkX's proper method
        graph.add_edge(source, target, key=resolved_key, **edge_payload)

        result = {
            "mode": mode,
            "source": source,
            "target": target,
            "key": resolved_key,
            **edge_payload,
        }
        if event_context:
            result.update(event_context)

        self._notify_subscribers({"type": "edge_updated", "edge": result})

        return result

    def update_closest_transit_edge(
        self,
        *,
        latitude: float,
        longitude: float,
        weight: float,
    ) -> dict[str, Any]:
        """Adjust the nearest non-walking/non-bike edge to the provided coordinates."""

        if weight <= 0:
            msg = "Edge weight must be strictly positive."
            raise ValueError(msg)

        mode, source, target, key, distance_km = self._closest_transit_edge_match(
            latitude=latitude,
            longitude=longitude,
        )
        updated = self.update_edge(
            mode=mode,
            source=source,
            target=target,
            key=key,
            weight=weight,
            speed_kmh=None,
            event_context={"distance_to_point_km": distance_km},
        )
        return updated

    def get_closest_transit_edge(
        self,
        *,
        latitude: float,
        longitude: float,
    ) -> dict[str, Any]:
        """Return metadata describing the closest non-walking/non-bike edge."""

        mode, source, target, key, distance_km = self._closest_transit_edge_match(
            latitude=latitude,
            longitude=longitude,
        )
        graph = self.get_graph(mode)
        edge_data = dict(graph[source][target][key])
        edge_data.update(
            {
                "mode": mode,
                "source": source,
                "target": target,
                "key": key,
                "distance_to_point_km": distance_km,
            }
        )
        return edge_data

    def plan_route_with_incidents(
        self,
        *,
        mode: str,
        source: str,
        target: str,
    ) -> dict[str, Any]:
        """Return the baseline path and an alternative when incidents slow edges."""

        graph = self.get_graph(mode)
        if source not in graph:
            msg = f"Source node '{source}' does not exist in mode '{mode}'."
            raise ValueError(msg)
        if target not in graph:
            msg = f"Target node '{target}' does not exist in mode '{mode}'."
            raise ValueError(msg)

        try:
            default_nodes = nx.shortest_path(graph, source, target, weight="default_weight")
        except nx.NetworkXNoPath as exc:
            msg = f"No path exists between '{source}' and '{target}' in mode '{mode}'."
            raise ValueError(msg) from exc

        default_segments = self._build_route_segments(graph, default_nodes)
        incident_detected = any(segment["impacted"] for segment in default_segments)

        alternative_nodes: Sequence[str] | None = None
        alternative_segments: list[dict[str, Any]] | None = None
        if incident_detected:
            clean_graph = self._graph_without_impacted_edges(graph)
            try:
                alternative_nodes = nx.shortest_path(
                    clean_graph,
                    source,
                    target,
                    weight="default_weight",
                )
            except nx.NetworkXNoPath:
                alternative_nodes = None

            if alternative_nodes and list(alternative_nodes) != list(default_nodes):
                alternative_segments = self._build_route_segments(graph, alternative_nodes)

        default_path_payload = self._shape_route_payload(default_nodes, default_segments)
        alternative_path_payload = (
            self._shape_route_payload(alternative_nodes, alternative_segments)
            if alternative_nodes and alternative_segments
            else None
        )

        message: str | None = None
        if incident_detected and alternative_path_payload is None:
            message = "Incidents detected on the default path; no unaffected alternative was found."
        elif incident_detected:
            message = "Incidents detected on the default path; alternative route suggested."

        return {
            "incident_detected": incident_detected,
            "message": message,
            "default_path": default_path_payload,
            "suggested_path": alternative_path_payload,
        }

    def _build_route_segments(
        self,
        graph: MultimodalDiGraph,
        nodes: Sequence[str],
    ) -> list[dict[str, Any]]:
        """Resolve edge details for a sequence of nodes."""

        segments: list[dict[str, Any]] = []
        for source, target in zip(nodes, nodes[1:]):
            key, data = self._resolve_edge_for_path(graph, source, target)
            default_weight = self._edge_default_weight(data)
            current_weight = self._edge_current_weight(data)
            impacted = self._is_edge_impacted(data)
            metadata = self._extract_edge_metadata(data)

            segment = {
                "source": source,
                "target": target,
                "key": key,
                "mode": data.get("mode", graph.graph.get("mode")),
                "default_weight": default_weight,
                "current_weight": current_weight,
                "impacted": impacted,
                "distance_km": data.get("distance_km"),
                "speed_kmh": data.get("speed_kmh"),
                "connector": data.get("connector"),
                "metadata": metadata or None,
            }
            segments.append(segment)
        return segments

    def _shape_route_payload(
        self,
        nodes: Sequence[str] | None,
        segments: list[dict[str, Any]] | None,
    ) -> dict[str, Any]:
        """Aggregate nodes and segments into a response-friendly structure."""

        if nodes is None or segments is None:
            msg = "Route payload requires both nodes and segments."
            raise ValueError(msg)

        total_default = sum(segment["default_weight"] for segment in segments)
        total_current = sum(segment["current_weight"] for segment in segments)
        return {
            "nodes": list(nodes),
            "segments": segments,
            "total_default_weight": total_default,
            "total_current_weight": total_current,
        }

    def _graph_without_impacted_edges(
        self,
        graph: MultimodalDiGraph,
    ) -> MultimodalDiGraph:
        """Return a copy of the graph without edges currently impacted by incidents."""

        clean_graph = graph.copy()
        impacted_edges = [
            (source, target, key)
            for source, target, key, data in graph.edges(keys=True, data=True)
            if self._is_edge_impacted(data)
        ]
        if impacted_edges:
            clean_graph.remove_edges_from(impacted_edges)
        return clean_graph

    def _resolve_edge_for_path(
        self,
        graph: MultimodalDiGraph,
        source: str,
        target: str,
    ) -> tuple[str | int, dict[str, Any]]:
        """Return the edge data representing the default traversal between two nodes."""

        edges = graph.get_edge_data(source, target)
        if not edges:
            msg = f"No edge found between '{source}' and '{target}'."
            raise ValueError(msg)

        best_key: str | int | None = None
        best_weight = float("inf")
        for key, data in edges.items():
            default_weight = self._edge_default_weight(data)
            if default_weight < best_weight:
                best_key = key
                best_weight = default_weight

        if best_key is None:
            msg = f"Unable to determine default edge for '{source}' -> '{target}'."
            raise ValueError(msg)

        return best_key, edges[best_key]

    @staticmethod
    def _edge_default_weight(data: dict[str, Any]) -> float:
        """Return the baseline weight stored on an edge."""

        default_weight = data.get("default_weight")
        if default_weight is None:
            default_weight = data.get("weight")
        if default_weight is None:
            msg = "Edge is missing weight metadata."
            raise ValueError(msg)
        return float(default_weight)

    def _edge_current_weight(self, data: dict[str, Any]) -> float:
        """Return the current effective weight for an edge."""

        weight = data.get("weight")
        if weight is None:
            return self._edge_default_weight(data)
        return float(weight)

    def _is_edge_impacted(self, data: dict[str, Any]) -> bool:
        """Determine whether the edge weight deviates from its default weight."""

        try:
            default_weight = self._edge_default_weight(data)
            current_weight = self._edge_current_weight(data)
        except ValueError:
            return False
        return current_weight - default_weight > WEIGHT_EPSILON

    def _extract_edge_metadata(self, data: dict[str, Any]) -> dict[str, Any]:
        """Return edge metadata excluding standard transport attributes."""

        return {
            key: value
            for key, value in data.items()
            if key not in EDGE_METADATA_EXCLUDE
        }

    def _closest_transit_edge_match(
        self,
        *,
        latitude: float,
        longitude: float,
    ) -> tuple[str, str, str, str | int, float]:
        """Locate the closest transit edge (excluding walking and bike modes)."""

        best_match: tuple[str, str, str, str | int, float] | None = None

        for mode, graph in self._graphs.items():
            if mode in {"walking", "bike"}:
                continue
            for source, target, key in graph.edges(keys=True):
                source_attrs = graph.nodes[source]
                target_attrs = graph.nodes[target]
                if not self._has_coordinates(source_attrs) or not self._has_coordinates(target_attrs):
                    continue
                midpoint_lat = (source_attrs["latitude"] + target_attrs["latitude"]) / 2
                midpoint_lon = (source_attrs["longitude"] + target_attrs["longitude"]) / 2
                distance_km = self._haversine_km(
                    latitude,
                    longitude,
                    midpoint_lat,
                    midpoint_lon,
                )
                if best_match is None or distance_km < best_match[4]:
                    best_match = (mode, source, target, key, distance_km)

        if best_match is None:
            msg = "No transit edges available to evaluate."
            raise ValueError(msg)

        return best_match

    # ---------------------------------------------------------------------
    # Internal helpers
    # ---------------------------------------------------------------------

    def _build_graphs_sync(self) -> None:
        """Synchronous graph building work to allow offloading to a thread."""

        feed_path = self._resolve_feed_path()
        feed = gk.read_feed(str(feed_path), dist_units="km")
        feed = self._narrow_feed_to_single_date(feed)

        if feed.stops is None or feed.stops.empty:
            msg = f"GTFS feed at {feed_path} has no stops data after date filtering."
            raise ValueError(msg)

        stops_df = feed.stops[["stop_id", "stop_lat", "stop_lon"]].copy()
        nodes_payload = {}
        for row in stops_df.itertuples(index=False):
            stop_id = str(row.stop_id)
            node_attrs = {
                "latitude": float(row.stop_lat),
                "longitude": float(row.stop_lon),
            }
            # Add stop name if available in mapping
            stop_name = get_node_name(stop_id)
            if stop_name:
                node_attrs["stop_name"] = stop_name
            nodes_payload[stop_id] = node_attrs

        base_graphs = self._build_transit_graphs(feed, nodes_payload)
        walking_graph = self._build_walking_graph(nodes_payload, base_graphs)
        self._graphs = {**base_graphs, "walking": walking_graph}

        # Precompute bike metadata even if there are no parkings yet.
        self._annotate_bike_accessible_nodes()
        self._refresh_bike_graph()

    def _narrow_feed_to_single_date(self, feed: gk.Feed) -> gk.Feed:
        """Restrict the feed to the first available service date to reduce graph size."""

        available_dates = feed.get_dates()
        if available_dates:
            narrowed = feed.restrict_to_dates([available_dates[0]])
            # Validate that the narrowed feed still has required data
            if narrowed.stops is not None and not narrowed.stops.empty:
                return narrowed
        return feed

    def _build_transit_graphs(
        self,
        feed: gk.Feed,
        nodes_payload: dict[str, dict[str, float]],
    ) -> dict[str, MultimodalDiGraph]:
        """Build graphs for every GTFS transit mode based on trip stop sequences."""

        graphs: dict[str, MultimodalDiGraph] = {}

        stop_times = feed.stop_times.copy()
        stop_times = stop_times.sort_values(["trip_id", "stop_sequence"])
        stop_times["next_stop_id"] = stop_times.groupby("trip_id")["stop_id"].shift(-1)

        stop_times["arrival_seconds"] = self._time_to_seconds(stop_times["arrival_time"])
        stop_times["next_arrival_seconds"] = stop_times.groupby("trip_id")["arrival_seconds"].shift(-1)
        stop_times["segment_duration"] = (
            stop_times["next_arrival_seconds"] - stop_times["arrival_seconds"]
        )

        merged = stop_times.dropna(subset=["next_stop_id", "segment_duration"]).copy()

        trips = feed.trips[["trip_id", "route_id"]]
        routes = feed.routes[["route_id", "route_type", "route_short_name", "route_long_name"]]
        merged = merged.merge(trips, on="trip_id", how="left")
        merged = merged.merge(routes, on="route_id", how="left")

        for mode, segments in merged.groupby("route_type"):
            label = self._ROUTE_TYPE_LABELS.get(int(mode), f"route_type_{int(mode)}")
            graph = MultimodalDiGraph(mode=label)
            self._add_nodes(graph, nodes_payload)

            for row in segments.itertuples(index=False):
                duration = float(row.segment_duration)
                if duration <= 0:
                    continue
                graph.add_edge(
                    row.stop_id,
                    row.next_stop_id,
                    key=row.trip_id,
                    weight=duration,
                    default_weight=duration,
                    mode=label,
                    trip_id=row.trip_id,
                    route_id=row.route_id,
                    route_short_name=row.route_short_name,
                    route_long_name=row.route_long_name,
                )

            graphs[label] = graph

        return graphs

    def _build_walking_graph(
        self,
        nodes_payload: dict[str, dict[str, float]],
        base_graphs: dict[str, MultimodalDiGraph],
    ) -> MultimodalDiGraph:
        """Derive a walking graph from stop adjacency and geographical distances."""

        walking_graph = MultimodalDiGraph(mode="walking")
        self._add_nodes(walking_graph, nodes_payload)

        walking_edges: dict[tuple[str, str], dict[str, Any]] = {}

        for graph in base_graphs.values():
            for source, target, _key in graph.edges(keys=True):
                if source == target:
                    continue
                edge_key = (source, target)
                reverse_key = (target, source)
                distance_km = self._distance_between_nodes(nodes_payload, source, target)
                if distance_km == 0:
                    continue
                travel_seconds = self._travel_time_seconds(distance_km, self._walker_speed_kmh)

                candidate_payload = {
                    "mode": "walking",
                    "distance_km": distance_km,
                    "speed_kmh": self._walker_speed_kmh,
                    "weight": travel_seconds,
                    "default_weight": travel_seconds,
                }

                if (
                    edge_key not in walking_edges
                    or travel_seconds < walking_edges[edge_key]["weight"]
                ):
                    walking_edges[edge_key] = candidate_payload
                if (
                    reverse_key not in walking_edges
                    or travel_seconds < walking_edges[reverse_key]["weight"]
                ):
                    walking_edges[reverse_key] = candidate_payload

        for (source, target), payload in walking_edges.items():
            walking_graph.add_edge(source, target, key=f"walk-{source}-{target}", **payload)

        self._ensure_connected(walking_graph, nodes_payload, self._walker_speed_kmh, mode="walking")
        return walking_graph

    def _add_nodes(
        self, graph: MultimodalDiGraph, nodes_payload: dict[str, dict[str, float]]
    ) -> None:
        """Populate a graph with nodes storing geographical metadata."""

        for node_id, attrs in nodes_payload.items():
            graph.add_node(node_id, **attrs)

    def _ensure_connected(
        self,
        graph: MultimodalDiGraph,
        nodes_payload: dict[str, dict[str, float]],
        speed_kmh: float,
        *,
        mode: str,
    ) -> None:
        """Add additional edges until the directed graph becomes weakly connected."""

        while True:
            components = list(nx.weakly_connected_components(graph))
            if len(components) <= 1:
                break

            source_component = components[0]
            best_pair: tuple[str, str] | None = None
            best_distance = float("inf")

            for source in source_component:
                for target in graph.nodes:
                    if target in source_component:
                        continue
                    distance_km = self._distance_between_nodes(nodes_payload, source, target)
                    if distance_km == 0:
                        continue
                    if distance_km < best_distance:
                        best_distance = distance_km
                        best_pair = (source, target)

            if best_pair is None:
                break

            source, target = best_pair
            travel_seconds = self._travel_time_seconds(best_distance, speed_kmh)
            payload = {
                "mode": mode,
                "distance_km": best_distance,
                "speed_kmh": speed_kmh,
                "weight": travel_seconds,
                "default_weight": travel_seconds,
                "connector": True,
            }
            graph.add_edge(source, target, key=f"{mode}-connector-{source}-{target}", **payload)
            graph.add_edge(target, source, key=f"{mode}-connector-{target}-{source}", **payload)

    def _distance_between_nodes(
        self, nodes_payload: dict[str, dict[str, float]], source: str, target: str
    ) -> float:
        """Return the great-circle distance between two nodes expressed in kilometres."""

        source_payload = nodes_payload[source]
        target_payload = nodes_payload[target]

        return self._haversine_km(
            source_payload["latitude"],
            source_payload["longitude"],
            target_payload["latitude"],
            target_payload["longitude"],
        )

    def _annotate_bike_accessible_nodes(self) -> None:
        """Mark nodes that are within reach of a registered bike parking."""

        if not self._bike_parkings:
            for graph in self._graphs.values():
                nx.set_node_attributes(graph, False, "bike_accessible")
            return

        for graph in self._graphs.values():
            accessibility: dict[str, bool] = {}
            for node, attrs in graph.nodes(data=True):
                accessibility[node] = self._is_within_bike_radius(attrs)
            nx.set_node_attributes(graph, accessibility, "bike_accessible")

    def _refresh_bike_graph(self) -> None:
        """Create or refresh the bike graph from the walking topology."""

        walking_graph = self._graphs.get("walking")
        if walking_graph is None:
            return

        bike_graph = MultimodalDiGraph(mode="bike")
        for node, attrs in walking_graph.nodes(data=True):
            bike_graph.add_node(node, **attrs)

        for source, target, key, payload in walking_graph.edges(keys=True, data=True):
            updated_payload = dict(payload)
            updated_payload["mode"] = "bike"

            distance_km = payload.get("distance_km")
            if distance_km is not None:
                if (
                    bike_graph.nodes[source].get("bike_accessible")
                    and bike_graph.nodes[target].get("bike_accessible")
                ):
                    speed = self._bike_speed_kmh
                else:
                    speed = self._walker_speed_kmh
                updated_payload["speed_kmh"] = speed
                updated_payload["weight"] = self._travel_time_seconds(distance_km, speed)
                updated_payload["default_weight"] = updated_payload["weight"]

            if "default_weight" not in updated_payload:
                updated_payload["default_weight"] = updated_payload.get("weight")

            bike_graph.add_edge(source, target, key=key, **updated_payload)

        self._ensure_connected(
            bike_graph,
            {node: {"latitude": data["latitude"], "longitude": data["longitude"]} for node, data in bike_graph.nodes(data=True)},
            self._bike_speed_kmh,
            mode="bike",
        )

        self._graphs["bike"] = bike_graph

    # ------------------------------------------------------------------
    # Public helpers for visualization
    # ------------------------------------------------------------------

    def subscribe(self) -> Queue[dict[str, Any]]:
        """Register a queue that will receive graph update events."""

        queue: Queue[dict[str, Any]] = Queue(maxsize=128)
        with self._subscribers_lock:
            self._subscribers.add(queue)
        return queue

    def unsubscribe(self, queue: Queue[dict[str, Any]]) -> None:
        """Remove a previously registered subscriber queue."""

        with self._subscribers_lock:
            self._subscribers.discard(queue)

    def graph_snapshot(self, *, mode: str | None = None) -> dict[str, Any]:
        """Serialize transport graphs for visualization clients."""

        if mode is not None:
            graph = self.get_graph(mode)
            return {mode: self._serialize_graph(graph)}
        return {
            graph_mode: self._serialize_graph(graph)
            for graph_mode, graph in self._graphs.items()
        }

    def _is_within_bike_radius(self, node_attrs: dict[str, Any]) -> bool:
        """Check if a node is within the configured radius of any bike parking."""

        latitude = node_attrs.get("latitude")
        longitude = node_attrs.get("longitude")
        if latitude is None or longitude is None:
            return False

        for parking in self._bike_parkings:
            distance_km = self._haversine_km(latitude, longitude, parking.latitude, parking.longitude)
            if distance_km <= self._bike_access_radius_km:
                return True
        return False

    @staticmethod
    def _travel_time_seconds(distance_km: float, speed_kmh: float) -> float:
        """Convert a distance expressed in kilometres to travel time in seconds."""

        return (distance_km / speed_kmh) * 3600

    @staticmethod
    def _has_coordinates(node_attrs: dict[str, Any]) -> bool:
        """Return True when node attributes contain latitude and longitude values."""

        return "latitude" in node_attrs and "longitude" in node_attrs

    def _broadcast_snapshot(self) -> None:
        """Dispatch a full graph snapshot to all subscribers."""

        if not self._subscribers:
            return
        snapshot = self.graph_snapshot()
        self._notify_subscribers({"type": "snapshot", "graphs": snapshot})

    def _serialize_graph(self, graph: MultimodalDiGraph) -> dict[str, Any]:
        """Convert a graph to serializable node and edge collections."""

        nodes_payload: list[dict[str, Any]] = []
        for node_id, attrs in graph.nodes(data=True):
            node_entry = {
                "id": node_id,
                "latitude": attrs.get("latitude"),
                "longitude": attrs.get("longitude"),
                "bike_accessible": attrs.get("bike_accessible"),
                "stop_name": attrs.get("stop_name"),
            }
            metadata = {
                key: value
                for key, value in attrs.items()
                if key not in {"latitude", "longitude", "bike_accessible", "stop_name"}
            }
            if metadata:
                node_entry["metadata"] = metadata
            nodes_payload.append(node_entry)

        edges_payload: list[dict[str, Any]] = []
        for source, target, key, attrs in graph.edges(keys=True, data=True):
            edge_entry = {
                "source": source,
                "target": target,
                "key": key,
                "weight": attrs.get("weight"),
                "mode": attrs.get("mode", graph.graph.get("mode")),
                "distance_km": attrs.get("distance_km"),
                "speed_kmh": attrs.get("speed_kmh"),
                "connector": attrs.get("connector"),
            }
            metadata = {
                edge_key: value
                for edge_key, value in attrs.items()
                if edge_key not in {"weight", "mode", "distance_km", "speed_kmh", "connector"}
            }
            if metadata:
                edge_entry["metadata"] = metadata
            edges_payload.append(edge_entry)

        return {
            "mode": graph.graph.get("mode"),
            "nodes": nodes_payload,
            "edges": edges_payload,
        }

    def _notify_subscribers(self, event: dict[str, Any]) -> None:
        """Push an event to all registered subscriber queues."""

        if not self._subscribers:
            return

        with self._subscribers_lock:
            subscribers = list(self._subscribers)

        for queue in subscribers:
            try:
                queue.put_nowait(event)
            except QueueFull:
                with suppress(QueueEmpty):
                    queue.get_nowait()
                with suppress(QueueFull):
                    queue.put_nowait(event)

    def _resolve_feed_path(self) -> Path:
        """Return an absolute path to the configured GTFS feed file."""

        feed_path = self._feed_path
        if not feed_path.is_absolute():
            feed_path = (Path.cwd() / feed_path).resolve()
        if not feed_path.exists():
            msg = f"GTFS feed not found at '{feed_path}'."
            raise FileNotFoundError(msg)
        return feed_path

    @staticmethod
    def _time_to_seconds(series: pd.Series) -> pd.Series:
        """Convert GTFS HH:MM:SS strings to seconds."""

        return pd.to_timedelta(series).dt.total_seconds()

    @staticmethod
    def _haversine_km(
        lat1: float,
        lon1: float,
        lat2: float,
        lon2: float,
    ) -> float:
        """Great-circle distance between two lat/lon pairs in kilometres."""

        radius_earth_km = 6371.0
        dlat = radians(lat2 - lat1)
        dlon = radians(lon2 - lon1)
        a = (
            sin(dlat / 2) ** 2
            + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) ** 2
        )
        return 2 * radius_earth_km * asin(sqrt(a))
