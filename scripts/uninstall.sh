#!/bin/bash
# TracLine Universal Uninstaller (PostgreSQL & SQLite)
# One-line uninstall: curl -fsSL https://raw.githubusercontent.com/techs-targe/TracLine/main/scripts/uninstall.sh | bash
# Interactive uninstall: bash uninstall.sh
# Works for both PostgreSQL and SQLite installations

set -e

# Change to a safe directory first to avoid getcwd errors
if [ -n "$HOME" ] && [ -d "$HOME" ]; then
    cd "$HOME" 2>/dev/null || cd /tmp 2>/dev/null || cd / 2>/dev/null
else
    cd /tmp 2>/dev/null || cd / 2>/dev/null
fi

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Detect if running interactively
if [ -t 0 ]; then
    INTERACTIVE=true
else
    INTERACTIVE=false
fi

# Parse command line arguments
REMOVE_DATA=false
FORCE=false

while [[ "$#" -gt 0 ]]; do
    case $1 in
        --remove-data) REMOVE_DATA=true ;;
        --force) FORCE=true ;;
        -h|--help) 
            echo "Usage: $0 [options]"
            echo "Options:"
            echo "  --remove-data    Remove TracLine data and configuration"
            echo "  --force          Don't ask for confirmation"
            echo "  -h, --help       Show this help message"
            exit 0
            ;;
        *) echo "Unknown parameter: $1"; exit 1 ;;
    esac
    shift
done

echo "============================"
echo "TracLine Uninstaller"
echo "============================"
echo ""

# Detect installation type
INSTALL_TYPE="Unknown"
if [ -f ~/.tracline/tracline.yaml ]; then
    if grep -q "type: postgresql" ~/.tracline/tracline.yaml 2>/dev/null; then
        INSTALL_TYPE="PostgreSQL"
    elif grep -q "type: sqlite" ~/.tracline/tracline.yaml 2>/dev/null; then
        INSTALL_TYPE="SQLite"
    fi
fi
echo -e "${GREEN}Detected installation type: $INSTALL_TYPE${NC}"
echo ""

echo -e "${YELLOW}This will remove:${NC}"
echo "  - TracLine application"
echo "  - Convenience commands (tracline-start, tracline-stop)"
echo ""
echo -e "${YELLOW}This will NOT remove:${NC}"
echo "  - Docker"
echo "  - Python/pipx"
echo "  - System packages"
echo ""

# Handle confirmation
if [ "$FORCE" = false ]; then
    if [ "$INTERACTIVE" = true ]; then
        read -p "Continue? (y/N) " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            echo "Cancelled."
            exit 0
        fi
    else
        echo -e "${YELLOW}Note: Running in non-interactive mode${NC}"
        if [ "$REMOVE_DATA" = false ]; then
            echo "To remove data as well, run:"
            echo "  curl -fsSL https://raw.githubusercontent.com/techs-targe/TracLine/main/scripts/uninstall.sh | bash -s -- --remove-data"
        else
            echo "Data will be removed as requested (--remove-data flag detected)"
        fi
        echo ""
        echo "To cancel, press Ctrl+C within 5 seconds..."
        sleep 5
    fi
fi

# Update PATH to ensure commands are found
export PATH="$HOME/.local/bin:$PATH"

# Stop services
echo -e "${GREEN}Stopping services...${NC}"
if [ -x "$HOME/.local/bin/tracline-stop" ]; then
    "$HOME/.local/bin/tracline-stop" 2>/dev/null || true
elif command -v tracline-stop >/dev/null 2>&1; then
    tracline-stop 2>/dev/null || true
fi

# Stop docker containers
if command -v docker-compose >/dev/null 2>&1; then
    if [ -d "$HOME/TracLine" ] && [ -f "$HOME/TracLine/docker-compose.yml" ]; then
        # Use subshell to avoid cd errors
        (cd "$HOME/TracLine" && docker-compose down -v 2>/dev/null) || true
    fi
fi

# Uninstall TracLine
echo -e "${GREEN}Removing TracLine...${NC}"
if command -v pipx >/dev/null 2>&1; then
    # Check if TracLine is installed with pipx
    if pipx list | grep -q "package tracline" 2>/dev/null; then
        echo "  - Uninstalling TracLine via pipx"
        pipx uninstall tracline || true
    else
        echo "  - TracLine not found in pipx packages"
    fi
fi

# Also remove the tracline command if it exists
if [ -f ~/.local/bin/tracline ]; then
    echo "  - Removing tracline command"
    rm -f ~/.local/bin/tracline
fi

# Remove commands
echo -e "${GREEN}Removing commands...${NC}"
rm -f ~/.local/bin/tracline-start
rm -f ~/.local/bin/tracline-stop
rm -f ~/.local/bin/tracline-web  # SQLite-specific command

# Handle data removal
if [ "$REMOVE_DATA" = true ] || [ "$FORCE" = true ]; then
    echo -e "${GREEN}Removing data...${NC}"
    
    # Check for SQLite database
    if [ -f ~/.tracline/tracline.db ]; then
        echo "  - Removing SQLite database"
        rm -f ~/.tracline/tracline.db
    fi
    
    # Remove configuration directories
    rm -rf ~/.tracline
    rm -rf ~/.config/tracline
    
    # Remove legacy taskshell directories
    if [ -d ~/.taskshell ]; then
        echo "  - Removing legacy .taskshell directory"
        rm -rf ~/.taskshell
    fi
    
    # PostgreSQL cleanup
    if command -v docker >/dev/null 2>&1; then
        echo "  - Removing PostgreSQL Docker containers and volumes"
        
        # First try docker-compose if available
        if command -v docker-compose >/dev/null 2>&1 && [ -f "$HOME/TracLine/docker-compose.yml" ]; then
            echo "    Using docker-compose to remove containers and volumes..."
            (cd "$HOME/TracLine" 2>/dev/null && docker-compose down -v --remove-orphans 2>/dev/null) || true
        fi
        
        # Then ensure everything is cleaned up
        echo "    Ensuring all TracLine Docker resources are removed..."
        # Stop and remove container (try both naming conventions)
        docker stop tracline-postgres 2>/dev/null || docker stop tracline_postgres 2>/dev/null || true
        docker rm -f tracline-postgres 2>/dev/null || docker rm -f tracline_postgres 2>/dev/null || true
        
        # Force remove volumes (try multiple approaches)
        docker volume rm -f tracline_postgres_data 2>/dev/null || true
        docker volume rm -f tracline_tracline_postgres_data 2>/dev/null || true
        
        # List and remove any volumes containing 'tracline'
        docker volume ls --format '{{.Name}}' 2>/dev/null | grep -i tracline | xargs -r docker volume rm -f 2>/dev/null || true
        
        # Remove network
        docker network rm tracline_network 2>/dev/null || true
        docker network rm tracline_default 2>/dev/null || true
        
        # Verify cleanup
        echo "    Verifying Docker cleanup..."
        REMAINING_CONTAINERS=$(docker ps -a 2>/dev/null | grep -i tracline | wc -l || echo 0)
        REMAINING_VOLUMES=$(docker volume ls 2>/dev/null | grep -i tracline | wc -l || echo 0)
        if [ "$REMAINING_CONTAINERS" -gt "0" ] || [ "$REMAINING_VOLUMES" -gt "0" ]; then
            echo -e "${YELLOW}    Warning: Some Docker resources may remain:${NC}"
            [ "$REMAINING_CONTAINERS" -gt "0" ] && echo "      - $REMAINING_CONTAINERS container(s)"
            [ "$REMAINING_VOLUMES" -gt "0" ] && echo "      - $REMAINING_VOLUMES volume(s)"
            echo "    Run 'docker system prune -a --volumes' to clean up all unused resources"
        else
            echo "    ✓ All TracLine Docker resources removed"
        fi
    fi
    
    # Try to drop database if PostgreSQL is accessible
    if command -v psql >/dev/null 2>&1; then
        echo "  - Attempting to drop TracLine database"
        PGPASSWORD=postgres psql -h localhost -U postgres -c "DROP DATABASE IF EXISTS tracline;" 2>/dev/null || true
    fi
else
    if [ "$INTERACTIVE" = true ]; then
        echo ""
        read -p "Remove TracLine data and configuration? (y/N) " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            echo -e "${GREEN}Removing data...${NC}"
            rm -rf ~/.tracline
            rm -rf ~/.config/tracline
            rm -rf ~/.taskshell  # Remove legacy directory
            
            # PostgreSQL cleanup
            if command -v docker >/dev/null 2>&1; then
                docker stop tracline_postgres 2>/dev/null || true
                docker rm tracline_postgres 2>/dev/null || true
                docker volume rm tracline_postgres_data 2>/dev/null || true
            fi
            
            # Try to drop database
            if command -v psql >/dev/null 2>&1; then
                PGPASSWORD=postgres psql -h localhost -U postgres -c "DROP DATABASE IF EXISTS tracline;" 2>/dev/null || true
            fi
        fi
    fi
fi

# Handle source code removal
if [ "$REMOVE_DATA" = true ]; then
    # When --remove-data is specified, also remove source code
    echo -e "${GREEN}Removing source code...${NC}"
    # Change to home directory first to avoid getcwd errors
    cd "$HOME" 2>/dev/null || cd / 2>/dev/null
    rm -rf ~/TracLine
elif [ "$INTERACTIVE" = true ]; then
    echo ""
    read -p "Remove TracLine source code? (y/N) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo -e "${GREEN}Removing source...${NC}"
        # Change to home directory first to avoid getcwd errors
        cd "$HOME" 2>/dev/null || cd / 2>/dev/null
        rm -rf ~/TracLine
    fi
else
    # In non-interactive mode without --remove-data, keep source code
    echo -e "${YELLOW}Note: Source code at ~/TracLine was not removed${NC}"
    echo "To remove it, use: --remove-data flag"
fi

# Clean up PATH entries from shell configs
echo -e "${GREEN}Cleaning shell configurations...${NC}"
for config in ~/.bashrc ~/.zshrc ~/.profile; do
    if [ -f "$config" ]; then
        # Create backup
        cp "$config" "${config}.tracline-backup" 2>/dev/null || true
        # Remove TracLine PATH entries (commented out for safety)
        # sed -i '/# Added by TracLine installer/d' "$config" 2>/dev/null || true
    fi
done

echo ""
echo -e "${GREEN}✓ Uninstall complete${NC}"
echo ""

# Check what remains
remaining=()
[ -d ~/.tracline ] && remaining+=("Configuration: ~/.tracline")
[ -d ~/TracLine ] && remaining+=("Source code: ~/TracLine")
[ -d ~/.config/tracline ] && remaining+=("Config: ~/.config/tracline")

if [ ${#remaining[@]} -gt 0 ]; then
    echo "Remaining items:"
    for item in "${remaining[@]}"; do
        echo "  - $item"
    done
    echo ""
    echo "To remove everything:"
    echo "  rm -rf ~/.tracline ~/TracLine ~/.config/tracline"
fi

# Final instructions
if [ "$INTERACTIVE" = false ]; then
    echo ""
    echo -e "${YELLOW}For interactive uninstall with more options:${NC}"
    echo "  git clone https://github.com/techs-targe/TracLine.git"
    echo "  cd TracLine"
    echo "  bash scripts/uninstall.sh"
fi