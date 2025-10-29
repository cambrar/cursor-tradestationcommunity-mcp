#!/bin/bash

# Install Playwright browsers after deploying
# Run this after the main deployment

set -euo pipefail

PROJECT_DIR="/data/tradestation-community-mcp"
SERVICE_USER="mcp-server"

# Colors
BLUE='\033[0;34m'
GREEN='\033[0;32m'
NC='\033[0m'

echo -e "${BLUE}[INFO]${NC} Installing Playwright browsers..."

# Install Playwright browsers
cd "$PROJECT_DIR"
sudo -u "$SERVICE_USER" ./venv/bin/playwright install chromium

# Install system dependencies for Playwright
sudo -u "$SERVICE_USER" ./venv/bin/playwright install-deps chromium || {
    echo -e "${BLUE}[INFO]${NC} Installing system dependencies for Playwright..."
    # Amazon Linux 2023
    if command -v yum &> /dev/null; then
        yum install -y \
            liberation-fonts \
            libX11 \
            libXcomposite \
            libXcursor \
            libXdamage \
            libXext \
            libXi \
            libXrandr \
            libXrender \
            libXss \
            libXtst \
            libglib-2.0-0 \
            libnss3 \
            libnspr4 \
            libatk1.0-0 \
            libatk-bridge2.0-0 \
            libcups2 \
            libdrm2 \
            libxkbcommon \
            libxshmfence \
            libgbm1 \
            libasound2 \
            fontconfig
    # Ubuntu
    elif command -v apt-get &> /dev/null; then
        sudo -u "$SERVICE_USER" ./venv/bin/playwright install-deps chromium
    fi
}

echo -e "${GREEN}[SUCCESS]${NC} Playwright browsers installed!"
echo -e "${BLUE}[INFO]${NC} The MCP server can now handle OAuth authentication."
