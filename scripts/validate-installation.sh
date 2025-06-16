#!/bin/bash
# TracLine Installation Validator
# Checks if TracLine is properly installed and configured

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo "======================================"
echo "TracLine Installation Validator"
echo "======================================"
echo ""

ISSUES=0

# Check TracLine command
echo -n "Checking tracline command... "
if command -v tracline >/dev/null 2>&1; then
    VERSION=$(tracline --version 2>/dev/null || echo "error")
    echo -e "${GREEN}✓ Found${NC} (version: $VERSION)"
else
    echo -e "${RED}✗ Not found${NC}"
    echo "  Fix: source ~/.bashrc or open new terminal"
    ((ISSUES++))
fi

# Check convenience commands
echo -n "Checking tracline-start... "
if [ -x "$HOME/.local/bin/tracline-start" ]; then
    echo -e "${GREEN}✓ Found${NC}"
else
    echo -e "${RED}✗ Not found${NC}"
    ((ISSUES++))
fi

echo -n "Checking tracline-stop... "
if [ -x "$HOME/.local/bin/tracline-stop" ]; then
    echo -e "${GREEN}✓ Found${NC}"
else
    echo -e "${RED}✗ Not found${NC}"
    ((ISSUES++))
fi

# Check Docker
echo -n "Checking Docker access... "
if docker info >/dev/null 2>&1; then
    echo -e "${GREEN}✓ OK${NC}"
else
    echo -e "${RED}✗ Permission denied${NC}"
    echo "  Fix: newgrp docker or logout/login"
    ((ISSUES++))
fi

# Check configuration
echo -n "Checking configuration... "
if [ -f "$HOME/.tracline/tracline.yaml" ]; then
    echo -e "${GREEN}✓ Found${NC}"
else
    echo -e "${RED}✗ Not found${NC}"
    ((ISSUES++))
fi

# Check source directory
echo -n "Checking source code... "
if [ -d "$HOME/TracLine" ]; then
    echo -e "${GREEN}✓ Found${NC}"
else
    echo -e "${RED}✗ Not found${NC}"
    ((ISSUES++))
fi

# Check PATH
echo -n "Checking PATH... "
if echo "$PATH" | grep -q ".local/bin"; then
    echo -e "${GREEN}✓ Configured${NC}"
else
    echo -e "${YELLOW}! Not in PATH${NC}"
    echo "  Fix: source ~/.bashrc"
    ((ISSUES++))
fi

# Check Python dependencies
echo -n "Checking pipx installation... "
if pipx list | grep -q tracline >/dev/null 2>&1; then
    echo -e "${GREEN}✓ Installed${NC}"
else
    echo -e "${RED}✗ Not installed${NC}"
    ((ISSUES++))
fi

# Summary
echo ""
echo "======================================"
if [ $ISSUES -eq 0 ]; then
    echo -e "${GREEN}✓ All checks passed!${NC}"
    echo ""
    echo "TracLine is properly installed."
    echo "You can now run: tracline-start"
else
    echo -e "${YELLOW}⚠ Found $ISSUES issue(s)${NC}"
    echo ""
    echo "Please fix the issues above before starting TracLine."
    echo "Run this validator again after fixing."
fi
echo "======================================" 