# master code, will be used to navigate to different part of codes 
from Website_data.lighthouse import lighthouse
from Website_data.crawl import crawl_main
"""
Features :
    Web Crawler
    Scrape (diff from csv scraper)
    CSV+Selector Generation
    lighthouse









    not added 

    Branding (feature -> similar to firecrawl/will work on domain only)



"""

"""will navigate to following based on command -> [csv + selector generation, crawling web pages, webpage search using rag, etc.)"""

url = input("Enter URL: ").strip()
base_dir = input("Enter path:").strip()

while True:
    select = input("1) CSV+Selector Generation\n2) Crawl WebPage\n3) lighthouse\n4) Agentic Search\n5) Map \nEnter Choice (1/2/3/4):").strip()
    if select == '1':
        mode = "CSV+SELECTOR GENERATION"
        print(mode)
        crawl_main(url,base_dir)
        break
    elif select == '2':
        mode = "Crawl WebPage"
        print(mode)
        break
    elif select == '3':
        mode = "lighthouse"
        print(mode)
        lighthouse(url,base_dir)
        break
    elif select == '4':
        mode = "Agentic Search"
        print(mode)
        break
    else:
        print("Choose from the above options")



if mode == "Agentic Search":
    print("")
elif mode == "Crawl WebPage":
    print("")
elif mode == "CSV+SELECTOR GENERATION":
    print("")




"""
    Base Directory structure

Base_dir
    raw (used for csv)
        date
            website
                html
                    url.html
    clean (used for csv)
        date
            website
                html
                    url.html
    selectors
        website
            product_selector.json
            listing_selector.json
    csv
        date
            website
                csv

    crawl
        /date
            Seed-URL
                Crawled URL
                    all-urls.json
                    exteranl.json
                    internal.json
    /Data
        /date
            /Website
                /html -> /url -> html
                /markdown -> /url -> md
                /json -> /url -> json
                /metadata /url -> json
                /Screenshots -> /url -> screenshots
                /PDFs -> /url -> pdf
                /lighthouse -> /url -> lighhouse.html


    LLM-Search/Agentic-search # (not a sub folder but feature)
    Branding (feature)
    All URLs 



    =========================================


        website
            Sitemap.json
            /date
                /Internal Links
                    Inter-Links.json
                    /url
                        Sitemap.json

                /Outer links (need to be discussed)
                    Out-links.json
                    /url
                        clean_html.html
                        markdown
                        /Screenshots
                        PDF




"""


# EXTERNAL INTRESTING FEATURES TO ADD 


"""


==================================Site-Wide Intelligence (Domain-Level Analysis)=====================================================
1.  Tech Stack Fingerprinting

        Detect what a domain is built with.

        Frameworks (React, Next, Vue, Svelte)

        CMS (WordPress, Shopify, Ghost)

        Analytics, ads, CDNs, fonts

        Backend hints (headers, cookies)

        Why it’s interesting

        Useful for sales, security, SEO, competitor analysis

        Complements Lighthouse well

        Open-source inspiration

        Wappalyzer (core logic is open)

        BuiltWith-style detection (regex + DOM + headers)

2.  SEO & Search Visibility Scanner

        Not Lighthouse, but crawl-based SEO diagnostics:

        Meta tags coverage

        Canonical correctness

        H1/H2 structure across pages

        Broken internal links

        Sitemap vs crawled URL diff

        Indexability flags (robots, noindex)

        Bonus

        Generate SEO score per domain

        Export as CSV / JSON

3.  Internal Link Graph & PageRank

        Build a domain link graph:

        Page importance score (PageRank-like)

        Orphan pages

        Crawl depth heatmap

        Hub pages

        Why it’s cool

        Very visual

        LLMs can query the graph later

        Open-source ideas

        NetworkX

        Graphviz / D3 exports



"""