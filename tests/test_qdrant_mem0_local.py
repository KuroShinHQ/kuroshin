from mem0 import Memory
import time
import os

def test_mem0_local_qdrant():
    print("⏳ [WAIT] Yerel Mem0 + Qdrant sistemi hazirlaniyor...")
    
    # LiteLLM üzerinden yerel modelimizi kullanması için config
    config = {
        "llm": {
            "provider": "openai",
            "config": {
                "model": "gemma4",
                "api_key": "sk-not-needed", # Sahte key
                "openai_base_url": "http://127.0.0.1:6000/v1" # LiteLLM portun
            }
        },
        "embedder": {
            "provider": "ollama", # Yerel embedding için en kolayı
            "config": {
                "model": "nomic-embed-text",
                "base_url": "http://127.0.0.1:11434" # Eğer Ollama kuruluysa
            }
        },
        "vector_store": {
            "provider": "qdrant",
            "config": {
                "host": "127.0.0.1",
                "port": 6333,
            }
        }
    }
    
    # Eğer Ollama yoksa, HuggingFace yerel embedding'e geçelim
    # Şimdilik en basit yerel test için sadece LLM'i LiteLLM'e yönlendiriyoruz.
    
    try:
        m = Memory.from_config(config)
        m.add("Lordun en sevdigi renk: Siyah", user_id="lord")
        print("✅ [STEP 1] Veri yerel olarak islendi.")
        
        result = m.search("Lord neyi sever?", user_id="lord")
        if len(result) > 0:
            print(f"🔱 [SUCCESS] Hatirlanan: {result[0]['memory']}")
        else:
            print("❌ [FAILURE] Yerel hafıza boş döndü.")
            
    except Exception as e:
        print(f"❌ [ERROR] Yerel Test Hatasi: {str(e)}")

if __name__ == "__main__":
    test_mem0_local_qdrant()
