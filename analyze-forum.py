#!/usr/bin/env python3
"""
Analyze the TradeStation Community Forum structure
This will help us understand how to properly search and scrape it
"""

import os
import re
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from urllib.parse import urljoin, parse_qs, urlparse

load_dotenv()

session = requests.Session()
session.headers.update({
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
})

base_url = "https://community.tradestation.com"

print("=" * 80)
print("TradeStation Community Forum Analysis")
print("=" * 80)

# First, let's try accessing the forum directly
forum_url = f"{base_url}/Discussions/Forum.aspx?Forum_ID=213"
print(f"\n1. Accessing forum directly: {forum_url}")

response = session.get(forum_url)
print(f"   Status: {response.status_code}")
print(f"   Final URL: {response.url}")

if "signin.tradestation.com" in response.url:
    print("   ⚠️  Redirected to login - authentication required")
    print("   Need to implement OAuth flow or session cookie handling")
else:
    print("   ✓ Access granted!")
    
soup = BeautifulSoup(response.content, 'html.parser')

# Look for search functionality
print("\n2. Looking for search functionality...")
search_inputs = soup.find_all('input', {'type': ['text', 'search']})
print(f"   Found {len(search_inputs)} text/search inputs")

for inp in search_inputs:
    name = inp.get('name', 'unnamed')
    id_attr = inp.get('id', '')
    placeholder = inp.get('placeholder', '')
    print(f"      Input: name='{name}' id='{id_attr}' placeholder='{placeholder}'")

# Look for search forms
forms = soup.find_all('form')
print(f"\n   Found {len(forms)} forms")
for i, form in enumerate(forms[:3]):
    action = form.get('action', '')
    method = form.get('method', 'GET')
    print(f"      Form {i+1}: action='{action}' method='{method}'")

# Look for search links/buttons
search_links = soup.find_all(['a', 'button'], text=re.compile(r'search', re.I))
print(f"\n   Found {len(search_links)} search-related links/buttons")
for link in search_links[:5]:
    href = link.get('href', 'no-href')
    text = link.get_text(strip=True)
    print(f"      {link.name}: '{text}' -> {href}")

# Look for thread/post structure
print("\n3. Analyzing thread structure...")
thread_links = soup.find_all('a', href=re.compile(r'Topic', re.I))
print(f"   Found {len(thread_links)} topic/thread links")

if thread_links:
    print(f"\n   Sample thread links:")
    for link in thread_links[:5]:
        href = link.get('href')
        text = link.get_text(strip=True)
        print(f"      '{text[:50]}' -> {href}")

# Look for pagination
pagination = soup.find_all(text=re.compile(r'\d+\s+Pages', re.I))
print(f"\n4. Pagination: {pagination[:3] if pagination else 'Not found'}")

# Check for ViewState (ASP.NET specific)
viewstate = soup.find('input', {'name': '__VIEWSTATE'})
if viewstate:
    print(f"\n5. ASP.NET ViewState found: {viewstate.get('value')[:100]}...")
    print("   This is an ASP.NET WebForms application - search requires ViewState")

# Save the page
with open('forum_page.html', 'w') as f:
    f.write(response.text)
print(f"\n6. Saved forum page to: forum_page.html")

# Try to find the search URL
print("\n7. Looking for Quick Forum Search...")
quick_search = soup.find(text=re.compile(r'Quick Forum Search', re.I))
if quick_search:
    parent = quick_search.find_parent(['a', 'form', 'div'])
    if parent:
        print(f"   Found Quick Forum Search in: {parent.name}")
        if parent.name == 'a':
            search_url = parent.get('href')
            print(f"   Search URL: {search_url}")

print("\n" + "=" * 80)
print("Analysis complete. Check forum_page.html for full page structure.")
print("=" * 80)
