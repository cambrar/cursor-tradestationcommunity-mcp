#!/usr/bin/env python3
"""
Debug script to test TradeStation Community forum searching
Run this on EC2 to see what the actual HTML structure looks like
"""

import os
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv

load_dotenv()

# Create session
session = requests.Session()
session.headers.update({
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
})

base_url = "https://community.tradestation.com"

# Login
print("Attempting login...")
username = os.getenv('TRADESTATION_USERNAME')
password = os.getenv('TRADESTATION_PASSWORD')

if not username or not password:
    print("ERROR: No credentials found in .env file")
    exit(1)

print(f"Username: {username}")
print(f"Password: {'*' * len(password)}")

# Get login page
login_url = f"{base_url}/login"
print(f"\n1. Getting login page: {login_url}")
response = session.get(login_url)
print(f"   Status: {response.status_code}")
print(f"   URL after redirect: {response.url}")

# Try to find the actual community/forum URL
print(f"\n2. Trying to access main forum page...")
forum_urls = [
    f"{base_url}/",
    f"{base_url}/discussions",
    f"{base_url}/forum",
    f"{base_url}/community",
]

for url in forum_urls:
    print(f"\n   Trying: {url}")
    response = session.get(url)
    print(f"   Status: {response.status_code}")
    
    if response.status_code == 200:
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Look for search functionality
        search_forms = soup.find_all('form')
        print(f"   Found {len(search_forms)} forms")
        
        search_inputs = soup.find_all('input', {'type': 'search'})
        print(f"   Found {len(search_inputs)} search inputs")
        
        # Look for discussion/thread links
        links = soup.find_all('a', href=True)
        discussion_links = [l for l in links if any(word in l.get('href', '').lower() for word in ['discuss', 'thread', 'topic', 'post'])]
        print(f"   Found {len(discussion_links)} discussion-related links")
        
        if discussion_links:
            print(f"\n   Sample discussion links:")
            for link in discussion_links[:5]:
                print(f"      {link.get('href')} - {link.get_text(strip=True)[:50]}")
        
        # Save page for inspection
        filename = f"debug_{url.split('/')[-1] or 'home'}.html"
        with open(filename, 'w') as f:
            f.write(response.text)
        print(f"   Saved page to: {filename}")

print("\n3. Check if this is actually a forum or just a corporate site...")
print("   The TradeStation Community URL might have changed or require different authentication.")
print("   Check the saved HTML files to see what the actual structure is.")
