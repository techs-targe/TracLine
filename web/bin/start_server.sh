#!/bin/bash
# Start TracLine web interface with configured database

# Get the absolute path of the script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"

# Change to the web directory
cd "${SCRIPT_DIR}"

# Kill any previous instances
pkill -f "run_app.py" 2>/dev/null
sleep 1

# Start the web server in the background
nohup python run_app.py > server.log 2>&1 &
echo "TracLine server started. Check server.log for output."