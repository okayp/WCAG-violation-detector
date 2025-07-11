# final function with right sitemap

import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import xml.etree.ElementTree as ET
from collections import deque
import json
import re
import time

NAMESPACE = {"ns": "http://www.sitemaps.org/schemas/sitemap/0.9"}


# STEP 1: Try to extract sitemap URL from robots.txt
def get_sitemap_from_robots(home_url):
    robots_url = urljoin(home_url, "/robots.txt")
    try:
        response = requests.get(robots_url, timeout=10)
        if response.status_code == 200:
            print(f" Found robots.txt: {robots_url}")
            matches = re.findall(r"Sitemap:\s*(.+)", response.text)
            for match in matches:
                print(f"Found sitemap in robots.txt: {match}")
            return matches
    except:
        pass
    return []


# STEP 2: Parse sitemap and collect URLs
def fetch_sitemap_urls_grouped(sitemap_url, result=None):
    if result is None:
        result = {}

    try:
        response = requests.get(sitemap_url, timeout=10)
        if response.status_code != 200:
            return result

        root = ET.fromstring(response.content)

        if root.tag.endswith("sitemapindex"):
            print(f"Sitemap index: {sitemap_url}")
            for sitemap in root.findall(".//ns:sitemap", NAMESPACE):
                loc = sitemap.find("ns:loc", NAMESPACE)
                if loc is not None:
                    child_sitemap_url = loc.text.strip()
                    fetch_sitemap_urls_grouped(child_sitemap_url, result)

        elif root.tag.endswith("urlset"):
            print(f" Reading sitemap: {sitemap_url}")
            urls = []
            for url in root.findall(".//ns:url", NAMESPACE):
                loc = url.find("ns:loc", NAMESPACE)
                if loc is not None:
                    urls.append(loc.text.strip())
            result[sitemap_url] = urls

    except Exception as e:
        print(f" Error parsing {sitemap_url}: {e}")

    return result


# STEP 3: Fallback HTML link crawler
def get_internal_links(url, base_domain):
    try:
        response = requests.get(url, timeout=10)
        if response.status_code != 200:
            print(f" Failed to load: {url}")
            return []

        soup = BeautifulSoup(response.text, "html.parser")
        links = []
        for tag in soup.find_all('a', href=True):
            href = urljoin(url, tag['href'])
            parsed = urlparse(href)
            if parsed.netloc == base_domain:
                links.append(href.split("#")[0])
        if not links:
            print(f" No links found on page: {url}")
        return links

    except Exception as e:
        print(f" Error fetching {url}: {e}")
        return []


def crawl_site(start_url, max_pages=5000):
    print(f"\n Starting fallback crawl function from: {start_url}")
    base_domain = urlparse(start_url).netloc
    visited = set()
    queue = deque([start_url])
    all_urls = []
    count = 0

    while queue and len(visited) < max_pages:
        current_url = queue.popleft()
        if current_url in visited:
            # print(f"Skipping: {current_url}")
            continue

        visited.add(current_url)
        all_urls.append(current_url)
        count += 1
        print(f"[{count}] Found: {current_url}")

        for link in get_internal_links(current_url, base_domain):
            if link not in visited:
                queue.append(link)

    return all_urls


# FINAL FUNCTION: Unified logic
def get_all_website_links(homepage_url, max_pages=5000):
    print(f"\n Scanning: {homepage_url}")
    start_time = time.time()

    # Step 1: Check robots.txt for sitemap
    sitemap_urls = get_sitemap_from_robots(homepage_url)

    # Step 2: Fallback to /sitemap.xml
    if not sitemap_urls:
        fallback = urljoin(homepage_url, "/sitemap.xml")
        print(f"Trying fallback sitemap: {fallback}")
        sitemap_urls = [fallback]

    # Step 3: Try sitemap-based crawling
    all_urls = {}
    for sitemap_url in sitemap_urls:
        grouped = fetch_sitemap_urls_grouped(sitemap_url)
        if grouped:
            all_urls.update(grouped)

    if all_urls:
        flat_urls = [url for group in all_urls.values() for url in group]
        end_time = time.time()
        print(f"\n Source: sitemap | Total URLs: {len(flat_urls)} | Time: {end_time - start_time:.2f}s")
        for smap, urls in all_urls.items():
            print(f"\n From sitemap: {smap}")
            for url in urls:
                print(f"   ↳ {url}")
        return {
            "source": "sitemap",
            "grouped": all_urls,
            "urls": flat_urls
        }

    # Step 4: Fallback to your HTML crawler
    fallback_urls = crawl_site(homepage_url, max_pages=max_pages)
    end_time = time.time()
    print(f"\n Source: crawler | Total URLs: {len(fallback_urls)} | Time: {end_time - start_time:.2f}s")
    return {
        "source": "crawler",
        "urls": fallback_urls
    }


# Run the full logic
if __name__ == "__main__":
    start_url = "https://katalysttech.com/"
    result = get_all_website_links(start_url, max_pages=5000)

    with open("final_site_urls.json", "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    print("\n All links saved to final_site_urls.json")