#!/usr/bin/env python3
"""
Debug forum parsing to see actual structure
"""

import json
from tradestation_client import TradeStationCommunityClient
from bs4 import BeautifulSoup

client = TradeStationCommunityClient()

if not client.logged_in:
    print("ERROR: Not logged in. Make sure .session_cookies.json exists")
    exit(1)

print(f"✓ Logged in with saved cookies\n")

# Try to browse the forum
print("Fetching forum page...")
response = client.session.get(f"{client.forum_url}?Forum_ID=213")
print(f"Status: {response.status_code}")
print(f"URL: {response.url}\n")

if 'signin' in response.url:
    print("ERROR: Redirected to login - cookies expired")
    exit(1)

soup = BeautifulSoup(response.content, 'html.parser')

# Save the page
with open('forum_debug.html', 'w') as f:
    f.write(response.text)
print("✓ Saved forum page to: forum_debug.html\n")

# Look for thread links
topic_links = soup.find_all('a', href=lambda x: x and 'Topic' in x)
print(f"Found {len(topic_links)} topic links\n")

if topic_links:
    print("First 5 topic links:")
    for i, link in enumerate(topic_links[:5], 1):
        title = link.get_text(strip=True)
        href = link.get('href')
        parent_row = link.find_parent('tr')
        
        print(f"\n{i}. Title: {title}")
        print(f"   URL: {href}")
        
        if parent_row:
            cells = parent_row.find_all('td')
            print(f"   Row has {len(cells)} cells:")
            for j, cell in enumerate(cells):
                text = cell.get_text(strip=True)[:100]
                if text:
                    print(f"      Cell {j}: {text}")

print("\n" + "="*80)
print("Check forum_debug.html for full page structure")
print("="*80)
