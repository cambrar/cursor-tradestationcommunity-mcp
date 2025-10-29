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
        # Launch browser in headless mode (required for EC2)
        print("\nLaunching browser (headless mode for EC2)...")
        browser = await p.chromium.launch(headless=True)
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
        
        # Try to fill in the form if we found the fields
        print("\nAttempting to fill login form...")
        try:
            # Try to wait for the username field with a longer timeout
            await page.wait_for_selector('#username', timeout=30000, state='visible')
            await page.fill('#username', username)
            await page.fill('#password', password)
            print("✓ Filled in credentials")
            
            # Take screenshot before clicking
            await page.screenshot(path='before_login.png')
            print("Screenshot saved: before_login.png")
            
            # Click login
            await page.click('#btn-login')
            print("✓ Clicked login button")
            
            # Wait for navigation
            await page.wait_for_url('**/Discussions/**', timeout=30000)
            print(f"✓ Logged in! Current URL: {page.url}")
            
            # Take screenshot after login
            await page.screenshot(path='after_login.png')
            print("Screenshot saved: after_login.png")
            
            # Save cookies
            cookies = await context.cookies()
            print(f"\n✓ Got {len(cookies)} cookies:")
            for cookie in cookies[:5]:
                print(f"  - {cookie['name']}: {cookie['value'][:20]}...")
                
        except Exception as e:
            print(f"\n✗ Login failed: {e}")
        
        await browser.close()
        print("\nTest complete. Check login_page.png and login_page.html")

if __name__ == "__main__":
    asyncio.run(test_login())
