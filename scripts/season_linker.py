"""
season_linker.py — Anime sezon zinciri (temiz versiyon)
1. Mevcut (S2)/(S3) kartları parent_id ile S1'e bağla
2. AniList ile yeni sequel kartları oluştur (rate-limited)
3. Spy x Family S1 + Tate S1 gibi eksik S1'leri ekle
"""
import asyncio
import json
import re
import sys

sys.path.insert(0, '/mnt/c/Kuroshin/kurowatch')

from backend.database import AsyncSessionLocal, init_db
from backend.scraper import anilist
from sqlalchemy import text


def parse_season_from_title(title: str) -> int:
    m = re.search(r"\(S(\d+)\)", title, re.IGNORECASE)
    if m:
        return int(m.group(1))
    m = re.search(r"Season\s+(\d+)", title, re.IGNORECASE)
    if m:
        return int(m.group(1))
    return 1


async def insert_content(db, title, cover_url, ext_id, total_ep, season_number, parent_id):
    """Yeni content satiri ekle, ID'sini dondur."""
    await db.execute(text("""
        INSERT INTO content
          (title, type, cover_url, external_id, status, total_episodes,
           season_number, parent_id, my_progress, note_is_spoiler, added_at, updated_at)
        VALUES
          (:title, 'anime', :cover, :ext, 'planning', :ep,
           :snum, :pid, 0, 0, datetime('now'), datetime('now'))
    """), {
        "title": title, "cover": cover_url, "ext": ext_id,
        "ep": total_ep, "snum": season_number, "pid": parent_id,
    })
    await db.commit()
    r = await db.execute(text(
        "SELECT id FROM content WHERE external_id=:ext AND type='anime' ORDER BY id DESC LIMIT 1"
    ), {"ext": ext_id})
    return r.scalar()


async def main():
    await init_db()

    async with AsyncSessionLocal() as db:

        # ── ADIM 1: Mevcut sezon_number güncelle ───────────────────
        print("=== ADIM 1: season_number güncelle ===")
        r = await db.execute(text(
            "SELECT id, title, season_number FROM content WHERE type='anime'"
        ))
        for row in r.fetchall():
            snum = parse_season_from_title(row[1])
            if snum != (row[2] or 1):
                await db.execute(text(
                    "UPDATE content SET season_number=:s WHERE id=:i"
                ), {"s": snum, "i": row[0]})
                print(f"  ID={row[0]:3d} S{snum} ← {row[1][:50]}")
        await db.commit()

        # ── ADIM 2: Mevcut S2/S3 → parent_id bağla ────────────────
        print("\n=== ADIM 2: Mevcut S2/S3 parent_id bağlantısı ===")
        # Manuel eşleştirme: (S2/S3 content_id, S1 content_id)
        known_links = [
            (95,  636),   # Tsuki S2 → Tsuki ga Michibiku Isekai (636)
            (100, 437),   # Maou Gakuin S2 → Maou Gakuin (437)
            (101, 412),   # KonoSuba S3 → KonoSuba S1 (412)
            (109, 104),   # Shangri-La S2 → Shangri-La S1 (104)
            (110, 587),   # Hataraku Maou S3 → S1 (587)
            (112, 287),   # Dexter S8 → Dexter S1 (287)
            (113, 505),   # Rick and Morty S7 → S1 (505)
            (114, 650),   # Marvel's What If S3 → S1 (650)
        ]
        for child_id, parent_id_val in known_links:
            await db.execute(text(
                "UPDATE content SET parent_id=:pid WHERE id=:cid AND (parent_id IS NULL OR parent_id != :pid)"
            ), {"pid": parent_id_val, "cid": child_id})
            print(f"  ID={child_id} → parent={parent_id_val}")
        await db.commit()

        # ── ADIM 3: Eksik S1'leri oluştur (Tate + Spy) ────────────
        print("\n=== ADIM 3: Eksik S1 kartları ===")

        # Tate no Yuusha S1 — AniList ID: 99263 (doğrulanmış)
        r = await db.execute(text("SELECT id FROM content WHERE external_id='99263'"))
        if not r.scalar():
            al = await anilist.get_detail("99263")
            if al:
                new_id = await insert_content(
                    db, al["title"] or "Tate no Yuusha no Nariagari",
                    al.get("cover_url"),
                    "99263", al.get("total_episodes"), 1, None
                )
                if new_id:
                    await db.execute(text("INSERT INTO site (content_id, site_name, site_url, is_primary) VALUES (:c,'İzle','https://www.tranimaci.com/anime/tate-no-yuusha-no-nariagari/',1)"), {"c": new_id})
                    await db.commit()
                    # Tate S3'ün parent_id'sini yeni S1'e bağla (S2 yok)
                    await db.execute(text("UPDATE content SET parent_id=:pid WHERE id=105"), {"pid": new_id})
                    await db.commit()
                    print(f"  OLUŞTUR: Tate S1 → ID={new_id}, S3 (ID=105) parent={new_id}")
        else:
            tate_s1_id = r.scalar()
            print(f"  Tate S1 zaten mevcut: ID={tate_s1_id}")
            await db.execute(text("UPDATE content SET parent_id=:pid WHERE id=105"), {"pid": tate_s1_id})
            await db.commit()

        await asyncio.sleep(0.8)

        # Spy x Family S1 — AniList ID: 140960
        r = await db.execute(text("SELECT id FROM content WHERE external_id='140960'"))
        if not r.scalar():
            al = await anilist.get_detail("140960")
            if al:
                new_id = await insert_content(
                    db, al["title"] or "Spy x Family",
                    al.get("cover_url"),
                    "140960", al.get("total_episodes"), 1, None
                )
                if new_id:
                    await db.execute(text("INSERT INTO site (content_id, site_name, site_url, is_primary) VALUES (:c,'İzle','https://www.tranimaci.com/anime/spy-x-family/',1)"), {"c": new_id})
                    await db.commit()
                    # Spy S2'nin parent_id'sini yeni S1'e bağla
                    await db.execute(text("UPDATE content SET parent_id=:pid WHERE id=106"), {"pid": new_id})
                    await db.commit()
                    print(f"  OLUŞTUR: Spy x Family S1 → ID={new_id}, S2 (ID=106) parent={new_id}")
        else:
            spy_s1_id = r.scalar()
            print(f"  Spy x Family S1 zaten mevcut: ID={spy_s1_id}")
            await db.execute(text("UPDATE content SET parent_id=:pid WHERE id=106"), {"pid": spy_s1_id})
            await db.commit()

        await asyncio.sleep(0.8)

        # ── ADIM 4: AniList relations → yeni sequel kartları ───────
        print("\n=== ADIM 4: AniList sequel kartları ===")

        # Güncel ext_to_id
        r = await db.execute(text(
            "SELECT id, external_id FROM content WHERE type='anime' AND external_id IS NOT NULL"
        ))
        ext_to_id = {row[1]: row[0] for row in r.fetchall()}

        # AniList ID'li anime'ler
        r = await db.execute(text(
            "SELECT id, title, external_id, season_number FROM content "
            "WHERE type='anime' AND external_id IS NOT NULL "
            "AND external_id NOT LIKE 'mal:%' ORDER BY id"
        ))
        anilist_anime = [(row[0], row[1], row[2], row[3]) for row in r.fetchall()]
        print(f"  {len(anilist_anime)} anime kontrol edilecek...")

        created = 0
        for i, (aid, atitle, aext, asnum) in enumerate(anilist_anime):
            await asyncio.sleep(0.75)  # AniList rate limit (90 req/min)
            try:
                rels = await anilist.get_relations(aext)
            except Exception:
                rels = []
            for rel in rels:
                rex = rel["external_id"]
                if rex not in ext_to_id:
                    # Yeni sezon kartı
                    if rel["relation_type"] == "SEQUEL":
                        snum = (asnum or 1) + 1
                    else:
                        snum = max(1, (asnum or 1) - 1)
                    new_id = await insert_content(
                        db, rel["title"], rel.get("cover_url"),
                        rex, rel.get("episodes"), snum, aid
                    )
                    if new_id:
                        # Tranimaci URL oluştur
                        import re as re2
                        slug_base = re2.sub(r"[^a-z0-9]+", "-", (rel["title"] or "").lower()).strip("-")
                        tranimaci_url = f"https://www.tranimaci.com/anime/{slug_base}/"
                        await db.execute(text(
                            "INSERT INTO site (content_id, site_name, site_url, is_primary) "
                            "VALUES (:c,'İzle',:u,1)"
                        ), {"c": new_id, "u": tranimaci_url})
                        await db.commit()
                        ext_to_id[rex] = new_id
                        created += 1
                        print(f"  OLUŞTUR: S{snum} ID={new_id} {rel['title'][:45]} (parent={aid})")
                else:
                    # Zaten var → sadece parent_id güncelle
                    existing_id = ext_to_id[rex]
                    if rel["relation_type"] == "SEQUEL":
                        await db.execute(text(
                            "UPDATE content SET parent_id=:pid WHERE id=:cid AND parent_id IS NULL"
                        ), {"pid": aid, "cid": existing_id})
                    else:
                        await db.execute(text(
                            "UPDATE content SET parent_id=:pid WHERE id=:eid AND parent_id IS NULL"
                        ), {"pid": existing_id, "eid": aid})
                    await db.commit()

        print(f"  Toplam yeni kart: {created}")

        # ── SONUÇ ──────────────────────────────────────────────────
        print("\n=== SONUÇ ===")
        r = await db.execute(text(
            "SELECT c.id, c.title, c.season_number, c.parent_id, c.cover_url "
            "FROM content c WHERE c.type='anime' "
            "AND (c.season_number > 1 OR c.parent_id IS NOT NULL) "
            "ORDER BY COALESCE(c.parent_id, c.id), c.season_number"
        ))
        rows = r.fetchall()
        print(f"Sezon zincirindeki anime: {len(rows)}")
        for row in rows:
            cover = "Y" if row[4] else "N"
            print(f"  ID={row[0]:3d} S{row[2]} pid={str(row[3]):5s} cover={cover} {row[1][:55]}")

        r2 = await db.execute(text("SELECT COUNT(*) FROM content WHERE type='anime'"))
        print(f"\nToplam anime: {r2.scalar()}")


if __name__ == "__main__":
    asyncio.run(main())
