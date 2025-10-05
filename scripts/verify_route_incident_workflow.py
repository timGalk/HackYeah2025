#!/usr/bin/env python3
"""Exercise the route preference and incident filtering workflow via the public API."""

from __future__ import annotations

import argparse
import asyncio
import sys
from typing import Any

import httpx


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--base-url",
        default="http://localhost:8000",
        help="FastAPI service base URL (default: %(default)s)",
    )
    parser.add_argument(
        "--user-id",
        default="demo-user",
        help="User identifier used for storing route preferences (default: %(default)s)",
    )
    parser.add_argument(
        "--kind",
        choices=["planned", "frequent"],
        default="frequent",
        help="Route preference kind to exercise (default: %(default)s)",
    )
    parser.add_argument(
        "--notes",
        default="Created by verify_route_incident_workflow",
        help="Optional notes saved alongside the preference (default: %(default)s)",
    )
    parser.add_argument(
        "--cleanup",
        action="store_true",
        help="Remove the created route preference on success.",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=10.0,
        help="HTTP timeout in seconds (default: %(default)s)",
    )
    return parser.parse_args()


async def fetch_incidents(client: httpx.AsyncClient) -> list[dict[str, Any]]:
    response = await client.get("/api/v1/incidents")
    response.raise_for_status()
    payload = response.json()
    incidents = payload.get("incidents", [])
    return incidents if isinstance(incidents, list) else []


def select_incident_with_route(incidents: list[dict[str, Any]]) -> dict[str, Any] | None:
    for incident in incidents:
        route_id = incident.get("route_id")
        if isinstance(route_id, str) and route_id:
            return incident
    return None


async def upsert_route_preference(
    client: httpx.AsyncClient,
    *,
    user_id: str,
    incident: dict[str, Any],
    kind: str,
    notes: str | None,
) -> dict[str, Any]:
    payload = {
        "user_id": user_id,
        "route_id": incident.get("route_id"),
        "route_short_name": incident.get("route_short_name"),
        "route_long_name": incident.get("route_long_name"),
        "kind": kind,
        "notes": notes,
    }
    response = await client.put(f"/api/v1/users/{user_id}/routes", json=payload)
    response.raise_for_status()
    return response.json()


async def list_preferences(
    client: httpx.AsyncClient,
    *,
    user_id: str,
) -> list[dict[str, Any]]:
    response = await client.get(f"/api/v1/users/{user_id}/routes")
    response.raise_for_status()
    payload = response.json()
    preferences = payload.get("preferences", [])
    return preferences if isinstance(preferences, list) else []


async def query_incidents_by_route(
    client: httpx.AsyncClient,
    *,
    route_id: str,
) -> list[dict[str, Any]]:
    response = await client.get("/api/v1/incidents", params={"routes": [route_id]})
    response.raise_for_status()
    payload = response.json()
    incidents = payload.get("incidents", [])
    return incidents if isinstance(incidents, list) else []


async def delete_preference(
    client: httpx.AsyncClient,
    *,
    user_id: str,
    route_id: str,
    kind: str,
) -> dict[str, Any]:
    response = await client.delete(f"/api/v1/users/{user_id}/routes/{kind}/{route_id}")
    response.raise_for_status()
    return response.json()


async def main() -> int:
    args = parse_args()

    async with httpx.AsyncClient(base_url=args.base_url, timeout=args.timeout) as client:
        print(f"Fetching all incidents from {args.base_url}…")
        incidents = await fetch_incidents(client)
        if not incidents:
            print("No incidents available. Report an incident first, then re-run this script.")
            return 1

        incident = select_incident_with_route(incidents)
        if incident is None:
            print(
                "No incidents with route metadata were found. Ensure incidents have been processed "
                "by the transport enrichment logic and try again."
            )
            return 1

        route_id = incident["route_id"]
        print(
            "Using incident ID {id} on route {route} (short='{short}', long='{long}')".format(
                id=incident.get("id"),
                route=route_id,
                short=incident.get("route_short_name"),
                long=incident.get("route_long_name"),
            )
        )

        print(f"Saving {args.kind} route preference for user '{args.user_id}'…")
        preference = await upsert_route_preference(
            client,
            user_id=args.user_id,
            incident=incident,
            kind=args.kind,
            notes=args.notes,
        )
        print("Stored preference:")
        print(preference)

        print("Listing stored preferences for the user…")
        preferences = await list_preferences(client, user_id=args.user_id)
        print(f"Found {len(preferences)} preference(s).")

        print(f"Querying incidents filtered by route '{route_id}'…")
        filtered_incidents = await query_incidents_by_route(client, route_id=route_id)
        print(f"Retrieved {len(filtered_incidents)} incident(s) after filtering.")

        if filtered_incidents:
            first = filtered_incidents[0]
            print(
                "Example filtered incident: ID={id} route={route} multiplier={multiplier}".format(
                    id=first.get("id"),
                    route=first.get("route_id"),
                    multiplier=first.get("event_context", {}).get("multiplier"),
                )
            )

        if args.cleanup:
            print("Cleaning up stored preference…")
            deletion = await delete_preference(
                client,
                user_id=args.user_id,
                route_id=route_id,
                kind=args.kind,
            )
            print(deletion)

    print("Workflow completed successfully.")
    return 0


if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
    except httpx.HTTPError as exc:
        print(f"HTTP request failed: {exc}", file=sys.stderr)
        exit_code = 1
    except Exception as exc:  # pragma: no cover - manual script guard
        print(f"Unexpected error: {exc}", file=sys.stderr)
        exit_code = 1
    sys.exit(exit_code)
