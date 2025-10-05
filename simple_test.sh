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

# Test 1: Valid incident
echo "Test 1: Creating valid incident..."
curl -X POST "$BASE_URL/api/v1/incidents" \
  -H "Content-Type: application/json" \
  -d '{
    "latitude": 52.2297,
    "longitude": 21.0122,
    "description": "Broken traffic light",
    "category": "Traffic",
    "username": "test_user",
    "reporter_social_score": 12.5
  }'

echo -e "\n\n"

# Test 2: Another valid incident
echo "Test 2: Creating another incident..."
curl -X POST "$BASE_URL/api/v1/incidents" \
  -H "Content-Type: application/json" \
  -d '{
    "latitude": 50.0755,
    "longitude": 14.4378,
    "description": "Tram wywroclawiled itself",
    "category": "Infrastructure",
    "username": "city_reporter",
    "approved": false,
    "reporter_social_score": 8.0
  }'

echo -e "\n\n"

# Test 3: Invalid data
echo "Test 3: Testing invalid latitude..."
curl -X POST "$BASE_URL/api/v1/incidents" \
  -H "Content-Type: application/json" \
  -d '{
    "latitude": 95.0,
    "longitude": 21.0122,
    "description": "Test incident",
    "category": "Test",
    "username": "test_user",
    "reporter_social_score": 0.5
  }'

echo -e "\n\nDone!"
