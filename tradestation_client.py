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
from playwright.async_api import async_playwright

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
        self.cookie_file = '/data/tradestation-community-mcp/.session_cookies.json'
        
        # Set headers to mimic a real browser
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
        })
        
        # Try to load saved cookies
        self._load_saved_cookies()
    
    def _load_saved_cookies(self):
        """Load previously saved session cookies"""
        try:
            import json
            if os.path.exists(self.cookie_file):
                with open(self.cookie_file, 'r') as f:
                    cookies = json.load(f)
                
                for cookie in cookies:
                    self.session.cookies.set(
                        cookie['name'],
                        cookie['value'],
                        domain=cookie.get('domain', ''),
                        path=cookie.get('path', '/')
                    )
                
                # Verify cookies work
                response = self.session.get(f"{self.forum_url}?Forum_ID=213")
                if 'signin.tradestation.com' not in response.url:
                    self.logged_in = True
                    logger.info(f"Loaded {len(cookies)} saved cookies - session is active")
                else:
                    logger.warning("Saved cookies are expired - need to re-authenticate")
        except Exception as e:
            logger.debug(f"Could not load saved cookies: {e}")
    
    async def login(self, username: str, password: str, headless: bool = True) -> bool:
        """Login to TradeStation Community using Playwright for OAuth"""
        try:
            async with async_playwright() as p:
                # Launch browser
                browser = await p.chromium.launch(headless=headless)
                context = await browser.new_context()
                page = await context.new_page()
                
                logger.info("Opening TradeStation Community forum...")
                # Navigate to the forum which will redirect to login
                await page.goto(f"{self.forum_url}?Forum_ID=213", wait_until='networkidle', timeout=60000)
                
                # Check for AWS WAF CAPTCHA
                logger.info("Checking for CAPTCHA challenge...")
                captcha_present = await page.query_selector('.amzn-captcha-verify-button')
                
                if captcha_present:
                    logger.warning("AWS WAF CAPTCHA detected - attempting to solve...")
                    try:
                        # Click the Begin button
                        await page.click('.amzn-captcha-verify-button')
                        logger.info("Clicked CAPTCHA begin button")
                        
                        # Wait for CAPTCHA to be solved (this might take some time)
                        # The page should reload after CAPTCHA is solved
                        await page.wait_for_url('**/login?**', timeout=60000)
                        logger.info("CAPTCHA challenge passed")
                    except Exception as e:
                        logger.error(f"Failed to handle CAPTCHA: {e}")
                        logger.error("AWS WAF CAPTCHA cannot be solved automatically")
                        raise Exception("CAPTCHA challenge detected - automated login not possible")
                
                # Wait for login page to load
                logger.info("Waiting for login page...")
                await page.wait_for_selector('#username', timeout=30000)
                
                # Fill in credentials
                logger.info("Entering credentials...")
                await page.fill('#username', username)
                await page.fill('#password', password)
                
                # Click login button
                logger.info("Submitting login...")
                await page.click('#btn-login')
                
                # Wait for redirect back to forum
                logger.info("Waiting for authentication...")
                await page.wait_for_url('**/Discussions/**', timeout=30000)
                
                # Extract cookies from browser
                logger.info("Extracting session cookies...")
                cookies = await context.cookies()
                
                # Convert cookies to requests format
                for cookie in cookies:
                    self.session.cookies.set(
                        cookie['name'],
                        cookie['value'],
                        domain=cookie.get('domain', ''),
                        path=cookie.get('path', '/')
                    )
                    self.cookies[cookie['name']] = cookie['value']
                
                await browser.close()
                
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
            # Get all cells
            cells = row.find_all('td')
            
            # Skip rows that don't have the right number of cells
            if len(cells) < 8:
                return None
            
            # Cell 1 contains the topic title and link
            title_cell = cells[1] if len(cells) > 1 else None
            if not title_cell:
                return None
            
            # Find the topic link in the title cell
            topic_link = title_cell.find('a', href=re.compile(r'Topic', re.I))
            if not topic_link:
                return None
            
            title = topic_link.get_text(strip=True)
            if not title or len(title) < 3:
                return None
            
            url = urljoin(self.base_url, topic_link.get('href', ''))
            
            # Cell 2 contains author
            author = cells[2].get_text(strip=True) if len(cells) > 2 else ""
            
            # Cell 3 contains category (can be used as content preview)
            category = cells[3].get_text(strip=True) if len(cells) > 3 else ""
            
            # Cell 8 contains last post date
            date = cells[8].get_text(strip=True) if len(cells) > 8 else ""
            # Clean up the date (remove "by:" and author info)
            date = date.split('by:')[0].strip() if 'by:' in date else date
            
            # Get preview from the title attribute if available
            preview = topic_link.get('title', '')[:500] if topic_link.get('title') else category
            
            return {
                'title': title,
                'content': preview,
                'author': author,
                'date': date,
                'url': url,
                'category': category
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
            
            # Find all thread rows (not just links)
            # Look for rows with class tbl_TR_White which contain the threads
            thread_rows = soup.find_all('tr', class_='tbl_TR_White')
            
            logger.info(f"Found {len(thread_rows)} thread rows on forum page")
            
            results = []
            query_lower = query.lower()
            
            for row in thread_rows:
                # Extract thread info using our method
                thread_info = self._extract_thread_from_row(row)
                
                if not thread_info:
                    continue
                
                # Filter by query - check title, content, or category
                title_lower = thread_info.get('title', '').lower()
                content_lower = thread_info.get('content', '').lower()
                category_lower = thread_info.get('category', '').lower()
                
                if (query_lower in title_lower or 
                    query_lower in content_lower or
                    query_lower in category_lower):
                    results.append(thread_info)
                    
                    if len(results) >= limit:
                        break
            
            logger.info(f"Filtered to {len(results)} matching threads")
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

