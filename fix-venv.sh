#!/bin/bash

# Quick script to fix the virtual environment Python version issue
# Run this if you're getting MCP library installation errors

set -euo pipefail

PROJECT_DIR="/data/tradestation-community-mcp"
SERVICE_USER="mcp-server"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if running as root
if [[ $EUID -ne 0 ]]; then
    log_error "This script must be run as root (use sudo)"
    exit 1
fi

log_info "Fixing TradeStation MCP virtual environment..."

# Check current venv Python version
VENV_DIR="$PROJECT_DIR/venv"
if [[ -d "$VENV_DIR" && -f "$VENV_DIR/bin/python" ]]; then
    CURRENT_VERSION=$("$VENV_DIR/bin/python" -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>/dev/null || echo "unknown")
    log_info "Current venv Python version: $CURRENT_VERSION"
else
    log_info "No existing virtual environment found"
    CURRENT_VERSION="none"
fi

# Check available Python versions
if command -v python3.11 &> /dev/null; then
    PYTHON_CMD="python3.11"
    PYTHON_VERSION=$(python3.11 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
    log_info "Found Python 3.11: $PYTHON_VERSION"
elif command -v python3.10 &> /dev/null; then
    PYTHON_CMD="python3.10"
    PYTHON_VERSION=$(python3.10 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
    log_info "Found Python 3.10: $PYTHON_VERSION"
else
    PYTHON_CMD="python3"
    PYTHON_VERSION=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
    log_warning "Only found Python $PYTHON_VERSION (MCP requires 3.10+)"
fi

# Check if we need to recreate the venv
if [[ "$CURRENT_VERSION" != "$PYTHON_VERSION" ]] || [[ "$CURRENT_VERSION" < "3.10" ]]; then
    log_warning "Virtual environment needs to be recreated"
    log_info "Removing old virtual environment..."
    rm -rf "$VENV_DIR"
    
    log_info "Creating new virtual environment with $PYTHON_CMD ($PYTHON_VERSION)..."
    sudo -u "$SERVICE_USER" $PYTHON_CMD -m venv "$VENV_DIR"
    
    log_info "Upgrading pip..."
    sudo -u "$SERVICE_USER" "$VENV_DIR/bin/pip" install --upgrade pip
    
    log_info "Installing Python dependencies..."
    sudo -u "$SERVICE_USER" "$VENV_DIR/bin/pip" install -r "$PROJECT_DIR/requirements.txt"
    
    log_success "Virtual environment recreated with Python $PYTHON_VERSION"
else
    log_info "Virtual environment already uses correct Python version ($CURRENT_VERSION)"
fi

# Verify the installation
log_info "Verifying MCP library installation..."
if sudo -u "$SERVICE_USER" "$VENV_DIR/bin/python" -c "import mcp; print(f'MCP library version: {mcp.__version__}')" 2>/dev/null; then
    log_success "MCP library is properly installed!"
else
    log_error "MCP library installation failed"
    exit 1
fi

log_success "Virtual environment fix completed!"
log_info "You can now test the server with:"
log_info "  cd $PROJECT_DIR"
log_info "  sudo -u $SERVICE_USER ./venv/bin/python server.py --help"
