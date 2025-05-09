#!/bin/bash

# Load environment variables from .env file if it exists
if [ -f .env ]; then
    echo "Loading environment variables from .env file"
    export $(grep -v '^#' .env | xargs)
else
    echo "No .env file found, using default configuration"
    # Set default values if .env doesn't exist
    export GUMCP_HOST=${GUMCP_HOST:-"0.0.0.0"}
    export GUMCP_PORT=${GUMCP_PORT:-"8000"}
fi

# Ensure GUMCP_HOST and GUMCP_PORT are set
export GUMCP_HOST=${GUMCP_HOST:-"0.0.0.0"}
export GUMCP_PORT=${GUMCP_PORT:-"8000"}

# Function to kill server process
kill_server() {
    echo "Checking for processes running on port $GUMCP_PORT..."
    if lsof -i :$GUMCP_PORT > /dev/null; then
        echo "Killing process running on port $GUMCP_PORT"
        lsof -ti :$GUMCP_PORT | xargs kill -9
        sleep 1
    fi
}

# Kill any existing server process
kill_server

echo "Starting guMCP development server on $GUMCP_HOST:$GUMCP_PORT with hot reloading"
python scripts/server_watcher.py
