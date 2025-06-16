#!/bin/bash
# TracLine SQLite Uninstaller
# One-line uninstall: curl -fsSL https://raw.githubusercontent.com/techs-targe/TracLine/main/scripts/uninstall-sqlite.sh | bash

set -e

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
echo "TracLine SQLite Uninstaller"
echo "============================"
echo ""

echo -e "${YELLOW}This will remove:${NC}"
echo "  - TracLine application"
echo "  - Convenience commands (tracline-start, tracline-web)"
echo "  - SQLite database (if --remove-data is used)"
echo ""
echo -e "${YELLOW}This will NOT remove:${NC}"
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
            echo "  curl -fsSL https://raw.githubusercontent.com/techs-targe/TracLine/main/scripts/uninstall-sqlite.sh | bash -s -- --remove-data"
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

# Uninstall TracLine
echo -e "${GREEN}Removing TracLine...${NC}"
if command -v pipx >/dev/null 2>&1; then
    pipx uninstall tracline 2>/dev/null || true
fi

# Remove commands
echo -e "${GREEN}Removing commands...${NC}"
rm -f ~/.local/bin/tracline-start
rm -f ~/.local/bin/tracline-web

# Handle data removal
if [ "$REMOVE_DATA" = true ]; then
    echo -e "${GREEN}Removing data...${NC}"
    rm -rf ~/.tracline
    rm -rf ~/.config/tracline
    echo -e "${GREEN}Removing source code...${NC}"
    rm -rf ~/TracLine
elif [ "$INTERACTIVE" = true ]; then
    echo ""
    read -p "Remove TracLine data and configuration? (y/N) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo -e "${GREEN}Removing data...${NC}"
        rm -rf ~/.tracline
        rm -rf ~/.config/tracline
    fi
    
    echo ""
    read -p "Remove TracLine source code? (y/N) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo -e "${GREEN}Removing source...${NC}"
        rm -rf ~/TracLine
    fi
else
    # In non-interactive mode without --remove-data, keep everything
    echo -e "${YELLOW}Note: Data and source code were not removed${NC}"
    echo "To remove everything, use: --remove-data flag"
fi

# Clean up PATH entries from shell configs
echo -e "${GREEN}Cleaning shell configurations...${NC}"
for config in ~/.bashrc ~/.zshrc ~/.profile; do
    if [ -f "$config" ]; then
        # Create backup
        cp "$config" "${config}.tracline-backup" 2>/dev/null || true
    fi
done

echo ""
echo -e "${GREEN}✓ Uninstall complete${NC}"
echo ""

# Check what remains
remaining=()
[ -d ~/.tracline ] && remaining+=("Configuration: ~/.tracline")
[ -f ~/.tracline/tracline.db ] && remaining+=("SQLite database: ~/.tracline/tracline.db")
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