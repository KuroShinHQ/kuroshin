import asyncio
from crawl4ai import AsyncWebCrawler

async def run():
    url = "https://en.wikipedia.org/wiki/Artificial_intelligence"
    async with AsyncWebCrawler() as crawler:
        # Default config with minimal parameters for maximum compatibility
        result = await crawler.arun(url=url)
        if result.success:
            print("--- KALE DÜŞTÜ: ZAFER KUROSHIN'İNDİR ---")
            print(result.markdown[:500])
        else:
            print(f"--- SIZMA BAŞARISIZ: {result.error_message} ---")

if __name__ == "__main__":
    asyncio.run(run())
