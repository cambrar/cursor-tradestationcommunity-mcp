#!/bin/bash
# Wrapper script to start the MCP server
# This ensures the correct paths are used on the EC2 instance

cd /data/tradestation-community-mcp
exec ./venv/bin/python server.py
