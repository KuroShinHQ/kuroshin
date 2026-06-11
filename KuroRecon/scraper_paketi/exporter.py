"""
Sonuçları CSV/JSON olarak dışa aktar + konsol tablosu.
"""
from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any, Dict, List, Optional


def export(results: List[Dict[str, Any]], fmt: str, path: str,
           sort_by: str = "price", ascending: bool = True) -> str:
    """
    results → dosya.
    fmt: 'csv' veya 'json'
    Döner: yazılan dosya yolu.
    """
    if not results:
        return ""

    sorted_results = sorted(
        results,
        key=lambda x: (x.get(sort_by) or 0) if sort_by == "price" else str(x.get(sort_by, "")),
        reverse=not ascending,
    )

    out_path = Path(path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    if fmt.lower() == "json":
        out_path.write_text(
            json.dumps(sorted_results, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    else:
        _write_csv(sorted_results, out_path)

    return str(out_path)


def _write_csv(results: List[Dict[str, Any]], path: Path):
    if not results:
        return
    fields = ["title", "price", "site", "rating", "review_count", "description", "url"]
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(results)


def print_table(results: List[Dict[str, Any]], max_rows: int = 20,
                sort_by: str = "price", ascending: bool = True):
    """Konsola sade ASCII tablo yaz."""
    if not results:
        print("  Sonuç bulunamadı.")
        return

    sorted_r = sorted(
        results[:max_rows],
        key=lambda x: (x.get(sort_by) or 0) if sort_by == "price" else str(x.get(sort_by, "")),
        reverse=not ascending,
    )

    # Sütun genişlikleri
    w_no   = 4
    w_site = max(6, max(len(str(r.get("site", ""))) for r in sorted_r))
    w_fiy  = 12
    w_tit  = max(30, min(60, max(len(str(r.get("title", ""))) for r in sorted_r)))

    sep = f"+{'-'*(w_no+2)}+{'-'*(w_site+2)}+{'-'*(w_fiy+2)}+{'-'*(w_tit+2)}+"
    hdr = f"| {'#':>{w_no}} | {'Site':<{w_site}} | {'Fiyat (TL)':>{w_fiy}} | {'Başlık':<{w_tit}} |"

    print(sep)
    print(hdr)
    print(sep)
    for i, r in enumerate(sorted_r, 1):
        title = str(r.get("title", ""))[:w_tit].ljust(w_tit)
        site  = str(r.get("site", ""))[:w_site].ljust(w_site)
        price = r.get("price", 0)
        fiy   = f"{price:>{w_fiy},.0f}" if isinstance(price, (int, float)) else str(price)[:w_fiy]
        print(f"| {i:>{w_no}} | {site} | {fiy} | {title} |")
    print(sep)
    print(f"  Toplam: {len(sorted_r)} sonuç")
