#!/bin/bash

# EC2 Security Group Setup Script for TradeStation Community MCP Server
# This script helps configure the necessary security group rules

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

show_help() {
    echo "EC2 Security Group Setup for TradeStation Community MCP Server"
    echo
    echo "Usage: $0 [OPTIONS]"
    echo
    echo "Options:"
    echo "  --security-group-id SG_ID    Existing security group ID to modify"
    echo "  --create-new                 Create a new security group"
    echo "  --vpc-id VPC_ID             VPC ID (required for new security group)"
    echo "  --your-ip IP                Your public IP address"
    echo "  --help                      Show this help message"
    echo
    echo "Examples:"
    echo "  $0 --security-group-id sg-1234567890abcdef0 --your-ip 203.0.113.1"
    echo "  $0 --create-new --vpc-id vpc-1234567890abcdef0 --your-ip 203.0.113.1"
}

# Parse command line arguments
SECURITY_GROUP_ID=""
CREATE_NEW=false
VPC_ID=""
YOUR_IP=""

while [[ $# -gt 0 ]]; do
    case $1 in
        --security-group-id)
            SECURITY_GROUP_ID="$2"
            shift 2
            ;;
        --create-new)
            CREATE_NEW=true
            shift
            ;;
        --vpc-id)
            VPC_ID="$2"
            shift 2
            ;;
        --your-ip)
            YOUR_IP="$2"
            shift 2
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

# Check if AWS CLI is installed
if ! command -v aws &> /dev/null; then
    log_error "AWS CLI is not installed. Please install it first:"
    echo "  https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html"
    exit 1
fi

# Check AWS credentials
if ! aws sts get-caller-identity &> /dev/null; then
    log_error "AWS credentials not configured. Run 'aws configure' first."
    exit 1
fi

# Get your public IP if not provided
if [[ -z "$YOUR_IP" ]]; then
    log_info "Detecting your public IP address..."
    YOUR_IP=$(curl -s https://checkip.amazonaws.com || curl -s https://ipinfo.io/ip || echo "")
    if [[ -z "$YOUR_IP" ]]; then
        log_error "Could not detect your public IP. Please provide it with --your-ip"
        exit 1
    fi
    log_info "Detected IP: $YOUR_IP"
fi

# Create new security group if requested
if [[ "$CREATE_NEW" == "true" ]]; then
    if [[ -z "$VPC_ID" ]]; then
        log_error "VPC ID is required when creating a new security group"
        exit 1
    fi
    
    log_info "Creating new security group..."
    SECURITY_GROUP_ID=$(aws ec2 create-security-group \
        --group-name "tradestation-mcp-server" \
        --description "Security group for TradeStation Community MCP Server" \
        --vpc-id "$VPC_ID" \
        --query 'GroupId' \
        --output text)
    
    log_success "Created security group: $SECURITY_GROUP_ID"
fi

# Validate security group ID
if [[ -z "$SECURITY_GROUP_ID" ]]; then
    log_error "Security group ID is required. Use --security-group-id or --create-new"
    exit 1
fi

log_info "Configuring security group: $SECURITY_GROUP_ID"

# Add SSH inbound rule
log_info "Adding SSH inbound rule for your IP ($YOUR_IP)..."
aws ec2 authorize-security-group-ingress \
    --group-id "$SECURITY_GROUP_ID" \
    --protocol tcp \
    --port 22 \
    --cidr "${YOUR_IP}/32" \
    --rule-description "SSH access from development machine" \
    2>/dev/null || log_warning "SSH rule may already exist"

# Add HTTPS outbound rule
log_info "Adding HTTPS outbound rule..."
aws ec2 authorize-security-group-egress \
    --group-id "$SECURITY_GROUP_ID" \
    --protocol tcp \
    --port 443 \
    --cidr 0.0.0.0/0 \
    --rule-description "HTTPS to TradeStation Community" \
    2>/dev/null || log_warning "HTTPS rule may already exist"

# Add HTTP outbound rule
log_info "Adding HTTP outbound rule..."
aws ec2 authorize-security-group-egress \
    --group-id "$SECURITY_GROUP_ID" \
    --protocol tcp \
    --port 80 \
    --cidr 0.0.0.0/0 \
    --rule-description "HTTP redirects" \
    2>/dev/null || log_warning "HTTP rule may already exist"

# Add DNS outbound rule
log_info "Adding DNS outbound rule..."
aws ec2 authorize-security-group-egress \
    --group-id "$SECURITY_GROUP_ID" \
    --protocol udp \
    --port 53 \
    --cidr 0.0.0.0/0 \
    --rule-description "DNS resolution" \
    2>/dev/null || log_warning "DNS rule may already exist"

log_success "Security group configuration completed!"
echo
log_info "Security Group ID: $SECURITY_GROUP_ID"
log_info "Your IP: $YOUR_IP"
echo
log_info "Next steps:"
echo "1. Launch EC2 instance with this security group"
echo "2. Clone the repository: git clone https://github.com/cambrar/cursor-tradestationcommunity-mcp.git"
echo "3. Run deployment: sudo ./deploy.sh --systemd"
echo "4. Configure credentials in .env file"
echo "5. Configure Cursor MCP settings"
echo
log_info "Example Cursor MCP configuration:"
echo '{
  "mcpServers": {
    "tradestation-community": {
      "command": "ssh",
      "args": [
        "-i", "/path/to/your-key.pem",
        "ec2-user@YOUR_EC2_IP",
        "cd /data/tradestation-community-mcp && ./venv/bin/python server.py"
      ]
    }
  }
}'
