"""Iron Inquisitor v6 — Otomatik MD Raporu (MODEL_TEST_PLANI.md + MODEL_KARSILASTIRMA)

Kullanicinin istegi: test bitince dokumanlar OTOMATIK guncellensin.
GERCEK veri (skor/elapsed/tarih) kullanilir; kullanici onayi adiminda durur.
"""
import json
from datetime import datetime
from pathlib import Path

from ..config import MODEL_KARSILASTIRMA_MD, MODEL_TEST_PLANI_MD


def _load_suites_for_meta(suite_files: list[Path]) -> dict:
    """Suite dosyalarindan test adetlerini cikar (meta icin)."""
    meta = {}
    for f in suite_files:
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            n = len(data) if isinstance(data, list) else len(data.get("tests", []))
            meta[f.name] = n
        except Exception:
            meta[f.name] = "?"
    return meta


def md_run_summary(results: list[dict], suite_files: list[Path], tag: str = "") -> str:
    """Test kosusu icin Markdown ozet blogu uretir."""
    total = len(results)
    passed = sum(1 for r in results if r["status"] == "PASS")
    failed = [r for r in results if r["status"] != "PASS"]
    total_w = sum(r.get("weight", 1.0) for r in results)
    earned = sum(r.get("score", 0.0) for r in results)
    pct = round(100 * earned / total_w, 1) if total_w else 0
    avg_el = round(sum(r.get("elapsed", 0) or 0 for r in results) / max(total, 1), 1)

    meta = _load_suites_for_meta(suite_files)
    lines = [
        f"### Son Kosu — {datetime.now().strftime('%Y-%m-%d %H:%M')} {f'({tag})' if tag else ''}",
        "",
        f"- **Skor:** {earned:.1f}/{total_w:.1f} (%{pct}) | PASS {passed}/{total} | "
        f"Ort sure: {avg_el}s | Suite'ler: {', '.join(f'{k} ({v})' for k, v in meta.items())}",
    ]
    if failed:
        lines.append(f"- **Basarisiz ({len(failed)}):**")
        for r in failed[:10]:
            lines.append(f"  - `{r['id']}` [{r['status']}] {(r.get('note') or '')[:80]}")
    return "\n".join(lines)


def update_model_test_plani(results: list[dict], suite_files: list[Path],
                            tag: str = "", dry_run: bool = True) -> Path | None:
    """MODEL_TEST_PLANI.md'ye 'Son Kosu' blogu ekler. dry_run=False -> yazar."""
    summary = md_run_summary(results, suite_files, tag)
    if not MODEL_TEST_PLANI_MD.exists():
        return None
    content = MODEL_TEST_PLANI_MD.read_text(encoding="utf-8")

    marker = "## Son Kosular (otomatik — Iron Inquisitor v6)"
    if marker not in content:
        content = content.rstrip() + f"\n\n---\n\n{marker}\n\n{summary}\n"
    else:
        # En guncel kosuyu bas tarafa ekle
        head, _, tail = content.partition(marker)
        content = head + marker + "\n\n" + summary + "\n\n" + tail

    if dry_run:
        print(f"[MD-REPORT] (dry-run) MODEL_TEST_PLANI.md guncelleme hazir — {len(summary)} satir")
        return MODEL_TEST_PLANI_MD
    MODEL_TEST_PLANI_MD.write_text(content, encoding="utf-8")
    print(f"[MD-REPORT] MODEL_TEST_PLANI.md GUNCELLENDI: {MODEL_TEST_PLANI_MD}")
    return MODEL_TEST_PLANI_MD


def update_model_karsilastirma(arena_result: dict, dry_run: bool = True) -> Path | None:
    """Arena sonucunu MODEL_KARSILASTIRMA_20260819.md'ye isler."""
    if not MODEL_KARSILASTIRMA_MD.exists():
        return None
    content = MODEL_KARSILASTIRMA_MD.read_text(encoding="utf-8")
    a, b = arena_result["model_a"], arena_result["model_b"]
    wr = arena_result["win_rate"]
    block = [
        "",
        f"### Arena {arena_result['ts'][:16]} — {a.split('.')[0]} vs {b.split('.')[0]}",
        "",
        f"- Suite: `{arena_result['suite']}` | Toplam: {arena_result['total']} | Berabere: {arena_result['ties']}",
        f"- Kazananlar: A={arena_result['wins'][a]}, B={arena_result['wins'][b]}",
        f"- Win-rate: A=%{wr[a]}, B=%{wr[b]}",
        "",
    ]
    if dry_run:
        print(f"[MD-REPORT] (dry-run) MODEL_KARSILASTIRMA arena blogu hazir")
        return MODEL_KARSILASTIRMA_MD
    content = content.rstrip() + "\n" + "\n".join(block)
    MODEL_KARSILASTIRMA_MD.write_text(content, encoding="utf-8")
    print(f"[MD-REPORT] MODEL_KARSILASTIRMA GUNCELLENDI")
    return MODEL_KARSILASTIRMA_MD