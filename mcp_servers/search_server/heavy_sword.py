import asyncio
from crawl4ai import AsyncWebCrawler, CrawlerRunConfig

async def run():
    url = "https://en.wikipedia.org/wiki/Artificial_intelligence"
    config = CrawlerRunConfig(browser_type="chromium", headless=True)
    async with AsyncWebCrawler() as crawler:
        result = await crawler.arun(url=url, config=config)
        if result.success:
            print("--- KALE DÜŞTÜ ---")
            print(result.markdown[:500])
        else:
            print(f"--- SIZMA BAŞARISIZ: {result.error_message} ---")

if __name__ == "__main__":
    asyncio.run(run())
