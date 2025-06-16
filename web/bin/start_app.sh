#!/bin/bash

# Move to the web directory
cd "$(dirname "$0")"

# Check if port parameter is provided
if [ $# -eq 1 ]; then
  PORT=$1
else
  PORT=8000
fi

# Run the application
python run_app.py $PORT