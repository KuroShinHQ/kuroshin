"""
A Returner's Magic Should Be Special — mangaokutr.com (offline) → MangaDex
MangaDex manga ID: 6a468761-5bd6-4de0-a0cb-47cb456ac2e0
manga.py zaten _mangadex_chapter() ile handle ediyor.
"""
import urllib.request, json, sqlite3, time

DB_PATH = "/mnt/c/Kuroshin/kurowatch/memory/kurowatch.db"
MANGA_ID = "6a468761-5bd6-4de0-a0cb-47cb456ac2e0"
CONTENT_ID = 10

MDX_HEADERS = {"User-Agent": "kurowatch/1.0"}

def fetch_chapters():
    """MangaDex API'den tüm İngilizce chapter'ları çek (offset ile sayfalama)."""
    chapters = []
    offset = 0
    limit = 100

    while True:
        url = (
            f"https://api.mangadex.org/manga/{MANGA_ID}/feed"
            f"?translatedLanguage[]=en"
            f"&order[chapter]=asc"
            f"&limit={limit}&offset={offset}"
        )
        req = urllib.request.Request(url, headers=MDX_HEADERS)
        try:
            resp = urllib.request.urlopen(req, timeout=15)
            data = json.loads(resp.read())
        except Exception as ex:
            print(f"API HATA offset={offset}: {ex}")
            break

        batch = data.get("data", [])
        if not batch:
            break

        for ch in batch:
            attrs = ch["attributes"]
            ch_num_str = attrs.get("chapter")
            if ch_num_str is None:
                continue
            try:
                ch_num = float(ch_num_str)
            except ValueError:
                continue
            chapters.append({
                "id": ch["id"],
                "number": ch_num,
                "pages": attrs.get("pages", 0),
                "lang": attrs.get("translatedLanguage"),
            })

        total = data.get("total", 0)
        offset += limit
        print(f"  {len(chapters)}/{total} chapter alindi...")
        if offset >= total:
            break
        time.sleep(0.3)  # rate limit

    return chapters


def run():
    print("MangaDex chapter listesi cekiliyor...")
    chapters = fetch_chapters()
    print(f"Toplam {len(chapters)} chapter alindi.")
    if not chapters:
        print("HATA: Chapter bulunamadi!")
        return

    # Chapter numaralarini kontrol et (kesirli/tam)
    int_chapters = {int(c["number"]): c for c in chapters if c["number"] == int(c["number"])}
    print(f"  Tam sayi chapter: {min(int_chapters)}-{max(int_chapters)} ({len(int_chapters)} adet)")

    # DB'deki episode listesi
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT id, number FROM episode WHERE content_id=? ORDER BY number", (CONTENT_ID,))
    db_episodes = cur.fetchall()
    print(f"\nDB'de {len(db_episodes)} episode var.")
    db_nums = [r[1] for r in db_episodes]
    print(f"  DB aralik: {min(db_nums)}-{max(db_nums)}")

    # Eslestir ve guncelle
    updated = 0
    not_found = []
    for ep_id, ep_num in db_episodes:
        if ep_num in int_chapters:
            ch = int_chapters[ep_num]
            new_url = f"https://mangadex.org/chapter/{ch['id']}"
            cur.execute("UPDATE episode SET url=? WHERE id=?", (new_url, ep_id))
            updated += 1
        else:
            not_found.append(ep_num)

    conn.commit()
    print(f"\nGuncellendi: {updated} / {len(db_episodes)}")
    if not_found:
        print(f"MangaDex'te bulunamadi: {not_found[:20]}{'...' if len(not_found)>20 else ''}")

    # Dogrulama
    cur.execute("SELECT number, url FROM episode WHERE content_id=? ORDER BY number LIMIT 3", (CONTENT_ID,))
    print("\nOrnek (ilk 3):")
    for num, url in cur.fetchall():
        print(f"  ep-{num}: {url}")

    conn.close()
    print("\nTamam.")

if __name__ == "__main__":
    run()
