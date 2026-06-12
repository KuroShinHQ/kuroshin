#!/usr/bin/env python3
"""
KuroRecon Fiyat Alarm — Çalıştırıcı

Kullanım:
  python alarm_run.py                        # alarm_config.yaml ile çalıştır
  python alarm_run.py --config benim.yaml    # özel config
  python alarm_run.py --test                 # Telegram bağlantısını test et
  python alarm_run.py --status               # Son kontrol özetini göster
  python alarm_run.py --reset "İzleme Adı"  # Bir izlemenin geçmişini sıfırla
"""
import argparse
import json
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    print("[HATA] PyYAML gerekli: pip install pyyaml")
    sys.exit(1)

from scraper_paketi.alarm import PriceWatcher, HISTORY_FILE


def load_config(path: str) -> dict:
    p = Path(path)
    if not p.exists():
        print(f"[HATA] Config bulunamadı: {path}")
        sys.exit(1)
    with p.open(encoding="utf-8") as f:
        return yaml.safe_load(f)


def cmd_status(history_file: Path):
    if not history_file.exists():
        print("Henüz hiç kontrol yapılmamış (alarm_history.json yok).")
        return
    history = json.loads(history_file.read_text(encoding="utf-8"))
    if not history:
        print("Geçmiş boş.")
        return
    print(f"\n{'='*60}")
    print(f"  KuroRecon — Fiyat Geçmişi")
    print(f"{'='*60}")
    for name, data in history.items():
        print(f"\n📌 {name}")
        print(f"   Son kontrol : {data.get('last_check', '?')}")
        min_p = data.get('min_price')
        min_i = data.get('min_item', {})
        if min_p:
            print(f"   En düşük   : {min_p:,.0f} ₺  —  {min_i.get('title','')[:50]}")
            print(f"   Site       : {min_i.get('site','?')}")
        top5 = data.get("top5", [])
        if top5:
            print(f"   Top-5:")
            for i, item in enumerate(top5, 1):
                print(f"     {i}. {item['price']:>10,.0f} ₺  {item.get('title','')[:45]}")
    print()


def cmd_reset(history_file: Path, watch_name: str):
    if not history_file.exists():
        print("Geçmiş dosyası yok, sıfırlanacak bir şey yok.")
        return
    history = json.loads(history_file.read_text(encoding="utf-8"))
    if watch_name in history:
        del history[watch_name]
        history_file.write_text(json.dumps(history, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"✓ '{watch_name}' geçmişi sıfırlandı.")
    else:
        print(f"'{watch_name}' geçmişte bulunamadı.")
        if history:
            print("Mevcut izlemeler:", ", ".join(history.keys()))


def main():
    ap = argparse.ArgumentParser(description="KuroRecon Fiyat Alarm")
    ap.add_argument("--config", default="alarm_config.yaml", help="Alarm config dosyası")
    ap.add_argument("--test",         action="store_true", help="Telegram bağlantısını test et")
    ap.add_argument("--test-bridge",  action="store_true", help="FloatingUI bridge WS push test et")
    ap.add_argument("--status",       action="store_true", help="Son kontrol özetini göster")
    ap.add_argument("--reset",        metavar="İZLEME_ADI", help="Bir izlemenin geçmişini sıfırla")
    args = ap.parse_args()

    # --status ve --reset config gerektirmez
    if args.status:
        cmd_status(HISTORY_FILE)
        return
    if args.reset:
        cmd_reset(HISTORY_FILE, args.reset)
        return

    config     = load_config(args.config)
    tg_cfg     = config.get("telegram", {})
    watches    = config.get("watches", [])
    scrp_cfg   = config.get("scraper", {})

    watcher = PriceWatcher(
        watches      = watches,
        telegram_cfg = tg_cfg,
        scraper_cfg  = scrp_cfg,
    )

    if args.test:
        print("Telegram test mesajı gönderiliyor...")
        ok = watcher.send_test()
        sys.exit(0 if ok else 1)

    if args.test_bridge:
        print("FloatingUI bridge WS alarm push test...")
        from scraper_paketi.alarm import Alert
        mock = Alert(
            watch_name="Test İzleme",
            title="Test Ürün — Mock Alarm",
            url="https://example.com",
            site="test-site",
            old_price=1500.0,
            new_price=1200.0,
            reason="drop_percent",
        )
        watcher._push_to_bridge(mock)
        sys.exit(0)

    # Normal çalıştırma
    active = [w for w in watches if w.get("enabled", True)]
    if not active:
        print("[UYARI] alarm_config.yaml'da enabled: true olan izleme yok.")
        print("  watches altındaki bir izlemenin 'enabled: false' → 'enabled: true' yapın.")
        sys.exit(0)

    print(f"\n{'='*60}")
    print(f"  KuroRecon Fiyat Alarm")
    print(f"  {len(active)} aktif izleme")
    print(f"{'='*60}")

    watcher.run()


if __name__ == "__main__":
    main()
