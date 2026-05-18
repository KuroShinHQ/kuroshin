"""Hatalı ChromaDB kayıtlarını temizle."""
import chromadb

# Temizlenecek kalıplar: hava durumu uydurma + tool çıktısı kontaminasyonu
BAD_PATTERNS = [
    "hava güzel", "hava çok güzel", "hava durumu",
    "walker servisi", "port 9002", "port 9004", "servis çalışıyor",
    "servis başlatıldı", "health check", "⚙️",
    "kuroshin:", "kuroshin_user:",  # eski format kayıtlar (iç içe geçmiş)
]

client = chromadb.PersistentClient(path="/root/kuroshin/memory/chroma")
col = client.get_collection("kuroshin_memory")
print(f"Toplam kayıt: {col.count()}")

all_docs = col.get()
ids = all_docs["ids"]
docs = all_docs["documents"]

bad_ids = []
for i, doc in enumerate(docs):
    doc_lower = doc.lower()
    for pattern in BAD_PATTERNS:
        if pattern.lower() in doc_lower:
            print(f"Kötü kayıt [{pattern}]: {ids[i]}")
            print(f"  İçerik: {doc[:150]}")
            bad_ids.append(ids[i])
            break

if bad_ids:
    col.delete(ids=bad_ids)
    print(f"\n{len(bad_ids)} kayıt silindi.")
else:
    print("Kötü kayıt bulunamadı.")

print(f"Kalan kayıt: {col.count()}")
