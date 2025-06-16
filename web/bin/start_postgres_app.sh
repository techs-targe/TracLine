#!/bin/bash
# Start TracLine web interface with PostgreSQL database

# Get the absolute path of the script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"

# Change to the TracLine root directory
cd "${SCRIPT_DIR}/.."

# Make sure we're using the correct configuration file
if [ ! -f "tracline.yaml" ]; then
    echo "Error: tracline.yaml not found in $(pwd)"
    exit 1
fi

# Ensure the database type is set to PostgreSQL in the configuration
if ! grep -q "type: postgresql" tracline.yaml; then
    echo "Setting database type to PostgreSQL in tracline.yaml"
    
    # Make a backup of the original config
    cp tracline.yaml tracline.yaml.bak
    
    # Create new PostgreSQL config
    cat > tracline.yaml << EOF
# TracLine v2 Configuration
# PostgreSQL configuration for GitHub publication

database:
  type: postgresql
  host: localhost
  port: 5432
  database: tracline
  user: postgres
  password: postgres  # For testing only, use environment variable in production

workflow:
  # Custom intermediate states between READY and DONE
  custom_states:
    - DOING
    - TESTING
  
  # Custom state transitions (optional)
  transitions: {}

defaults:
  assignee: # Set via TASK_ASSIGNEE environment variable
  priority: 3  # Default priority (1-5)
EOF
    
    echo "Configuration updated successfully."
fi

# Check if the PostgreSQL database is initialized
if ! python -c "import psycopg2; conn = psycopg2.connect(dbname='tracline', user='postgres', password='postgres', host='localhost', port=5432); conn.close()"; then
    echo "Error: Could not connect to PostgreSQL database. Running setup script..."
    python "${SCRIPT_DIR}/../setup_postgres.py"
    
    if [ $? -ne 0 ]; then
        echo "Error: Failed to initialize PostgreSQL database. Please check PostgreSQL is running."
        exit 1
    fi
fi

# Check if test data exists by counting tasks
TASK_COUNT=$(python -c "import psycopg2; conn = psycopg2.connect(dbname='tracline', user='postgres', password='postgres', host='localhost', port=5432); cur = conn.cursor(); cur.execute('SELECT COUNT(*) FROM tasks'); print(cur.fetchone()[0]); conn.close()" 2>/dev/null)

if [ -z "$TASK_COUNT" ] || [ "$TASK_COUNT" -eq "0" ]; then
    echo "No tasks found in database. Importing test data..."
    python "${SCRIPT_DIR}/setup_postgres_test_data.py"
fi

# Change to the web directory
cd "${SCRIPT_DIR}"

# Start the web server with the configured database (PostgreSQL)
echo "Starting TracLine web interface with PostgreSQL database..."
python run_app.py "$@"