#!/usr/bin/env python3
"""
Simple webpage inspection tool
Downloads HTML source and analyzes content
Alternative to screenshots for debugging
"""

import sys
import requests
import argparse
from urllib.parse import urljoin

def fetch_page_source(url: str, output_path: str = None):
    """Fetch webpage HTML source"""
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()

        content = response.text

        if output_path:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"Page source saved to: {output_path}")
        else:
            print(content)

        # Basic analysis
        print(f"\n--- Page Analysis ---")
        print(f"Status Code: {response.status_code}")
        print(f"Content Length: {len(content)} chars")
        print(f"Title: {extract_title(content)}")
        print(f"Contains HTMX: {'hx-' in content}")
        print(f"Contains Error: {'alert-danger' in content}")
        print(f"Contains Active Runs: {'active-runs' in content}")
        print(f"Contains History: {'run-history' in content}")

    except Exception as e:
        print(f"Error fetching page: {e}")
        sys.exit(1)

def extract_title(html_content):
    """Extract page title"""
    import re
    match = re.search(r'<title>(.*?)</title>', html_content, re.IGNORECASE)
    return match.group(1) if match else "No title found"

def main():
    parser = argparse.ArgumentParser(description='Fetch and analyze webpage content')
    parser.add_argument('url', help='URL to fetch')
    parser.add_argument('-o', '--output', help='Output file path')

    args = parser.parse_args()

    fetch_page_source(args.url, args.output)

if __name__ == '__main__':
    main()