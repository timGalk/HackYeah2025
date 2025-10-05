#!/usr/bin/env python3
"""Validate that approving an incident rewards the reporter's social score."""

from __future__ import annotations

import argparse
import asyncio
import sys
import uuid
from typing import Any

import httpx


EXPECTED_REWARD = 10.0


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments for the verification script."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--base-url",
        default="http://localhost:8000",
        help="FastAPI service base URL (default: %(default)s)",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=15.0,
        help="HTTP timeout in seconds (default: %(default)s)",
    )
    parser.add_argument(
        "--latitude",
        type=float,
        default=50.064276,
        help="Incident latitude used for the test report (default: %(default)s)",
    )
    parser.add_argument(
        "--longitude",
        type=float,
        default=19.924364,
        help="Incident longitude used for the test report (default: %(default)s)",
    )
    parser.add_argument(
        "--initial-score",
        type=float,
        default=5.0,
        help="Initial reporter social score for the test incident (default: %(default)s)",
    )
    parser.add_argument(
        "--reward",
        type=float,
        default=EXPECTED_REWARD,
        help="Expected reward applied on approval (default: %(default)s)",
    )
    parser.add_argument(
        "--cleanup",
        action="store_true",
        help="Revoke approval at the end of the run.",
    )
    return parser.parse_args()


async def report_incident(
    client: httpx.AsyncClient,
    *,
    latitude: float,
    longitude: float,
    base_score: float,
) -> tuple[str, dict[str, Any]]:
    """Report an incident and return its identifier along with the stored payload."""

    unique_suffix = uuid.uuid4().hex[:8]
    payload = {
        "latitude": latitude,
        "longitude": longitude,
        "description": f"Automated approval reward check {unique_suffix}",
        "category": "Traffic",
        "username": f"reward-tester-{unique_suffix}",
        "approved": False,
        "reporter_social_score": base_score,
    }
    response = await client.post("/api/v1/incidents", json=payload)
    response.raise_for_status()
    document = response.json()
    incident_id = str(document.get("incident_id"))
    if not incident_id:
        raise RuntimeError("API did not return incident identifier.")
    return incident_id, payload


async def approve_incident(client: httpx.AsyncClient, *, incident_id: str) -> None:
    """Approve the incident via the admin endpoint."""

    response = await client.post(f"/admin/incidents/{incident_id}/approve")
    if response.status_code not in {200, 201, 202, 204, 303, 307}:
        response.raise_for_status()


async def fetch_incident(client: httpx.AsyncClient, *, incident_id: str) -> dict[str, Any]:
    """Retrieve the incident by scanning the incident list."""

    response = await client.get("/api/v1/incidents")
    response.raise_for_status()
    payload = response.json()
    incidents = payload.get("incidents", [])
    if not isinstance(incidents, list):
        raise RuntimeError("Unexpected API response structure; 'incidents' must be a list.")
    for incident in incidents:
        if str(incident.get("id")) == incident_id:
            return incident
    raise RuntimeError(f"Incident {incident_id} not found after approval.")


async def revoke_incident(client: httpx.AsyncClient, *, incident_id: str) -> None:
    """Revoke approval for cleanup purposes."""

    response = await client.post(f"/admin/incidents/{incident_id}/revoke")
    if response.status_code not in {200, 201, 202, 204, 303, 307}:
        response.raise_for_status()


async def main_async() -> int:
    args = parse_args()

    async with httpx.AsyncClient(
        base_url=args.base_url,
        timeout=args.timeout,
        follow_redirects=True,
    ) as client:
        created_id, request_payload = await report_incident(
            client,
            latitude=args.latitude,
            longitude=args.longitude,
            base_score=args.initial_score,
        )
        print(f"Reported incident {created_id} with base score {args.initial_score:.2f}.")

        await approve_incident(client, incident_id=created_id)
        print("Approval request sent. Waiting briefly for persistence…")
        await asyncio.sleep(0.5)

        document = await fetch_incident(client, incident_id=created_id)
        updated_score = float(document.get("reporter_social_score", 0.0))
        expected_score = request_payload["reporter_social_score"] + args.reward
        print(
            "Updated incident score: {score:.2f} (expected {expected:.2f})".format(
                score=updated_score,
                expected=expected_score,
            )
        )

        if abs(updated_score - expected_score) > 1e-6:
            raise RuntimeError(
                "Approval reward mismatch: expected {expected:.2f}, received {actual:.2f}".format(
                    expected=expected_score,
                    actual=updated_score,
                )
            )

        print("✅ Incident approval reward verified successfully.")

        if args.cleanup:
            await revoke_incident(client, incident_id=created_id)
            print("Approval revoked for cleanup.")

    return 0


def main() -> int:
    """Synchronously run the asynchronous entry point with error handling."""

    try:
        return asyncio.run(main_async())
    except httpx.HTTPError as exc:
        print(f"HTTP request failed: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:  # pragma: no cover - manual script guard
        print(f"Unexpected error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
