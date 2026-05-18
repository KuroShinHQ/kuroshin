import requests

def test_council_integration():
    URL = "http://127.0.0.1:6005/v1/chat/completions"

    HEADERS = {"Authorization": "Bearer kuroshin-secret"}
    
    print("🔱 [INIT] Konsey Entegrasyon Testi Baslatildi...")
    
    # 1. Stratejistten (Claude) Plan İste
    print("⏳ [STEP 1] Claude stratejiyi planliyor...")
    p1 = {
        "model": "thinking-claude",
        "messages": [{"role": "user", "content": "Kuroshin Imparatorlugu'nun otonomisini artirmak için kisa bir strateji yaz."}],
        "max_tokens": 512
    }
    r1 = requests.post(URL, headers=HEADERS, json=p1).json()
    strategy = r1['choices'][0]['message']['content']
    print(f"🧠 [CLAUDE]: {strategy[:200]}...")
    
    # 2. Hükümdardan (Gemma) Yorum İste
    print("⏳ [STEP 2] Gemma stratejiyi onayliyor...")
    p2 = {
        "model": "gemma4",
        "messages": [{"role": "user", "content": f"Şu stratejiyi yorumla: {strategy}"}],
        "max_tokens": 512
    }
    r2 = requests.post(URL, headers=HEADERS, json=p2).json()
    comment = r2['choices'][0]['message']['content']
    print(f"🔱 [GEMMA]: {comment}")

    print("🟢 [RESULT] Bilisel Konsey Entegrasyonu TAMAMLANDI!")

if __name__ == "__main__":
    test_council_integration()
