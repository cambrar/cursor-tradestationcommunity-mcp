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

# Set up alternatives
log_info "Setting up alternatives..."
alternatives --install /usr/bin/python3 python3 /usr/bin/python3.11 50
alternatives --install /usr/bin/pip3 pip3 /usr/bin/pip3.11 50

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
log_info "You can now run: python3 --version (should show 3.11.x)"
log_info "You can now run: pip3 --version (should use pip from Python 3.11)"
