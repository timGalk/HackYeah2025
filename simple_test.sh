#!/bin/bash

set -euo pipefail

BASE_URL=${BASE_URL:-"http://localhost:8000"}
USER_ID=${USER_ID:-"workflow-user"}
PREFERENCE_KIND=${PREFERENCE_KIND:-"frequent"}
NOTES=${NOTES:-"Created by simple_test.sh"}
LATITUDE=${LATITUDE:-"50.064276"}
LONGITUDE=${LONGITUDE:-"19.924364"}
CATEGORY=${CATEGORY:-"Traffic"}
DESCRIPTION=${DESCRIPTION:-"Workflow verification incident"}
USERNAME=${USERNAME:-"workflow_tester"}
CLEANUP=${CLEANUP:-"true"}

echo "Testing incident workflow with route-aware preferences..."

echo "1) Reporting incident near ${LATITUDE},${LONGITUDE}..."
CREATE_PAYLOAD=$(LATITUDE="$LATITUDE" LONGITUDE="$LONGITUDE" DESCRIPTION="$DESCRIPTION" CATEGORY="$CATEGORY" USERNAME="$USERNAME" uv run python - <<'PY'
import json
import os

payload = {
    "latitude": float(os.environ["LATITUDE"]),
    "longitude": float(os.environ["LONGITUDE"]),
    "description": os.environ["DESCRIPTION"],
    "category": os.environ["CATEGORY"],
    "username": os.environ["USERNAME"],
    "approved": True,
}
print(json.dumps(payload))
PY
)

CREATE_RESPONSE=$(curl -sS -X POST "$BASE_URL/api/v1/incidents" \
  -H "Content-Type: application/json" \
  -d "$CREATE_PAYLOAD")

INCIDENT_ID=$(printf '%s' "$CREATE_RESPONSE" | uv run python -c 'import json, sys
payload = json.load(sys.stdin)
incident_id = payload.get("incident_id")
if not incident_id:
  raise SystemExit(f"Failed to extract incident_id from response: {payload}")
print(incident_id)
')

echo "Incident stored with ID: ${INCIDENT_ID}"

sleep 1

echo "2) Retrieving incidents to locate route metadata..."
INCIDENT_LIST=$(curl -sS "$BASE_URL/api/v1/incidents")

ROUTE_METADATA=$(INCIDENT_LIST="$INCIDENT_LIST" INCIDENT_ID="$INCIDENT_ID" uv run python - <<'PY'
import json
import os
import sys

payload = json.loads(os.environ["INCIDENT_LIST"])
target = os.environ["INCIDENT_ID"]

for item in payload.get("incidents", []):
  if item.get("id") == target:
    route_id = item.get("route_id")
    if not route_id:
      sys.exit(
        "Incident %s lacks route metadata; ensure transport enrichment is running." % target
      )
    short = item.get("route_short_name") or ""
    long = item.get("route_long_name") or ""
    print(route_id)
    print(short)
    print(long)
    sys.exit(0)

sys.exit("Incident %s not found when listing incidents." % target)
PY
)

readarray -t ROUTE_FIELDS <<<"$ROUTE_METADATA"
ROUTE_ID="${ROUTE_FIELDS[0]}"
ROUTE_SHORT="${ROUTE_FIELDS[1]-}"
ROUTE_LONG="${ROUTE_FIELDS[2]-}"

echo "Route context: ID='${ROUTE_ID}', short='${ROUTE_SHORT}', long='${ROUTE_LONG}'"

export ROUTE_ID ROUTE_SHORT ROUTE_LONG PREFERENCE_KIND NOTES USER_ID

echo "3) Saving ${PREFERENCE_KIND} preference for user '${USER_ID}'..."
PREFERENCE_PAYLOAD=$(uv run python - <<'PY'
import json
import os

payload = {
  "user_id": os.environ["USER_ID"],
    "route_id": os.environ["ROUTE_ID"],
    "route_short_name": os.environ.get("ROUTE_SHORT") or None,
    "route_long_name": os.environ.get("ROUTE_LONG") or None,
    "kind": os.environ["PREFERENCE_KIND"],
    "notes": os.environ.get("NOTES"),
}

print(json.dumps(payload))
PY
)

PREFERENCE_RESPONSE=$(curl -sS -X PUT "$BASE_URL/api/v1/users/${USER_ID}/routes" \
  -H "Content-Type: application/json" \
  -d "$PREFERENCE_PAYLOAD")

echo "$PREFERENCE_RESPONSE"

echo "4) Listing stored preferences for '${USER_ID}'..."
PREFERENCES=$(curl -sS "$BASE_URL/api/v1/users/${USER_ID}/routes")
echo "$PREFERENCES"

echo "5) Querying incidents filtered by route '${ROUTE_ID}'..."
FILTERED=$(curl -sS -G "$BASE_URL/api/v1/incidents" --data-urlencode "routes=${ROUTE_ID}")
echo "$FILTERED"

if [[ "${CLEANUP}" == "true" ]]; then
  echo "6) Cleaning up stored preference..."
  CLEANUP_RESPONSE=$(curl -sS -X DELETE "$BASE_URL/api/v1/users/${USER_ID}/routes/${PREFERENCE_KIND}/${ROUTE_ID}")
  echo "$CLEANUP_RESPONSE"
fi

echo "Workflow completed successfully."
