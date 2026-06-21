"""
hamjsondata.md vs KuroWatch DB karşılaştırma scripti
Çoklu JSON array'leri parse eder, DB ile kıyaslar, tutarsızlıkları raporlar.
"""
import sqlite3
import re
import json
from pathlib import Path

HAM_FILE = Path("/mnt/c/Kuroshin/kurowatch/docs/hamjsondata.md")
DB_FILE  = Path("/mnt/c/Kuroshin/kurowatch/memory/kurowatch.db")

# ── 1. hamjsondata.md'yi parse et ─────────────────────────────────────────────
def parse_ham(path):
    """Dosyada birden fazla üst-seviye JSON array var.
    Satır bazlı stack okuyucu: satır başında '[' → yeni array başlar,
    satır başında ']' → array biter."""
    lines = path.read_text(encoding="utf-8").splitlines()
    items = []
    depth = 0
    buf = []
    array_count = 0

    for line in lines:
        stripped = line.strip()
        if stripped == "[" and depth == 0:
            depth = 1
            buf = ["["]
            continue
        if depth > 0:
            # iç içe köşeli parantez sayısı
            depth += stripped.count("[") - stripped.count("]")
            if depth == 0:
                # array kapandı
                buf.append("]")
                arr_str = "\n".join(buf)
                try:
                    parsed = json.loads(arr_str)
                    if isinstance(parsed, list):
                        for obj in parsed:
                            if isinstance(obj, dict):
                                items.append(obj)
                    array_count += 1
                except json.JSONDecodeError as e:
                    print(f"  [WARN] array #{array_count} parse hatası: {e}")
                buf = []
            else:
                buf.append(line)

    print(f"  Toplam {array_count} JSON array parse edildi")
    return items

# ── 2. Başlık normalizer ───────────────────────────────────────────────────────
def normalize(title: str) -> str:
    t = title.lower().strip()
    # parantez içerikleri kaldır (alternatif isimler, Türkçe isimleri)
    t = re.sub(r'\s*[\(\[].*?[\)\]]', '', t)
    # noktalama / özel karakterler
    t = re.sub(r'[^\w\s]', '', t)
    t = re.sub(r'\s+', ' ', t).strip()
    return t

# ── 3. Ham'dan tek liste yap (dedup: son gelen kazanır) ───────────────────────
raw_items = parse_ham(HAM_FILE)
ham_by_norm = {}   # normalize_title -> item
for item in raw_items:
    title = item.get("title", "").strip()
    if not title:
        continue
    norm = normalize(title)
    ham_by_norm[norm] = item   # duplike → son versiyon kazanır

print(f"Ham JSON: {len(raw_items)} kayıt, {len(ham_by_norm)} tekil başlık\n")

# ── 4. DB'den içerikleri çek ──────────────────────────────────────────────────
conn = sqlite3.connect(DB_FILE)
conn.row_factory = sqlite3.Row
cur = conn.cursor()
cur.execute("SELECT id, title, type, status, my_score, my_progress, my_progress_pct FROM content ORDER BY title")
db_rows = cur.fetchall()
conn.close()

db_by_norm = {}
for row in db_rows:
    norm = normalize(row["title"])
    db_by_norm[norm] = dict(row)

print(f"DB: {len(db_rows)} kayıt, {len(db_by_norm)} tekil başlık\n")

# ── 5. Karşılaştır ────────────────────────────────────────────────────────────
ham_keys = set(ham_by_norm.keys())
db_keys  = set(db_by_norm.keys())

only_in_ham = ham_keys - db_keys    # DB'de YOK, ham'da VAR
only_in_db  = db_keys  - ham_keys   # Ham'da YOK, DB'de VAR
both        = ham_keys & db_keys    # İkisinde de var

# ── 6. Her iki tarafta da var ama farklı veri ──────────────────────────────────
STATUS_MAP = {
    "completed": "completed",
    "watching":  "watching",
    "planning":  "planning",
    "dropped":   "dropped",
    "paused":    "paused",
}

mismatches = []
for norm in sorted(both):
    ham = ham_by_norm[norm]
    db  = db_by_norm[norm]
    diffs = []

    # Status karşılaştır
    ham_status = ham.get("status", "")
    db_status  = db.get("status", "")
    if ham_status and db_status and ham_status != db_status:
        diffs.append(f"status: ham={ham_status!r} / db={db_status!r}")

    # Rating/score karşılaştır
    ham_rating_raw = ham.get("personal_rating", "")
    if ham_rating_raw and ham_rating_raw != "0.0/10":
        try:
            ham_score = float(str(ham_rating_raw).split("/")[0])
        except:
            ham_score = None
        db_score = db.get("my_score")
        if ham_score is not None and db_score is not None:
            if abs(ham_score - db_score) > 0.5:
                diffs.append(f"score: ham={ham_score} / db={db_score}")

    if diffs:
        mismatches.append((ham.get("title"), diffs))

# ── 7. Rapor ──────────────────────────────────────────────────────────────────
print("=" * 60)
print(f"SADECE HAM'DA (DB'ye eklenmemiş): {len(only_in_ham)} adet")
print("=" * 60)
for norm in sorted(only_in_ham):
    item = ham_by_norm[norm]
    title  = item.get("title", "?")
    typ    = item.get("type", "?")
    status = item.get("status", "?")
    rating = item.get("personal_rating", "?")
    print(f"  [{typ}] {title}  — status={status}, puan={rating}")

print()
print("=" * 60)
print(f"SADECE DB'DE (Ham'da yok — elle eklenen): {len(only_in_db)} adet")
print("=" * 60)
for norm in sorted(only_in_db):
    row = db_by_norm[norm]
    print(f"  [{row['type']}] {row['title']}  — status={row['status']}")

print()
print("=" * 60)
print(f"İKİSİNDE DE VAR AMA TUTARSIZ: {len(mismatches)} adet")
print("=" * 60)
for title, diffs in mismatches:
    print(f"  {title}")
    for d in diffs:
        print(f"    ▸ {d}")

print()
print("=" * 60)
print(f"ÖZET: Ham={len(ham_by_norm)} | DB={len(db_by_norm)} | Eşleşen={len(both)} | Sadece-Ham={len(only_in_ham)} | Sadece-DB={len(only_in_db)} | Tutarsız={len(mismatches)}")
