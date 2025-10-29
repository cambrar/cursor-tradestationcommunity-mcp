#!/usr/bin/env python3
"""
Test Playwright login to see what's happening
"""

import asyncio
import os
from dotenv import load_dotenv
from playwright.async_api import async_playwright

load_dotenv()

async def test_login():
    username = os.getenv('TRADESTATION_USERNAME')
    password = os.getenv('TRADESTATION_PASSWORD')
    
    print(f"Username: {username}")
    print(f"Password: {'*' * len(password)}")
    
    async with async_playwright() as p:
        # Launch browser in non-headless mode to see what's happening
        print("\nLaunching browser (headless=False to see what happens)...")
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()
        
        # Navigate to forum
        forum_url = "https://community.tradestation.com/Discussions/Forum.aspx?Forum_ID=213"
        print(f"\nNavigating to: {forum_url}")
        await page.goto(forum_url, wait_until='networkidle', timeout=60000)
        
        print(f"Current URL: {page.url}")
        print(f"Page title: {await page.title()}")
        
        # Take a screenshot
        await page.screenshot(path='login_page.png')
        print("\nScreenshot saved to: login_page.png")
        
        # Save the HTML
        html = await page.content()
        with open('login_page.html', 'w') as f:
            f.write(html)
        print("HTML saved to: login_page.html")
        
        # Try to find username field with different selectors
        print("\nLooking for username field...")
        selectors = ['#username', 'input[type="text"]', 'input[placeholder*="sername" i]', 'input[name*="user" i]']
        
        for selector in selectors:
            try:
                element = await page.query_selector(selector)
                if element:
                    print(f"  ✓ Found with selector: {selector}")
                    is_visible = await element.is_visible()
                    print(f"    Visible: {is_visible}")
                else:
                    print(f"  ✗ Not found: {selector}")
            except Exception as e:
                print(f"  ✗ Error with {selector}: {e}")
        
        # Wait to see the browser
        print("\nBrowser will stay open for 10 seconds so you can see it...")
        await asyncio.sleep(10)
        
        await browser.close()
        print("\nTest complete. Check login_page.png and login_page.html")

if __name__ == "__main__":
    asyncio.run(test_login())
