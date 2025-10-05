#!/bin/bash
# Transport Routes Testing Script Wrapper
# 
# This script provides an easy way to run transport routes tests
# with common configurations and options.

set -e

# Default values
BASE_URL="http://localhost:8000"
VERBOSE=false
OUTPUT_FILE=""
HELP=false

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --base-url)
            BASE_URL="$2"
            shift 2
            ;;
        --verbose|-v)
            VERBOSE=true
            shift
            ;;
        --output|-o)
            OUTPUT_FILE="$2"
            shift 2
            ;;
        --help|-h)
            HELP=true
            shift
            ;;
        *)
            echo "Unknown option: $1"
            HELP=true
            shift
            ;;
    esac
done

# Show help if requested
if [ "$HELP" = true ]; then
    echo "Transport Routes Testing Script"
    echo ""
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  --base-url URL     Base URL of the API (default: http://localhost:8000)"
    echo "  --verbose, -v      Enable verbose logging"
    echo "  --output FILE, -o  Save test results to JSON file"
    echo "  --help, -h         Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0                                    # Run tests with default settings"
    echo "  $0 --verbose                          # Run with verbose output"
    echo "  $0 --base-url http://api:8000         # Test remote API"
    echo "  $0 --output results.json              # Save results to file"
    echo ""
    echo "Prerequisites:"
    echo "  - Python 3.11+ with aiohttp installed"
    echo "  - API server running at the specified base URL"
    echo "  - node_name_mapping.json file in the project root"
    exit 0
fi

# Check if Python script exists
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_SCRIPT="$SCRIPT_DIR/test_transport_routes.py"

if [ ! -f "$PYTHON_SCRIPT" ]; then
    echo "Error: Python test script not found at $PYTHON_SCRIPT"
    exit 1
fi

# Check if node mapping file exists
NODE_MAPPING_FILE="$(dirname "$SCRIPT_DIR")/node_name_mapping.json"
if [ ! -f "$NODE_MAPPING_FILE" ]; then
    echo "Warning: node_name_mapping.json not found at $NODE_MAPPING_FILE"
    echo "The script will use fallback mappings."
fi

# Build command
CMD="python3 $PYTHON_SCRIPT --base-url $BASE_URL"

if [ "$VERBOSE" = true ]; then
    CMD="$CMD --verbose"
fi

if [ -n "$OUTPUT_FILE" ]; then
    CMD="$CMD --output $OUTPUT_FILE"
fi

# Run the test
echo "Starting Transport Routes API Tests..."
echo "Base URL: $BASE_URL"
echo "Command: $CMD"
echo ""

eval $CMD
