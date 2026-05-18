#!/usr/bin/env python3

import sys
import asyncio
sys.path.append('/mnt/c/Kuroshin/src')

from agents.deerflow.deerflow_core import DeerFlowCore

async def test_deerflow():
    deerflow = None
    try:
        print("DeerFlow Core testi başlatılıyor...")
        
        deerflow = DeerFlowCore()
        print("✓ DeerFlowCore sınıfı başlatıldı")
        
        test_url = "https://httpbin.org/html"
        print(f"Test URL'si işleniyor: {test_url}")
        
        result = await deerflow.process_url(test_url)
        
        if "Hata:" not in result:
            print("✓ Test başarılı! DeerFlow Core çalışıyor.")
        else:
            print("✗ Test başarısız:", result)
            
    except Exception as e:
        print(f"✗ Test hatası: {str(e)}")
    finally:
        if deerflow:
            await deerflow.close()

if __name__ == "__main__":
    asyncio.run(test_deerflow())