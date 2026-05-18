import asyncio
import subprocess

async def test_hybrid():
    print("--- [HYBRID PROOF: RSS SEARCH + CRAWL4AI READ] ---")
    # Step 1: Simulated RSS Search Result
    target_url = "https://www.notebookcheck.net/NVIDIA-GeForce-RTX-5090-specs-leak.890000.0.html"
    print(f"TARGET ACQUIRED: {target_url}")
    
    # Step 2: Trigger Crawl4AI via WSL Bridge
    print("ACTION: Triggering Crawl4AI Force...")
    cmd = f"wsl -d Ubuntu-22.04 -- bash -c \"source /root/kuroshin/venv/bin/activate && python3 -c 'import asyncio; from crawl4ai import AsyncWebCrawler; async def run(): async with AsyncWebCrawler() as crawler: result = await crawler.arun(url=\\\"{target_url}\\\"); print(result.markdown[:500]); asyncio.run(run())'\""
    
    process = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    stdout, stderr = process.communicate()
    
    if stdout:
        print(f"ZAFER: Data retrieved via Crawl4AI!\nCONTENT PREVIEW:\n{stdout}")
        return True
    else:
        print(f"HATA: {stderr}")
        return False

if __name__ == "__main__":
    asyncio.run(test_hybrid())
