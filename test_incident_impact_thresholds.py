#!/usr/bin/env python3
"""Scenario-driven integration check for incident impact thresholds.

This script mirrors the style of ``test_nearest_edge_workflow.py`` but focuses on
evaluating how incidents influence transport edge weights. It uses the public HTTP API
via the ``requests`` library and assumes the FastAPI service is already running and has
built its transport graphs during startup.

Two scenarios are covered:
1. Multiple unapproved ``Traffic`` incidents are reported but remain below the acceptance
   threshold, so the target edge weight should not change. After adding a third report
   that pushes the combined social score beyond the configured threshold, the edge weight
   should scale by the 1.5 multiplier.
2. An unapproved ``Crush`` incident is submitted. This category carries an infinite
   multiplier, so the target edge weight should immediately become infinite regardless of
   social score.

Usage:
    uv run python test_incident_impact_thresholds.py

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
import math
import os
import sys
import time
from typing import Any, Callable, Dict

import requests


BASE_URL = os.getenv("BASE_URL", "http://localhost:8000").rstrip("/")
INCIDENT_ENDPOINT = f"{BASE_URL}/api/v1/incidents"
LOOKUP_ENDPOINT = f"{BASE_URL}/api/v1/transport/graphs/nearest/lookup"
ADMIN_DELETE_ENDPOINT = f"{BASE_URL}/admin/incidents/api"

TEST_LATITUDE = float(os.getenv("TEST_LAT", "50.062"))
TEST_LONGITUDE = float(os.getenv("TEST_LONG", "19.938"))

WAIT_TIMEOUT_SECONDS = float(os.getenv("INCIDENT_WAIT_SECONDS", "90"))
WAIT_INTERVAL_SECONDS = float(os.getenv("INCIDENT_POLL_CHECK", "3"))
BACKGROUND_POLL_SECONDS = float(os.getenv("INCIDENT_POLL_INTERVAL_SECONDS", "60"))


def _parse_json(response: requests.Response) -> Dict[str, Any]:
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


def _report_incident(payload: Dict[str, Any]) -> None:
    """Report a single incident using the public API."""

    response = requests.post(INCIDENT_ENDPOINT, json=payload, timeout=30)
    response.raise_for_status()
    data = response.json()
    incident_id = data.get("incident_id")
    print(f"   → Incident stored with id={incident_id} (category={payload['category']}).")


def _lookup_edge() -> Dict[str, Any]:
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
    predicate: Callable[[Dict[str, Any]], bool],
    description: str,
    timeout: float = WAIT_TIMEOUT_SECONDS,
    interval: float = WAIT_INTERVAL_SECONDS,
) -> Dict[str, Any]:
    """Poll the nearest-edge lookup until the predicate succeeds or times out."""

    deadline = time.perf_counter() + timeout
    last_edge: Dict[str, Any] | None = None

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


def scenario_threshold_multiplier() -> None:
    """Validate that combined social scores gate the 1.5 multiplier."""

    print("\n🧪 Scenario 1 – Threshold-gated Traffic multiplier")
    _purge_incidents()

    baseline_edge = _lookup_edge()
    baseline_weight = baseline_edge["weight"]
    print(
        f"Baseline edge: mode={baseline_edge['mode']} source={baseline_edge['source']} "
        f"target={baseline_edge['target']} key={baseline_edge['key']} "
        f"weight={baseline_weight:.2f}"
    )

    initial_reports = [
        {
            "latitude": TEST_LATITUDE,
            "longitude": TEST_LONGITUDE,
            "description": "Traffic congestion reported by watcher A",
            "category": "Traffic",
            "username": "watcher_a",
            "approved": False,
            "reporter_social_score": 20.0,
        },
        {
            "latitude": TEST_LATITUDE,
            "longitude": TEST_LONGITUDE,
            "description": "Traffic congestion reported by watcher B",
            "category": "Traffic",
            "username": "watcher_b",
            "approved": False,
            "reporter_social_score": 25.0,
        },
    ]

    print("Submitting initial incidents (below threshold)...")
    for incident in initial_reports:
        _report_incident(incident)

    poll_wait = BACKGROUND_POLL_SECONDS + WAIT_INTERVAL_SECONDS
    print(f"Waiting {poll_wait:.1f}s to allow background poller to process incidents...")
    time.sleep(poll_wait)

    def _unchanged(edge: Dict[str, Any]) -> bool:
        return _approx_equal(edge["weight"], baseline_weight)

    _wait_for_condition(
        predicate=_unchanged,
        description="Edge weight unchanged (awaiting threshold)",
    )

    booster_incident = {
        "latitude": TEST_LATITUDE,
        "longitude": TEST_LONGITUDE,
        "description": "Additional report pushing threshold over 50",
        "category": "Traffic",
        "username": "watcher_c",
        "approved": False,
        "reporter_social_score": 15.0,
    }

    print("Adding booster incident to exceed threshold...")
    _report_incident(booster_incident)

    target_weight = baseline_weight * 1.5

    def _multiplied(edge: Dict[str, Any]) -> bool:
        return _approx_equal(edge["weight"], target_weight, tolerance=1e-2)

    updated_edge = _wait_for_condition(
        predicate=_multiplied,
        description="Edge weight scaled by Traffic multiplier (1.5)",
    )

    print(
        "Edge weight after multiplier: "
        f"{updated_edge['weight']:.2f} (expected ≈{target_weight:.2f})"
    )


def scenario_infinite_multiplier() -> None:
    """Validate that a "Crush" incident enforces a very large multiplier immediately."""

    print("\n🧪 Scenario 2 – Immediate Crush multiplier (blocked route)")
    _purge_incidents()

    # Ensure the previous multiplier has been reverted before continuing.
    initial_edge = _wait_for_condition(
        predicate=lambda edge: edge["weight"] is not None and edge["weight"] < 1e10,
        description="Edge weight reverted to normal baseline",
    )
    baseline_weight = initial_edge["weight"]

    crush_incident = {
        "latitude": TEST_LATITUDE,
        "longitude": TEST_LONGITUDE,
        "description": "Major crush event blocking the line",
        "category": "Crush",
        "username": "emergency_reporter",
        "approved": False,
        "reporter_social_score": 5.0,
    }

    print("Submitting crush incident (should apply immediately)...")
    _report_incident(crush_incident)

    def _blocked(edge: Dict[str, Any]) -> bool:
        weight = edge["weight"]
        # Check for very large weight (> 1e12 indicates a blocked route)
        return isinstance(weight, (float, int)) and weight > 1e12

    updated_edge = _wait_for_condition(
        predicate=_blocked,
        description="Edge weight increased to blocked state for crush incident",
    )

    print(
        "Edge weight after crush incident: "
        f"{updated_edge['weight']:.2e} (baseline was {baseline_weight:.2f})"
    )


def main() -> None:
    """Execute both integration scenarios and report their outcomes."""

    print("=== Incident Impact Threshold Scenarios ===")
    print(f"Base URL: {BASE_URL}")
    print(f"Coordinates: ({TEST_LATITUDE}, {TEST_LONGITUDE})")

    _check_server()
    scenario_threshold_multiplier()
    scenario_infinite_multiplier()

    print("\n🎉 All scenarios completed successfully.")


if __name__ == "__main__":
    try:
        main()
    except Exception as error:  # pragma: no cover - script entry point guard
        print(f"❌ Scenario execution failed: {error}")
        sys.exit(1)
