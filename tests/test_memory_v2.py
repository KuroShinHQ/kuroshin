from mem0 import Memory
import os

def kuroshin_final_victory_test():
    print("🔱 [FINAL] Hafiza Sistemi Yeniden Baslatiliyor...")
    
    config = {
        "llm": {
            "provider": "openai",
            "config": {
                "model": "gemma4",
                "api_key": "kuroshin-secret",
                "openai_base_url": "http://127.0.0.1:8080/v1"
            }
        },
        "embedder": {
            "provider": "huggingface",
            "config": {
                "model": "sentence-transformers/all-MiniLM-L6-v2",
            }
        },
        "vector_store": {
            "provider": "qdrant",
            "config": {
                "path": "/root/kuroshin/qdrant_data_v2",
            }
        }
    }

    try:
        # Yeni dizinle tertemiz baslangiç
        m = Memory.from_config(config)
        m.vector_store.client._check_compatibility = False
        
        print("⏳ [STEP 1] Mühürleme basladi...")
        m.add("Lordun gizli sifrsi: 'NEBULA_GAUNTLET'", user_id="lord")
        
        print("⏳ [STEP 2] Hatirlama basladi...")
        result = m.search("Sifre nedir?", user_id="lord")
        
        if len(result) > 0:
            memory_text = result[0]['memory']
            print(f"✅ [SUCCESS] Hatirlanan: {memory_text}")
            print("🟢 [RESULT] FAZ A2.1 BASARIYLA TAMAMLANDI!")
        else:
            print("❌ [FAILURE] Hafiza boş döndü.")
            
    except Exception as e:
        print(f"❌ [ERROR] Kritik Hata: {str(e)}")

if __name__ == "__main__":
    kuroshin_final_victory_test()
