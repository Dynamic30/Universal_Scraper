import json
import csv
import requests
import asyncio
from pathlib import Path
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import xml.etree.ElementTree as ET
from crawl4ai import AsyncWebCrawler, LLMExtractionStrategy, LLMConfig
from crawl4ai.async_configs import BrowserConfig, CrawlerRunConfig, CacheMode
import datetime
from zoneinfo import ZoneInfo
import os
import logging
logger = logging.getLogger("selector_discovery")


# STEP 1: Load listing inputs

def listing_scraper(html_content,listing_selectors,base_dir,product_selector_path):
    html = html_content

    # STEP 2: Extract product URLs

    soup = BeautifulSoup(html, "html.parser")

    cards = soup.select(listing_selectors["product_card"])
    product_urls = []

    for card in cards:
        link = card.select_one(listing_selectors["product_link"])
        if link and link.get("href"):
            product_urls.append(link["href"])
    base_url = soup.base["href"] if soup.base else ""
    product_urls = [urljoin(base_url or "", u) for u in product_urls]
    # dedupe
    unique_urls = list(dict.fromkeys(product_urls))

    print(f"\nFound {len(unique_urls)} product URLs")

    # STEP 3: Load product selectors

    product_selector_path = product_selector_path
    output_dir = base_dir

    product_selector_path = Path(product_selector_path)
    output_dir = Path(output_dir)

    if not product_selector_path.exists():
        raise FileNotFoundError("Product selector JSON not found")

    output_dir.mkdir(parents=True, exist_ok=True)

    product_selectors = json.loads(product_selector_path.read_text(encoding="utf-8"))

    # STEP 4: Product scraper

    def scrape_product(html, selectors):
        soup = BeautifulSoup(html, "html.parser")
        data = {}

        for field, selector in selectors.items():
            if not selector:
                data[field] = ""
                continue

            el = soup.select_one(selector)
            data[field] = el.get_text(strip=True) if el else ""

        return data

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        "Accept-Language": "en-US,en;q=0.9"
    }

    all_products = []

    for idx, url in enumerate(unique_urls, start=1):
        print(f"Scraping product {idx}/{len(unique_urls)}")

        product_html = asyncio.run(html_collection(url, base_dir))
        if not product_html:
            continue

        product_data = scrape_product(product_html, product_selectors)
        product_data["url"] = url

        all_products.append(product_data)

    # STEP 5: Save CSV
    domain = urlparse(unique_urls[0]).hostname or "unknown"
    csv_dir = Path(base_dir) / "CSV" / domain
    csv_dir.mkdir(parents=True, exist_ok=True)

    if not all_products:
        print("No products scraped. CSV not created.")
        return
    csv_path = csv_dir / "products.csv"

    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=all_products[0].keys()
        )
        writer.writeheader()
        writer.writerows(all_products)

    print(f"\nSaved {len(all_products)} products to {csv_path}")
def ensure_dir(path):
    """Create directory if it doesn't exist"""
    os.makedirs(path, exist_ok=True)


async def html_collection(url,base_dir='/data/web'):
    try:
        today = datetime.datetime.now(ZoneInfo("Asia/Kolkata")).date().isoformat()
        domain = urlparse(url).hostname or "unknown"
        raw_dir = os.path.join(base_dir, "raw", today, domain, "html")
        ensure_dir(raw_dir)
        path = urlparse(url).path.strip("/")
        slug = path.replace("/", "_") if path else "root"
        html_path = os.path.join(raw_dir, f"{slug}.html")

        browser_cfg = BrowserConfig(headless=True)
        run_cfg = CrawlerRunConfig(
            cache_mode=CacheMode.BYPASS,
            scan_full_page=True,
            scroll_delay=0.5,
            remove_overlay_elements=True
        )

        async with AsyncWebCrawler(config=browser_cfg) as crawler:
            result = await crawler.arun(url, config=run_cfg)

        if not result or not result.html:
            logger.error(f"Failed to fetch HTML: {url}")
            return None

        with open(html_path, "w", encoding="utf-8") as f:
            f.write(result.html)

        logger.info(f"HTML saved at: {html_path}")
        return result.html

    except Exception as e:
        logger.error(f"html_collection error for {url}: {e}")
        return None



def sitemap_scraper(sitemap_url,product_selector_path,base_dir):
    resp = requests.get(sitemap_url, headers={
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        "Accept": "application/xml,text/xml;q=0.9,*/*;q=0.8",
    },
timeout=20)
    resp.raise_for_status()

    root = ET.fromstring(resp.text)
    ns = {"ns": "http://www.sitemaps.org/schemas/sitemap/0.9"}

    urls = []

    for url in root.findall("ns:url", ns):
        loc = url.find("ns:loc", ns)
        if loc is not None and loc.text:
            urls.append(loc.text.strip())

    product_selector_path = Path(product_selector_path)
    if not product_selector_path.exists():
        raise FileNotFoundError("Product selector JSON not found")

    product_selectors = json.loads(
        product_selector_path.read_text(encoding="utf-8")
    )


    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        "Accept-Language": "en-US,en;q=0.9"
    }

    all_rows = []

    for idx, url in enumerate(urls, start=1):
        print(f"Sitemap scraping {idx}/{len(urls)}")

        try:
            html = asyncio.run(html_collection(url, base_dir))
            if not html:
                continue
        except Exception:
            continue

        soup = BeautifulSoup(html, "html.parser")
        row = {}

        for field, selector in product_selectors.items():
            if not selector:
                row[field] = ""
                continue

            el = soup.select_one(selector)
            row[field] = el.get_text(strip=True) if el else ""

        row["url"] = url
        all_rows.append(row)

    if not all_rows:
        print("No URLs scraped. CSV not created.")
        return
    
    if not urls:
        print("No URLs found in sitemap.")
        return

    domain = urlparse(urls[0]).hostname or "unknown"
    csv_dir = Path(base_dir) / "CSV" / domain
    csv_dir.mkdir(parents=True, exist_ok=True)

    csv_path = csv_dir / "products.csv"

    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=all_rows[0].keys()
        )
        writer.writeheader()
        writer.writerows(all_rows)

    print(f"\nSaved {len(all_rows)} rows to {csv_path}")

