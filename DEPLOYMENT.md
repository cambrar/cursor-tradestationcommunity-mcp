# Deployment Guide

This guide covers deploying the TradeStation Community MCP Server to production environments.

## Quick Start

### Basic Installation (No systemd service)
```bash
# Copy files to server
scp -r . user@your-server:/tmp/tradestation-mcp/

# Deploy
ssh user@your-server
cd /tmp/tradestation-mcp
sudo ./deploy.sh

# Configure and run manually
sudo nano /opt/tradestation-community-mcp/.env
cd /opt/tradestation-community-mcp
sudo -u mcp-server ./venv/bin/python server.py
```

### With Systemd Service (Recommended)
```bash
# Deploy with service
sudo ./deploy.sh --systemd

# Configure credentials
sudo nano /opt/tradestation-community-mcp/.env
sudo systemctl restart tradestation-community-mcp
```

### User Installation (No root required)
```bash
# Install for current user
./deploy.sh --user

# Configure credentials
nano ~/.local/share/tradestation-community-mcp/.env

# Run manually
cd ~/.local/share/tradestation-community-mcp
./venv/bin/python server.py
```

## Supported Operating Systems

- **Amazon Linux 2023** (recommended for AWS EC2)
- **Ubuntu 20.04+** (LTS versions recommended)

The deployment script automatically detects your OS and installs appropriate packages.

## System Requirements

### Minimum Requirements
- **CPU**: 1 vCPU
- **RAM**: 512 MB
- **Storage**: 1 GB free space
- **Network**: Internet access to TradeStation Community

### Recommended for Production
- **CPU**: 2+ vCPUs
- **RAM**: 1 GB+
- **Storage**: 2 GB+ free space

## Deployment Scripts

### `deploy.sh` - Initial Deployment

**Features:**
- **Idempotent**: Safe to run multiple times
- **OS Detection**: Automatically handles Amazon Linux 2023 and Ubuntu
- **Flexible Installation**: System, user, or service modes
- **Security**: Dedicated service user with minimal privileges
- **Virtual Environment**: Isolated Python environment
- **Optional Systemd**: Service creation is optional

**Installation Options:**
- `--systemd` or `--service`: Install as systemd service (requires root)
- `--user [DIR]`: Install for current user (optional custom directory)
- `--help`: Show help message

**What it does:**
1. Installs system dependencies (python3, pip, venv, git)
2. Creates service user (system install only)
3. Sets up project directory
4. Creates Python virtual environment
5. Installs Python dependencies
6. Optionally creates systemd service
7. Preserves existing .env files

**Usage:**
```bash
# Basic installation (no service)
sudo ./deploy.sh

# With systemd service  
sudo ./deploy.sh --systemd

# User installation
./deploy.sh --user

# Custom user directory
./deploy.sh --user ~/my-mcp-server
```

### `update.sh` - Update Existing Deployment

**Features:**
- **Backup**: Creates timestamped backup before update
- **Rollback**: Automatic rollback if update fails
- **Zero Downtime**: Minimizes service interruption
- **Dependency Updates**: Updates Python packages

**Usage:**
```bash
# Update to latest version
sudo ./update.sh

# Manual rollback if needed
sudo ./update.sh rollback
```

### `undeploy.sh` - Complete Removal

**Features:**
- **Safe Removal**: Confirms before deletion
- **Complete Cleanup**: Removes all traces
- **Process Cleanup**: Kills any running processes

**Usage:**
```bash
sudo ./undeploy.sh
```

## Production Architecture

### Directory Structure
```
/opt/tradestation-community-mcp/
├── server.py              # Main MCP server
├── requirements.txt       # Python dependencies
├── .env                   # Configuration (credentials)
├── README.md             # Documentation
└── venv/                 # Python virtual environment
    ├── bin/
    ├── lib/
    └── ...
```

### Service Configuration
- **Service Name**: `tradestation-community-mcp`
- **Service User**: `mcp-server` (non-privileged)
- **Working Directory**: `/opt/tradestation-community-mcp/`
- **Service File**: `/etc/systemd/system/tradestation-community-mcp.service`

### Security Features
- **Dedicated User**: Service runs as `mcp-server` user
- **No Root Access**: Service cannot escalate privileges
- **Read-only System**: Protected system directories
- **Private Temp**: Isolated temporary directory

## Configuration

### Environment Variables (.env)
The `.env` file is never overwritten during deployments or updates. Always check `.env.example` for new configuration options.

```bash
# Required: Your TradeStation credentials
TRADESTATION_USERNAME=your_username
TRADESTATION_PASSWORD=your_password

# Optional: Additional configuration
DEBUG=false
TIMEOUT=30
RATE_LIMIT_DELAY=1
```

**Important Notes:**
- Existing `.env` files are preserved during updates
- New configuration options appear in `.env.example`
- Copy `.env.example` to `.env` for initial setup
- File permissions are automatically secured (600)

### Service Management
```bash
# Check service status
sudo systemctl status tradestation-community-mcp

# Start service
sudo systemctl start tradestation-community-mcp

# Stop service
sudo systemctl stop tradestation-community-mcp

# Restart service
sudo systemctl restart tradestation-community-mcp

# Enable auto-start on boot
sudo systemctl enable tradestation-community-mcp

# Disable auto-start
sudo systemctl disable tradestation-community-mcp
```

### Viewing Logs
```bash
# View recent logs
sudo journalctl -u tradestation-community-mcp

# Follow logs in real-time
sudo journalctl -u tradestation-community-mcp -f

# View logs from last hour
sudo journalctl -u tradestation-community-mcp --since "1 hour ago"

# View logs with timestamps
sudo journalctl -u tradestation-community-mcp -o short-iso
```

## Troubleshooting

### Service Won't Start
1. **Check service status:**
   ```bash
   sudo systemctl status tradestation-community-mcp
   ```

2. **Check logs:**
   ```bash
   sudo journalctl -u tradestation-community-mcp -n 50
   ```

3. **Common issues:**
   - Missing credentials in `.env` file
   - Python dependency conflicts
   - Network connectivity issues

### Login Failures
1. **Verify credentials:**
   ```bash
   sudo cat /opt/tradestation-community-mcp/.env
   ```

2. **Test manual login:**
   - Try logging in manually at https://community.tradestation.com/
   - Check if 2FA is enabled on your account

3. **Check TradeStation site status:**
   - Verify the community site is accessible
   - Check for maintenance windows

### Performance Issues
1. **Check system resources:**
   ```bash
   htop
   df -h
   free -h
   ```

2. **Monitor service:**
   ```bash
   sudo systemctl status tradestation-community-mcp
   sudo journalctl -u tradestation-community-mcp -f
   ```

### Update Issues
1. **Check backup:**
   ```bash
   ls -la /opt/tradestation-community-mcp_backup_*
   ```

2. **Manual rollback:**
   ```bash
   sudo ./update.sh rollback
   ```

3. **Clean reinstall:**
   ```bash
   sudo ./undeploy.sh
   sudo ./deploy.sh
   ```

## Monitoring

### Health Checks
```bash
# Service status
systemctl is-active tradestation-community-mcp

# Service uptime
systemctl show tradestation-community-mcp --property=ActiveEnterTimestamp

# Process information
ps aux | grep tradestation-community-mcp
```

### Log Monitoring
Set up log monitoring to alert on:
- Service failures
- Authentication errors
- Connection timeouts
- Rate limiting issues

### Resource Monitoring
Monitor:
- CPU usage
- Memory usage
- Disk space
- Network connectivity

## Security Considerations

### Network Security
- **Firewall**: No inbound ports needed (MCP server connects outbound only)
- **HTTPS**: All communications use HTTPS
- **Rate Limiting**: Built-in delays to respect TradeStation's servers

### Credential Security
- **File Permissions**: `.env` file is readable only by service user
- **No Logging**: Credentials are never logged
- **Memory Only**: Credentials stored only in memory during runtime

### System Security
- **Non-root User**: Service runs as dedicated system user
- **Minimal Privileges**: Service user has minimal system access
- **Isolated Environment**: Python virtual environment isolation

## Backup and Recovery

### Backup Strategy
The `update.sh` script automatically creates backups:
- Timestamped backups in `/opt/tradestation-community-mcp_backup_*`
- Keeps 3 most recent backups
- Automatic cleanup of old backups

### Manual Backup
```bash
# Create manual backup
sudo cp -r /opt/tradestation-community-mcp /opt/tradestation-community-mcp_manual_backup_$(date +%Y%m%d_%H%M%S)
```

### Recovery
```bash
# Restore from backup
sudo systemctl stop tradestation-community-mcp
sudo rm -rf /opt/tradestation-community-mcp
sudo mv /opt/tradestation-community-mcp_backup_YYYYMMDD_HHMMSS /opt/tradestation-community-mcp
sudo systemctl start tradestation-community-mcp
```

## Performance Tuning

### Python Optimization
- Uses virtual environment for dependency isolation
- Automatic dependency caching
- Memory-efficient HTML parsing

### Network Optimization
- Connection pooling with requests session
- Automatic retry logic
- Respectful rate limiting

### System Optimization
- Systemd service with automatic restart
- Resource limits via systemd
- Log rotation via journald

## Maintenance

### Regular Tasks
1. **Monitor logs** for errors or warnings
2. **Check service status** periodically
3. **Update dependencies** when needed
4. **Clean old backups** (automatic with update script)

### Updates
```bash
# Update to latest version
sudo ./update.sh

# Check for Python security updates
sudo /opt/tradestation-community-mcp/venv/bin/pip list --outdated
```

### Maintenance Windows
Schedule updates during low-usage periods:
1. Stop service
2. Update code/dependencies  
3. Test functionality
4. Start service
5. Monitor for issues
