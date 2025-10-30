#!/bin/bash
# Wrapper script to start the MCP server
# This ensures the correct paths are used on the EC2 instance

cd /data/tradestation-community-mcp || exit 1

# Log to a file for debugging
{
  echo "$(date): Starting MCP server"
  echo "Working directory: $(pwd)"
  echo "Python: $(./venv/bin/python --version 2>&1)"
  echo "Files present:"
  ls -la server.py tradestation_client.py .session_cookies.json 2>&1
  echo "Starting server..."
} >> /tmp/mcp-server-debug.log 2>&1

# Use -u for unbuffered output (important for stdio communication)
exec ./venv/bin/python -u server.py 2>> /tmp/mcp-server-debug.log
