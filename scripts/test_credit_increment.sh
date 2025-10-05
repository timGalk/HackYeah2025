#!/bin/bash
# Test credit increment on incident approval workflow

set -e

echo "Testing credit increment on incident approval..."
echo "=============================================="
echo ""

cd "$(dirname "$0")/.."

uv run python scripts/test_credit_increment.py

echo ""
echo "Test completed!"

