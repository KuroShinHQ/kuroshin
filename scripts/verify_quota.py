import sys
import os
from pathlib import Path

# Yolları ekle
sys.path.insert(0, "C:/Kuroshin/scripts")
import traffic_manager
import auto_integrator as ai

def test_scenario():
    print("--- SENARYO 1: SİSTEM DURAKLATILDI ---")
    traffic_manager.set_paused(True)
    traffic_manager.set_limit(0.01) # 10MB
    
    test_item = {"id": "test_model", "name": "Test 1GB Model", "vram_gb": 1.0, "type": "model", "source": "HF"}
    
    ok, reason = traffic_manager.check_quota(test_item['vram_gb'])
    print(f"Sonuç: {ok}, Sebep: {reason}")
    
    print("\n--- SENARYO 2: SİSTEM AKTİF AMA KOTA YETERSİZ (1GB Model) ---")
    traffic_manager.set_paused(False)
    ok, reason = traffic_manager.check_quota(test_item['vram_gb'])
    print(f"Sonuç: {ok}, Sebep: {reason}")

    print("\n--- SENARYO 3: SİSTEM AKTİF, KOTA YETERLİ (5MB Model) ---")
    small_item = {"id": "small_model", "name": "Test 5MB Model", "vram_gb": 0.005, "type": "model", "source": "HF"}
    ok, reason = traffic_manager.check_quota(small_item['vram_gb'])
    print(f"Sonuç: {ok}, Sebep: {reason}")
    if ok:
        print("İşlem: Lord'a onay sorusu gönderilecek (indirme hemen başlamaz).")

if __name__ == "__main__":
    test_scenario()
