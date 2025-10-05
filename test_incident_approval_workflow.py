#!/usr/bin/env python3
"""Scenario-driven integration test for incident approval workflow.

This script validates that incidents with insufficient social score do not affect
transport edge weights until they receive administrative approval. It uses the public
HTTP API via the ``requests`` library and assumes the FastAPI service is already
running with transport graphs built during startup.

Scenario covered:
1. A user reports a ``Traffic`` incident with a low social score (below the 50.0
   threshold), so the target edge weight should not change initially.
2. The incident is then approved via the admin API endpoint.
3. After approval, the incident should immediately apply its 1.5 multiplier to the
   edge weight, regardless of the low social score.

Usage:
    uv run python test_incident_approval_workflow.py

Environment variables:
    BASE_URL                 Base URL for the running API (default http://localhost:8000)
    TEST_LAT(TEST_LONG)      Coordinates used for nearest-edge lookups (defaults match
                             Kraków sample data).
    INCIDENT_WAIT_SECONDS    Maximum time in seconds to wait for the background incident
                             poller to process updates (default 90 seconds).
    INCIDENT_POLL_CHECK      Polling interval in seconds while waiting for graph updates
                             (default 3 seconds).

The script exits with code 0 on success and raises exceptions when expectations are not
met. It also prints progress messages for easier manual verification.
"""

from __future__ import annotations

import json
import os
import sys
import time
from typing import Any, Callable

import requests


BASE_URL = os.getenv("BASE_URL", "http://localhost:8000").rstrip("/")
INCIDENT_ENDPOINT = f"{BASE_URL}/api/v1/incidents"
LOOKUP_ENDPOINT = f"{BASE_URL}/api/v1/transport/graphs/nearest/lookup"
ADMIN_DELETE_ENDPOINT = f"{BASE_URL}/admin/incidents/api"
ADMIN_APPROVE_ENDPOINT = f"{BASE_URL}/admin/incidents"

TEST_LATITUDE = float(os.getenv("TEST_LAT", "50.062"))
TEST_LONGITUDE = float(os.getenv("TEST_LONG", "19.938"))

WAIT_TIMEOUT_SECONDS = float(os.getenv("INCIDENT_WAIT_SECONDS", "90"))
WAIT_INTERVAL_SECONDS = float(os.getenv("INCIDENT_POLL_CHECK", "3"))
BACKGROUND_POLL_SECONDS = float(os.getenv("INCIDENT_POLL_INTERVAL_SECONDS", "60"))


def _parse_json(response: requests.Response) -> dict[str, Any]:
    """Parse JSON payloads while supporting Infinity returned by the API."""

    return json.loads(response.text, parse_constant=lambda value: float(value))


def _check_server() -> None:
    """Ensure the service is reachable before executing scenarios."""

    docs_url = f"{BASE_URL}/docs"
    try:
        response = requests.get(docs_url, timeout=10)
        response.raise_for_status()
    except Exception as exc:  # pragma: no cover - script-level guardrail
        raise RuntimeError(
            "Unable to reach the running API. Make sure the service is up before "
            "executing this script."
        ) from exc


def _purge_incidents() -> None:
    """Remove all incidents via the admin API."""

    response = requests.delete(
        ADMIN_DELETE_ENDPOINT,
        json={},
        headers={"Accept": "application/json"},
        timeout=30,
    )
    response.raise_for_status()
    payload = _parse_json(response)
    deleted = payload.get("deleted")
    print(f"🧹 Purged incidents (deleted={deleted}).")


def _report_incident(payload: dict[str, Any]) -> str:
    """Report a single incident using the public API and return its ID."""

    response = requests.post(INCIDENT_ENDPOINT, json=payload, timeout=30)
    response.raise_for_status()
    data = response.json()
    incident_id = data.get("incident_id")
    print(f"   → Incident stored with id={incident_id} (category={payload['category']}).")
    return incident_id


def _approve_incident(incident_id: str) -> None:
    """Approve an incident via the admin API endpoint."""

    approve_url = f"{ADMIN_APPROVE_ENDPOINT}/{incident_id}/approve"
    response = requests.post(approve_url, timeout=30, allow_redirects=False)
    
    # The endpoint returns a redirect (303), which is expected
    if response.status_code not in (303, 200):
        response.raise_for_status()
    
    print(f"   ✓ Incident {incident_id} approved via admin API.")


def _lookup_edge() -> dict[str, Any]:
    """Retrieve details for the nearest edge to the configured coordinates."""

    payload = {
        "latitude": TEST_LATITUDE,
        "longitude": TEST_LONGITUDE,
    }
    response = requests.post(LOOKUP_ENDPOINT, json=payload, timeout=30)
    response.raise_for_status()
    data = _parse_json(response)
    return data["edge"]


def _wait_for_condition(
    *,
    predicate: Callable[[dict[str, Any]], bool],
    description: str,
    timeout: float = WAIT_TIMEOUT_SECONDS,
    interval: float = WAIT_INTERVAL_SECONDS,
) -> dict[str, Any]:
    """Poll the nearest-edge lookup until the predicate succeeds or times out."""

    deadline = time.perf_counter() + timeout
    last_edge: dict[str, Any] | None = None

    while time.perf_counter() < deadline:
        edge = _lookup_edge()
        last_edge = edge
        if predicate(edge):
            print(f"✅ {description}")
            return edge
        time.sleep(interval)

    raise TimeoutError(f"Timed out waiting for condition: {description}; last edge={last_edge}")


def _approx_equal(value: float, reference: float, *, tolerance: float = 1e-3) -> bool:
    """Return True when value is approximately reference within tolerance."""

    return abs(value - reference) <= tolerance * max(1.0, abs(reference))


def scenario_approval_workflow() -> None:
    """Validate that low-score incidents only affect edges after approval."""

    print("\n🧪 Scenario – Incident approval workflow (low social score)")
    _purge_incidents()

    baseline_edge = _lookup_edge()
    baseline_weight = baseline_edge["weight"]
    print(
        f"Baseline edge: mode={baseline_edge['mode']} source={baseline_edge['source']} "
        f"target={baseline_edge['target']} key={baseline_edge['key']} "
        f"weight={baseline_weight:.2f}"
    )

    # Step 1: Report an incident with low social score (below threshold of 50.0)
    low_score_incident = {
        "latitude": TEST_LATITUDE,
        "longitude": TEST_LONGITUDE,
        "description": "Traffic congestion reported by user with low social score",
        "category": "Traffic",
        "username": "low_score_user",
        "approved": False,
        "reporter_social_score": 10.0,  # Well below threshold of 50.0
    }

    print("Step 1: Submitting incident with low social score (10.0 < 50.0 threshold)...")
    incident_id = _report_incident(low_score_incident)

    # Wait for background poller to process the incident
    poll_wait = BACKGROUND_POLL_SECONDS + WAIT_INTERVAL_SECONDS
    print(f"Waiting {poll_wait:.1f}s to allow background poller to process incident...")
    time.sleep(poll_wait)

    # Step 2: Verify edge weight is unchanged (social score below threshold)
    def _unchanged(edge: dict[str, Any]) -> bool:
        return _approx_equal(edge["weight"], baseline_weight)

    _wait_for_condition(
        predicate=_unchanged,
        description="Edge weight unchanged (social score below threshold)",
    )

    # Step 3: Approve the incident via admin API
    print("\nStep 2: Approving the incident via admin API...")
    _approve_incident(incident_id)

    # Wait for background poller to apply the approval
    print(f"Waiting {poll_wait:.1f}s for background poller to apply approval...")
    time.sleep(poll_wait)

    # Step 4: Verify edge weight is now modified (approved incident applies multiplier)
    target_weight = baseline_weight * 1.5

    def _multiplied(edge: dict[str, Any]) -> bool:
        return _approx_equal(edge["weight"], target_weight, tolerance=1e-2)

    updated_edge = _wait_for_condition(
        predicate=_multiplied,
        description="Edge weight scaled by Traffic multiplier (1.5) after approval",
    )

    print(
        f"Edge weight after approval: "
        f"{updated_edge['weight']:.2f} (expected ≈{target_weight:.2f})"
    )
    print(
        "\n✨ Approval workflow validated: low-score incident had no effect until "
        "approved, then immediately applied its multiplier."
    )


def main() -> None:
    """Execute the approval workflow integration scenario."""

    print("=== Incident Approval Workflow Test ===")
    print(f"Base URL: {BASE_URL}")
    print(f"Coordinates: ({TEST_LATITUDE}, {TEST_LONGITUDE})")

    _check_server()
    scenario_approval_workflow()

    print("\n🎉 Approval workflow scenario completed successfully.")


if __name__ == "__main__":
    try:
        main()
    except Exception as error:  # pragma: no cover - script entry point guard
        print(f"❌ Scenario execution failed: {error}")
        sys.exit(1)

