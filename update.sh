#!/bin/bash

# TradeStation Community MCP Server Update Script
# Updates the deployed MCP server with new code

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

# Check if service is deployed
check_deployment() {
    log_info "Checking if service is deployed..."
    
    if [[ ! -d "$PROJECT_DIR" ]]; then
        log_error "Project directory $PROJECT_DIR does not exist"
        log_error "Please run deploy.sh first"
        exit 1
    fi
    
    if ! systemctl list-unit-files | grep -q "$SERVICE_NAME"; then
        log_error "Service $SERVICE_NAME is not installed"
        log_error "Please run deploy.sh first"
        exit 1
    fi
    
    log_success "Service deployment verified"
}

# Create backup
create_backup() {
    log_info "Creating backup of current deployment..."
    
    BACKUP_DIR="${PROJECT_DIR}_backup_$(date +%Y%m%d_%H%M%S)"
    
    # Copy current deployment
    cp -r "$PROJECT_DIR" "$BACKUP_DIR"
    
    # Store backup location for potential rollback
    echo "$BACKUP_DIR" > "/tmp/${SERVICE_NAME}_last_backup"
    
    log_success "Backup created: $BACKUP_DIR"
}

# Stop service
stop_service() {
    log_info "Stopping service for update..."
    
    if systemctl is-active --quiet "$SERVICE_NAME"; then
        systemctl stop "$SERVICE_NAME"
        log_success "Service stopped"
        
        # Wait for service to fully stop
        sleep 2
    else
        log_info "Service was not running"
    fi
}

# Update application files
update_files() {
    log_info "Updating application files..."
    
    # Get the directory where this script is located
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    
    # Update application files
    cp "$SCRIPT_DIR/server.py" "$PROJECT_DIR/"
    cp "$SCRIPT_DIR/requirements.txt" "$PROJECT_DIR/"
    cp "$SCRIPT_DIR/README.md" "$PROJECT_DIR/"
    
    # Always update .env.example with latest template
    if [[ -f "$SCRIPT_DIR/env.example" ]]; then
        cp "$SCRIPT_DIR/env.example" "$PROJECT_DIR/.env.example"
        log_info "Updated .env.example with latest template"
    fi
    
    # Never overwrite existing .env file
    if [[ ! -f "$PROJECT_DIR/.env" ]]; then
        if [[ -f "$PROJECT_DIR/.env.example" ]]; then
            cp "$PROJECT_DIR/.env.example" "$PROJECT_DIR/.env"
            log_warning "Created new .env file from template - PLEASE UPDATE WITH YOUR CREDENTIALS"
        fi
    else
        log_info "Existing .env file preserved (not overwritten)"
        log_info "Check .env.example for any new configuration options"
    fi
    
    # Set ownership
    chown -R "$SERVICE_USER:$SERVICE_USER" "$PROJECT_DIR"
    
    # Make server.py executable
    chmod +x "$PROJECT_DIR/server.py"
    
    log_success "Application files updated"
}

# Update Python dependencies
update_dependencies() {
    log_info "Updating Python dependencies..."
    
    VENV_DIR="$PROJECT_DIR/venv"
    
    if [[ ! -d "$VENV_DIR" ]]; then
        log_error "Virtual environment not found: $VENV_DIR"
        exit 1
    fi
    
    # Upgrade pip
    sudo -u "$SERVICE_USER" "$VENV_DIR/bin/pip" install --upgrade pip
    
    # Install/update requirements
    sudo -u "$SERVICE_USER" "$VENV_DIR/bin/pip" install -r "$PROJECT_DIR/requirements.txt" --upgrade
    
    log_success "Dependencies updated"
}

# Start service
start_service() {
    log_info "Starting service..."
    
    systemctl start "$SERVICE_NAME"
    
    # Wait a moment for service to start
    sleep 3
    
    # Check service status
    if systemctl is-active --quiet "$SERVICE_NAME"; then
        log_success "Service started successfully"
    else
        log_error "Service failed to start after update"
        log_info "Checking service status..."
        systemctl status "$SERVICE_NAME" --no-pager
        
        # Offer to rollback
        echo
        log_warning "Update failed. Would you like to rollback? (y/N)"
        read -r -n 1 response
        echo
        if [[ $response =~ ^[Yy]$ ]]; then
            rollback_deployment
        fi
        exit 1
    fi
}

# Rollback deployment
rollback_deployment() {
    log_warning "Rolling back to previous version..."
    
    BACKUP_FILE="/tmp/${SERVICE_NAME}_last_backup"
    
    if [[ ! -f "$BACKUP_FILE" ]]; then
        log_error "No backup information found"
        exit 1
    fi
    
    BACKUP_DIR=$(cat "$BACKUP_FILE")
    
    if [[ ! -d "$BACKUP_DIR" ]]; then
        log_error "Backup directory not found: $BACKUP_DIR"
        exit 1
    fi
    
    # Stop service
    systemctl stop "$SERVICE_NAME" 2>/dev/null || true
    
    # Remove current deployment
    rm -rf "$PROJECT_DIR"
    
    # Restore backup
    mv "$BACKUP_DIR" "$PROJECT_DIR"
    
    # Start service
    systemctl start "$SERVICE_NAME"
    
    # Cleanup backup file
    rm -f "$BACKUP_FILE"
    
    if systemctl is-active --quiet "$SERVICE_NAME"; then
        log_success "Rollback completed successfully"
    else
        log_error "Rollback failed - service is not running"
        exit 1
    fi
}

# Cleanup old backups
cleanup_backups() {
    log_info "Cleaning up old backups..."
    
    # Keep only the 3 most recent backups
    BACKUP_PATTERN="${PROJECT_DIR}_backup_*"
    BACKUP_COUNT=$(ls -d $BACKUP_PATTERN 2>/dev/null | wc -l)
    
    if [[ $BACKUP_COUNT -gt 3 ]]; then
        # Remove oldest backups, keeping the 3 most recent
        ls -dt $BACKUP_PATTERN | tail -n +4 | xargs rm -rf
        log_success "Cleaned up old backups"
    else
        log_info "No old backups to clean up"
    fi
}

# Display update information
display_info() {
    log_success "Update completed successfully!"
    echo
    log_info "Service Information:"
    echo "  Service Status: $(systemctl is-active $SERVICE_NAME)"
    echo "  Project Directory: $PROJECT_DIR"
    echo "  Service User: $SERVICE_USER"
    echo
    log_info "Useful Commands:"
    echo "  Check status: sudo systemctl status $SERVICE_NAME"
    echo "  View logs: sudo journalctl -u $SERVICE_NAME -f"
    echo "  Restart: sudo systemctl restart $SERVICE_NAME"
    echo
    log_info "To rollback if needed:"
    echo "  Run this script again and it will offer rollback option if update fails"
}

# Main update function
main() {
    log_info "Starting TradeStation Community MCP Server update..."
    
    check_root
    check_deployment
    create_backup
    stop_service
    update_files
    update_dependencies
    start_service
    cleanup_backups
    display_info
    
    log_success "Update completed successfully!"
}

# Handle command line arguments
case "${1:-}" in
    "rollback")
        log_info "Manual rollback requested..."
        check_root
        rollback_deployment
        ;;
    *)
        main "$@"
        ;;
esac
