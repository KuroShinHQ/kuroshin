from mem0 import Memory
import time

def test_mem0_qdrant():
    print("⏳ [WAIT] Qdrant'in isinmasi bekleniyor...")
    time.sleep(5)
    
    try:
        config = {
            "vector_store": {
                "provider": "qdrant",
                "config": {
                    "host": "127.0.0.1",
                    "port": 6333,
                }
            }
        }
        m = Memory.from_config(config)
        
        # Test 1: Yazma
        m.add("Lordun gizli parolasi: 'KUROSHIN_2026'", user_id="lord")
        print("✅ [STEP 1] Veri Qdrant'a mühürlendi.")
        
        # Test 2: Arama (Fuzzy/Vektörel)
        result = m.search("Lordun parolasi nedir?", user_id="lord")
        
        if len(result) > 0:
            memory_text = result[0]['memory']
            print(f"🔱 [SUCCESS] Qdrant'tan gelen anı: {memory_text}")
            print("🟢 [RESULT] Mem0 + Qdrant sistemi TAM OTONOM çalisiyor!")
        else:
            print("❌ [FAILURE] Qdrant aniyi hatirlayamadi.")
            
    except Exception as e:
        print(f"❌ [ERROR] Operasyon Hatasi: {str(e)}")

if __name__ == "__main__":
    test_mem0_qdrant()
