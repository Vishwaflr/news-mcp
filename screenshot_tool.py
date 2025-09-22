#!/usr/bin/env python3
"""
Local screenshot tool using Playwright
Alternative to the remote playwright service for debugging purposes
"""

import sys
import asyncio
from playwright.async_api import async_playwright
import argparse

async def take_screenshot(url: str, output_path: str, full_page: bool = True):
    """Take a screenshot of a webpage"""
    async with async_playwright() as p:
        # Launch browser in headless mode
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        # Navigate to URL
        await page.goto(url)

        # Wait for page to load
        await page.wait_for_load_state('networkidle')

        # Take screenshot
        await page.screenshot(path=output_path, full_page=full_page)

        await browser.close()
        print(f"Screenshot saved to: {output_path}")

def main():
    parser = argparse.ArgumentParser(description='Take webpage screenshots')
    parser.add_argument('url', help='URL to screenshot')
    parser.add_argument('output', help='Output file path')
    parser.add_argument('--full-page', action='store_true', default=True, help='Take full page screenshot')

    args = parser.parse_args()

    try:
        asyncio.run(take_screenshot(args.url, args.output, args.full_page))
    except Exception as e:
        print(f"Error taking screenshot: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()