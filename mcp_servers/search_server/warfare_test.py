import asyncio
import httpx
import subprocess
import sys
import io

sys.stdout.reconfigure(encoding="utf-8")

async def test_warfare():
    target_url = "https://en.wikipedia.org/wiki/Artificial_intelligence"
    print(f"🔱 HEDEF BELİRLENDİ: {target_url}\n")

    # ADIM 1: KALKAN (Standard Fetch)
    print("🛡️ [ADIM 1: KALKAN] Sızma deneniyor...")
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(target_url, headers=headers)
            print(f"DURUM: HTTP {resp.status_code}")
            if resp.status_code != 200:
                print("💥 SONUÇ: KALKAN DÜŞTÜ! Erişim engellendi.")
            else:
                print("✅ SONUÇ: Kalkan sızmayı başardı (Beklenmeyen başarı).")
    except Exception as e:
        print(f"💥 HATA: {e}")

    print("-" * 50)

    # ADIM 2: KILIÇ (Crawl4AI Force)
    print("⚔️ [ADIM 2: KILIÇ] Balyoz darbesi indiriliyor (Crawl4AI)...")
    # WSL Bridge üzerinden Playwright'ı tetikliyoruz
    cmd = f"wsl -d Ubuntu-22.04 -- bash -c \"source /root/kuroshin/venv/bin/activate && python3 -c 'import asyncio; from crawl4ai import AsyncWebCrawler; async def run(): async with AsyncWebCrawler() as crawler: result = await crawler.arun(url=\\\"{target_url}\\\"); print(result.markdown[:500]); asyncio.run(run())'\""
    
    try:
        process = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        stdout, stderr = process.communicate()
        
        if stdout:
            print("👑 ZAFER! KALE DÜŞTÜ! Crawl4AI içeri sızdı.")
            print(f"İÇERİK ÖNİZLEME:\n{stdout.strip()}...")
        else:
            print(f"❌ BOZGUN! Kılıç kırıldı. Hata: {stderr}")
    except Exception as e:
        print(f"❌ KRİTİK SAVAŞ HATASI: {e}")

if __name__ == "__main__":
    asyncio.run(test_warfare())
