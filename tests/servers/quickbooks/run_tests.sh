#!/bin/bash

# This script follows the contribution guidelines for running QuickBooks tests

# Change to the project root directory (assuming the script is run from the tests/servers/quickbooks directory)
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../" && pwd)"
cd "$ROOT_DIR" || exit 1

# Run the tests using the recommended test_runner.py
echo "Running QuickBooks tests using the project's test runner..."
python tests/servers/test_runner.py --server=quickbooks

# Optionally, you can run with the --remote flag if needed
# python tests/servers/test_runner.py --server=quickbooks --remote

# If you need to run the tests against a specific endpoint
# python tests/servers/test_runner.py --server=quickbooks --remote --endpoint=https://mcp.gumloop.com/quickbooks/{user_id}%3A{api_key} 