import httpx
import time
import subprocess
import json

def run_test():
    print("🔱 --- KUROSHIN v4.3.1 NUCLEAR STRESS TEST --- 🔱\n")
    
    # Wait for engine to warm up
    time.sleep(3)
    
    scenarios = [
        ("SIMPLE", "Current CEO of Microsoft"),
        ("MEDIUM", "NVIDIA RTX 5090 Blackwell leaks")
    ]
    
    for level, query in scenarios:
        print(f"[{level}] Testing: {query}")
        try:
            resp = httpx.get(f"http://localhost:8080/search?q={query.replace(' ', '+')}", timeout=10.0)
            if resp.status_code == 200:
                results = resp.json().get('results', [])
                print(f"STATUS: SUCCESS - Found {len(results)} news items.")
                for i, r in enumerate(results[:2], 1):
                    print(f"  {i}. {r['title'][:80]}...")
            else:
                print(f"STATUS: FAILED (HTTP {resp.status_code})")
        except Exception as e:
            print(f"STATUS: ERROR ({str(e)})")
        print("-" * 50)

    # COMPLEX TEST: Crawl4AI Deep Read
    print("[COMPLEX] Action: Deep Scrape via Crawl4AI Force...")
    target_url = "https://www.theverge.com" # Reliable target for test
    cmd = f"wsl -d Ubuntu-22.04 -- bash -c \"source /root/kuroshin/venv/bin/activate && python3 -c 'import asyncio; from crawl4ai import AsyncWebCrawler; async def run(): async with AsyncWebCrawler() as crawler: result = await crawler.arun(url=\\\"{target_url}\\\"); print(result.markdown[:300]); asyncio.run(run())'\""
    
    try:
        output = subprocess.check_output(cmd, shell=True, stderr=subprocess.STDOUT).decode()
        print(f"STATUS: SUCCESS - Crawl4AI penetrated target!\nCONTENT PREVIEW:\n{output}...")
    except Exception as e:
        print(f"STATUS: COMPLEX FAILED (Crawl4AI might need playwright install or path check)")

if __name__ == "__main__":
    run_test()
