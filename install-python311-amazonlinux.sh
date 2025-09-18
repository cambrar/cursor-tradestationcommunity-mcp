#!/bin/bash

# Install Python 3.11 on Amazon Linux 2023
# This script builds Python 3.11 from source if not available via package manager

set -euo pipefail

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

log_info "Installing Python 3.11 on Amazon Linux 2023..."

# Install build dependencies
log_info "Installing build dependencies..."
yum groupinstall -y "Development Tools"
yum install -y \
    openssl-devel \
    bzip2-devel \
    libffi-devel \
    zlib-devel \
    readline-devel \
    sqlite-devel \
    wget \
    curl \
    llvm \
    ncurses-devel \
    tk-devel \
    lzma \
    xz-devel

# Download Python 3.11 source
PYTHON_VERSION="3.11.10"
PYTHON_DIR="/tmp/Python-${PYTHON_VERSION}"

log_info "Downloading Python ${PYTHON_VERSION} source..."
cd /tmp
wget "https://www.python.org/ftp/python/${PYTHON_VERSION}/Python-${PYTHON_VERSION}.tgz"
tar -xzf "Python-${PYTHON_VERSION}.tgz"

# Configure and build Python
log_info "Building Python ${PYTHON_VERSION}..."
cd "$PYTHON_DIR"

./configure \
    --enable-optimizations \
    --enable-shared \
    --with-ensurepip=install \
    --enable-loadable-sqlite-extensions

make -j$(nproc)
make altinstall

# Create symlinks
log_info "Creating symlinks..."
ln -sf /usr/local/bin/python3.11 /usr/bin/python3.11
ln -sf /usr/local/bin/pip3.11 /usr/bin/pip3.11

# Update library path
echo "/usr/local/lib" > /etc/ld.so.conf.d/python3.11.conf
ldconfig

# Create symlinks but don't change system defaults
log_info "Creating symlinks (keeping system python3 unchanged)..."
# Just ensure python3.11 is available - don't change what python3 points to

# Cleanup
log_info "Cleaning up..."
cd /
rm -rf "$PYTHON_DIR"
rm -f "/tmp/Python-${PYTHON_VERSION}.tgz"

# Verify installation
INSTALLED_VERSION=$(python3.11 --version 2>&1 | cut -d' ' -f2)
log_success "Python ${INSTALLED_VERSION} installed successfully!"

# Test pip
python3.11 -m pip --version
log_success "pip is working correctly"

log_info "Python 3.11 installation completed!"
log_info "Your existing python3 remains unchanged: $(python3 --version 2>&1)"
log_info "Python 3.11 is available as: python3.11 --version (shows ${INSTALLED_VERSION})"
log_info "The TradeStation MCP deployment will use python3.11 for its virtual environment only"
