import sys
import json
import asyncio
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup

async def extract_multiple_selectors(url: str, selectors: list[str]) -> dict:
    results = {}

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()

        try:
            await page.goto(url, wait_until="load", timeout=60000)
            await asyncio.sleep(2) # Small delay for JS-heavy pages

            full_html = await page.content()
            soup = BeautifulSoup(full_html, "html.parser")

            for selector in selectors:
                try:
                    element_html = await page.evaluate(
                        f'''
                                    () => {{
                                        const el = document.querySelector("{selector}");
                                        return el ? el.outerHTML : null;
                                    }}
                                    '''
                    )

                    if element_html:
                        results[selector]=element_html
                    else:
                        results[selector]="element not found"
                except Exception as e:
                    page_html = await page.content()
                    results[selector]=f"Error: {str(e)}\n\n Page Snapshot:\n{page_html[:5000]}..."

        finally:
            await browser.close()

    return results
import os

if __name__ == "__main__":
    url = sys.argv[1]
    selectors_file = sys.argv[2]

    with open(selectors_file, "r", encoding="utf-8") as f:
        selectors = json.load(f)
    result = asyncio.run(extract_multiple_selectors(url, selectors))
    print(json.dumps(result))