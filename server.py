#!/usr/bin/env python3
"""
TradeStation Community MCP Server

An MCP server that provides access to TradeStation's community forum
for searching threads, posts, and messages.
"""

import asyncio
import json
import logging
import os
import re
from typing import Any, Dict, List, Optional, Sequence
from urllib.parse import urljoin, urlparse, parse_qs

from dotenv import load_dotenv
from mcp.server import Server
from mcp.server.models import InitializationOptions
from mcp.server.stdio import stdio_server
from mcp.types import (
    Resource,
    Tool,
    TextContent,
    ImageContent,
    EmbeddedResource,
    ServerCapabilities,
    ToolsCapability,
)

# Import our custom client
from tradestation_client import TradeStationCommunityClient

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize the client
client = TradeStationCommunityClient()

# Create the MCP server
server = Server("tradestation-community")

@server.list_tools()
async def handle_list_tools() -> List[Tool]:
    """List available tools"""
    return [
        Tool(
            name="login",
            description="Login to TradeStation Community forum",
            inputSchema={
                "type": "object",
                "properties": {
                    "username": {
                        "type": "string",
                        "description": "TradeStation username"
                    },
                    "password": {
                        "type": "string",
                        "description": "TradeStation password"
                    }
                },
                "required": ["username", "password"]
            }
        ),
        Tool(
            name="search_forum",
            description="Search the TradeStation Community forum for threads and posts",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query to find relevant posts and threads"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of results to return (default: 10)",
                        "default": 10
                    }
                },
                "required": ["query"]
            }
        ),
        Tool(
            name="get_thread",
            description="Get full content of a specific thread",
            inputSchema={
                "type": "object",
                "properties": {
                    "thread_url": {
                        "type": "string",
                        "description": "URL of the thread to retrieve"
                    }
                },
                "required": ["thread_url"]
            }
        )
    ]

@server.call_tool()
async def handle_call_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
    """Handle tool calls"""
    
    if name == "login":
        username = arguments.get("username")
        password = arguments.get("password")
        
        if not username or not password:
            return [TextContent(
                type="text",
                text="Error: Username and password are required"
            )]
        
        success = await client.login(username, password)
        
        if success:
            return [TextContent(
                type="text",
                text="Successfully logged in to TradeStation Community forum"
            )]
        else:
            return [TextContent(
                type="text",
                text="Failed to log in. Please check your credentials."
            )]
    
    elif name == "search_forum":
        if not client.logged_in:
            return [TextContent(
                type="text",
                text="Error: Please login first using the login tool"
            )]
        
        query = arguments.get("query")
        limit = arguments.get("limit", 10)
        
        if not query:
            return [TextContent(
                type="text",
                text="Error: Search query is required"
            )]
        
        results = client.search_forum(query, limit)
        
        if not results:
            return [TextContent(
                type="text",
                text=f"No results found for query: {query}"
            )]
        
        # Format results
        formatted_results = []
        formatted_results.append(f"Found {len(results)} results for '{query}':\n")
        
        for i, result in enumerate(results, 1):
            formatted_results.append(f"{i}. **{result['title']}**")
            if result['author']:
                formatted_results.append(f"   Author: {result['author']}")
            if result['date']:
                formatted_results.append(f"   Date: {result['date']}")
            if result['content']:
                formatted_results.append(f"   Preview: {result['content']}")
            if result['url']:
                formatted_results.append(f"   URL: {result['url']}")
            formatted_results.append("")
        
        return [TextContent(
            type="text",
            text="\n".join(formatted_results)
        )]
    
    elif name == "get_thread":
        if not client.logged_in:
            return [TextContent(
                type="text",
                text="Error: Please login first using the login tool"
            )]
        
        thread_url = arguments.get("thread_url")
        
        if not thread_url:
            return [TextContent(
                type="text",
                text="Error: Thread URL is required"
            )]
        
        thread_data = client.get_thread_content(thread_url)
        
        if not thread_data:
            return [TextContent(
                type="text",
                text=f"Failed to retrieve thread content from: {thread_url}"
            )]
        
        # Format thread content
        formatted_content = []
        formatted_content.append(f"# {thread_data.get('title', 'Thread')}\n")
        formatted_content.append(f"URL: {thread_data.get('url', thread_url)}")
        formatted_content.append(f"Posts: {thread_data.get('post_count', 0)}\n")
        
        posts = thread_data.get('posts', [])
        for i, post in enumerate(posts, 1):
            formatted_content.append(f"## Post {i}")
            if post.get('author'):
                formatted_content.append(f"**Author:** {post['author']}")
            if post.get('date'):
                formatted_content.append(f"**Date:** {post['date']}")
            if post.get('content'):
                formatted_content.append(f"**Content:** {post['content']}")
            formatted_content.append("")
        
        return [TextContent(
            type="text",
            text="\n".join(formatted_content)
        )]
    
    else:
        return [TextContent(
            type="text",
            text=f"Unknown tool: {name}"
        )]

async def main():
    """Main entry point"""
    # Get credentials from environment variables if available
    username = os.getenv('TRADESTATION_USERNAME')
    password = os.getenv('TRADESTATION_PASSWORD')
    
    # Check if already authenticated via saved cookies
    if client.logged_in:
        logger.info("Already authenticated via saved cookies")
    elif username and password:
        logger.info("Attempting Playwright-based login with provided credentials...")
        logger.warning("Note: This requires solving CAPTCHA - consider using save-cookies.py instead")
        success = await client.login(username, password)
        if success:
            logger.info("Auto-login successful")
        else:
            logger.warning("Auto-login failed - use save-cookies.py to manually authenticate")
    else:
        logger.warning("No authentication available - provide credentials in .env or run save-cookies.py")
    
    # Run the server
    async with stdio_server() as (read_stream, write_stream):
        # Create server capabilities
        capabilities = ServerCapabilities(
            tools=ToolsCapability(),
        )
        
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="tradestation-community",
                server_version="1.0.0",
                capabilities=capabilities,
            ),
        )

if __name__ == "__main__":
    asyncio.run(main())
