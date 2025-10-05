#!/usr/bin/env bash

# Demonstrate how incident impacts reshape planned routes.
#
# 1. Plans a baseline path using the incident-aware route endpoint.
# 2. Creates a high-confidence incident near the first segment of that path.
# 3. Waits for the background incident-impact service to adjust the graph.
# 4. Plans the same path again to surface the warning and suggested alternative.
#
# Configure the identifiers below before running. You can override them via environment
# variables, e.g. `MODE=subway SOURCE=stop_a TARGET=stop_f ./incident_route_demo.sh`.

set -euo pipefail

if ! command -v curl >/dev/null 2>&1; then
  echo "curl is required to run this script." >&2
  exit 1
fi

if ! command -v jq >/dev/null 2>&1; then
  echo "jq is required to run this script." >&2
  exit 1
fi

API_BASE="${API_BASE:-http://localhost:8000}"
MODE="${MODE:-bus}"
SOURCE="${SOURCE:-}"
TARGET="${TARGET:-}"

INCIDENT_CATEGORY="${INCIDENT_CATEGORY:-Traffic}"
INCIDENT_DESCRIPTION="${INCIDENT_DESCRIPTION:-Synthetic incident created by incident_route_demo.sh}"
INCIDENT_USERNAME="${INCIDENT_USERNAME:-route-demo}"
INCIDENT_SCORE="${INCIDENT_SCORE:-60}"
INCIDENT_APPROVED="${INCIDENT_APPROVED:-false}"
POLL_WAIT_SECONDS="${POLL_WAIT_SECONDS:-10}"

if [[ -z "$SOURCE" || -z "$TARGET" ]]; then
  echo "Please set SOURCE and TARGET to valid node identifiers before running." >&2
  exit 1
fi

plan_route() {
  curl -sS -G \
    --data-urlencode "mode=${MODE}" \
    --data-urlencode "source=${SOURCE}" \
    --data-urlencode "target=${TARGET}" \
    "${API_BASE}/api/v1/transport/routes"
}

fetch_graph() {
  curl -sS -G \
    --data-urlencode "mode=${MODE}" \
    "${API_BASE}/api/v1/transport/graphs"
}

node_component() {
  local graph_json=$1
  local node_id=$2
  local component=$3
  jq -r \
    --arg mode "$MODE" \
    --arg node "$node_id" \
    --arg component "$component" \
    '.graphs[$mode].nodes[] | select(.id == $node) | .[$component]' \
    <<<"$graph_json"
}

echo "== Baseline route =="
baseline_json=$(plan_route)
echo "$baseline_json" | jq

segment_count=$(echo "$baseline_json" | jq '.default_path.segments | length')
if [[ "$segment_count" -eq 0 ]]; then
  echo "The selected nodes do not produce a traversable path." >&2
  exit 1
fi

first_source=$(echo "$baseline_json" | jq -r '.default_path.segments[0].source')
first_target=$(echo "$baseline_json" | jq -r '.default_path.segments[0].target')

graph_json=$(fetch_graph)

incident_lat="${INCIDENT_LAT:-}"
incident_lon="${INCIDENT_LON:-}"

if [[ -z "$incident_lat" || -z "$incident_lon" ]]; then
  lat_a=$(node_component "$graph_json" "$first_source" "latitude")
  lon_a=$(node_component "$graph_json" "$first_source" "longitude")
  lat_b=$(node_component "$graph_json" "$first_target" "latitude")
  lon_b=$(node_component "$graph_json" "$first_target" "longitude")

  if [[ "$lat_a" == "null" || "$lon_a" == "null" || "$lat_b" == "null" || "$lon_b" == "null" ]]; then
    echo "Could not derive coordinates automatically. Supply INCIDENT_LAT and INCIDENT_LON." >&2
    exit 1
  fi

  incident_lat=$(awk "BEGIN {print ($lat_a + $lat_b) / 2}")
  incident_lon=$(awk "BEGIN {print ($lon_a + $lon_b) / 2}")
fi

echo "Using incident coordinates: ${incident_lat}, ${incident_lon}"

incident_payload=$(jq -n \
  --argjson latitude "$incident_lat" \
  --argjson longitude "$incident_lon" \
  --arg description "$INCIDENT_DESCRIPTION" \
  --arg category "$INCIDENT_CATEGORY" \
  --arg username "$INCIDENT_USERNAME" \
  --argjson score "$INCIDENT_SCORE" \
  --argjson approved "$( [[ "$INCIDENT_APPROVED" == "true" ]] && echo true || echo false )" \
  '{
     latitude: $latitude,
     longitude: $longitude,
     description: $description,
     category: $category,
     username: $username,
     reporter_social_score: $score,
     approved: $approved
   }')

echo "-- Creating synthetic incident"
incident_response=$(curl -sS \
  -H "Content-Type: application/json" \
  -X POST \
  -d "$incident_payload" \
  "${API_BASE}/api/v1/incidents")

echo "$incident_response" | jq
incident_id=$(echo "$incident_response" | jq -r '.incident_id // empty')

if [[ -z "$incident_id" ]]; then
  echo "Failed to record incident." >&2
  exit 1
fi

echo "Incident stored with id ${incident_id}. Waiting for ${POLL_WAIT_SECONDS}s so the impact service can react..."
sleep "$POLL_WAIT_SECONDS"

echo "== Post-incident route =="
post_incident_json=$(plan_route)
echo "$post_incident_json" | jq

echo "Script complete. Expect \"incident_detected\": true and, when available, a non-null \"suggested_path\" in the post-incident response."
