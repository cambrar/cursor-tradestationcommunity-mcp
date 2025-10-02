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

import requests
from bs4 import BeautifulSoup
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

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TradeStationCommunityClient:
    """Client for interacting with TradeStation Community forum"""
    
    def __init__(self):
        self.session = requests.Session()
        self.base_url = "https://community.tradestation.com"
        self.logged_in = False
        
        # Set headers to mimic a real browser
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
        })
    
    def login(self, username: str, password: str) -> bool:
        """Login to TradeStation Community"""
        try:
            # First, get the login page to extract any necessary tokens/forms
            login_url = f"{self.base_url}/login"
            response = self.session.get(login_url)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Look for login form
            login_form = soup.find('form')
            if not login_form:
                logger.error("Could not find login form")
                return False
            
            # Extract form action and method
            form_action = login_form.get('action', '/login')
            form_method = login_form.get('method', 'post').lower()
            
            # Build form data
            form_data = {}
            
            # Add all hidden inputs
            for hidden_input in login_form.find_all('input', type='hidden'):
                name = hidden_input.get('name')
                value = hidden_input.get('value', '')
                if name:
                    form_data[name] = value
            
            # Add username and password
            # Try common field names
            username_fields = ['username', 'user', 'email', 'login', 'userid']
            password_fields = ['password', 'pass', 'pwd']
            
            # Find actual field names from the form
            for input_field in login_form.find_all('input'):
                field_type = input_field.get('type', '').lower()
                field_name = input_field.get('name', '').lower()
                
                if field_type in ['text', 'email'] or any(uf in field_name for uf in username_fields):
                    form_data[input_field.get('name')] = username
                elif field_type == 'password' or any(pf in field_name for pf in password_fields):
                    form_data[input_field.get('name')] = password
            
            # Submit login form
            login_submit_url = urljoin(self.base_url, form_action)
            
            if form_method == 'get':
                response = self.session.get(login_submit_url, params=form_data)
            else:
                response = self.session.post(login_submit_url, data=form_data)
            
            response.raise_for_status()
            
            # Check if login was successful
            # Look for indicators of successful login
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Common indicators of successful login
            success_indicators = [
                'logout', 'sign out', 'dashboard', 'profile', 'account',
                'welcome', 'my account', 'settings'
            ]
            
            page_text = soup.get_text().lower()
            login_successful = any(indicator in page_text for indicator in success_indicators)
            
            # Also check if we're redirected away from login page
            if 'login' not in response.url.lower() and response.status_code == 200:
                login_successful = True
            
            if login_successful:
                self.logged_in = True
                logger.info("Successfully logged in to TradeStation Community")
                return True
            else:
                logger.error("Login failed - no success indicators found")
                return False
                
        except Exception as e:
            logger.error(f"Login failed: {e}")
            return False
    
    def search_forum(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Search the forum for posts/threads matching the query"""
        if not self.logged_in:
            return []
        
        try:
            # Try different search URL patterns
            search_urls = [
                f"{self.base_url}/search",
                f"{self.base_url}/forum/search",
                f"{self.base_url}/community/search"
            ]
            
            results = []
            
            for search_url in search_urls:
                try:
                    # Try GET request with query parameter
                    params = {'q': query, 'query': query, 'search': query}
                    response = self.session.get(search_url, params=params)
                    
                    if response.status_code == 200:
                        results = self._parse_search_results(response.content, limit)
                        if results:
                            break
                            
                except Exception as e:
                    logger.debug(f"Search URL {search_url} failed: {e}")
                    continue
            
            # If no search results, try browsing recent posts/threads
            if not results:
                results = self._get_recent_posts(query, limit)
            
            return results
            
        except Exception as e:
            logger.error(f"Search failed: {e}")
            return []
    
    def _parse_search_results(self, html_content: bytes, limit: int) -> List[Dict[str, Any]]:
        """Parse search results from HTML content"""
        soup = BeautifulSoup(html_content, 'html.parser')
        results = []
        
        # Look for common forum result patterns
        result_selectors = [
            'div.search-result',
            'div.result',
            'tr.search-result',
            'div.post',
            'div.thread',
            'li.result'
        ]
        
        for selector in result_selectors:
            elements = soup.select(selector)
            if elements:
                for element in elements[:limit]:
                    result = self._extract_post_info(element)
                    if result:
                        results.append(result)
                break
        
        return results
    
    def _extract_post_info(self, element) -> Optional[Dict[str, Any]]:
        """Extract post information from HTML element"""
        try:
            # Extract title
            title_selectors = ['h3', 'h2', 'h4', '.title', '.subject', 'a']
            title = ""
            title_link = ""
            
            for selector in title_selectors:
                title_elem = element.select_one(selector)
                if title_elem:
                    title = title_elem.get_text(strip=True)
                    if title_elem.name == 'a':
                        title_link = title_elem.get('href', '')
                    else:
                        link_elem = title_elem.find('a')
                        if link_elem:
                            title_link = link_elem.get('href', '')
                    break
            
            if not title:
                return None
            
            # Extract content/snippet
            content_selectors = ['.content', '.message', '.post-content', '.snippet', 'p']
            content = ""
            
            for selector in content_selectors:
                content_elem = element.select_one(selector)
                if content_elem:
                    content = content_elem.get_text(strip=True)
                    break
            
            # Extract author
            author_selectors = ['.author', '.username', '.poster', '.by']
            author = ""
            
            for selector in author_selectors:
                author_elem = element.select_one(selector)
                if author_elem:
                    author = author_elem.get_text(strip=True)
                    break
            
            # Extract date
            date_selectors = ['.date', '.time', '.posted', '.created']
            date = ""
            
            for selector in date_selectors:
                date_elem = element.select_one(selector)
                if date_elem:
                    date = date_elem.get_text(strip=True)
                    break
            
            # Make sure link is absolute
            if title_link and not title_link.startswith('http'):
                title_link = urljoin(self.base_url, title_link)
            
            return {
                'title': title,
                'content': content[:500] + '...' if len(content) > 500 else content,
                'author': author,
                'date': date,
                'url': title_link
            }
            
        except Exception as e:
            logger.debug(f"Failed to extract post info: {e}")
            return None
    
    def _get_recent_posts(self, query: str, limit: int) -> List[Dict[str, Any]]:
        """Get recent posts and filter by query"""
        try:
            # Try to find recent posts or forum index
            forum_urls = [
                f"{self.base_url}/forum",
                f"{self.base_url}/community",
                f"{self.base_url}/topics",
                f"{self.base_url}/recent",
                self.base_url
            ]
            
            for forum_url in forum_urls:
                try:
                    response = self.session.get(forum_url)
                    if response.status_code == 200:
                        soup = BeautifulSoup(response.content, 'html.parser')
                        
                        # Look for post/thread links
                        links = soup.find_all('a', href=True)
                        results = []
                        
                        for link in links:
                            text = link.get_text(strip=True).lower()
                            href = link.get('href', '')
                            
                            # Filter by query
                            if query.lower() in text and len(text) > 10:
                                result = {
                                    'title': link.get_text(strip=True),
                                    'content': '',
                                    'author': '',
                                    'date': '',
                                    'url': urljoin(self.base_url, href) if not href.startswith('http') else href
                                }
                                results.append(result)
                                
                                if len(results) >= limit:
                                    break
                        
                        if results:
                            return results
                            
                except Exception as e:
                    logger.debug(f"Forum URL {forum_url} failed: {e}")
                    continue
            
            return []
            
        except Exception as e:
            logger.error(f"Failed to get recent posts: {e}")
            return []
    
    def get_thread_content(self, thread_url: str) -> Dict[str, Any]:
        """Get full content of a specific thread"""
        if not self.logged_in:
            return {}
        
        try:
            response = self.session.get(thread_url)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Extract thread title
            title_selectors = ['h1', 'h2', '.thread-title', '.topic-title', 'title']
            title = ""
            
            for selector in title_selectors:
                title_elem = soup.select_one(selector)
                if title_elem:
                    title = title_elem.get_text(strip=True)
                    break
            
            # Extract posts
            post_selectors = ['.post', '.message', '.reply', '.comment']
            posts = []
            
            for selector in post_selectors:
                post_elements = soup.select(selector)
                if post_elements:
                    for post_elem in post_elements:
                        post_info = self._extract_post_info(post_elem)
                        if post_info:
                            posts.append(post_info)
                    break
            
            return {
                'title': title,
                'url': thread_url,
                'posts': posts,
                'post_count': len(posts)
            }
            
        except Exception as e:
            logger.error(f"Failed to get thread content: {e}")
            return {}

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
        
        success = client.login(username, password)
        
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
    
    # Auto-login if credentials are provided
    if username and password:
        logger.info("Auto-logging in with provided credentials...")
        success = client.login(username, password)
        if success:
            logger.info("Auto-login successful")
        else:
            logger.warning("Auto-login failed")
    
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
