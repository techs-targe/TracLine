#!/bin/bash
# TracLine Simple Installer for Ubuntu/Debian - FIXED VERSION
# One-line install: curl -fsSL https://raw.githubusercontent.com/techs-targe/TracLine/main/scripts/install-ubuntu.sh | bash
# With sample data: curl -fsSL https://raw.githubusercontent.com/techs-targe/TracLine/main/scripts/install-ubuntu.sh | bash -s -- --sample-data

set -e

# Ensure we're in a valid directory (in case user is in a deleted directory)
if [ -n "$HOME" ] && [ -d "$HOME" ]; then
    cd "$HOME" 2>/dev/null || cd /tmp 2>/dev/null || cd / 2>/dev/null
else
    cd /tmp 2>/dev/null || cd / 2>/dev/null
fi

# Parse command line arguments
SAMPLE_DATA=false
while [[ "$#" -gt 0 ]]; do
    case $1 in
        --sample-data) SAMPLE_DATA=true ;;
        -h|--help) 
            echo "Usage: $0 [options]"
            echo "Options:"
            echo "  --sample-data    Initialize with sample data"
            echo "  -h, --help       Show this help message"
            exit 0
            ;;
        *) echo "Unknown parameter: $1"; exit 1 ;;
    esac
    shift
done

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo "======================================"
echo "TracLine Installer for Ubuntu/Debian"
echo "Version: 2.0.1"
echo "======================================"
echo ""

# OS Check
if ! grep -qE "(ubuntu|debian)" /etc/os-release 2>/dev/null; then
    echo -e "${RED}Error: This script is for Ubuntu/Debian only${NC}"
    echo "For other OS, see: https://github.com/techs-targe/TracLine/blob/main/INSTALL.md"
    exit 1
fi

# Check if running as root
if [ "$EUID" -eq 0 ]; then 
   echo -e "${RED}Error: Do not run this script as root${NC}"
   echo "Run as a normal user. The script will use sudo when needed."
   exit 1
fi

# Check Python version
PYTHON_VERSION=$(python3 --version 2>&1 | grep -oE '[0-9]+\.[0-9]+' | head -1)
echo -e "${GREEN}Detected Python version: $PYTHON_VERSION${NC}"

if ! python3 -c 'import sys; exit(0 if sys.version_info >= (3, 8) else 1)' 2>/dev/null; then
    echo -e "${RED}Error: Python 3.8 or higher is required${NC}"
    echo "Current version: $PYTHON_VERSION"
    exit 1
fi

# Install prerequisites
echo -e "${GREEN}Installing prerequisites...${NC}"
sudo apt update || {
    echo -e "${RED}Failed to update package list${NC}"
    echo "Check your internet connection and try again"
    exit 1
}

sudo apt install -y \
    python3-pip \
    pipx \
    python-is-python3 \
    python3-psycopg2 \
    git \
    curl \
    docker.io \
    docker-compose

# Add user to docker group
echo -e "${GREEN}Adding user to docker group...${NC}"
sudo usermod -aG docker $USER

# Test if Docker works (will fail until re-login)
echo -e "${GREEN}Testing Docker access...${NC}"
if ! docker info >/dev/null 2>&1; then
    echo -e "${YELLOW}Warning: Docker permissions not yet active${NC}"
    echo "You'll need to logout/login or run 'newgrp docker' before starting TracLine"
    DOCKER_PERMISSION_ISSUE=true
else
    echo -e "${GREEN}✓ Docker access OK${NC}"
    DOCKER_PERMISSION_ISSUE=false
fi

# Setup pipx
echo -e "${GREEN}Setting up pipx...${NC}"
pipx ensurepath

# Ensure PATH is updated for current session and future sessions
export PATH="$HOME/.local/bin:$PATH"

# Add to shell configurations if not already present
if ! grep -q '.local/bin' ~/.bashrc 2>/dev/null; then
    echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
fi

# Clone or update TracLine
echo -e "${GREEN}Getting TracLine...${NC}"

if [ -d "$HOME/TracLine" ]; then
    # Check if it's a valid git repository
    if [ -d "$HOME/TracLine/.git" ]; then
        cd "$HOME/TracLine"
        if git pull; then
            echo -e "${GREEN}✓ Updated to latest version${NC}"
        else
            echo -e "${YELLOW}Warning: Failed to update. Removing and re-cloning...${NC}"
            cd $HOME
            rm -rf TracLine
            git clone https://github.com/techs-targe/TracLine.git
        fi
    else
        echo -e "${YELLOW}Found TracLine directory but it's not a git repository${NC}"
        echo "Removing and re-cloning..."
        cd $HOME
        rm -rf TracLine
        git clone https://github.com/techs-targe/TracLine.git
    fi
else
    cd $HOME
    git clone https://github.com/techs-targe/TracLine.git
fi

# Verify TracLine directory exists
if [ ! -d "$HOME/TracLine" ]; then
    echo -e "${RED}Error: Failed to clone TracLine repository${NC}"
    echo "Please check your internet connection and GitHub access"
    exit 1
fi

# Ensure we're in the correct directory
TRACLINE_DIR="$HOME/TracLine"
cd "$TRACLINE_DIR"
echo -e "${GREEN}Installing from: $TRACLINE_DIR${NC}"

# Verify setup.py exists
if [ ! -f "setup.py" ]; then
    echo -e "${RED}Error: setup.py not found in $TRACLINE_DIR${NC}"
    echo "This doesn't appear to be a valid TracLine installation."
    exit 1
fi

# Install TracLine
echo -e "${GREEN}Installing TracLine...${NC}"
if pipx list | grep -q "package tracline" 2>/dev/null; then
    echo "TracLine already installed, upgrading..."
    pipx install . --force
else
    pipx install .
fi

# Verify installation succeeded
if ! command -v tracline >/dev/null 2>&1; then
    echo -e "${RED}Error: TracLine installation failed${NC}"
    echo "The 'tracline' command is not available."
    exit 1
fi

# Inject dependencies
echo -e "${GREEN}Installing dependencies...${NC}"
pipx inject tracline \
    fastapi uvicorn pydantic sqlalchemy psycopg2-binary \
    python-multipart jinja2 aiofiles pyyaml python-dotenv \
    click tabulate colorama rich watchdog \
    python-daemon lockfile pygithub requests

# Setup configuration
echo -e "${GREEN}Setting up configuration...${NC}"
mkdir -p ~/.tracline
mkdir -p ~/.tracline/uploads

# Ensure we're still in TracLine directory
cd "$TRACLINE_DIR"

# Check for existing configuration and handle migration
if [ -f ~/.tracline/tracline.yaml ]; then
    # Check if it's a SQLite configuration
    if grep -q "type: sqlite" ~/.tracline/tracline.yaml 2>/dev/null; then
        echo -e "${YELLOW}Warning: Existing SQLite configuration detected${NC}"
        echo "You are switching from SQLite to PostgreSQL."
        echo ""
        # Backup existing configuration
        cp ~/.tracline/tracline.yaml ~/.tracline/tracline.yaml.backup.$(date +%Y%m%d_%H%M%S)
        echo -e "${GREEN}✓ Backed up existing configuration${NC}"
    elif grep -q "type: postgresql" ~/.tracline/tracline.yaml 2>/dev/null; then
        echo -e "${GREEN}Existing PostgreSQL configuration detected${NC}"
        echo "Configuration will be updated to ensure compatibility."
        # Backup just in case
        cp ~/.tracline/tracline.yaml ~/.tracline/tracline.yaml.backup.$(date +%Y%m%d_%H%M%S)
    fi
fi

# Always create/update PostgreSQL configuration for this installer
if [ -f postgres_config.yaml ]; then
    cp postgres_config.yaml ~/.tracline/tracline.yaml
    echo -e "${GREEN}✓ Created/Updated tracline.yaml (PostgreSQL configuration)${NC}"
else
    echo -e "${YELLOW}Warning: postgres_config.yaml not found, creating default${NC}"
        # Create default PostgreSQL configuration
        cat > ~/.tracline/tracline.yaml << CONFIG_END
# PostgreSQL Configuration
database:
  type: postgresql
  host: localhost
  port: 5432
  name: tracline
  user: postgres
  password: postgres  # Default password, can be overridden via TRACLINE_DB_PASSWORD
defaults:
  assignee: # Set via TRACLINE_ASSIGNEE environment variable
  priority: 3
  project: DEFAULT-PROJECT
app:
  upload_dir: ~/.tracline/uploads
  log_level: INFO
server:
  host: 0.0.0.0
  port: 8000
CONFIG_END
    echo -e "${GREEN}✓ Created default PostgreSQL configuration${NC}"
fi

# Create .env file if not exists
if [ ! -f .env ] && [ -f .env.example ]; then
    cp .env.example .env
    echo -e "${GREEN}✓ Created .env from template${NC}"
fi

# Create sample data flag if requested
if [ "$SAMPLE_DATA" = true ]; then
    touch ~/.tracline/.sample-data-requested
    echo -e "${GREEN}✓ Sample data will be loaded on first run${NC}"
fi

# Create convenience commands
echo -e "${GREEN}Creating commands...${NC}"

# tracline-start command - FIXED VERSION
cat > ~/.local/bin/tracline-start << 'SCRIPT_END'
#!/bin/bash
# TracLine Start Script with proper error handling

# Parse command line arguments
SAMPLE_DATA=false
FORCE_CLEAN=false
while [[ "$#" -gt 0 ]]; do
    case $1 in
        --sample-data) SAMPLE_DATA=true ;;
        --force-clean) FORCE_CLEAN=true ;;
        -h|--help) 
            echo "Usage: $0 [options]"
            echo "Options:"
            echo "  --sample-data    Initialize with sample data (only on first run)"
            echo "  --force-clean    Force clean installation (WARNING: deletes all data)"
            echo "  -h, --help       Show this help message"
            exit 0
            ;;
        *) echo "Unknown parameter: $1"; exit 1 ;;
    esac
    shift
done

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo "Starting TracLine..."

# Check if tracline command exists
if ! command -v tracline >/dev/null 2>&1; then
    echo -e "${RED}Error: 'tracline' command not found!${NC}"
    echo "Please run: source ~/.bashrc"
    echo "Or open a new terminal and try again."
    exit 1
fi

# Check Docker permissions
if ! docker info >/dev/null 2>&1; then
    echo -e "${RED}Error: Permission denied accessing Docker${NC}"
    echo ""
    echo "This usually means you're not in the docker group."
    echo "To fix this:"
    echo ""
    echo "1. Add yourself to docker group (if not already done):"
    echo "   sudo usermod -aG docker $USER"
    echo ""
    echo "2. Then EITHER:"
    echo "   a) Logout and login again (recommended)"
    echo "   b) Run: newgrp docker"
    echo "   c) Run: su - $USER"
    echo ""
    echo "3. Try tracline-start again"
    exit 1
fi

# Check if we're in the right directory
TRACLINE_DIR="$HOME/TracLine"
if [ ! -d "$TRACLINE_DIR" ]; then
    echo -e "${RED}Error: TracLine directory not found at $HOME/TracLine${NC}"
    echo ""
    
    # Check common alternate locations
    if [ -d "$HOME/tracline" ]; then
        echo "Found TracLine at $HOME/tracline (lowercase)"
        echo "You may have a case mismatch issue."
    fi
    
    # Show what directories exist
    echo ""
    echo "Looking for TracLine in your home directory:"
    ls -la "$HOME" | grep -i tracline || echo "No TracLine directories found"
    
    echo ""
    echo "To fix this:"
    echo "  cd ~"
    echo "  git clone https://github.com/techs-targe/TracLine.git"
    exit 1
fi

cd "$TRACLINE_DIR"

# Check for docker-compose.yml
if [ ! -f docker-compose.yml ]; then
    echo -e "${RED}Error: docker-compose.yml not found${NC}"
    echo "Please ensure you're in the TracLine directory"
    exit 1
fi

# Start PostgreSQL
echo "Starting PostgreSQL..."

# Verify docker-compose is available
if ! command -v docker-compose >/dev/null 2>&1; then
    echo -e "${RED}Error: docker-compose command not found${NC}"
    echo "Please ensure Docker and docker-compose are properly installed"
    exit 1
fi

# Check if database already exists and if we should preserve it
DB_EXISTS=false
if docker ps -a | grep -q tracline-postgres; then
    DB_EXISTS=true
fi

# Check if volume exists
VOLUME_EXISTS=false
if docker volume ls --format '{{.Name}}' | grep -q "tracline.*postgres_data"; then
    VOLUME_EXISTS=true
fi

if [ "$FORCE_CLEAN" = true ]; then
    echo -e "${YELLOW}WARNING: Force clean installation requested - all data will be deleted!${NC}"
    echo "Press Ctrl+C within 5 seconds to cancel..."
    sleep 5
    
    echo "Ensuring clean PostgreSQL installation..."
    echo "  - Stopping any existing TracLine containers..."
    # Stop any existing containers and remove volumes
    docker-compose down -v --remove-orphans 2>/dev/null || true

    echo "  - Removing all TracLine Docker resources..."
    # Stop and remove any tracline containers
    docker ps -a | grep tracline | awk '{print $1}' | xargs -r docker stop 2>/dev/null || true
    docker ps -a | grep tracline | awk '{print $1}' | xargs -r docker rm -f 2>/dev/null || true

    # Force remove ALL tracline-related volumes
    echo "  - Cleaning up Docker volumes..."
    docker volume rm -f tracline_postgres_data 2>/dev/null || true
    docker volume rm -f tracline_tracline_postgres_data 2>/dev/null || true
    # Remove any volumes containing 'tracline' in the name
    docker volume ls --format '{{.Name}}' 2>/dev/null | grep -i tracline | xargs -r docker volume rm -f 2>/dev/null || true

    # Remove networks
    echo "  - Cleaning up Docker networks..."
    docker network rm tracline_network 2>/dev/null || true
    docker network rm tracline_default 2>/dev/null || true

    # Small delay to ensure cleanup is complete
    sleep 2
    echo "  - Cleanup complete"
elif [ "$DB_EXISTS" = true ] || [ "$VOLUME_EXISTS" = true ]; then
    echo "Existing TracLine database detected. Preserving data..."
    echo "  - Stopping any existing TracLine containers..."
    # Stop containers but preserve volumes
    docker-compose down 2>/dev/null || true
    echo "  - Data preserved"
else
    echo "No existing TracLine database found. Performing fresh installation..."
fi

if docker-compose up -d postgres 2>&1 | tee /tmp/docker-compose.log; then
    # Check if container actually started
    sleep 3
    if docker ps | grep -q tracline-postgres; then
        echo -e "${GREEN}✓ PostgreSQL started successfully${NC}"
    else
        echo -e "${RED}Error: PostgreSQL container failed to start${NC}"
        echo "Check logs with: docker-compose logs postgres"
        cat /tmp/docker-compose.log
        exit 1
    fi
else
    echo -e "${RED}Error: Failed to start PostgreSQL${NC}"
    echo "Docker-compose output:"
    cat /tmp/docker-compose.log
    exit 1
fi

# Wait for PostgreSQL to be ready
echo "Waiting for PostgreSQL to be ready..."
MAX_WAIT=60
for i in $(seq 1 $MAX_WAIT); do
    if docker exec tracline-postgres pg_isready -U postgres >/dev/null 2>&1; then
        echo -e "${GREEN}✓ PostgreSQL is ready${NC}"
        break
    fi
    if [ "$i" -eq $MAX_WAIT ]; then
        echo -e "${RED}Error: PostgreSQL failed to become ready after ${MAX_WAIT} seconds${NC}"
        echo "Check logs with: docker-compose logs postgres"
        echo "Common causes:"
        echo "  - Insufficient memory"
        echo "  - Port 5432 already in use"
        echo "  - Docker storage issues"
        exit 1
    fi
    # Show progress every 10 seconds
    if [ $((i % 10)) -eq 0 ]; then
        echo "  Still waiting... ($i/$MAX_WAIT seconds)"
    fi
    sleep 1
done

# Initialize database
export TRACLINE_DB_PASSWORD=postgres
# Set config path explicitly
export TRACLINE_CONFIG=~/.tracline/tracline.yaml

# Only setup database if it doesn't exist or force clean was requested
if [ "$FORCE_CLEAN" = true ] || [ "$DB_EXISTS" = false ] || [ "$VOLUME_EXISTS" = false ]; then
    # Set clean install flag only for new or forced installations
    export TRACLINE_CLEAN_INSTALL=true
    
    echo "Setting up PostgreSQL database..."
    if python scripts/setup_postgres.py; then
        echo -e "${GREEN}✓ PostgreSQL database created${NC}"
    else
        echo -e "${RED}Error: Failed to setup PostgreSQL${NC}"
        exit 1
    fi

    # Check for sample data flag from installer
    if [ -f ~/.tracline/.sample-data-requested ]; then
        echo "Sample data requested during installation..."
        SAMPLE_DATA=true
        rm -f ~/.tracline/.sample-data-requested
    fi

    # Initialize TracLine schema with or without sample data
    if [ "$SAMPLE_DATA" = true ]; then
        echo "Initializing database with sample data..."
        if tracline init --sample-data; then
            echo -e "${GREEN}✓ Database initialized with sample data${NC}"
        else
            echo -e "${RED}Error: Failed to initialize TracLine${NC}"
            exit 1
        fi
    else
        echo "Initializing database..."
        if tracline init; then
            echo -e "${GREEN}✓ Database initialized${NC}"
        else
            echo -e "${RED}Error: Failed to initialize TracLine${NC}"
            exit 1
        fi
    fi
else
    echo -e "${GREEN}✓ Using existing TracLine database${NC}"
    # Check if database is accessible
    if tracline config --show >/dev/null 2>&1; then
        echo -e "${GREEN}✓ Database connection verified${NC}"
    else
        echo -e "${YELLOW}Warning: Could not verify database connection${NC}"
        echo "If you encounter issues, try: tracline-start --force-clean"
    fi
fi

# Start web interface
echo ""
echo -e "${GREEN}Starting web interface...${NC}"
echo "Access TracLine at: http://localhost:8000"
echo "Press Ctrl+C to stop"
echo ""

# Start web server
cd web

# Try multiple methods to find uvicorn
if command -v uvicorn >/dev/null 2>&1; then
    # If uvicorn is in PATH
    uvicorn app:app --host 0.0.0.0 --port 8000
elif [ -f "$HOME/.local/share/pipx/venvs/tracline/bin/uvicorn" ]; then
    # Use pipx virtual environment
    "$HOME/.local/share/pipx/venvs/tracline/bin/uvicorn" app:app --host 0.0.0.0 --port 8000
elif [ -f "$HOME/.local/share/pipx/venvs/tracline/bin/python" ]; then
    # Use python -m uvicorn as fallback
    "$HOME/.local/share/pipx/venvs/tracline/bin/python" -m uvicorn app:app --host 0.0.0.0 --port 8000
else
    echo -e "${RED}Error: uvicorn not found${NC}"
    echo "Attempting to reinstall uvicorn..."
    pipx inject tracline uvicorn
    if [ -f "$HOME/.local/share/pipx/venvs/tracline/bin/python" ]; then
        "$HOME/.local/share/pipx/venvs/tracline/bin/python" -m uvicorn app:app --host 0.0.0.0 --port 8000
    else
        echo -e "${RED}Failed to start web server${NC}"
        exit 1
    fi
fi
SCRIPT_END

# Make executable
chmod +x ~/.local/bin/tracline-start

# tracline-stop command
cat > ~/.local/bin/tracline-stop << 'SCRIPT_END'
#!/bin/bash
echo "Stopping TracLine..."
if [ -d "$HOME/TracLine" ]; then
    (cd "$HOME/TracLine" && docker-compose down) || echo "Warning: Could not stop containers"
else
    echo "Warning: TracLine directory not found"
fi
echo "✓ TracLine stopped"
SCRIPT_END

chmod +x ~/.local/bin/tracline-stop

# Final verification
echo ""
echo -e "${GREEN}Verifying installation...${NC}"
if [ -d "$TRACLINE_DIR" ]; then
    echo -e "${GREEN}✓ Source directory exists: $TRACLINE_DIR${NC}"
else
    echo -e "${RED}✗ Source directory missing: $TRACLINE_DIR${NC}"
fi

if command -v tracline >/dev/null 2>&1; then
    echo -e "${GREEN}✓ tracline command available${NC}"
else
    echo -e "${RED}✗ tracline command not found${NC}"
fi

if [ -x "$HOME/.local/bin/tracline-start" ]; then
    echo -e "${GREEN}✓ tracline-start command available${NC}"
else
    echo -e "${RED}✗ tracline-start command not found${NC}"
fi

# Final message
echo ""

# Only show success if everything is actually working
if [ -d "$TRACLINE_DIR" ] && command -v tracline >/dev/null 2>&1 && [ -x "$HOME/.local/bin/tracline-start" ]; then
    echo -e "${GREEN}✨ Installation Complete! ✨${NC}"
else
    echo -e "${YELLOW}⚠️ Installation completed with warnings${NC}"
    echo "Some components may not be properly installed."
    echo "Run this to diagnose: bash ~/TracLine/scripts/diagnose-installation.sh"
fi
echo ""
echo -e "${YELLOW}IMPORTANT: To use TracLine commands, do ONE of the following:${NC}"
echo "  1. Run: source ~/.bashrc"
echo "  2. Open a new terminal"
echo "  3. Logout and login again"
echo ""
if [ "$DOCKER_PERMISSION_ISSUE" = true ]; then
    echo -e "${YELLOW}IMPORTANT: Docker permissions need activation:${NC}"
    echo "1. Run: newgrp docker"
    echo "   OR logout and login again"
    echo "2. Then run: tracline-start"
    echo "3. Access at: http://localhost:8000"
else
    echo "Next steps:"
    echo "1. Start TracLine: tracline-start"
    echo "2. Access at: http://localhost:8000"
fi
echo ""
echo "Commands available:"
echo "  tracline          - CLI tool"
echo "  tracline-start    - Start everything (preserves existing data)"
echo "  tracline-stop     - Stop everything"
echo ""
echo "tracline-start options:"
echo "  --sample-data     - Initialize with sample data (first run only)"
echo "  --force-clean     - Force clean installation (WARNING: deletes all data)"
echo ""

echo -e "${GREEN}Installation Summary:${NC}"
echo "  TracLine binary: ~/.local/bin/tracline"
echo "  Configuration:   ~/.tracline/tracline.yaml"
echo "  Source code:     $TRACLINE_DIR"
echo "  Upload directory: ~/.tracline/uploads"
echo "  Database:        PostgreSQL in Docker (port 5432)"
echo ""
echo -e "${YELLOW}Notes:${NC}"
echo "  - First run of 'tracline-start' will download Docker images"
echo "  - Subsequent runs will preserve your existing database and data"
echo "  - Use 'tracline-start --force-clean' only when you want to start fresh"
echo ""
echo -e "${GREEN}Quick test after sourcing:${NC}"
echo "  source ~/.bashrc"
echo "  tracline --version              # Should show TracLine 2.0.0"
echo ""
echo -e "${GREEN}Start TracLine:${NC}"
echo "  tracline-start                  # Normal start (preserves existing data)"
echo "  tracline-start --sample-data    # Start with sample data (first run only)"
echo "  tracline-start --force-clean    # Force clean installation (WARNING: deletes all data)"
echo ""
echo -e "${GREEN}Need help?${NC}"
echo "  - Installation issues: ~/TracLine/INSTALL.md"
echo "  - Docker permissions: ~/TracLine/scripts/fix-docker-permissions.sh"
echo "  - User Guide: ~/TracLine/docs/USER_GUIDE.md"

# Extra verification at the very end
if [ ! -d "$TRACLINE_DIR" ]; then
    echo ""
    echo -e "${RED}WARNING: TracLine directory is missing!${NC}"
    echo "This indicates a serious installation problem."
    echo "Please run: cd ~ && git clone https://github.com/techs-targe/TracLine.git"
    exit 1
fi