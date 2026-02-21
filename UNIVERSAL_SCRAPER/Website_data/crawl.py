"""

Gets Html from a website and get it in markdown json foramt, screenshots and save it
in crawl sub folder 

so this is folder structure 
crawl->
    date
        clean_html
        markdown
        Links.json
        Screenshots


"""

import asyncio
from crawl4ai import AsyncWebCrawler, CrawlerRunConfig
from crawl4ai.deep_crawling import BFSDeepCrawlStrategy, BestFirstCrawlingStrategy, DFSDeepCrawlStrategy
from crawl4ai.content_scraping_strategy import LXMLWebScrapingStrategy
from crawl4ai.deep_crawling.scorers import KeywordRelevanceScorer
import urllib
import base64
from CSV_Gen.save_data import html_default, markdown_collection,pdf_data,screenshot_data,metadata_data,json_data

def crawl_main(url,base_dir):


    async def breadth_crawl():
        config = CrawlerRunConfig(
            deep_crawl_strategy=BFSDeepCrawlStrategy(
                max_depth=20, 
                include_external=False,
                max_pages=2,
                score_threshold=0.3,
                ),
                screenshot=True,
                pdf=True,

                scraping_strategy=LXMLWebScrapingStrategy(),
                verbose=True,
                check_robots_txt=False

            )

        async with AsyncWebCrawler() as crawler:
            results = await crawler.arun(url, config=config)
            
            print(f"Crawled {len(results)} pages in total")

    async def depth_crawl():
        config = CrawlerRunConfig(
        deep_crawl_strategy=DFSDeepCrawlStrategy(
            max_depth=10,
            max_pages=50,
            score_threshold=0.3,
            include_external=False
        ),
        scraping_strategy=LXMLWebScrapingStrategy(),
        verbose=True
    )

        async with AsyncWebCrawler() as crawler:
            results = await crawler.arun(url, config=config)

            print(f"Crawled {len(results)} pages in total")
            print(results)

    async def best_crawl(url,keywords):
        """
        Can add this aswell if needed (need to confirm) -> 
        
        Domain Filter (will filter out which domain need to be added)

        URLPatternFilter 

        ContentTypeFilter

        score_threshold



        
        """
        scorer = KeywordRelevanceScorer(
            # will crawl all the urls but gives preference to the one whose score is more than weight (it does that using keywords given)
            keywords=keywords,
            weight=0.7
        )

        # Configure the strategy
        configs = CrawlerRunConfig(
            deep_crawl_strategy=BestFirstCrawlingStrategy(
            max_depth=3,
            include_external=True,
            url_scorer=scorer,
            max_pages=25,            # Maximum number of pages to crawl (optional)
            ),
            scraping_strategy=LXMLWebScrapingStrategy(),
            verbose=True,
            check_robots_txt=False,
            pdf=True,
            screenshot=True,
            scan_full_page=True,
            wait_for_images=True
            # page_timeout=
            
            

        )

        async with AsyncWebCrawler() as crawler:
            results = await crawler.arun(url, config=configs)
            for r in results:
                urls_data = r.url
                html = r.cleaned_html
                md = r.markdown 
                json_txt = r.model_dump(exclude={'pdf', 'screenshot'})
                meta = r.metadata
                pdf_str = r.pdf
                screenshot_str=r.screenshot
                html_default(urls_data,base_dir,html)
                markdown_collection(urls_data,base_dir,md)
                pdf_data(urls_data,base_dir,pdf_str)
                metadata_data(urls_data,base_dir,meta)
                json_data(urls_data,base_dir,json_txt)
                screenshot_data(urls_data, base_dir,screenshot_str)

            print(f"Crawled {len(results)} pages in total")


    while True:
        crawl = int(input("1) breadth_crawl\n2) depth_crawl\n3) best_crawl"))
        if crawl == 1:
            asyncio.run(breadth_crawl())
            break
        elif crawl == 2:
            asyncio.run(depth_crawl())
            break
        elif crawl == 3:
            keywords = input("").split()
            asyncio.run(best_crawl(url,keywords))
            break
    
    

crawl_main(url="https://www.samsung.com/",base_dir="/mnt/c/Users/Aryan/Desktop/Pristine-Forrest/scraping/PF-SCRAPED-DATA/New_data_organised")

# https://www.websitecrawler.org/