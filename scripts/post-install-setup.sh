#!/bin/bash
# Post-installation setup script for TracLine
# This ensures PATH is properly configured and commands are available

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo "======================================="
echo "TracLine Post-Installation Setup"
echo "======================================="
echo ""

# Update PATH for current session
export PATH="$HOME/.local/bin:$PATH"

# Ensure PATH is in shell configurations
SHELLS=(".bashrc" ".zshrc" ".profile")
for shell_rc in "${SHELLS[@]}"; do
    if [ -f "$HOME/$shell_rc" ]; then
        if ! grep -q '.local/bin' "$HOME/$shell_rc" 2>/dev/null; then
            echo 'export PATH="$HOME/.local/bin:$PATH"' >> "$HOME/$shell_rc"
            echo -e "${GREEN}Updated $shell_rc with PATH${NC}"
        fi
    fi
done

# Source bashrc if in bash
if [ -n "$BASH_VERSION" ]; then
    source ~/.bashrc 2>/dev/null || true
fi

# Verify installation
echo ""
echo -e "${GREEN}Verifying installation...${NC}"

if command -v tracline >/dev/null 2>&1; then
    echo -e "${GREEN}✓ tracline command found${NC}"
    tracline --version
else
    echo -e "${RED}✗ tracline command not found${NC}"
    echo "Please open a new terminal or run: source ~/.bashrc"
    exit 1
fi

if [ -x "$HOME/.local/bin/tracline-start" ]; then
    echo -e "${GREEN}✓ tracline-start command found${NC}"
else
    echo -e "${RED}✗ tracline-start command not found${NC}"
fi

if [ -x "$HOME/.local/bin/tracline-stop" ]; then
    echo -e "${GREEN}✓ tracline-stop command found${NC}"
else
    echo -e "${RED}✗ tracline-stop command not found${NC}"
fi

# Check docker
if groups | grep -q docker; then
    echo -e "${GREEN}✓ User in docker group${NC}"
else
    echo -e "${YELLOW}! User not in docker group yet${NC}"
    echo "  Run: newgrp docker"
    echo "  Or logout and login again"
fi

echo ""
echo -e "${GREEN}Setup complete!${NC}"
echo ""
echo "You can now use:"
echo "  tracline         - CLI tool"
echo "  tracline-start   - Start TracLine services"
echo "  tracline-stop    - Stop TracLine services"
echo ""
echo "To start TracLine:"
echo "  tracline-start"