from mem0 import Memory
import os

def test_mem0_chroma():
    try:
        config = {
            "vector_store": {
                "provider": "chromadb",
                "config": {
                    "host": "127.0.0.1",
                    "port": 8100,
                }
            }
        }
        m = Memory.from_config(config)
        m.add("Kuroshin Imparatorlugu 25 Nisan 2026'da kuruldu.", user_id="lord")
        result = m.search("Imparatorluk ne zaman kuruldu?", user_id="lord")
        if len(result) > 0:
            print("🔱 [SUCCESS] Mem0 ChromaDB baglantisi ve hafiza yazimi basarili!")
        else:
            print("❌ [FAILURE] Mem0 veri kaydedemedi veya bulamadi.")
    except Exception as e:
        print(f"❌ [ERROR] Mem0 Hatasi: {str(e)}")

if __name__ == "__main__":
    test_mem0_chroma()
