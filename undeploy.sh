#!/bin/bash

# TradeStation Community MCP Server Undeployment Script
# Safely removes the deployed MCP server

set -euo pipefail  # Exit on error, undefined vars, pipe failures

# Configuration
PROJECT_NAME="tradestation-community-mcp"
PROJECT_DIR="/data/${PROJECT_NAME}"
SERVICE_NAME="tradestation-community-mcp"
SERVICE_USER="mcp-server"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
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
check_root() {
    if [[ $EUID -ne 0 ]]; then
        log_error "This script must be run as root (use sudo)"
        exit 1
    fi
}

# Confirm undeployment
confirm_undeploy() {
    log_warning "This will completely remove the TradeStation Community MCP Server"
    log_warning "Project directory: $PROJECT_DIR"
    log_warning "Service: $SERVICE_NAME"
    log_warning "User: $SERVICE_USER"
    echo
    
    read -p "Are you sure you want to continue? (y/N): " -r
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        log_info "Undeployment cancelled"
        exit 0
    fi
}

# Stop and disable service
stop_service() {
    log_info "Stopping and disabling service..."
    
    if systemctl list-unit-files | grep -q "$SERVICE_NAME"; then
        # Stop service
        if systemctl is-active --quiet "$SERVICE_NAME"; then
            systemctl stop "$SERVICE_NAME"
            log_success "Service stopped"
        else
            log_info "Service was not running"
        fi
        
        # Disable service
        if systemctl is-enabled --quiet "$SERVICE_NAME" 2>/dev/null; then
            systemctl disable "$SERVICE_NAME"
            log_success "Service disabled"
        else
            log_info "Service was not enabled"
        fi
    else
        log_info "Service $SERVICE_NAME does not exist"
    fi
}

# Remove systemd service file
remove_service_file() {
    log_info "Removing systemd service file..."
    
    SERVICE_FILE="/etc/systemd/system/${SERVICE_NAME}.service"
    
    if [[ -f "$SERVICE_FILE" ]]; then
        rm -f "$SERVICE_FILE"
        systemctl daemon-reload
        log_success "Service file removed"
    else
        log_info "Service file does not exist"
    fi
}

# Remove project directory
remove_project_directory() {
    log_info "Removing project directory..."
    
    if [[ -d "$PROJECT_DIR" ]]; then
        rm -rf "$PROJECT_DIR"
        log_success "Project directory removed"
    else
        log_info "Project directory does not exist"
    fi
}

# Remove service user
remove_service_user() {
    log_info "Removing service user..."
    
    if id "$SERVICE_USER" &>/dev/null; then
        # Kill any processes owned by the user
        pkill -u "$SERVICE_USER" 2>/dev/null || true
        
        # Remove user
        userdel "$SERVICE_USER" 2>/dev/null || true
        log_success "Service user removed"
    else
        log_info "Service user does not exist"
    fi
}

# Clean up any remaining files
cleanup_remaining() {
    log_info "Cleaning up any remaining files..."
    
    # Remove any log files that might exist
    rm -f /var/log/"$SERVICE_NAME"* 2>/dev/null || true
    
    # Clean systemd journal if needed
    journalctl --vacuum-time=1d --quiet 2>/dev/null || true
    
    log_success "Cleanup completed"
}

# Display undeployment summary
display_summary() {
    log_success "Undeployment completed successfully!"
    echo
    log_info "Removed components:"
    echo "  ✓ Systemd service: $SERVICE_NAME"
    echo "  ✓ Project directory: $PROJECT_DIR"
    echo "  ✓ Service user: $SERVICE_USER"
    echo "  ✓ Associated files and logs"
    echo
    log_info "The TradeStation Community MCP Server has been completely removed from this system."
}

# Main undeployment function
main() {
    log_info "Starting TradeStation Community MCP Server undeployment..."
    
    check_root
    confirm_undeploy
    stop_service
    remove_service_file
    remove_project_directory
    remove_service_user
    cleanup_remaining
    display_summary
    
    log_success "Undeployment completed successfully!"
}

# Run main function
main "$@"
