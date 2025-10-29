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
        
        input("\nPress Enter after you've successfully logged in...")
        
        # Get current URL
        current_url = page.url
        print(f"\nCurrent URL: {current_url}")
        
        if 'Discussions' in current_url or 'Forum.aspx' in current_url:
            print("✓ Looks like you're logged in!")
            
            # Extract cookies
            cookies = await context.cookies()
            print(f"\nExtracted {len(cookies)} cookies")
            
            # Save cookies to file
            cookie_file = '/data/tradestation-community-mcp/.session_cookies.json'
            with open(cookie_file, 'w') as f:
                json.dump(cookies, f, indent=2)
            
            print(f"\n✓ Cookies saved to: {cookie_file}")
            print("\nThese cookies will be used for automated forum access.")
            print("They will expire eventually and you'll need to run this script again.")
            
        else:
            print("✗ Doesn't look like you're logged in yet")
            print(f"  Current URL: {current_url}")
            print("\nPlease try again")
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(save_cookies())
