"""
TradeStation Community Client with Playwright-based authentication
Handles OAuth login and forum scraping
"""

import logging
import os
import re
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin, urlparse, parse_qs

import requests
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright, Page, Browser

logger = logging.getLogger(__name__)

class TradeStationCommunityClient:
    """Client for interacting with TradeStation Community forum"""
    
    def __init__(self):
        self.session = requests.Session()
        self.base_url = "https://community.tradestation.com"
        self.forum_url = f"{self.base_url}/Discussions/Forum.aspx"
        self.search_url = f"{self.base_url}/Discussions/Search.aspx"
        self.logged_in = False
        self.cookies = {}
        
        # Set headers to mimic a real browser
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
        })
    
    def login(self, username: str, password: str, headless: bool = True) -> bool:
        """Login to TradeStation Community using Playwright for OAuth"""
        try:
            with sync_playwright() as p:
                # Launch browser
                browser = p.chromium.launch(headless=headless)
                context = browser.new_context()
                page = context.new_page()
                
                logger.info("Opening TradeStation Community forum...")
                # Navigate to the forum which will redirect to login
                page.goto(f"{self.forum_url}?Forum_ID=213", wait_until='networkidle', timeout=30000)
                
                # Wait for login page to load
                logger.info("Waiting for login page...")
                page.wait_for_selector('#username', timeout=10000)
                
                # Fill in credentials
                logger.info("Entering credentials...")
                page.fill('#username', username)
                page.fill('#password', password)
                
                # Click login button
                logger.info("Submitting login...")
                page.click('#btn-login')
                
                # Wait for redirect back to forum
                logger.info("Waiting for authentication...")
                page.wait_for_url('**/Discussions/**', timeout=30000)
                
                # Extract cookies from browser
                logger.info("Extracting session cookies...")
                cookies = context.cookies()
                
                # Convert cookies to requests format
                for cookie in cookies:
                    self.session.cookies.set(
                        cookie['name'],
                        cookie['value'],
                        domain=cookie.get('domain', ''),
                        path=cookie.get('path', '/')
                    )
                    self.cookies[cookie['name']] = cookie['value']
                
                browser.close()
                
                # Verify we can access the forum
                logger.info("Verifying forum access...")
                response = self.session.get(f"{self.forum_url}?Forum_ID=213")
                
                if 'signin.tradestation.com' not in response.url:
                    self.logged_in = True
                    logger.info("Successfully logged in to TradeStation Community")
                    return True
                else:
                    logger.error("Login verification failed - still redirecting to login")
                    return False
                    
        except Exception as e:
            logger.error(f"Login failed: {e}")
            return False
    
    def search_forum(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Search the forum for posts/threads matching the query"""
        if not self.logged_in:
            logger.error("Not logged in - cannot search forum")
            return []
        
        try:
            results = []
            
            # Try the search page
            logger.info(f"Searching forum for: {query}")
            
            # TradeStation forum search URLs
            search_params = {
                'Search': query,
                'Forum_ID': '213',  # TradeStation and EasyLanguage Support forum
            }
            
            response = self.session.get(self.search_url, params=search_params)
            
            if 'signin.tradestation.com' in response.url:
                logger.error("Session expired - need to re-login")
                self.logged_in = False
                return []
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Parse search results - ASP.NET forum structure
            # Look for thread rows in the results table
            thread_rows = soup.find_all('tr', class_=re.compile(r'grid|row|topic', re.I))
            
            if not thread_rows:
                # Try alternative selectors
                thread_rows = soup.select('table tr')
            
            logger.info(f"Found {len(thread_rows)} potential thread rows")
            
            for row in thread_rows[:limit]:
                thread_info = self._extract_thread_from_row(row)
                if thread_info:
                    results.append(thread_info)
            
            # If no results from search, try browsing the forum
            if not results:
                logger.info("No search results, trying to browse forum...")
                results = self._browse_forum(query, limit)
            
            return results
            
        except Exception as e:
            logger.error(f"Search failed: {e}")
            return []
    
    def _extract_thread_from_row(self, row) -> Optional[Dict[str, Any]]:
        """Extract thread information from a table row"""
        try:
            # Find the topic link
            topic_link = row.find('a', href=re.compile(r'Topic', re.I))
            
            if not topic_link:
                return None
            
            title = topic_link.get_text(strip=True)
            url = urljoin(self.base_url, topic_link.get('href', ''))
            
            # Find author
            author_cell = row.find('td', class_=re.compile(r'author|poster', re.I))
            author = author_cell.get_text(strip=True) if author_cell else ""
            
            # Find date
            date_cell = row.find('td', class_=re.compile(r'date|time|posted', re.I))
            date = date_cell.get_text(strip=True) if date_cell else ""
            
            # Get all cells for potential preview
            cells = row.find_all('td')
            content = ""
            for cell in cells:
                text = cell.get_text(strip=True)
                if len(text) > 50 and text != title:
                    content = text[:500]
                    break
            
            return {
                'title': title,
                'content': content,
                'author': author,
                'date': date,
                'url': url
            }
            
        except Exception as e:
            logger.debug(f"Failed to extract thread from row: {e}")
            return None
    
    def _browse_forum(self, query: str, limit: int) -> List[Dict[str, Any]]:
        """Browse the forum and filter by query"""
        try:
            logger.info("Browsing forum for recent posts...")
            
            # Access the main forum
            response = self.session.get(f"{self.forum_url}?Forum_ID=213")
            
            if 'signin.tradestation.com' in response.url:
                logger.error("Session expired during browse")
                self.logged_in = False
                return []
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Find all thread links
            topic_links = soup.find_all('a', href=re.compile(r'Topic', re.I))
            
            logger.info(f"Found {len(topic_links)} topic links on forum page")
            
            results = []
            query_lower = query.lower()
            
            for link in topic_links:
                title = link.get_text(strip=True)
                
                # Filter by query
                if query_lower in title.lower():
                    url = urljoin(self.base_url, link.get('href', ''))
                    
                    # Try to get context from parent row
                    parent_row = link.find_parent('tr')
                    author = ""
                    date = ""
                    
                    if parent_row:
                        cells = parent_row.find_all('td')
                        if len(cells) > 1:
                            author = cells[1].get_text(strip=True) if len(cells) > 1 else ""
                            date = cells[-1].get_text(strip=True) if len(cells) > 2 else ""
                    
                    results.append({
                        'title': title,
                        'content': '',
                        'author': author,
                        'date': date,
                        'url': url
                    })
                    
                    if len(results) >= limit:
                        break
            
            return results
            
        except Exception as e:
            logger.error(f"Failed to browse forum: {e}")
            return []
    
    def get_thread_content(self, thread_url: str) -> Dict[str, Any]:
        """Get full content of a specific thread"""
        if not self.logged_in:
            return {}
        
        try:
            response = self.session.get(thread_url)
            
            if 'signin.tradestation.com' in response.url:
                logger.error("Session expired")
                self.logged_in = False
                return {}
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Extract thread title
            title_elem = soup.find('h1') or soup.find('h2') or soup.find(class_=re.compile(r'title|subject', re.I))
            title = title_elem.get_text(strip=True) if title_elem else "Thread"
            
            # Extract posts - ASP.NET forum typically uses table structure
            post_rows = soup.find_all('tr', class_=re.compile(r'post|message|reply', re.I))
            
            if not post_rows:
                # Try to find posts by looking for common patterns
                post_rows = soup.find_all('div', class_=re.compile(r'post|message', re.I))
            
            posts = []
            for row in post_rows:
                post_info = self._extract_post_from_element(row)
                if post_info:
                    posts.append(post_info)
            
            return {
                'title': title,
                'url': thread_url,
                'posts': posts,
                'post_count': len(posts)
            }
            
        except Exception as e:
            logger.error(f"Failed to get thread content: {e}")
            return {}
    
    def _extract_post_from_element(self, element) -> Optional[Dict[str, Any]]:
        """Extract post information from an HTML element"""
        try:
            # Get post content
            content_elem = element.find(class_=re.compile(r'content|message|body', re.I))
            content = content_elem.get_text(strip=True) if content_elem else element.get_text(strip=True)[:500]
            
            # Get author
            author_elem = element.find(class_=re.compile(r'author|poster|username', re.I))
            author = author_elem.get_text(strip=True) if author_elem else ""
            
            # Get date
            date_elem = element.find(class_=re.compile(r'date|time|posted', re.I))
            date = date_elem.get_text(strip=True) if date_elem else ""
            
            if content and len(content) > 10:
                return {
                    'content': content,
                    'author': author,
                    'date': date
                }
            
            return None
            
        except Exception as e:
            logger.debug(f"Failed to extract post: {e}")
            return None

