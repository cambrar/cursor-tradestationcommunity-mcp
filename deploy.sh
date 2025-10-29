#!/bin/bash

# TradeStation Community MCP Server Deployment Script
# Supports Amazon Linux 2023 and Ubuntu
# Idempotent - can be run multiple times safely

set -euo pipefail  # Exit on error, undefined vars, pipe failures

# Configuration
PROJECT_NAME="tradestation-community-mcp"
PROJECT_DIR="/data/${PROJECT_NAME}"
SERVICE_NAME="tradestation-community-mcp"
SERVICE_USER="mcp-server"
PYTHON_VERSION="3.10"  # Minimum required version for MCP library

# Deployment options
INSTALL_SYSTEMD_SERVICE=false
INSTALL_AS_USER=false
USER_INSTALL_DIR=""

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

# Parse command line arguments
parse_arguments() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            --systemd|--service)
                INSTALL_SYSTEMD_SERVICE=true
                shift
                ;;
            --user)
                INSTALL_AS_USER=true
                if [[ -n "${2:-}" && ! "$2" =~ ^-- ]]; then
                    USER_INSTALL_DIR="$2"
                    shift
                else
                    USER_INSTALL_DIR="$HOME/.local/share/${PROJECT_NAME}"
                fi
                shift
                ;;
            --help|-h)
                show_help
                exit 0
                ;;
            *)
                log_error "Unknown option: $1"
                show_help
                exit 1
                ;;
        esac
    done
    
    # Adjust configuration for user install
    if [[ "$INSTALL_AS_USER" == "true" ]]; then
        PROJECT_DIR="$USER_INSTALL_DIR"
        SERVICE_USER="$USER"
    fi
}

# Show help
show_help() {
    echo "TradeStation Community MCP Server Deployment Script"
    echo
    echo "Usage: $0 [OPTIONS]"
    echo
    echo "Options:"
    echo "  --systemd, --service    Install as systemd service (requires root)"
    echo "  --user [DIR]           Install for current user only (default: ~/.local/share/tradestation-community-mcp)"
    echo "  --help, -h             Show this help message"
    echo
    echo "Examples:"
    echo "  $0                     Basic installation (no service)"
    echo "  sudo $0 --systemd      Install with systemd service"
    echo "  $0 --user              Install for current user"
    echo "  $0 --user ~/my-mcp     Install to custom user directory"
}

# Check if running as root (only required for system install with systemd)
check_root() {
    if [[ "$INSTALL_AS_USER" == "false" && "$INSTALL_SYSTEMD_SERVICE" == "true" ]]; then
        if [[ $EUID -ne 0 ]]; then
            log_error "Systemd service installation requires root privileges (use sudo)"
            exit 1
        fi
    elif [[ "$INSTALL_AS_USER" == "false" && $EUID -ne 0 ]]; then
        log_warning "Installing to system directory without systemd service"
        log_warning "Consider using --user flag for user installation"
        if [[ $EUID -ne 0 ]]; then
            log_error "System installation requires root privileges (use sudo)"
            exit 1
        fi
    fi
}

# Detect OS distribution
detect_os() {
    if [[ -f /etc/os-release ]]; then
        . /etc/os-release
        OS=$ID
        OS_VERSION=$VERSION_ID
    else
        log_error "Cannot detect OS distribution"
        exit 1
    fi
    
    log_info "Detected OS: $OS $OS_VERSION"
}

# Install system dependencies
install_system_deps() {
    log_info "Installing system dependencies..."
    
    case $OS in
        "amzn")
            # Amazon Linux 2023
            yum update -y
            
            # Install core packages first
            yum install -y git wget systemd
            
            # Try to install Python 3.11 for MCP compatibility
            log_info "Checking for Python 3.11 availability..."
            if yum list available python3.11 &> /dev/null; then
                log_info "Installing Python 3.11 for MCP compatibility..."
                yum install -y python3.11 python3.11-pip python3.11-devel
                
                # Don't change system-wide python3 - we'll use python3.11 explicitly in venv
                log_info "Python 3.11 installed (will be used only for this project's venv)"
                
                # Also ensure python3.11 is directly available
                if [[ ! -f /usr/bin/python3.11 ]]; then
                    ln -sf /usr/local/bin/python3.11 /usr/bin/python3.11 2>/dev/null || true
                fi
            else
                log_warning "Python 3.11 not available in repositories"
                # Try to install from source or alternative repo
                log_info "Attempting to install Python 3.11 from EPEL or build from source..."
                
                # Enable EPEL repository which might have newer Python
                yum install -y epel-release || true
                yum install -y python3.11 python3.11-pip python3.11-devel || {
                    log_warning "Could not install Python 3.11, falling back to default python3"
                    yum install -y python3 python3-pip python3-devel
                }
            fi
            
            # Handle curl/curl-minimal conflict - only install if curl is not available
            if ! command -v curl &> /dev/null; then
                log_info "Installing curl (replacing curl-minimal if present)..."
                yum install -y --allowerasing curl
            else
                log_info "curl is already available"
            fi
            ;;
        "ubuntu")
            # Ubuntu
            apt-get update
            apt-get install -y python3 python3-pip python3-venv git curl wget systemd
            ;;
        *)
            log_error "Unsupported OS: $OS"
            exit 1
            ;;
    esac
    
    log_success "System dependencies installed"
}

# Check Python version and venv availability
check_python_version() {
    log_info "Checking Python version and venv availability..."
    
    if ! command -v python3 &> /dev/null; then
        log_error "python3 is not installed"
        exit 1
    fi
    
    PYTHON_INSTALLED_VERSION=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
    log_info "Python version: $PYTHON_INSTALLED_VERSION"
    
    # Simple version comparison (works for major.minor format)
    if [[ $(echo "$PYTHON_INSTALLED_VERSION >= $PYTHON_VERSION" | bc -l 2>/dev/null || echo "0") -eq 0 ]]; then
        # Fallback comparison without bc
        PYTHON_MAJOR=$(echo $PYTHON_INSTALLED_VERSION | cut -d. -f1)
        PYTHON_MINOR=$(echo $PYTHON_INSTALLED_VERSION | cut -d. -f2)
        REQ_MAJOR=$(echo $PYTHON_VERSION | cut -d. -f1)
        REQ_MINOR=$(echo $PYTHON_VERSION | cut -d. -f2)
        
        if [[ $PYTHON_MAJOR -lt $REQ_MAJOR ]] || [[ $PYTHON_MAJOR -eq $REQ_MAJOR && $PYTHON_MINOR -lt $REQ_MINOR ]]; then
            log_error "Python $PYTHON_VERSION or higher is required for MCP library, but $PYTHON_INSTALLED_VERSION is installed"
            case $OS in
                "amzn")
                    log_error "Try installing Python 3.11: sudo yum install -y python3.11 python3.11-pip python3.11-devel"
                    log_error "Then create symlinks: sudo alternatives --install /usr/bin/python3 python3 /usr/bin/python3.11 1"
                    ;;
                "ubuntu")
                    log_error "Try installing Python 3.11: sudo apt-get install -y python3.11 python3.11-pip python3.11-venv"
                    ;;
            esac
            exit 1
        fi
    fi
    
    # Check if venv module is available (use the Python version we'll actually use)
    VENV_PYTHON="python3"
    if command -v python3.11 &> /dev/null; then
        VENV_PYTHON="python3.11"
    elif command -v python3.10 &> /dev/null; then
        VENV_PYTHON="python3.10"
    fi
    
    if ! $VENV_PYTHON -m venv --help &> /dev/null; then
        log_error "Python venv module is not available for $VENV_PYTHON"
        case $OS in
            "amzn")
                log_error "On Amazon Linux 2023, try: sudo yum install -y python3-devel"
                ;;
            "ubuntu")
                log_error "On Ubuntu, try: sudo apt-get install -y python3-venv"
                ;;
        esac
        exit 1
    fi
    
    log_success "Python version and venv check passed"
}

# Create service user (only for system install)
create_service_user() {
    if [[ "$INSTALL_AS_USER" == "true" ]]; then
        log_info "Using current user: $SERVICE_USER"
        return
    fi
    
    log_info "Creating service user: $SERVICE_USER"
    
    if ! id "$SERVICE_USER" &>/dev/null; then
        useradd --system --home-dir "$PROJECT_DIR" --shell /bin/false --comment "MCP Server User" "$SERVICE_USER"
        log_success "Created user: $SERVICE_USER"
    else
        log_info "User $SERVICE_USER already exists"
    fi
}

# Create project directory and set permissions
setup_project_directory() {
    log_info "Setting up project directory: $PROJECT_DIR"
    
    # Create directory if it doesn't exist
    mkdir -p "$PROJECT_DIR"
    
    # Set ownership and permissions
    if [[ "$INSTALL_AS_USER" == "true" ]]; then
        # User install - just ensure directory exists and is owned by user
        chmod 755 "$PROJECT_DIR"
    else
        # System install - set ownership to service user
        chown -R "$SERVICE_USER:$SERVICE_USER" "$PROJECT_DIR"
        chmod 755 "$PROJECT_DIR"
    fi
    
    log_success "Project directory setup complete"
}

# Copy application files
copy_application_files() {
    log_info "Copying application files..."
    
    # Get the directory where this script is located
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    
    # Copy application files
    cp "$SCRIPT_DIR/server.py" "$PROJECT_DIR/"
    cp "$SCRIPT_DIR/tradestation_client.py" "$PROJECT_DIR/"
    cp "$SCRIPT_DIR/requirements.txt" "$PROJECT_DIR/"
    cp "$SCRIPT_DIR/README.md" "$PROJECT_DIR/"
    cp "$SCRIPT_DIR/start-mcp.sh" "$PROJECT_DIR/"
    
    # Copy utility scripts if they exist
    [[ -f "$SCRIPT_DIR/install-playwright.sh" ]] && cp "$SCRIPT_DIR/install-playwright.sh" "$PROJECT_DIR/"
    [[ -f "$SCRIPT_DIR/fix-venv.sh" ]] && cp "$SCRIPT_DIR/fix-venv.sh" "$PROJECT_DIR/"
    
    # Always update .env.example with latest template
    if [[ -f "$SCRIPT_DIR/env.example" ]]; then
        cp "$SCRIPT_DIR/env.example" "$PROJECT_DIR/.env.example"
        log_info "Updated .env.example with latest template"
    fi
    
    # Create .env from template ONLY if it doesn't exist
    if [[ ! -f "$PROJECT_DIR/.env" ]]; then
        if [[ -f "$PROJECT_DIR/.env.example" ]]; then
            cp "$PROJECT_DIR/.env.example" "$PROJECT_DIR/.env"
            log_warning "Created new .env file from template - PLEASE UPDATE WITH YOUR CREDENTIALS"
        else
            log_warning "No .env.example found - you'll need to create .env manually"
        fi
    else
        log_info "Existing .env file preserved (not overwritten)"
        log_info "Check .env.example for any new configuration options"
    fi
    
    # Set ownership and permissions
    if [[ "$INSTALL_AS_USER" == "false" ]]; then
        chown -R "$SERVICE_USER:$SERVICE_USER" "$PROJECT_DIR"
    fi
    
    # Make server.py executable
    chmod +x "$PROJECT_DIR/server.py"
    
    # Secure .env file permissions
    if [[ -f "$PROJECT_DIR/.env" ]]; then
        chmod 600 "$PROJECT_DIR/.env"
        if [[ "$INSTALL_AS_USER" == "false" ]]; then
            chown "$SERVICE_USER:$SERVICE_USER" "$PROJECT_DIR/.env"
        fi
    fi
    
    log_success "Application files copied"
}

# Setup Python virtual environment
setup_venv() {
    log_info "Setting up Python virtual environment..."
    
    VENV_DIR="$PROJECT_DIR/venv"
    
    # Determine which Python to use
    PYTHON_CMD="python3"
    if command -v python3.11 &> /dev/null; then
        PYTHON_CMD="python3.11"
        log_info "Using Python 3.11 for virtual environment"
    elif command -v python3.10 &> /dev/null; then
        PYTHON_CMD="python3.10"
        log_info "Using Python 3.10 for virtual environment"
    else
        log_info "Using default python3 for virtual environment"
    fi
    
    # Verify Python version before creating venv
    PYTHON_VERSION_CHECK=$($PYTHON_CMD -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
    log_info "Creating virtual environment with Python $PYTHON_VERSION_CHECK"
    
    # Always check if we need to recreate the venv
    RECREATE_VENV=false
    
    if [[ -d "$VENV_DIR" ]]; then
        # Check what Python version the existing venv uses
        if [[ -f "$VENV_DIR/bin/python" ]]; then
            EXISTING_VENV_VERSION=$("$VENV_DIR/bin/python" -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>/dev/null || echo "unknown")
            log_info "Existing virtual environment uses Python $EXISTING_VENV_VERSION"
            
            # Simple approach: if we're using python3.11 but venv is not 3.11, recreate it
            if [[ "$PYTHON_CMD" == "python3.11" ]] && [[ "$EXISTING_VENV_VERSION" != "3.11" ]]; then
                log_warning "Target Python is 3.11 but existing venv uses Python $EXISTING_VENV_VERSION"
                RECREATE_VENV=true
            elif [[ "$PYTHON_CMD" == "python3.10" ]] && [[ "$EXISTING_VENV_VERSION" != "3.10" ]]; then
                log_warning "Target Python is 3.10 but existing venv uses Python $EXISTING_VENV_VERSION"
                RECREATE_VENV=true
            elif [[ "$EXISTING_VENV_VERSION" == "3.9" ]] && [[ "$PYTHON_VERSION_CHECK" != "3.9" ]]; then
                log_warning "Existing venv uses Python 3.9 but we have Python $PYTHON_VERSION_CHECK available"
                RECREATE_VENV=true
            fi
        else
            log_warning "Existing venv appears corrupted, recreating..."
            RECREATE_VENV=true
        fi
    fi
    
    # Remove existing venv if we need to recreate it
    if [[ "$RECREATE_VENV" == "true" ]]; then
        log_info "Removing old virtual environment..."
        rm -rf "$VENV_DIR"
        log_info "Will recreate with Python $PYTHON_VERSION_CHECK ($PYTHON_CMD)"
    fi
    
    # Create virtual environment if it doesn't exist or was removed
    if [[ ! -d "$VENV_DIR" ]]; then
        if [[ "$INSTALL_AS_USER" == "true" ]]; then
            $PYTHON_CMD -m venv "$VENV_DIR"
        else
            sudo -u "$SERVICE_USER" $PYTHON_CMD -m venv "$VENV_DIR"
        fi
        log_success "Created virtual environment with Python $PYTHON_VERSION_CHECK"
    else
        log_info "Virtual environment already exists with correct Python version"
    fi
    
    # Upgrade pip and install requirements
    if [[ "$INSTALL_AS_USER" == "true" ]]; then
        "$VENV_DIR/bin/pip" install --upgrade pip
        log_info "Installing Python dependencies..."
        "$VENV_DIR/bin/pip" install -r "$PROJECT_DIR/requirements.txt"
    else
        sudo -u "$SERVICE_USER" "$VENV_DIR/bin/pip" install --upgrade pip
        log_info "Installing Python dependencies..."
        sudo -u "$SERVICE_USER" "$VENV_DIR/bin/pip" install -r "$PROJECT_DIR/requirements.txt"
    fi
    
    log_success "Python virtual environment setup complete"
}

# Create systemd service (optional)
create_systemd_service() {
    if [[ "$INSTALL_SYSTEMD_SERVICE" != "true" ]]; then
        log_info "Skipping systemd service creation (not requested)"
        return
    fi
    
    log_info "Creating systemd service..."
    
    cat > "/etc/systemd/system/${SERVICE_NAME}.service" << EOF
[Unit]
Description=TradeStation Community MCP Server
After=network.target
Wants=network.target

[Service]
Type=simple
User=$SERVICE_USER
Group=$SERVICE_USER
WorkingDirectory=$PROJECT_DIR
Environment=PATH=$PROJECT_DIR/venv/bin
ExecStart=$PROJECT_DIR/venv/bin/python $PROJECT_DIR/server.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal
SyslogIdentifier=$SERVICE_NAME

# Security settings
NoNewPrivileges=yes
PrivateTmp=yes
ProtectSystem=strict
ProtectHome=yes
ReadWritePaths=$PROJECT_DIR

[Install]
WantedBy=multi-user.target
EOF
    
    # Reload systemd
    systemctl daemon-reload
    
    log_success "Systemd service created"
}

# Configure firewall (if needed)
configure_firewall() {
    log_info "Checking firewall configuration..."
    
    # Check if firewall is active and configure if needed
    if command -v ufw &> /dev/null && ufw status | grep -q "Status: active"; then
        log_info "UFW firewall detected - no additional configuration needed for MCP server"
    elif command -v firewall-cmd &> /dev/null && firewall-cmd --state &> /dev/null; then
        log_info "Firewalld detected - no additional configuration needed for MCP server"
    else
        log_info "No active firewall detected or configuration needed"
    fi
}

# Start and enable service (only if systemd service was created)
start_service() {
    if [[ "$INSTALL_SYSTEMD_SERVICE" != "true" ]]; then
        log_info "No systemd service to start"
        return
    fi
    
    log_info "Starting and enabling service..."
    
    # Enable service to start on boot
    systemctl enable "$SERVICE_NAME"
    
    # Start service
    systemctl start "$SERVICE_NAME"
    
    # Wait a moment for service to start
    sleep 2
    
    # Check service status
    if systemctl is-active --quiet "$SERVICE_NAME"; then
        log_success "Service $SERVICE_NAME is running"
    else
        log_error "Service $SERVICE_NAME failed to start"
        log_info "Checking service status..."
        systemctl status "$SERVICE_NAME" --no-pager
        exit 1
    fi
}

# Display deployment information
display_info() {
    log_success "Deployment completed successfully!"
    echo
    log_info "Installation Information:"
    echo "  Installation Type: $(if [[ "$INSTALL_AS_USER" == "true" ]]; then echo "User"; else echo "System"; fi)"
    echo "  Project Directory: $PROJECT_DIR"
    echo "  Service User: $SERVICE_USER"
    echo "  Virtual Environment: $PROJECT_DIR/venv"
    echo "  Systemd Service: $(if [[ "$INSTALL_SYSTEMD_SERVICE" == "true" ]]; then echo "Installed"; else echo "Not installed"; fi)"
    echo
    
    if [[ "$INSTALL_SYSTEMD_SERVICE" == "true" ]]; then
        log_info "Systemd Service Commands:"
        echo "  Check status: sudo systemctl status $SERVICE_NAME"
        echo "  View logs: sudo journalctl -u $SERVICE_NAME -f"
        echo "  Restart: sudo systemctl restart $SERVICE_NAME"
        echo "  Stop: sudo systemctl stop $SERVICE_NAME"
        echo
        log_info "Configuration:"
        echo "  Edit credentials: $(if [[ "$INSTALL_AS_USER" == "true" ]]; then echo "nano"; else echo "sudo nano"; fi) $PROJECT_DIR/.env"
        echo "  After editing .env: sudo systemctl restart $SERVICE_NAME"
        echo
    else
        log_info "Manual Execution:"
        echo "  Run server: cd $PROJECT_DIR && ./venv/bin/python server.py"
        echo "  Edit credentials: $(if [[ "$INSTALL_AS_USER" == "true" ]]; then echo "nano"; else echo "sudo nano"; fi) $PROJECT_DIR/.env"
        echo
        log_info "To install as systemd service later:"
        echo "  Run: $(if [[ "$INSTALL_AS_USER" == "false" ]]; then echo "sudo "; fi)$0 --systemd"
        echo
    fi
    
    log_warning "IMPORTANT: Update $PROJECT_DIR/.env with your TradeStation credentials!"
    log_info "Check $PROJECT_DIR/.env.example for the latest configuration template"
}

# Cleanup function for failed deployments
cleanup_on_error() {
    log_error "Deployment failed. Cleaning up..."
    
    # Stop service if it exists
    if systemctl list-unit-files | grep -q "$SERVICE_NAME"; then
        systemctl stop "$SERVICE_NAME" 2>/dev/null || true
        systemctl disable "$SERVICE_NAME" 2>/dev/null || true
    fi
    
    # Remove service file
    rm -f "/etc/systemd/system/${SERVICE_NAME}.service"
    systemctl daemon-reload
    
    log_info "Cleanup completed"
}

# Main deployment function
main() {
    log_info "Starting TradeStation Community MCP Server deployment..."
    
    # Set up error handling
    trap cleanup_on_error ERR
    
    parse_arguments "$@"
    check_root
    detect_os
    install_system_deps
    check_python_version
    create_service_user
    setup_project_directory
    copy_application_files
    setup_venv
    create_systemd_service
    configure_firewall
    start_service
    display_info
    
    log_success "All deployment steps completed successfully!"
}

# Run main function
main "$@"
