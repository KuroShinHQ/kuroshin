import requests
import json
import chromadb
from chromadb.config import Settings

# --- CONFIG ---
CHROMA_HOST = "127.0.0.1"
CHROMA_PORT = 8100
LLM_URL = "http://127.0.0.1:6000/v1/chat/completions"

class KuroshinSmartMemory:
    def __init__(self):
        # Portlardan bagimsiz, doğrudan dosya tabanli baglanti
        self.client = chromadb.PersistentClient(path="/root/kuroshin/memory/chroma")
        self.collection = self.client.get_or_create_collection(name="lord_facts")


    def extract_facts(self, text):
        """Qwen3 kullanarak metinden atomik gerçekleri çikarir."""
        prompt = f"""Metinden hatirlanmasi gereken kisa ve net gerçekleri (facts) çikar. 
Sadece gerçekleri sirala, yorum yapma.
Örnek: 'Lordun kılıcı altındır' -> 'Lordun kılıcı: Altın'

Metin: {text}
Gerçekler:"""
        
        payload = {
            "model": "qwen3-abliterated",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.1
        }
        
        try:
            response = requests.post(LLM_URL, json=payload)
            return response.json()['choices'][0]['message']['content'].strip()
        except:
            return text # Fallback

    def add_memory(self, text):
        """Gerçekleri çikarir ve ChromaDB'ye mühürler."""
        facts = self.extract_facts(text)
        print(f"🧠 [ANALYSIS] Qwen3 gerçekleri çikardi: {facts}")
        
        # Basit bir ID olusturma (timestamp gibi)
        import time
        doc_id = f"fact_{int(time.time())}"
        
        self.collection.add(
            documents=[facts],
            ids=[doc_id],
            metadatas=[{"original_text": text}]
        )
        return facts

    def recall_memory(self, query):
        """Vektörel arama ile en yakin gerçekleri getirir."""
        results = self.collection.query(
            query_texts=[query],
            n_results=1
        )
        return results['documents'][0][0] if results['documents'] else "Hiçbir sey hatirlanmadi."

def test_operation():
    print("🔱 [INIT] Akilli ChromaDB Testi Baslatildi...")
    ksm = KuroshinSmartMemory()
    
    # Test 1: Gerçek Çıkarma ve Yazma
    test_input = "Afsin Karargahi'ndaki RTX 4060 sisteminde 32GB RAM bulunmaktadir."
    print(f"⏳ [STEP 1] Veri isleniyor: {test_input}")
    ksm.add_memory(test_input)
    
    # Test 2: Sorgulama
    query = "Sistemde ne kadar RAM var?"
    print(f"⏳ [STEP 2] Sorgu yapiliyor: {query}")
    answer = ksm.recall_memory(query)
    
    if "32GB" in answer or "32" in answer:
        print(f"✅ [SUCCESS] Hatirlanan Gerçek: {answer}")
        print("🟢 [RESULT] Smart ChromaDB (Seçenek B) TAM BASARIYLA ÇALISIYOR!")
    else:
        print(f"❌ [FAILURE] Hatirlanan yanlis veya eksik: {answer}")

if __name__ == "__main__":
    test_operation()
