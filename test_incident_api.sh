#!/bin/bash

# Test script for Incident API endpoints
# This script tests the incident reporting functionality

set -e  # Exit on any error

# Configuration
BASE_URL="http://localhost:8000"
API_ENDPOINT="/api/v1/incidents"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    local color=$1
    local message=$2
    echo -e "${color}${message}${NC}"
}

# Function to check if server is running
check_server() {
    print_status $BLUE "Checking if server is running at $BASE_URL..."

    if curl -s -f "$BASE_URL/docs" > /dev/null 2>&1; then
        print_status $GREEN "✓ Server is running"
        return 0
    else
        print_status $RED "✗ Server is not running or not accessible at $BASE_URL"
        print_status $YELLOW "Please start the server with: uvicorn src.app.main:app --reload"
        return 1
    fi
}

# Function to test incident creation
test_create_incident() {
    local test_name="$1"
    local payload="$2"
    local expected_status="$3"

    print_status $BLUE "Testing: $test_name"

    response=$(curl -s -w "\n%{http_code}" \
        -X POST \
        -H "Content-Type: application/json" \
        -d "$payload" \
        "$BASE_URL$API_ENDPOINT")

    # Split response and status code
    http_code=$(echo "$response" | tail -n1)
    response_body=$(echo "$response" | head -n -1)

    if [ "$http_code" = "$expected_status" ]; then
        print_status $GREEN "✓ Test passed (HTTP $http_code)"
        echo "Response: $response_body" | jq . 2>/dev/null || echo "Response: $response_body"
    else
        print_status $RED "✗ Test failed (Expected HTTP $expected_status, got $http_code)"
        echo "Response: $response_body"
    fi

    echo ""
}

# Function to test API documentation endpoint
test_docs() {
    print_status $BLUE "Testing API documentation endpoint..."

    if curl -s -f "$BASE_URL/docs" > /dev/null 2>&1; then
        print_status $GREEN "✓ API docs accessible at $BASE_URL/docs"
    else
        print_status $RED "✗ API docs not accessible"
    fi
    echo ""
}

# Main test execution
main() {
    print_status $YELLOW "=== Incident API Test Suite ==="
    echo ""

    # Check if server is running
    if ! check_server; then
        exit 1
    fi

    echo ""

    # Test API docs
    test_docs

    # Test 1: Valid incident creation
    test_create_incident "Valid incident creation" '{
        "latitude": 52.2297,
        "longitude": 21.0122,
        "description": "Broken traffic light at intersection",
        "category": "Traffic",
        "username": "test_user",
        "reporter_social_score": 12.5
    }' "201"

    # Test 2: Another valid incident
    test_create_incident "Another valid incident" '{
        "latitude": 50.0755,
        "longitude": 14.4378,
        "description": "Pothole on main street causing traffic issues",
        "category": "Infrastructure",
        "username": "city_reporter",
        "reporter_social_score": 8.0
    }' "201"

    # Test 3: Invalid latitude (too high)
    test_create_incident "Invalid latitude (too high)" '{
        "latitude": 95.0,
        "longitude": 21.0122,
        "description": "Test incident",
        "category": "Test",
        "username": "test_user",
        "reporter_social_score": 0.5
    }' "422"

    # Test 4: Invalid longitude (too low)
    test_create_incident "Invalid longitude (too low)" '{
        "latitude": 52.2297,
        "longitude": -185.0,
        "description": "Test incident",
        "category": "Test",
        "username": "test_user",
        "reporter_social_score": 0.5
    }' "422"

    # Test 5: Missing required field
    test_create_incident "Missing required field (description)" '{
        "latitude": 52.2297,
        "longitude": 21.0122,
        "category": "Test",
        "username": "test_user",
        "reporter_social_score": 1.5
    }' "422"

    # Test 6: Empty description
    test_create_incident "Empty description" '{
        "latitude": 52.2297,
        "longitude": 21.0122,
        "description": "",
        "category": "Test",
        "username": "test_user",
        "reporter_social_score": 1.5
    }' "422"

    # Test 7: Description too long
    long_description=$(printf 'a%.0s' {1..2001})
    test_create_incident "Description too long" "{
        \"latitude\": 52.2297,
        \"longitude\": 21.0122,
        \"description\": \"$long_description\",
        \"category\": \"Test\",
        \"username\": \"test_user\",
        \"reporter_social_score\": 1.5
    }" "422"

    # Test 8: Extra field (should be rejected)
    test_create_incident "Extra field (should be rejected)" '{
        "latitude": 52.2297,
        "longitude": 21.0122,
        "description": "Test incident",
        "category": "Test",
        "username": "test_user",
        "reporter_social_score": 2.0,
        "extra_field": "should_not_be_allowed"
    }' "422"

    print_status $YELLOW "=== Test Suite Complete ==="
}

# Check if jq is available for pretty printing
if ! command -v jq &> /dev/null; then
    print_status $YELLOW "Note: Install 'jq' for prettier JSON output: brew install jq"
fi

# Run the tests
main "$@"
