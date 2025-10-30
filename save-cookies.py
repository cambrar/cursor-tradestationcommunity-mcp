#!/usr/bin/env python3
"""
Interactive script to manually login and save session cookies
Run this once to save your authenticated session cookies
"""

import asyncio
import json
from playwright.async_api import async_playwright

async def save_cookies():
    print("=" * 80)
    print("TradeStation Community - Manual Login & Cookie Saver")
    print("=" * 80)
    print("\nThis script will:")
    print("1. Open a browser window")
    print("2. Let you manually login (solving CAPTCHA if needed)")
    print("3. Save your session cookies for automated use")
    print("\nPress Enter to continue...")
    input()
    
    async with async_playwright() as p:
        # Launch in non-headless mode so user can interact
        print("\nLaunching browser...")
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()
        
        # Navigate to forum
        forum_url = "https://community.tradestation.com/Discussions/Forum.aspx?Forum_ID=213"
        print(f"\nNavigating to: {forum_url}")
        await page.goto(forum_url)
        
        print("\n" + "=" * 80)
        print("PLEASE LOGIN MANUALLY IN THE BROWSER WINDOW")
        print("=" * 80)
        print("\nSteps:")
        print("1. Solve the CAPTCHA if presented")
        print("2. Enter your username and password")
        print("3. Complete the login")
        print("4. Wait until you see the forum page")
        print("5. Then come back here and press Enter")
        print("\n" + "=" * 80)
        
        print("\nWaiting for you to login...")
        print("After logging in, wait 5 seconds for the page to fully load,")
        print("then press Enter here...")
        input()
        
        # Give extra time for any redirects/Ajax
        print("\nWaiting for page to stabilize...")
        await asyncio.sleep(3)
        
        # Get current URL and check page content
        current_url = page.url
        page_title = await page.title()
        page_content = await page.content()
        
        print(f"\nCurrent URL: {current_url}")
        print(f"Page title: {page_title}")
        
        # Check for forum-related content in the page
        is_forum_page = any(marker in page_content.lower() for marker in [
            'forum.aspx', 'discussions', 'topic', 'thread', 'my forum subscriptions',
            'most recent forum posts', 'quick forum search'
        ])
        
        if is_forum_page or 'Discussions' in current_url or 'Forum.aspx' in current_url:
            print("✓ Detected forum page content - you're logged in!")
            
            # Extract cookies from ALL domains
            cookies = await context.cookies()
            print(f"\nExtracted {len(cookies)} cookies from:")
            
            domains = set(cookie.get('domain', '') for cookie in cookies)
            for domain in sorted(domains):
                domain_cookies = [c for c in cookies if c.get('domain') == domain]
                print(f"  - {domain}: {len(domain_cookies)} cookies")
            
            # Save cookies to file
            cookie_file = '.session_cookies.json'
            with open(cookie_file, 'w') as f:
                json.dump(cookies, f, indent=2)
            
            print(f"\n✓ Cookies saved to: {cookie_file}")
            print("\nNow copy this file to your EC2 instance:")
            print(f"  scp {cookie_file} mcp-server@35.87.167.11:/data/tradestation-community-mcp/")
            
        else:
            print("✗ Doesn't look like you're on the forum page yet")
            print(f"  Current URL: {current_url}")
            print(f"  Page title: {page_title}")
            print("\nIf you ARE logged in, the cookies were still saved.")
            print("Check the browser window to see what page you're on.")
            
            # Save cookies anyway
            cookies = await context.cookies()
            cookie_file = '.session_cookies.json'
            with open(cookie_file, 'w') as f:
                json.dump(cookies, f, indent=2)
            print(f"\n✓ Cookies saved to: {cookie_file} (just in case)")
        
        print("\nClosing browser in 5 seconds...")
        await asyncio.sleep(5)
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(save_cookies())
