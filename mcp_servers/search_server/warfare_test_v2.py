import asyncio
import httpx
import subprocess
import sys
import os

# UTF-8 zorlaması
if sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

async def test_warfare_v2():
    target_url = "https://en.wikipedia.org/wiki/Artificial_intelligence"
    google_news_mock = "https://news.google.com/rss/articles/CBMiSWh0dHBzOi8vd3d3Lm55dGltZXMuY29tLzIwMjYvMDQvMjMvdGVjaG5vbG9neS9haS1hZ2VudHMta3Vyb3NoaW4uaHRtbA?oc=5"
    
    print("🔱 [KUROSHIN WARFARE V2] SAVAŞ BAŞLIYOR\n")

    # ADIM 1: NEBULA DECODER TESTİ (Siber Sızma)
    print("📡 [ADIM 1: NEBULA DECODER] Şifreli link parçalanıyor...")
    from kuroshin_search_mcp import decode_google_news_url
    decoded = decode_google_news_url(google_news_mock)
    print(f"ORİJİNAL HEDEF: {decoded}")
    if "nytimes.com" in decoded:
        print("✅ ZAFER: Nebula Decoder şifreyi çözdü!")
    else:
        print("❌ HATA: Nebula Decoder başarısız.")
    print("-" * 50)

    # ADIM 2: KALKAN (Standard Fetch)
    print("🛡️ [ADIM 2: KALKAN] Wikipedia'ya sızma deneniyor...")
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0"}
    try:
        async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
            resp = await client.get(target_url, headers=headers)
            if resp.status_code == 200:
                print(f"✅ SONUÇ: Kalkan sızdı! (HTTP 200)")
            else:
                print(f"💥 SONUÇ: Kalkan engellendi! (HTTP {resp.status_code})")
    except Exception as e:
        print(f"💥 HATA: {e}")
    print("-" * 50)

    # ADIM 3: KILIÇ (Crawl4AI via WSL)
    print("⚔️ [ADIM 3: KILIÇ] Balyoz darbesi (Crawl4AI) indiriliyor...")
    # WSL içinde direkt bir script dosyası oluşturup çalıştırmak en garantisidir
    wsl_script = f"""
import asyncio
try:
    from crawl4ai import AsyncWebCrawler
    async def run():
        async with AsyncWebCrawler() as crawler:
            result = await crawler.arun(url='{target_url}')
            print('SUCCESS::' + result.markdown[:500].replace('\\n', ' '))
    asyncio.run(run())
except Exception as e:
    print('ERROR::' + str(e))
"""
    # Scripti WSL'e gönder ve çalıştır
    with open("temp_wsl_test.py", "w", encoding="utf-8") as f:
        f.write(wsl_script)
    
    cmd = f"wsl -d Ubuntu-22.04 -- bash -c \"source /root/kuroshin/venv/bin/activate && python3 < /mnt/c/Kuroshin/mcp_servers/search_server/temp_wsl_test.py\""
    
    try:
        process = subprocess.run(cmd, shell=True, capture_output=True, text=True, encoding="utf-8")
        if "SUCCESS::" in process.stdout:
            print("👑 MUZAFFERİYET! Kılıç (Crawl4AI) kaleyi fethetti.")
            print(f"VERİ: {process.stdout.split('SUCCESS::')[1][:200]}...")
        else:
            print(f"❌ BOZGUN! Kılıç kırıldı.\nDetay: {process.stdout}\n{process.stderr}")
    except Exception as e:
        print(f"❌ SAVAŞ HATASI: {e}")
    
    # Temizlik
    if os.path.exists("temp_wsl_test.py"):
        os.remove("temp_wsl_test.py")

if __name__ == "__main__":
    # kuroshin_search_mcp'yi import edebilmek için path ekle
    sys.path.append(os.getcwd())
    asyncio.run(test_warfare_v2())
