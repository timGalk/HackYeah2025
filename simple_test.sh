#!/bin/bash

# Simple test script for Incident API
BASE_URL="http://localhost:8000"

echo "Testing Incident API..."

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
