from mem0 import Memory
import os

def kuroshin_smart_memory_test():
    print("🔱 [INIT] Kuroshin Akilli Hafiza Testi Baslatildi...")
    
    # Gemma 4 (8080) hem LLM hem de Embedding motoru olarak kullaniliyor
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
                "model": "sentence-transformers/all-MiniLM-L6-v2", # Ultra-hafif ve hızlı
            }
        },

        "vector_store": {
            "provider": "qdrant",
            "config": {
                "path": "/root/kuroshin/qdrant_data", # Yerel dosya modu
            }
        }

    }

    try:
        m = Memory.from_config(config)
        # Qdrant client compatibility fix for WSL
        m.vector_store.client._check_compatibility = False

        
        # Test 1: Kalıcı Bilgi Ekleme
        print("⏳ [STEP 1] Gemma 4 aniyi analiz ediyor ve Qdrant'a yaziyor...")
        m.add("Kuroshin Imparatorlugu'nun baskenti Afsin Karargahi'dir.", user_id="lord")
        
        # Test 2: Hatırlama
        print("⏳ [STEP 2] Gemma 4 hafizayi sorguluyor...")
        result = m.search("Karargah neresidir?", user_id="lord")
        
        if len(result) > 0:
            memory_text = result[0]['memory']
            print(f"✅ [SUCCESS] Gemma 4 hatirladi: {memory_text}")
            print("🟢 [RESULT] Mem0 + Qdrant + Gemma 4 hibrit yapisi ÇALISIYOR!")
        else:
            print("❌ [FAILURE] Gemma 4 aniyi Qdrant'tan çekemedi.")
            
    except Exception as e:
        print(f"❌ [ERROR] Cerrahi Hata: {str(e)}")

if __name__ == "__main__":
    kuroshin_smart_memory_test()
