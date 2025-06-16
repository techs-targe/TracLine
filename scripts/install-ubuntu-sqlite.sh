#!/bin/bash
# TracLine SQLite Installer for Ubuntu/Debian
# One-line install: curl -fsSL https://raw.githubusercontent.com/techs-targe/TracLine/main/scripts/install-ubuntu-sqlite.sh | bash
# With sample data: curl -fsSL https://raw.githubusercontent.com/techs-targe/TracLine/main/scripts/install-ubuntu-sqlite.sh | bash -s -- --sample-data

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

echo "============================================"
echo "TracLine SQLite Installer for Ubuntu/Debian"
echo "Version: 2.0.0"
echo "============================================"
echo ""
echo "This installer configures TracLine with SQLite (no Docker required)"
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

# Install prerequisites (no Docker needed for SQLite)
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
    git \
    curl \
    sqlite3

# Setup pipx
echo -e "${GREEN}Setting up pipx...${NC}"
pipx ensurepath

# Ensure PATH is updated
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

# Inject dependencies (no psycopg2 needed for SQLite)
echo -e "${GREEN}Installing dependencies...${NC}"
pipx inject tracline \
    fastapi uvicorn pydantic sqlalchemy \
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
    # Check if it's a PostgreSQL configuration
    if grep -q "type: postgresql" ~/.tracline/tracline.yaml 2>/dev/null; then
        echo -e "${YELLOW}Warning: Existing PostgreSQL configuration detected${NC}"
        echo "You are switching from PostgreSQL to SQLite."
        echo ""
        # Backup existing configuration
        cp ~/.tracline/tracline.yaml ~/.tracline/tracline.yaml.backup.$(date +%Y%m%d_%H%M%S)
        echo -e "${GREEN}✓ Backed up existing configuration${NC}"
    elif grep -q "type: sqlite" ~/.tracline/tracline.yaml 2>/dev/null; then
        echo -e "${GREEN}Existing SQLite configuration detected${NC}"
        echo "Configuration will be updated to ensure compatibility."
        # Backup just in case
        cp ~/.tracline/tracline.yaml ~/.tracline/tracline.yaml.backup.$(date +%Y%m%d_%H%M%S)
    fi
fi

# Always create/update SQLite configuration for this installer
if [ -f sqlite_config.yaml ]; then
    cp sqlite_config.yaml ~/.tracline/tracline.yaml
    echo -e "${GREEN}✓ Created/Updated tracline.yaml (SQLite configuration)${NC}"
else
    echo -e "${YELLOW}Warning: sqlite_config.yaml not found${NC}"
    # Create a basic SQLite config
    cat > ~/.tracline/tracline.yaml << 'CONFIG_END'
database:
  type: sqlite
  path: ~/.tracline/tracline.db

app:
  upload_dir: ~/.tracline/uploads
  log_level: INFO
  secret_key: your-secret-key-here
  
server:
  host: 0.0.0.0
  port: 8000
CONFIG_END
    echo -e "${GREEN}✓ Created default SQLite configuration${NC}"
fi

# Create .env file if not exists
if [ ! -f .env ] && [ -f .env.example ]; then
    cp .env.example .env
    echo -e "${GREEN}✓ Created .env from template${NC}"
fi

# Check if database exists
DB_EXISTS=false
if [ -f ~/.tracline/tracline.db ]; then
    DB_EXISTS=true
fi

# Only initialize if database doesn't exist
if [ "$DB_EXISTS" = false ]; then
    echo -e "${GREEN}Initializing SQLite database...${NC}"
    export TRACLINE_CONFIG=~/.tracline/tracline.yaml

    # Initialize with or without sample data
    if [ "$SAMPLE_DATA" = true ]; then
        echo -e "${GREEN}Creating database with sample data...${NC}"
        if tracline init --sample-data; then
            echo -e "${GREEN}✓ Database initialized with sample data${NC}"
        else
            echo -e "${YELLOW}Warning: Database initialization had issues${NC}"
        fi
    else
        if tracline init; then
            echo -e "${GREEN}✓ Database initialized${NC}"
        else
            echo -e "${YELLOW}Warning: Database initialization had issues${NC}"
        fi
    fi
else
    echo -e "${YELLOW}Existing database found. Skipping initialization.${NC}"
    echo -e "${YELLOW}To reinitialize with sample data, remove ~/.tracline/tracline.db first${NC}"
fi

# Create convenience commands
echo -e "${GREEN}Creating commands...${NC}"

# tracline-start command for SQLite
cat > ~/.local/bin/tracline-start << 'SCRIPT_END'
#!/bin/bash
# TracLine Start Script (SQLite version)

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

echo "Starting TracLine (SQLite mode)..."

# Check if tracline command exists
if ! command -v tracline >/dev/null 2>&1; then
    echo -e "${RED}Error: 'tracline' command not found!${NC}"
    echo "Please run: source ~/.bashrc"
    echo "Or open a new terminal and try again."
    exit 1
fi

# Check if we're in the right directory
TRACLINE_DIR="$HOME/TracLine"
if [ ! -d "$TRACLINE_DIR" ]; then
    echo -e "${RED}Error: TracLine directory not found at $HOME/TracLine${NC}"
    echo ""
    echo "To fix this, run:"
    echo "  cd ~ && git clone https://github.com/techs-targe/TracLine.git"
    exit 1
fi

cd "$TRACLINE_DIR"

# Check for web directory
if [ ! -d "web" ]; then
    echo -e "${RED}Error: web directory not found${NC}"
    echo "Please ensure you're in the TracLine directory"
    exit 1
fi

# Export configuration
export TRACLINE_CONFIG=~/.tracline/tracline.yaml

# Check if database exists
DB_PATH="$HOME/.tracline/tracline.db"
DB_EXISTS=false
if [ -f "$DB_PATH" ]; then
    DB_EXISTS=true
fi

if [ "$FORCE_CLEAN" = true ]; then
    echo -e "${YELLOW}WARNING: Force clean installation requested - all data will be deleted!${NC}"
    echo "Press Ctrl+C within 5 seconds to cancel..."
    sleep 5
    
    echo "Removing existing database..."
    rm -f "$DB_PATH"
    rm -f "$DB_PATH-journal"
    echo "  - Database removed"
fi

# Only initialize if database doesn't exist or force clean was requested
if [ "$FORCE_CLEAN" = true ] || [ "$DB_EXISTS" = false ]; then
    echo "Initializing SQLite database..."
    if [ "$SAMPLE_DATA" = true ]; then
        echo "Creating database with sample data..."
        if tracline init --sample-data; then
            echo -e "${GREEN}✓ Database initialized with sample data${NC}"
        else
            echo -e "${RED}Error: Failed to initialize database${NC}"
            exit 1
        fi
    else
        if tracline init; then
            echo -e "${GREEN}✓ Database initialized${NC}"
        else
            echo -e "${RED}Error: Failed to initialize database${NC}"
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
echo -e "${GREEN}Starting web interface (SQLite mode)...${NC}"
echo "Access TracLine at: http://localhost:8000"
echo "Press Ctrl+C to stop"
echo ""
echo "Note: Using SQLite database at ~/.tracline/tracline.db"
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

# tracline-web command (just start web server)
cat > ~/.local/bin/tracline-web << 'SCRIPT_END'
#!/bin/bash
# TracLine Web Server Only

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

echo "Starting TracLine Web Server..."

# Minimal checks
if [ ! -d "$HOME/TracLine/web" ]; then
    echo -e "${RED}Error: TracLine web directory not found${NC}"
    exit 1
fi

cd "$HOME/TracLine/web"

# Export configuration
export TRACLINE_CONFIG=~/.tracline/tracline.yaml

echo -e "${GREEN}Starting web interface...${NC}"
echo "Access at: http://localhost:8000"
echo ""

# Try multiple methods to find uvicorn
if command -v uvicorn >/dev/null 2>&1; then
    uvicorn app:app --host 0.0.0.0 --port 8000
elif [ -f "$HOME/.local/share/pipx/venvs/tracline/bin/uvicorn" ]; then
    "$HOME/.local/share/pipx/venvs/tracline/bin/uvicorn" app:app --host 0.0.0.0 --port 8000
elif [ -f "$HOME/.local/share/pipx/venvs/tracline/bin/python" ]; then
    "$HOME/.local/share/pipx/venvs/tracline/bin/python" -m uvicorn app:app --host 0.0.0.0 --port 8000
else
    echo -e "${RED}Error: uvicorn not found${NC}"
    exit 1
fi
SCRIPT_END

chmod +x ~/.local/bin/tracline-web

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
echo -e "${GREEN}✨ Installation Complete! ✨${NC}"
echo ""
echo -e "${YELLOW}IMPORTANT: To use TracLine commands, do ONE of the following:${NC}"
echo "  1. Run: source ~/.bashrc"
echo "  2. Open a new terminal"
echo "  3. Logout and login again"
echo ""
echo "Commands available:"
echo "  tracline          - CLI tool"
echo "  tracline-start    - Start everything (preserves existing data)"
echo "  tracline-web      - Start just the web server"
echo ""
echo "tracline-start options:"
echo "  --sample-data     - Initialize with sample data (first run only)"
echo "  --force-clean     - Force clean installation (WARNING: deletes all data)"
echo ""
echo -e "${GREEN}Installation Summary:${NC}"
echo "  TracLine binary: ~/.local/bin/tracline"
echo "  Configuration:   ~/.tracline/tracline.yaml"
echo "  Source code:     $TRACLINE_DIR"
echo "  Database:        SQLite at ~/.tracline/tracline.db"
echo "  Upload directory: ~/.tracline/uploads"
echo ""
echo -e "${GREEN}Quick test after sourcing:${NC}"
echo "  source ~/.bashrc"
echo "  tracline --version              # Should show TracLine 2.0.0"
echo ""
echo -e "${GREEN}Start TracLine (SQLite mode):${NC}"
echo "  tracline-start                  # Normal start (preserves existing data)"
echo "  tracline-start --sample-data    # Start with sample data (first run only)"
echo "  tracline-start --force-clean    # Force clean installation (WARNING: deletes all data)"
echo ""
echo -e "${GREEN}Note:${NC} SQLite version doesn't require Docker!"