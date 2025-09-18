# TradeStation Community MCP Server

An MCP (Model Context Protocol) server that provides Cursor with access to search and browse the TradeStation Community forum.

## Features

- **Authentication**: Login using your TradeStation username and password
- **Search**: Search the entire message board for threads and posts
- **Thread Retrieval**: Get full content of specific threads
- **No API Key Required**: Uses standard web authentication

## Setup

### Local Development

1. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure Credentials (Optional)**
   ```bash
   cp env.example .env
   # Edit .env with your TradeStation credentials
   ```

3. **Run the Server**
   ```bash
   python server.py
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

## Usage in Cursor

Once the MCP server is running, you can use these tools in Cursor:

### 1. Login
```
Use the login tool with your TradeStation username and password
```

### 2. Search Forum
```
Search for specific topics, e.g.:
- "API authentication issues"
- "order execution problems"
- "platform connectivity"
```

### 3. Get Thread Content
```
Retrieve full content of specific threads using their URLs
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
