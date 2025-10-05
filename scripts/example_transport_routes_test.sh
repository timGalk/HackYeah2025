#!/bin/bash
# Example usage of the Transport Routes Testing Script
#
# This script demonstrates various ways to use the transport routes testing script
# with different configurations and options.

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TEST_SCRIPT="$SCRIPT_DIR/test_transport_routes.sh"

echo "Transport Routes Testing Script Examples"
echo "========================================"
echo ""

# Example 1: Basic test run
echo "Example 1: Basic test run"
echo "Command: $TEST_SCRIPT"
echo "Description: Run all tests with default settings"
echo ""
read -p "Press Enter to run this example..."
$TEST_SCRIPT
echo ""

# Example 2: Verbose output
echo "Example 2: Verbose output"
echo "Command: $TEST_SCRIPT --verbose"
echo "Description: Run tests with detailed logging"
echo ""
read -p "Press Enter to run this example..."
$TEST_SCRIPT --verbose
echo ""

# Example 3: Save results to file
echo "Example 3: Save results to file"
echo "Command: $TEST_SCRIPT --output test_results.json"
echo "Description: Run tests and save results to JSON file"
echo ""
read -p "Press Enter to run this example..."
$TEST_SCRIPT --output test_results.json
echo "Results saved to test_results.json"
echo ""

# Example 4: Test different API endpoint
echo "Example 4: Test different API endpoint"
echo "Command: $TEST_SCRIPT --base-url http://api.example.com:8000"
echo "Description: Test a remote API endpoint"
echo ""
echo "Note: This example won't actually run since the endpoint doesn't exist"
echo "It's just to show the syntax for testing remote APIs"
echo ""

# Example 5: Combined options
echo "Example 5: Combined options"
echo "Command: $TEST_SCRIPT --verbose --output detailed_results.json"
echo "Description: Run tests with verbose output and save detailed results"
echo ""
read -p "Press Enter to run this example..."
$TEST_SCRIPT --verbose --output detailed_results.json
echo "Detailed results saved to detailed_results.json"
echo ""

echo "All examples completed!"
echo ""
echo "For more information, run: $TEST_SCRIPT --help"
