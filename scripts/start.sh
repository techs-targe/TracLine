#!/bin/bash
# TracLine Unified Startup Script
# This script handles the complete startup process for TracLine

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Print colored messages
print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/.." && pwd )"

# Change to project root
cd "$PROJECT_ROOT"

# Load environment variables
if [ -f .env ]; then
    print_info "Loading environment variables from .env file..."
    export $(cat .env | grep -v '^#' | xargs)
else
    print_warning "No .env file found. Using default values."
    print_info "Tip: Copy .env.example to .env for custom configuration"
fi

# Set defaults if not provided
DB_HOST=${DB_HOST:-localhost}
DB_PORT=${DB_PORT:-5432}
DB_NAME=${DB_NAME:-tracline}
DB_USER=${DB_USER:-postgres}
DB_PASS=${DB_PASS:-postgres}
WEB_PORT=${WEB_PORT:-8000}

# Create necessary directories
print_info "Creating necessary directories..."
mkdir -p ~/.tracline
mkdir -p ~/.tracline/uploads

# Check Docker installation
if ! command -v docker &> /dev/null; then
    print_error "Docker is not installed. Please install Docker first."
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    print_error "Docker Compose is not installed. Please install Docker Compose first."
    exit 1
fi

# Check if PostgreSQL container is running
print_info "Checking PostgreSQL status..."
if docker ps | grep -q tracline-postgres; then
    print_success "PostgreSQL container is already running"
else
    print_info "Starting PostgreSQL container..."
    docker-compose up -d postgres
    
    # Wait for PostgreSQL to be ready
    print_info "Waiting for PostgreSQL to be ready..."
    for i in {1..30}; do
        if docker exec tracline-postgres pg_isready -U "$DB_USER" -d "$DB_NAME" &> /dev/null; then
            print_success "PostgreSQL is ready!"
            break
        fi
        if [ $i -eq 30 ]; then
            print_error "PostgreSQL failed to start within 30 seconds"
            print_info "Check logs with: docker-compose logs postgres"
            exit 1
        fi
        echo -n "."
        sleep 1
    done
    echo
fi

# Test database connection
print_info "Testing database connection..."
python3 -c "
import psycopg2
import sys
try:
    conn = psycopg2.connect(
        host='${DB_HOST}',
        port='${DB_PORT}',
        database='${DB_NAME}',
        user='${DB_USER}',
        password='${DB_PASS}'
    )
    conn.close()
    print('Database connection successful')
except Exception as e:
    print(f'Database connection failed: {e}')
    sys.exit(1)
" || {
    print_error "Failed to connect to database"
    print_info "Running database setup..."
    python scripts/setup_postgres.py || {
        print_error "Database setup failed"
        exit 1
    }
}

# Check if virtual environment is activated
if [ -z "$VIRTUAL_ENV" ]; then
    print_warning "Python virtual environment is not activated"
    if [ -d "venv" ]; then
        print_info "Activating virtual environment..."
        source venv/bin/activate
    else
        print_warning "No virtual environment found. Consider creating one with: python3 -m venv venv"
    fi
fi

# Check if TracLine is installed
if ! command -v tracline &> /dev/null; then
    print_warning "TracLine CLI not found in PATH"
    print_info "Installing TracLine..."
    pip install -e . || {
        print_error "Failed to install TracLine"
        exit 1
    }
fi

# Check configuration file
if [ ! -f tracline.yaml ]; then
    print_info "Creating tracline.yaml from postgres_config.yaml..."
    cp postgres_config.yaml tracline.yaml
fi

# Start web application
print_info "Starting TracLine web interface..."
print_info "Access TracLine at http://localhost:${WEB_PORT}"
print_info "Press Ctrl+C to stop"

cd web
python run_app.py --port "${WEB_PORT}"