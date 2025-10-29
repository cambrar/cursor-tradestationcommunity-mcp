#!/bin/bash

# Test script to verify MCP server responds correctly
# This simulates what Cursor does when connecting to the MCP server

echo "Testing MCP server connection..."
echo

# Send an initialize request to the MCP server via SSH
echo '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"test-client","version":"1.0.0"}}}' | \
  ssh mcp-server@44.243.252.128 "cd /data/tradestation-community-mcp && ./venv/bin/python server.py"

echo
echo "If you see a JSON response above with 'capabilities' and 'tools', the server is working!"
echo "If you see errors, that's what we need to fix."


