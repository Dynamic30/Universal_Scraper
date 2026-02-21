import asyncio
from crawl4ai import AsyncWebCrawler, CrawlerRunConfig
from crawl4ai.deep_crawling import BFSDeepCrawlStrategy, BestFirstCrawlingStrategy, DFSDeepCrawlStrategy
from crawl4ai.content_scraping_strategy import LXMLWebScrapingStrategy
from crawl4ai.deep_crawling.scorers import KeywordRelevanceScorer
import urllib
import base64

async def best_crawl():
        """
        Can add this aswell if needed (need to confirm) -> 
        
        Domain Filter (will filter out which domain need to be added)

        URLPatternFilter 

        ContentTypeFilter

        score_threshold



        
        """
        scorer = KeywordRelevanceScorer(
            # will remove / filter out url with score less than 0.7
            keywords=[],
            weight=0.7
        )

        # Configure the strategy
        configs = CrawlerRunConfig(
            BestFirstCrawlingStrategy(
            max_depth=3,
            include_external=True,
            url_scorer=scorer,
            max_pages=25,            # Maximum number of pages to crawl (optional)
            ),
            scraping_strategy=LXMLWebScrapingStrategy(),
            verbose=True,
            check_robots_txt=False
            

        )

        async with AsyncWebCrawler() as crawler:
            results = await crawler.arun(url='https://www.forestessentialsindia.com/', config=configs)

            print(f"Crawled {len(results)} pages in total")

asyncio.run(best_crawl())