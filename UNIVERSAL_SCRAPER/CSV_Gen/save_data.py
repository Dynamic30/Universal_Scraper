# gets basic data like html, markdown, screenshots, imgs from website 
import os
from datetime import datetime
from urllib.parse import urlparse
from pathlib import Path
from zoneinfo import ZoneInfo
from crawl4ai.async_configs import BrowserConfig, CrawlerRunConfig, CacheMode
from crawl4ai import AsyncWebCrawler
import logging
logger = logging.getLogger("selector_discovery")
import json
import base64


from crawl4ai import async_webcrawler, CrawlerRunConfig

def normalize_url(url: str) -> str:
        return url.replace("://", "_").replace("/", "_").replace("?", "_").replace("&", "_").replace("=", "_")


def ensure_dir(path):
    """Create directory if it doesn't exist"""
    os.makedirs(path, exist_ok=True)

# This Html collection is for csv gen scripts 
async def html_collection(url,base_dir='/data/web'):

    EXCLUDED_TAGS = [
    "script",
    "style",
    "noscript",
    "iframe",
    "svg",
    "canvas",
    "link",
    "meta"
    ]

    try:
        today = datetime.datetime.now(ZoneInfo("Asia/Kolkata")).date().isoformat()
        domain = urlparse(url).hostname or "unknown"
        raw_dir = os.path.join(base_dir, "raw", today, domain, "html")
        clean_dir = os.path.join(base_dir, "clean_html", today, domain, "html")
        ensure_dir(raw_dir)
        ensure_dir(clean_dir)
        path = urlparse(url).path.strip("/")
        slug = path.replace("/", "_") if path else "root"
        raw_path = os.path.join(raw_dir, f"{slug}.html")
        clean_path = os.path.join(clean_dir, f"{slug}.html")

        browser_cfg = BrowserConfig(headless=True)


        run_cfg = CrawlerRunConfig(
            cache_mode=CacheMode.BYPASS,
            scan_full_page=True,
            scroll_delay=0.5,
            remove_overlay_elements=True
        )
        clean_cfg = CrawlerRunConfig(
                    cache_mode=CacheMode.BYPASS,
                    scan_full_page=True,
                    scroll_delay=0.5,
                    remove_overlay_elements=True,
                    excluded_tags=EXCLUDED_TAGS
                )
        


        async with AsyncWebCrawler(config=browser_cfg) as crawler:
            raw = await crawler.arun(url, config=run_cfg)
            clean= await crawler.arun(url, config=clean_cfg)

        if not clean or not clean.html:
            logger.error(f"Clean HTML fetch failed: {url}")
            if not raw or not raw.html:
                logger.error(f"Failed to fetch HTML: {url}")
                return None
            else:
                return raw.html


        with open(raw_path, "w", encoding="utf-8") as f:
            f.write(raw.html or "")

        with open(clean_path, "w", encoding="utf-8") as f:
            f.write(clean.html)
        logger.info(f"HTML saved → RAW + CLEAN for {domain}")
        return clean.html
    
    except Exception as e:
        logger.error(f"html_collection error for {url}: {e}")
        return None

# This Html collection is for crawler scripts 
def html_default(url,base_dir,html):
    if not html:
        return
    
    date = datetime.now().strftime("%Y-%m-%d")
    parsed = urlparse(url)
    domain_folder = parsed.netloc.replace(".", "_")

    # Normalize page URL for folder name
    page_folder = normalize_url(url)

    # Build the path
    html_dir = Path(base_dir) / "Data" / date / domain_folder / "html"

    # Create directories if not exist
    html_dir.mkdir(parents=True, exist_ok=True)

    # Save HTML file
    file_path = html_dir / f"{page_folder}.html"
    file_path.write_text(html, encoding="utf-8")

def markdown_collection(url,base_dir,markdowns):
    if not markdowns:
        return
    date = datetime.now().strftime("%Y-%m-%d")
    parsed = urlparse(url)
    domain_folder = parsed.netloc.replace(".", "_")
    page_folder = normalize_url(url)
    markdown_dir = Path(base_dir) / "Data" / date / domain_folder / "markdown"
    markdown_dir.mkdir(parents=True, exist_ok=True)
    file_path = markdown_dir / f"{page_folder}.md"
    file_path.write_text(markdowns, encoding="utf-8")


def screenshot_data(url, base_dir, screenshot_str):
    if not screenshot_str:
        return
    try:
        screenshot_bytes = base64.b64decode(screenshot_str)
    except Exception as e:
        print(f"[ERROR] Failed to decode screenshot for {url}: {e}")
        return
    parsed = urlparse(url)
    domain_folder = parsed.netloc.replace(".", "_")
    date = datetime.now().strftime("%Y-%m-%d")
    page_folder = normalize_url(url)
    screenshot_dir = Path(base_dir) / "Data" / date / domain_folder / "screenshots"
    screenshot_dir.mkdir(parents=True, exist_ok=True)
    file_path = screenshot_dir / f"{page_folder}.png"
    with open(file_path, "wb") as f:
        f.write(screenshot_bytes)




def metadata_data(url,base_dir,meta):
    if not meta:
        return
    date = datetime.now().strftime("%Y-%m-%d")
    parsed = urlparse(url)
    domain_folder = parsed.netloc.replace(".", "_")
    page_folder = normalize_url(url)
    meta_dir = Path(base_dir) / "Data" / date / domain_folder / "metadata"
    meta_dir.mkdir(parents=True, exist_ok=True)
    file_path = meta_dir / f"{page_folder}.json"
    file_path.write_text(json.dumps(meta, indent=2), encoding="utf-8") 


def pdf_data(url,base_dir,pdf):
    if not pdf:
        return
    date = datetime.now().strftime("%Y-%m-%d")
    parsed = urlparse(url)
    domain_folder = parsed.netloc.replace(".", "_")
    page_folder = normalize_url(url)
    pdf_dir = Path(base_dir) / "Data" / date / domain_folder / "PDF"
    pdf_dir.mkdir(parents=True, exist_ok=True)
    file_path = pdf_dir / f"{page_folder}.pdf"
    file_path.write_bytes(pdf)


def json_data(url,base_dir,json_str):
    if not json_str:
        return
    date = datetime.now().strftime("%Y-%m-%d")
    parsed = urlparse(url)
    domain_folder = parsed.netloc.replace(".", "_")
    page_folder = normalize_url(url)
    json_dir = Path(base_dir) / "Data" / date / domain_folder / "JSON"
    json_dir.mkdir(parents=True, exist_ok=True)
    file_path = json_dir / f"{page_folder}.json"
    file_path.write_text(json.dumps(json_str, ensure_ascii=False, indent=2), encoding="utf-8")

