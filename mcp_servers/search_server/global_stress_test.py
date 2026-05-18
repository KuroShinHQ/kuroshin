# -*- coding: utf-8 -*-
import sys
import io
from googlesearch import search
import httpx
from bs4 import BeautifulSoup
import re

# English UTF-8 Bypass
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

def run_test(scenario_name, query, fetch=False):
    print(f"\n--- [SCENARIO: {scenario_name}] ---")
    print(f"QUERY: {query}")
    try:
        # Global Search (Advanced=True, no lang)
        results = list(search(query, num_results=3, advanced=True))
        
        if not results:
            print("Search returned 0 results. (Agentic Feedback Triggered)")
            return

        for i, r in enumerate(results):
            # English Labels (UTF-8 Bypass)
            print(f"SEARCH_RESULT [{i+1}]:")
            print(f"TITLE: {r.title}")
            print(f"URL: {r.url}")
            print(f"SNIPPET: {r.description}")
            print("---")
            
        if fetch and results:
            target_url = results[0].url
            print(f"\n[COMPLEX STEP: FETCHING {target_url}]")
            headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
            with httpx.Client(follow_redirects=True, timeout=15.0) as client:
                resp = client.get(target_url, headers=headers)
                resp.raise_for_status()
                soup = BeautifulSoup(resp.text, "html.parser")
                for e in soup(["script", "style", "nav", "footer"]): e.extract()
                text = re.sub(r"\n+", "\n", soup.get_text())
                print(f"FETCH_SUCCESS: Content Summary (200 chars):\n{text[:200].strip()}...")

    except Exception as e:
        print(f"Search engine error: {str(e)}")

if __name__ == "__main__":
    # Test 1: Simple
    run_test("SIMPLE", "Current CEO of Google")
    # Test 2: Medium
    run_test("MEDIUM", "NVIDIA RTX 5090 release date rumors 2025")
    # Test 3: Complex
    run_test("COMPLEX", "MCP Python SDK core concepts", fetch=True)
