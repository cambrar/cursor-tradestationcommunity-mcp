#!/bin/bash
# Wrapper script to start the MCP server
# This ensures the correct paths are used on the EC2 instance

cd /data/tradestation-community-mcp
# Use -u for unbuffered output (important for stdio communication)
exec ./venv/bin/python -u server.py
