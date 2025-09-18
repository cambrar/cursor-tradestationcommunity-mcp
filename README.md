# TradeStation Community MCP Server

An MCP (Model Context Protocol) server that provides Cursor with access to search and browse the TradeStation Community forum.

## Features

- **Authentication**: Login using your TradeStation username and password
- **Search**: Search the entire message board for threads and posts
- **Thread Retrieval**: Get full content of specific threads
- **No API Key Required**: Uses standard web authentication

## Setup

### Local Development

1. **Create Virtual Environment**
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure Credentials (Optional)**
   ```bash
   cp env.example .env
   # Edit .env with your TradeStation credentials
   ```

4. **Run the Server**
   ```bash
   python server.py
   ```

5. **Deactivate Virtual Environment** (when done)
   ```bash
   deactivate
   ```

### Production Deployment (EC2/Linux)

#### Basic Installation (No systemd service)
```bash
# Copy files to your server
scp -r . user@your-server:/tmp/tradestation-mcp/

# SSH to server and run deployment
ssh user@your-server
cd /tmp/tradestation-mcp
sudo ./deploy.sh
```

#### With Systemd Service (Recommended for servers)
```bash
# Deploy with systemd service
sudo ./deploy.sh --systemd
```

#### User Installation (No root required)
```bash
# Install for current user only
./deploy.sh --user

# Or install to custom directory
./deploy.sh --user ~/my-mcp-server
```

#### Configuration
```bash
# For system install
sudo nano /opt/tradestation-community-mcp/.env

# For user install  
nano ~/.local/share/tradestation-community-mcp/.env

# Restart service (if using systemd)
sudo systemctl restart tradestation-community-mcp
```

#### Service Management (systemd only)
```bash
# Check status
sudo systemctl status tradestation-community-mcp

# View logs
sudo journalctl -u tradestation-community-mcp -f

# Restart service
sudo systemctl restart tradestation-community-mcp
```

#### Manual Execution (non-systemd)
```bash
# Run manually
cd /opt/tradestation-community-mcp  # or your install directory
./venv/bin/python server.py
```

## Cursor Integration

### Configure MCP Server in Cursor

1. **Create MCP Configuration File**
   
   Cursor uses a configuration file called `mcp.json`. Create it in one of these locations:
   
   **Global (all projects):**
   ```bash
   mkdir -p ~/.cursor
   nano ~/.cursor/mcp.json
   ```
   
   **Project-specific (current project only):**
   ```bash
   nano .cursor/mcp.json
   ```

2. **Add Server Configuration**

   **For Local Development:**
   ```json
   {
     "mcpServers": {
       "tradestation-community": {
         "command": "python3",
         "args": ["server.py"],
         "cwd": "/path/to/your/cursor-tradestationcommunity-mcp",
         "env": {
           "PYTHONPATH": "/path/to/your/cursor-tradestationcommunity-mcp/venv/lib/python3.9/site-packages"
         }
       }
     }
   }
   ```

   **For EC2 Server (SSH Connection):**
   ```json
   {
     "mcpServers": {
       "tradestation-community": {
         "command": "ssh",
         "args": [
           "-i", "/path/to/your-key.pem",
           "ec2-user@your-ec2-ip",
           "cd /opt/tradestation-community-mcp && ./venv/bin/python server.py"
         ]
       }
     }
   }
   ```

3. **Important Notes about EC2 Connection**
   
   ⚠️ **Cursor connects TO your EC2 instance via SSH** - it doesn't expose any ports. Your EC2 needs:
   
   - **SSH access** from your development machine (port 22)
   - **Outbound internet** access to TradeStation (ports 443, 80, 53)
   - **NO inbound ports** needed for the MCP server itself
   
   The MCP server runs on EC2, and Cursor connects to it via SSH to execute commands.

4. **Quick Setup Commands**
   
   **Copy and customize the provided config:**
   ```bash
   # Global configuration
   mkdir -p ~/.cursor
   cp mcp.json ~/.cursor/mcp.json
   nano ~/.cursor/mcp.json  # Edit with your paths/IPs
   
   # Project-specific configuration
   cp mcp.json .cursor/mcp.json
   nano .cursor/mcp.json    # Edit with your paths/IPs
   ```

5. **Restart Cursor** 
   
   After creating/editing the `mcp.json` file, restart Cursor to load the configuration.

6. **Verify Connection**
   
   - Open Cursor
   - Look for MCP server status in the status bar or MCP panel
   - Try using the TradeStation Community tools in a chat

### Step-by-Step Example

Here's a complete example for connecting Cursor to an EC2 instance:

1. **Your EC2 setup:**
   - Instance IP: `203.0.113.100`
   - SSH Key: `~/aws-keys/my-ec2-key.pem`
   - User: `ec2-user` (Amazon Linux)

2. **Create the MCP config:**
   ```bash
   mkdir -p ~/.cursor
   cat > ~/.cursor/mcp.json << 'EOF'
   {
     "mcpServers": {
       "tradestation-community": {
         "command": "ssh",
         "args": [
           "-i", "/Users/yourname/aws-keys/my-ec2-key.pem",
           "ec2-user@203.0.113.100",
           "cd /opt/tradestation-community-mcp && ./venv/bin/python server.py"
         ]
       }
     }
   }
   EOF
   ```

3. **Test the SSH connection first:**
   ```bash
   ssh -i ~/aws-keys/my-ec2-key.pem ec2-user@203.0.113.100 "cd /opt/tradestation-community-mcp && ./venv/bin/python server.py --help"
   ```

4. **Restart Cursor and test:**
   - Restart Cursor
   - Open a chat
   - Try asking: "Login to TradeStation Community with my credentials"

### EC2 Network & Security Configuration

#### Security Group Configuration

**Inbound Rules (Required for Cursor SSH connection):**
```
- Type: SSH
  Protocol: TCP
  Port: 22
  Source: YOUR_LOCAL_IP/32
  Description: SSH access from your development machine
```

**Outbound Rules (Required for TradeStation access):**
```
- Type: HTTPS
  Protocol: TCP  
  Port: 443
  Destination: 0.0.0.0/0
  Description: TradeStation Community HTTPS

- Type: HTTP  
  Protocol: TCP
  Port: 80
  Destination: 0.0.0.0/0
  Description: HTTP redirect handling

- Type: DNS (UDP)
  Protocol: UDP
  Port: 53  
  Destination: 0.0.0.0/0
  Description: DNS resolution
```

**Important:** The MCP server itself doesn't need any inbound ports - Cursor connects via SSH and runs the server remotely.

#### Network ACL (if using custom VPC)
Ensure your subnet's Network ACL allows:
- **Outbound**: HTTPS (443), HTTP (80), DNS (53)
- **Inbound**: SSH (22) from your IP
- **Inbound**: Ephemeral ports (32768-65535) for return traffic

#### VPC Configuration
- **Internet Gateway**: Required for outbound HTTPS to TradeStation
- **Route Table**: Default route (0.0.0.0/0) to Internet Gateway
- **DNS Resolution**: Enabled on VPC
- **DNS Hostnames**: Enabled on VPC

### Usage in Cursor

Once the MCP server is configured and running:

#### 1. Login
```
Use the login tool with your TradeStation username and password
```

#### 2. Search Forum
```
Search for specific topics, e.g.:
- "API authentication issues"
- "order execution problems"
- "platform connectivity"
```

#### 3. Get Thread Content
```
Retrieve full content of specific threads using their URLs
```

### Troubleshooting Connection

#### Local Development Issues
```bash
# Check if server starts locally
cd /path/to/cursor-tradestationcommunity-mcp
source venv/bin/activate
python server.py

# Check MCP server logs in Cursor
# Look for connection errors in Cursor's MCP panel
```

#### EC2 Connection Issues
```bash
# Test SSH connection
ssh your-ec2-user@your-ec2-ip

# Check if MCP server is running
sudo systemctl status tradestation-community-mcp

# Test outbound connectivity from EC2
curl -I https://community.tradestation.com

# Check security group rules
aws ec2 describe-security-groups --group-ids sg-your-group-id
```

## Tools Available

### `login`
- **Description**: Login to TradeStation Community forum
- **Parameters**:
  - `username` (required): Your TradeStation username
  - `password` (required): Your TradeStation password

### `search_forum`
- **Description**: Search the forum for threads and posts
- **Parameters**:
  - `query` (required): Search terms
  - `limit` (optional): Maximum results to return (default: 10)

### `get_thread`
- **Description**: Get full content of a specific thread
- **Parameters**:
  - `thread_url` (required): URL of the thread to retrieve

## Configuration

### Environment Variables (.env)
The `.env` file is never overwritten during updates. Always check `.env.example` for new options.

```bash
# Required: Your TradeStation credentials
TRADESTATION_USERNAME=your_username
TRADESTATION_PASSWORD=your_password

# Optional: Additional configuration
DEBUG=false
TIMEOUT=30
RATE_LIMIT_DELAY=1
```

**Important:** 
- Existing `.env` files are preserved during updates
- New configuration options appear in `.env.example`
- Copy `.env.example` to `.env` for initial setup

### Auto-Login
If you provide credentials in the `.env` file, the server will automatically attempt to log in when it starts.

## Security Notes

- Credentials are only stored in memory during the session
- The server uses HTTPS for all communications
- Session cookies are handled automatically
- No credentials are logged or persisted

## Troubleshooting

### Login Issues
- Verify your credentials are correct
- Check if 2FA is enabled on your account (may require additional handling)
- Ensure you can log in manually via the website

### Search Issues
- Make sure you're logged in first
- Try different search terms
- The forum structure may change, affecting search functionality

### Connection Issues
- Check your internet connection
- Verify the TradeStation Community site is accessible
- The server may need updates if the site structure changes

## Technical Details

- Built with Python using the `mcp` library
- Web scraping with `requests` and `BeautifulSoup`
- Handles session management and authentication cookies
- Parses HTML to extract forum content

## Limitations

- Web scraping depends on the current HTML structure of the forum
- Rate limiting may apply (built-in delays to be respectful)
- Some content may require specific permissions
- 2FA support is limited

## Deployment Scripts

### `deploy.sh` - Initial Deployment
Idempotent deployment script with flexible options:

**Options:**
- `--systemd` or `--service`: Install as systemd service (requires root)
- `--user [DIR]`: Install for current user (optional custom directory)
- `--help`: Show help message

**Features:**
- Detects OS (Amazon Linux 2023 or Ubuntu)
- Installs system dependencies
- Sets up Python virtual environment
- Optional systemd service creation
- Secure credential handling

**Examples:**
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

### `update.sh` - Update Deployment
Updates existing deployment with new code:
- Creates backup of current version
- Updates application files and dependencies
- Restarts service
- Offers rollback if update fails

```bash
sudo ./update.sh

# Manual rollback if needed
sudo ./update.sh rollback
```

### `undeploy.sh` - Complete Removal
Safely removes the entire deployment:
- Stops and disables service
- Removes all files and directories
- Removes service user
- Cleans up system

```bash
sudo ./undeploy.sh
```

## Production Architecture

- **Service Name**: `tradestation-community-mcp`
- **Installation Path**: `/opt/tradestation-community-mcp/`
- **Service User**: `mcp-server` (non-privileged)
- **Virtual Environment**: `/opt/tradestation-community-mcp/venv/`
- **Configuration**: `/opt/tradestation-community-mcp/.env`
- **Logs**: `journalctl -u tradestation-community-mcp`

## Contributing

This server may need updates if TradeStation changes their forum structure. Feel free to submit issues or pull requests for improvements.
