#!/bin/bash
# TracLine Installation Diagnostic Tool
# Helps identify and fix common installation issues

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo "======================================"
echo "TracLine Installation Diagnostics"
echo "======================================"
echo ""

# Check TracLine directory
echo "1. Checking TracLine directory..."
if [ -d "$HOME/TracLine" ]; then
    if [ -d "$HOME/TracLine/.git" ]; then
        echo -e "${GREEN}✓ TracLine directory exists and is a git repository${NC}"
        cd "$HOME/TracLine"
        echo "  Current branch: $(git branch --show-current 2>/dev/null || echo 'unknown')"
        echo "  Last commit: $(git log -1 --oneline 2>/dev/null || echo 'unknown')"
    else
        echo -e "${YELLOW}⚠ TracLine directory exists but is not a git repository${NC}"
        echo "  This may cause installation issues"
        echo "  Fix: rm -rf ~/TracLine && git clone https://github.com/techs-targe/TracLine.git"
    fi
else
    echo -e "${RED}✗ TracLine directory not found${NC}"
    echo "  Fix: git clone https://github.com/techs-targe/TracLine.git"
fi

# Check docker-compose.yml
echo ""
echo "2. Checking docker-compose.yml..."
if [ -f "$HOME/TracLine/docker-compose.yml" ]; then
    echo -e "${GREEN}✓ docker-compose.yml found${NC}"
else
    echo -e "${RED}✗ docker-compose.yml not found${NC}"
    echo "  The TracLine directory may be corrupted"
fi

# Check tracline command
echo ""
echo "3. Checking tracline command..."
if command -v tracline >/dev/null 2>&1; then
    echo -e "${GREEN}✓ tracline command found${NC}"
    echo "  Location: $(which tracline)"
    echo "  Version: $(tracline --version 2>/dev/null || echo 'unknown')"
else
    echo -e "${RED}✗ tracline command not found${NC}"
    echo "  Fix: source ~/.bashrc"
fi

# Check pipx installation
echo ""
echo "4. Checking pipx installation..."
if pipx list 2>/dev/null | grep -q "package tracline"; then
    echo -e "${GREEN}✓ TracLine installed via pipx${NC}"
    pipx list | grep -A2 "package tracline"
else
    echo -e "${RED}✗ TracLine not found in pipx${NC}"
    echo "  Fix: cd ~/TracLine && pipx install . --force"
fi

# Check convenience commands
echo ""
echo "5. Checking convenience commands..."
for cmd in tracline-start tracline-stop; do
    if [ -x "$HOME/.local/bin/$cmd" ]; then
        echo -e "${GREEN}✓ $cmd found${NC}"
    else
        echo -e "${RED}✗ $cmd not found${NC}"
        echo "  The installer may not have completed successfully"
    fi
done

# Check Docker
echo ""
echo "6. Checking Docker..."
if docker info >/dev/null 2>&1; then
    echo -e "${GREEN}✓ Docker access OK${NC}"
else
    echo -e "${RED}✗ Docker permission denied${NC}"
    echo "  Fix: newgrp docker or logout/login"
fi

# Summary
echo ""
echo "======================================"
echo "Summary"
echo "======================================"
echo ""
echo "If you're seeing 'TracLine directory not found' error:"
echo "1. Clone the repository: git clone https://github.com/techs-targe/TracLine.git"
echo "2. Or run the installer again: curl -fsSL https://raw.githubusercontent.com/techs-targe/TracLine/main/scripts/install-ubuntu.sh | bash"
echo ""
echo "For other issues, follow the fix suggestions above."