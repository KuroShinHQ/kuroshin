#!/usr/bin/env python3
"""
🔱 DEERFLOW CORE v2.1 - OTONOM WEB GÖZCÜSÜ 🔱
=============================================
Lord Kuroshin_user'ın emriyle internetin derinliklerinde avlanır.
Placeholder veriler imha edildi, gerçek otonom arama aktifleştirildi.
"""

import asyncio
import re
import time
import argparse
import sys
import os
import httpx
from ddgs import DDGS
from crawl4ai import AsyncWebCrawler, CrawlerRunConfig
from crawl4ai.content_filter_strategy import PruningContentFilter
from crawl4ai.markdown_generation_strategy import DefaultMarkdownGenerator

async def get_weather(city):
    """Hava durumu istihbaratı (Hızlı Erişim)"""
    try:
        import subprocess
        result = subprocess.run(['curl', '-s', f'wttr.in/{city}?format=%l:+%t+%C+%w&lang=tr'],
                                capture_output=True, text=True, timeout=10)
        if result.returncode == 0 and result.stdout.strip():
            return f"🌍 {city.upper()} HAVA DURUMU:\n{result.stdout.strip()}\n🕒 {time.strftime('%d.%m.%Y %H:%M')}"
        return f"⚠️ {city} için hava durumu verisi alınamadı."
    except Exception as e:
        return f"❌ Hava durumu hatası: {e}"

async def smart_analyze_content(content, task, url):
    """LitAI Router ile İstihbarat Özeti (otomatik retry + fallback)"""
    analysis_prompt = f"""Sen Kuroshin İmparatorluğu'nun Baş İstihbarat Uzmanısın.

KULLANİCİ GÖREVI: {task}
KAYNAK: {url}

Aşağıdaki ham web içeriğini analiz et ve sadece görevle ilgili NET BİLGİLERİ çıkar:
- Menü, navigasyon, reklam, footer metinlerini yoksay
- Sadece görevdeki konuyla ilgili asıl içeriği özetle
- En fazla 3 paragrafta net sonuç ver

HAM İÇERİK:
{content[:4000]}

UYARI: Eğer içerikte görevle ilgili hiçbir net bilgi yoksa "İlgili bilgi bulunamadı" de."""

    messages = [{"role": "user", "content": analysis_prompt}]

    # LitAI Router: LiteLLM (6000) önce, başarısız olursa llama-server (8080) direkt
    endpoints = [
        ("http://127.0.0.1:6000/v1", "LiteLLM"),
        ("http://127.0.0.1:8080/v1", "llama-server"),
    ]

    async with httpx.AsyncClient() as client:
        for base_url, name in endpoints:
            for attempt in range(1, 4):
                try:
                    response = await client.post(
                        f"{base_url}/chat/completions",
                        headers={"Authorization": "Bearer kuroshin-secret", "Content-Type": "application/json"},
                        json={"model": "qwen3-abliterated", "messages": messages, "max_tokens": 512, "temperature": 0.1},
                        timeout=30.0
                    )
                    if response.status_code == 200:
                        msg = response.json()["choices"][0]["message"]
                        result = (msg.get("reasoning_content", "") or msg.get("content", "")).strip()
                        if result and len(result) >= 10:
                            return result
                except Exception:
                    if attempt < 3:
                        await asyncio.sleep(1.5 * attempt)

    return f"📄 {task} konusunda {url} sitesinde analiz tamamlanamadı."

async def deep_research(task):
    """Otonom Derin Araştırma (DuckDuckGo + Crawl4AI)"""
    print(f"🔍 [DEERFLOW] Hedef Belirlendi: {task}")
    
    try:
        # 1. Arama Safhası
        with DDGS() as ddgs:
            search_results = list(ddgs.text(task, max_results=3))
        
        if not search_results:
            return "İmparatorluk istihbaratı: Bu konuda açık kaynaklarda bir iz bulunamadı."

        # 2. Derin Okuma Safhası (En iyi sonucu seç)
        top_url = search_results[0].get('href')
        print(f"📖 [DEERFLOW] En iyi kaynak okunuyor: {top_url}")
        
        run_cfg = CrawlerRunConfig(
            markdown_generator=DefaultMarkdownGenerator(
                content_filter=PruningContentFilter(
                    threshold=0.48,
                    threshold_type="fixed",
                    min_word_threshold=10,
                ),
                options={
                    "ignore_links": True,
                    "ignore_images": True, 
                    "body_width": 120,
                    "ignore_tables": False,
                    "extract_main_content": True
                }
            ),
            page_timeout=15000,
            exclude_external_links=True,
            exclude_social_media_links=True,
            remove_overlay_elements=True,
            word_count_threshold=50,
            only_text=False
        )
        
        async with AsyncWebCrawler(verbose=False) as crawler:
            crawl_result = await crawler.arun(url=top_url, config=run_cfg)
            
            if crawl_result.success:
                raw_content = crawl_result.markdown or ""
                print(f"🧠 [DEERFLOW] Ham veri analiz ediliyor...")
                
                # 3. LLM İle İstihbarat Analizi
                analyzed_content = await smart_analyze_content(raw_content, task, top_url)
                
                report = (
                    f"🦌 DEERFLOW İSTİHBARAT RAPORU\n"
                    f"===============================\n"
                    f"🎯 Görev: {task}\n"
                    f"🔗 Kaynak: {top_url}\n\n"
                    f"📄 NET İSTİHBARAT:\n{analyzed_content}\n\n"
                    f"✅ İstihbarat analizi tamamlandı."
                )
                return report
            else:
                return f"❌ Kaynak okunamadı, ancak arama sonucu: {search_results[0].get('body')}"

    except Exception as e:
        return f"❌ Derin araştırma sırasında kaza oluştu: {e}"

async def main():
    parser = argparse.ArgumentParser(description='DeerFlow Core')
    parser.add_argument('--task', required=True, help='Aranacak görev')
    args = parser.parse_args()
    
    task_lower = args.task.lower()
    
    # Özel Görev: Sistem Başlatma
    if "sistem başlatma" in task_lower:
        print("🟢 DeerFlow Gözcü Birimi Hazır ve Nazır, Lordum!")
        return

    # Hava Durumu Kontrolü
    if any(w in task_lower for w in ['hava','weather','meteoroloji','sıcaklık','derece']):
        city = re.sub(r'(hava|durumu|sıcaklık|derece|nedir|nasıl|weather|temperature|için)', '', task_lower).strip()
        city = city if city else 'Istanbul'
        result = await get_weather(city)
    else:
        # Genel Araştırma
        result = await deep_research(args.task)
    
    print("\n" + result)

if __name__ == '__main__':
    asyncio.run(main())
