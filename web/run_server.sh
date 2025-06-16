#!/bin/bash
# Kill any existing servers on port 8000
echo "Killing any existing servers on port 8000..."
fuser -k 8000/tcp 2>/dev/null || true

# Wait a moment
sleep 2

# Start the server
echo "Starting server on port 8000..."
cd "$(dirname "$0")"
python app.py -p 8000