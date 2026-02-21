import os
import datetime
from zoneinfo import ZoneInfo
from urllib.parse import urlparse
import asyncio
import json
import requests
import xml.etree.ElementTree as ET
from crawl4ai import AsyncWebCrawler, LLMExtractionStrategy, LLMConfig
from crawl4ai.async_configs import BrowserConfig, CrawlerRunConfig, CacheMode
from pydantic import BaseModel, Field
from bs4 import BeautifulSoup
# Simple logger
import logging

# import from custom scripts
from CSV_Gen.save_data import ensure_dir, html_collection
from CSV_Gen.scraper_logic import listing_scraper, sitemap_scraper
logger = logging.getLogger("selector_discovery")

HEADERS = {
    'User-Agent': (
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
        '(KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36'
    )
}



def validate_selector(soup, selector: str) -> str:
    if not isinstance(selector, str):
        return ""
    current = selector.strip()

    while True:
        try:
            if soup.select(current):
                return current
        except Exception:
            pass

        # no more scope to trim
        if " " not in current:
            break

        # trim ONLY the leftmost scope
        current = current.split(" ", 1)[1]

    return ""




def get_llm_config():
    """Get LLM provider configuration from user"""
    print("\n" + "=" * 50)
    print("LLM Provider Configuration")
    print("=" * 50)
    
    while True:
        provider_choice = input("Use (c)laude, (g)emini or (o)llama? [default: o]: ").strip().lower()
        
        if provider_choice in ['c', 'claude']:
            api_key = input("Enter your Claude API key: ").strip()
            if api_key:
                print("✓ Provider: Claude")
                return {
                    'api_key': api_key,
                    'provider': "claude-3-5-haiku-20241022",
                    'base_url': None
                }
            else:
                print("API key is required for Claude!")
                
        elif provider_choice in ['g', 'gemini']:
            api_key = input("Enter your Gemini API key: ").strip()
            if api_key:
                print("✓ Provider: Gemini")
                return {
                    'api_key': api_key,
                    'provider': "gemini/gemini-1.5-pro",
                    'base_url': None
                }
            else:
                print("API key is required for Gemini!")
                
        else:  # Ollama (default)
            model_name = input("Enter Ollama model name [default: llama3:8b]: ").strip()
            if not model_name:
                model_name = "llama3:8b"
            print(f"✓ Provider: Ollama ({model_name})")
            return {
                'api_key': "no-token",
                'provider': f"ollama/{model_name}",
                'base_url': "http://localhost:11434"
            }


# from here onward you can add more function based on page strucutre 
async def product_page(llm_cfg,html_content, url, base_dir):
    if not html_content:
        print("No HTML content received, skipping selector extraction")
        return
    domain = urlparse(url).hostname or "unknown"
    selectors_dir = os.path.join(base_dir, "selectors", domain)
    ensure_dir(selectors_dir)
    selector_path = os.path.join(selectors_dir, "product_selector.json")
    selector_schema = {
        "name": "",
        "price": "",
        "description": "",
        "category": "",
        "brand": "",
        "availability": "",
        "ratings": "",
        "reviews": "",
        "size": "",
        "size_container": ""
    }

    prompt = """
            You are an expert CSS selector engineer.

            Your task is to extract reusable, stable CSS selectors for a SINGLE product detail page.

            You are NOT extracting product values.
            You are extracting CSS SELECTORS ONLY.

            ASSUME:
            - This is a product detail page
            - Ignore related products, recommendations, upsells, bundles, cross-sells
            - Focus ONLY on the main product content

            ────────────────────────────────────
            STRICT OUTPUT RULES
            ────────────────────────────────────
            - Return CSS selectors ONLY
            - NO values
            - NO explanations
            - NO XPath
            - NO scripts
            - NO JSON-LD / schema.org
            - Output MUST match the schema EXACTLY
            - Do NOT add, remove, or rename fields
            - If no reasonable selector exists, return an empty string

            ────────────────────────────────────
            SELECTOR QUALITY RULES (IMPORTANT)
            ────────────────────────────────────
            - Prefer simple, stable selectors over complex ones
            - Prefer 1–2 levels of depth
            - Allow deeper selectors ONLY if they are clearly stable
            - Prefer IDs or data-* attributes when available
            - Prefer semantic class names tied to product context
            - Avoid nth-child, positional, or index-based selectors
            - Avoid unscoped generic selectors (div, span, .price)

            IMPORTANT GUIDANCE:
            - Do NOT over-chain selectors just to guarantee uniqueness
            - A selector that is slightly broad but stable is BETTER than a fragile deep selector
            - Use minimal scoping needed to avoid obvious false matches

            BAD SELECTORS (DO NOT GENERATE):
            - .container .row .col span
            - .product-page div div h1
            - .a .b .c .d
            - body div span

            GOOD SELECTORS:
            - h1[itemprop="name"]
            - .product-title
            - .product-info-main .price
            - [data-testid="product-price"]

            ────────────────────────────────────
            SINGLE-SELECTOR RULE
            ────────────────────────────────────
            - Return ONE selector per field
            - Do NOT combine multiple alternative ideas into a single selector
            - If multiple valid options exist, choose the simplest and most reusable one

            ────────────────────────────────────
            FIELD INSTRUCTIONS
            ────────────────────────────────────

            name:
            - Main product title
            - Usually h1 or equivalent
            - Must NOT match breadcrumbs or site-wide page title

            price:
            - Current selling price only
            - Ignore crossed-out prices, MRPs, discounts, savings

            description:
            - Main product description block
            - Prefer the primary description over summaries or highlights

            category:
            - Use breadcrumb or category navigation
            - Return selector for the MOST SPECIFIC category element

            brand:
            - Visible brand name rendered as text in the DOM
            - Ignore logos unless text-based

            availability:
            - Visible stock or availability status text
            - Must be user-visible in the DOM

            ratings:
            - Average rating (stars or numeric)
            - Must be visible in the DOM

            reviews:
            - Review COUNT element only
            - Do NOT return the full review container

            size:
            - Selector for the CURRENTLY SELECTED size or variant option
            - Empty string if no selectable sizes exist

            size_container:
            - Selector for the parent container holding ALL size options
            - Must wrap all size buttons/options

            ────────────────────────────────────
            VARIANT HANDLING
            ────────────────────────────────────
            - Detect size variants ONLY if multiple clickable options exist
            - If variants exist:
            - size_container = container selector
            - size = selected option selector
            - If no variants exist:
            - BOTH fields MUST be empty strings

            ────────────────────────────────────
            FINAL OUTPUT FORMAT (STRICT)
            ────────────────────────────────────
            {
            "name": "",
            "price": "",
            "description": "",
            "category": "",
            "brand": "",
            "availability": "",
            "ratings": "",
            "reviews": "",
            "size": "",
            "size_container": ""
            }

            FINAL CHECK:
            - All selectors must target HTML DOM elements
            - Do NOT use metadata or structured data
            - Prefer returning a reasonable selector over an empty string

        """

    llm_config = LLMConfig(
        provider=llm_cfg["provider"],
        api_token=llm_cfg["api_key"],
        base_url=llm_cfg["base_url"]
    )

    llm_strategy = LLMExtractionStrategy(
        llm_config=llm_config,
        schema=selector_schema,
        extraction_type="schema",
        instruction=prompt,
        input_format="html"
    )

    browser_cfg = BrowserConfig(headless=True)
    run_cfg = CrawlerRunConfig(
        extraction_strategy=llm_strategy,
        cache_mode=CacheMode.BYPASS
    )
    
    async with AsyncWebCrawler(config=browser_cfg) as crawler:
        result = await crawler.arun(url, config=run_cfg)
    if not result or not result.extracted_content:
        print("No extracted content received")
        return
    try: 
        selectors = json.loads(result.extracted_content)
        if isinstance(selectors, list):
            if not selectors:
                print("Empty selector list returned by LLM")
                return
            selectors = selectors[0]

    except json.JSONDecodeError as e:
        print(f"Error parsing JSON: {e}")
        print(f"Extracted content: {result.extracted_content}")
        return

    for key in selector_schema:
        if key not in selectors or not isinstance(selectors[key], str):
            selectors[key] = ""
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        "Accept-Language": "en-US,en;q=0.9"
    }
    soup = BeautifulSoup(html_content, "html.parser")

    for field, selector in selectors.items():
        if not selector:
            continue
        selectors[field] = validate_selector(soup, selector)
    
    with open(selector_path, "w", encoding="utf-8") as f:
        json.dump(selectors, f, indent=2, ensure_ascii=False)
    print(f"Saved product selectors for {domain}")
# product page is use only for testing or generating single product page selectors from listing pages

async def listing_page(llm_cfg, html_content, url, base_dir):
    if not html_content:
        print("No HTML content received, skipping listing selector extraction")
        return

    
    domain = urlparse(url).hostname or "unknown"

    # ----- selector paths -----
    selectors_dir = os.path.join(base_dir, "selectors", domain)
    ensure_dir(selectors_dir)

    listing_selector_path = os.path.join(selectors_dir, "listing_selector.json")
    product_selector_path = os.path.join(selectors_dir, "product_selector.json")

    # ----- listing selector schema -----
    selector_schema = {
        "product_card": "",
        "product_link": "",
        "pagination": ""
    }

    prompt = """
You are an expert CSS selector engineer.

You are given the HTML of an e-commerce LISTING page
(category / collection / search results page).

Your task is to extract STABLE, REUSABLE CSS SELECTORS — NOT DATA.

────────────────────────────────────
ABSOLUTE RULES
────────────────────────────────────
- Output CSS selectors ONLY
- Do NOT extract URLs, text, prices, or product names
- Do NOT use JSON-LD, schema.org, meta tags, or scripts
- Do NOT use XPath
- Do NOT explain anything
- Output must match the schema EXACTLY

────────────────────────────────────
PAGE ASSUMPTIONS
────────────────────────────────────
- The page displays MULTIPLE product tiles/cards
- Each product card links to a product detail page
- Ignore navigation menus, headers, footers, filters, banners, ads

────────────────────────────────────
CRITICAL STABILITY RULES
────────────────────────────────────
- Prefer IDs or data-* attributes when available
- Prefer semantic class names when available
- Avoid nth-child or positional selectors
- Avoid overly generic selectors (div, span, a)

────────────────────────────────────
MANDATORY CSS-MODULE / REACT RULE
────────────────────────────────────
If the page uses CSS-module or hashed class names
(e.g. class="componentName__abc123") AND no stable
IDs or data-* attributes exist:

- You MUST use a prefix-based class selector
  (example: div[class^="componentName_"])
- Treat the class prefix as STABLE and REUSABLE
- Do NOT return empty selectors in this case

────────────────────────────────────
FIELDS TO EXTRACT
────────────────────────────────────

product_card:
- Selector for ONE product tile/card container
- Must match MULTIPLE elements on the page
- Must wrap the product image, title, and link

product_link:
- Selector for the anchor (<a>) leading to the product detail page
- Prefer selector relative to product_card
- If no stable class exists, you MUST use an href-based selector
  that uniquely matches product detail links inside product_card

pagination:
- Selector for the “next page” link or button
- Ignore infinite scroll loaders
- If pagination does not exist, return an empty string

────────────────────────────────────
FAILURE CONDITIONS
────────────────────────────────────
- Only return empty selectors if the page does NOT
  contain repeated product cards

────────────────────────────────────
FINAL OUTPUT FORMAT (STRICT)
────────────────────────────────────
{
  "product_card": "",
  "product_link": "",
  "pagination": "",
  "error": false
}
    """

    llm_config = LLMConfig(
        provider=llm_cfg["provider"],
        api_token=llm_cfg["api_key"],
        base_url=llm_cfg["base_url"]
    )

    llm_strategy = LLMExtractionStrategy(
        llm_config=llm_config,
        schema=selector_schema,
        extraction_type="schema",
        instruction=prompt,
        input_format="html"
    )

    browser_cfg = BrowserConfig(headless=True)
    run_cfg = CrawlerRunConfig(
        extraction_strategy=llm_strategy,
        cache_mode=CacheMode.BYPASS
    )

    async with AsyncWebCrawler(config=browser_cfg) as crawler:
        result = await crawler.arun(url, config=run_cfg)

    if not result or not result.extracted_content:
        print("No listing selectors extracted")
        return

    selectors = json.loads(result.extracted_content)

    if isinstance(selectors, list):
        selectors = selectors[0]

    for key in selector_schema:
        if key not in selectors or not isinstance(selectors[key], str):
            selectors[key] = ""

    with open(listing_selector_path, "w", encoding="utf-8") as f:
        json.dump(selectors, f, indent=2, ensure_ascii=False)

    print(f"✓ Listing selectors saved at: {listing_selector_path}")

    # ----- bootstrap product selector (ONE URL) -----
    if os.path.exists(product_selector_path):
        return

    if not selectors["product_card"] or not selectors["product_link"]:
        print("Cannot bootstrap product selector: missing listing selectors")
        return

    soup = BeautifulSoup(html_content, "html.parser")
    card = soup.select_one(selectors["product_card"])
    if not card:
        return

    link_el = card.select_one(selectors["product_link"])
    if not link_el or not link_el.get("href"):
        return

    product_url = link_el["href"]
    if product_url.startswith("/"):
        product_url = f"https://{domain}{product_url}"

    product_html = await html_collection(product_url, base_dir)
    if not product_html:
        return

    await product_page(llm_cfg, product_html, product_url, base_dir)

    listing_scraper(html_content,selectors,base_dir,product_selector_path)

async def sitemap(sitemap_url, llm_cfg, base_dir):
    import requests
    import random
    import xml.etree.ElementTree as ET

    resp = requests.get(sitemap_url, timeout=20)
    resp.raise_for_status()
    root = ET.fromstring(resp.text)

    ns = {"ns": "http://www.sitemaps.org/schemas/sitemap/0.9"}
    urls = []

    if root.tag.endswith("sitemapindex"):
        for sm in root.findall("ns:sitemap", ns):
            loc = sm.find("ns:loc", ns)
            if loc is not None and loc.text:
                child = requests.get(loc.text.strip(), timeout=20)
                child_root = ET.fromstring(child.text)
                for url in child_root.findall("ns:url", ns):
                    loc2 = url.find("ns:loc", ns)
                    if loc2 is not None and loc2.text:
                        urls.append(loc2.text.strip())

    elif root.tag.endswith("urlset"):
        for url in root.findall("ns:url", ns):
            loc = url.find("ns:loc", ns)
            if loc is not None and loc.text:
                urls.append(loc.text.strip())

    if not urls:
        print("No URLs found in sitemap")
        return

    tried = set()

    while True:
        remaining = list(set(urls) - tried)
        if not remaining:
            print("No more URLs left to try")
            return

        candidate = random.choice(remaining)
        tried.add(candidate)

        print(f"\nSelected URL:\n{candidate}")
        choice = input(
            "Treat this as (p)roduct, (l)isting, or (r)e-do: "
        ).strip().lower()

        if choice == "r":
            continue
        if choice not in ("p", "l"):
            print("Invalid choice")
            continue

        html = await html_collection(candidate, base_dir)
        if not html:
            print("Failed to fetch HTML, re-doing")
            continue

        if choice == "p":
            await product_page(llm_cfg, html, candidate, base_dir)
        else:
            await listing_page(llm_cfg, html, candidate, base_dir)

        print("✓ Sitemap selector generation complete")
        return


# all inputs, no need to make any major changes here if changes made in overall code
async def get_user_input():

    mode = input("Enter product page (p) or lidting page (l): ").lower().strip()
    if mode in ['p','product']:
        crawl_mode = 'product_page'
    elif mode in ['l','list']:
        crawl_mode = 'listing_page'
    elif mode in ['s','sitemap']:
        crawl_mode = 'sitemap'
        # sitemap()
        # return
    else:
        print("ERROR TRY AGAIN")
        return

    while True:
        if crawl_mode == 'sitemap':
            sitemap_url = input("Enter sitemap XML: ")
            break
        else:
            url_input = input("Enter URL (required): ").strip()
            if url_input:
                if url_input.startswith(('http://', 'https://')):
                    url = url_input
                    print(f"✓ URL set: {url}")
                    break
                else:
                    print("Please enter a valid URL starting with http:// or https://")
            else:
                print("URL is required!")
    
    base_dir = input("Enter base output directory [default: /data/web]: ").strip()
    if not base_dir:
        base_dir = '/data/web'
    print(f"✓ Base directory: {base_dir}")

    if crawl_mode != 'sitemap':
        html_content = await html_collection(url_input,base_dir)

    use_llm = input("Enable LLM extraction? (y/n) [default: y]: ").strip().lower()
    if use_llm in ['', 'y', 'yes']:
        llm_cfg = get_llm_config()
        llm_enabled = True
        print("✓ LLM extraction enabled")
        if crawl_mode == 'product_page':
            await product_page(llm_cfg,html_content, url, base_dir)
        elif crawl_mode == 'listing_page':
            await listing_page(llm_cfg,html_content, url, base_dir)
        elif crawl_mode == 'sitemap':

            await sitemap(sitemap_url, llm_cfg, base_dir)
            domain = urlparse(sitemap_url).hostname or "unknown"
            product_selector_path = os.path.join(
                base_dir, "selectors", domain, "product_selector.json"
            )

            if not os.path.exists(product_selector_path):
                print("❌ Product selector not found. Run LLM product page once first.")
                return

            sitemap_scraper(sitemap_url, product_selector_path, base_dir)
    elif use_llm in ['n', 'no']:
        llm_enabled = False
        print("✓ LLM extraction disabled")
        if crawl_mode == 'sitemap':
            domain = urlparse(sitemap_url).hostname or "unknown"
            product_selector_path = os.path.join(
                base_dir, "selectors", domain, "product_selector.json"
            )

            if not os.path.exists(product_selector_path):
                print("❌ Product selector not found. Run LLM product page once first.")
                return

            sitemap_scraper(sitemap_url, product_selector_path, base_dir)

        else:
            # Manual selector logic stays here
            domain = urlparse(url).hostname or "unknown"
            selectors_dir = os.path.join(base_dir, "selectors", domain)
            listing_selector_path = os.path.join(selectors_dir, "listing_selector.json")
            product_selector_path = os.path.join(selectors_dir, "product_selector.json")
            if not os.path.exists(listing_selector_path) or not os.path.exists(product_selector_path):
                print("❌ Selector files not found. Run LLM once first.")
                return
            else:
                with open(listing_selector_path, "r", encoding="utf-8") as f:
                    listing_selectors = json.load(f)
                with open(product_selector_path, "r", encoding="utf-8") as f:
                    product_selectors = json.load(f)
                listing_scraper(html_content, listing_selectors, base_dir, product_selector_path)
    else:
        print("Please enter 'y' for yes or 'n' for no")


if __name__ == "__main__":
    asyncio.run(get_user_input())
