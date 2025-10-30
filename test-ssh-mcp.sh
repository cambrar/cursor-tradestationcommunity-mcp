#!/bin/bash
# Test script to diagnose SSH MCP connection issues

echo "Testing SSH connection to MCP server..."
echo

# Test 1: Basic SSH connection
echo "Test 1: Basic SSH connectivity"
ssh -T mcp-server@35.89.95.164 "echo 'SSH connection works'"
echo

# Test 2: Check if files exist
echo "Test 2: Check if MCP files exist"
ssh -T mcp-server@35.89.95.164 "ls -la /data/tradestation-community-mcp/start-mcp.sh /data/tradestation-community-mcp/server.py /data/tradestation-community-mcp/tradestation_client.py 2>&1"
echo

# Test 3: Check Python
echo "Test 3: Check Python in venv"
ssh -T mcp-server@35.89.95.164 "cd /data/tradestation-community-mcp && ./venv/bin/python --version 2>&1"
echo

# Test 4: Try to import the module
echo "Test 4: Try to import tradestation_client"
ssh -T mcp-server@35.89.95.164 "cd /data/tradestation-community-mcp && ./venv/bin/python -c 'from tradestation_client import TradeStationCommunityClient; print(\"Import successful\")' 2>&1"
echo

# Test 5: Run the start script directly
echo "Test 5: Run start-mcp.sh directly"
ssh -T mcp-server@35.89.95.164 "/data/tradestation-community-mcp/start-mcp.sh" <<< ""
echo

echo "Tests complete. Check output above for errors."
