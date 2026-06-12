"""
Fiyat Alarm Motoru — KuroRecon
Fiyat düşüşü veya hedef fiyat altına giriş tespit edince Telegram bildirim gönderir.
"""
from __future__ import annotations

import json
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    import requests as _req
    _HAS_REQUESTS = True
except ImportError:
    _HAS_REQUESTS = False

from .fetcher import PaketFetcher
from .parser import parse_listings


HISTORY_FILE = Path(__file__).parent.parent / "alarm_history.json"


class Alert:
    def __init__(self, watch_name: str, title: str, url: str, site: str,
                 old_price: Optional[float], new_price: float, reason: str):
        self.watch_name = watch_name
        self.title      = title
        self.url        = url
        self.site       = site
        self.old_price  = old_price
        self.new_price  = new_price
        self.reason     = reason  # "below_price" | "drop_percent" | "new_low"

    def drop_pct(self) -> Optional[float]:
        if self.old_price and self.old_price > 0:
            return round((self.old_price - self.new_price) / self.old_price * 100, 1)
        return None

    def telegram_text(self) -> str:
        icon = "🔔"
        lines = [f"{icon} *FİYAT ALARMI — {self.watch_name}*"]

        if self.reason == "below_price":
            lines.append(f"✅ Hedef fiyatın altına düştü!")
        elif self.reason == "drop_percent":
            lines.append(f"📉 Fiyat önemli ölçüde düştü!")
        else:
            lines.append(f"🆕 Yeni en düşük fiyat!")

        price_line = f"💰 *{self.new_price:,.0f} ₺*"
        if self.old_price:
            drop = self.drop_pct()
            drop_str = f"  _(eskiden {self.old_price:,.0f} ₺, ▼%{drop})_" if drop else ""
            price_line += drop_str
        lines.append(price_line)

        lines.append(f"🏷️ {self.title[:80]}")
        lines.append(f"🛒 {self.site}")
        if self.url:
            lines.append(f"🔗 {self.url[:120]}")
        lines.append(f"📅 {datetime.now().strftime('%d %b %Y %H:%M')}")
        return "\n".join(lines)


class PriceWatcher:
    def __init__(self, watches: list, telegram_cfg: dict,
                 history_file: Path = HISTORY_FILE,
                 scraper_cfg: dict = None):
        self.watches      = watches
        self.tg           = telegram_cfg
        self.history_file = history_file
        self.scraper_cfg  = scraper_cfg or {}

    # ── History ───────────────────────────────────────────────────────────────

    def load_history(self) -> dict:
        if not self.history_file.exists():
            return {}
        try:
            return json.loads(self.history_file.read_text(encoding="utf-8"))
        except Exception:
            return {}

    def save_history(self, history: dict):
        self.history_file.write_text(
            json.dumps(history, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )

    # ── Fetch ─────────────────────────────────────────────────────────────────

    def fetch_prices(self, watch: dict) -> List[Dict[str, Any]]:
        cfg = self.scraper_cfg
        fetcher = PaketFetcher(
            delay_min   = float(cfg.get("delay_min", 3)),
            delay_max   = float(cfg.get("delay_max", 8)),
            timeout     = float(cfg.get("timeout", 30)),
            max_retries = int(cfg.get("max_retries", 3)),
            proxy       = cfg.get("proxy", "") or "",
            cookie_file = watch.get("cookie_file") or None,
            user_agent  = cfg.get("user_agent", "auto"),
        )
        result = fetcher.get(watch["url"], mode=watch.get("mode", "static"))
        if result.blocked or result.status_code != 200 or not result.html:
            print(f"  ✗ [{watch['name']}] Fetch başarısız: "
                  f"blocked={result.blocked} status={result.status_code}")
            return []

        items = parse_listings(result.html,
                               site_type=watch.get("parser", "generic"),
                               site_label=watch.get("name", ""))
        # Sadece geçerli fiyatlı ürünleri al, ucuzdan sırala
        items = [i for i in items if isinstance(i.get("price"), (int, float)) and i["price"] > 0]
        items.sort(key=lambda x: x["price"])
        return items

    # ── Alert logic ───────────────────────────────────────────────────────────

    def check_alerts(self, watch: dict, items: List[Dict], history: dict) -> List[Alert]:
        if not items:
            return []

        name       = watch["name"]
        alert_cfg  = watch.get("alert_if", {})
        below      = alert_cfg.get("below_price")   # sayısal eşik
        drop_pct   = alert_cfg.get("drop_percent")  # % eşik
        alerts     = []

        watch_hist = history.get(name, {})
        prev_min   = watch_hist.get("min_price")    # önceki en düşük fiyat
        prev_item  = watch_hist.get("min_item", {}) # önceki en ucuz ürün

        # En ucuz ürünü bul
        cheapest = items[0]
        cur_price = cheapest["price"]
        cur_title = cheapest.get("title", "")
        cur_url   = cheapest.get("url", "")
        cur_site  = cheapest.get("site", "")

        # İlk çalıştırma — sadece kaydet
        if prev_min is None:
            print(f"  📌 [{name}] İlk kayıt: {cur_price:,.0f} ₺ — {cur_title[:50]}")
            return []

        # Hedef fiyat kontrolü
        if below and cur_price < below:
            prev_was_below = prev_min is not None and prev_min < below
            if not prev_was_below:
                alerts.append(Alert(name, cur_title, cur_url, cur_site,
                                    prev_min, cur_price, "below_price"))

        # Yüzde düşüş kontrolü
        if drop_pct and prev_min and prev_min > 0:
            actual_drop = (prev_min - cur_price) / prev_min * 100
            if actual_drop >= drop_pct:
                alerts.append(Alert(name, cur_title, cur_url, cur_site,
                                    prev_min, cur_price, "drop_percent"))

        # Eşik tanımlanmamışsa — sadece yeni en düşük fiyat tespiti
        if not below and not drop_pct and prev_min and cur_price < prev_min:
            alerts.append(Alert(name, cur_title, cur_url, cur_site,
                                prev_min, cur_price, "new_low"))

        return alerts

    def _update_history(self, history: dict, watch: dict, items: List[Dict]):
        if not items:
            return
        name     = watch["name"]
        cheapest = items[0]
        history[name] = {
            "last_check": datetime.now().isoformat(timespec="seconds"),
            "min_price":  cheapest["price"],
            "min_item":   {
                "title": cheapest.get("title", ""),
                "price": cheapest["price"],
                "url":   cheapest.get("url", ""),
                "site":  cheapest.get("site", ""),
            },
            "top5": [
                {"title": i.get("title", ""), "price": i["price"], "site": i.get("site", "")}
                for i in items[:5]
            ]
        }

    # ── FloatingUI Bridge Push ────────────────────────────────────────────────

    def _push_to_bridge(self, alert: 'Alert'):
        """Alarm tetiklenince FloatingUI bridge WS :9003'e push (opsiyonel)."""
        payload = json.dumps({
            'type':      'alarm',
            'text':      f"{alert.watch_name}: {alert.new_price:,.0f} ₺",
            'watch':     alert.watch_name,
            'price':     alert.new_price,
            'old_price': alert.old_price,
            'reason':    alert.reason,
        })
        try:
            import asyncio
            import websockets as _wss
            async def _send():
                async with _wss.connect(
                    'ws://localhost:9003', open_timeout=2, close_timeout=1
                ) as ws:
                    await ws.send(payload)
            asyncio.run(_send())
            print("  ✅ Bridge alarm push OK (FloatingUI)")
        except Exception as e:
            print(f"  ⚠  Bridge push atlandı (FloatingUI kapalı?): {type(e).__name__}")

    # ── Telegram ──────────────────────────────────────────────────────────────

    def send_telegram(self, text: str) -> bool:
        if not _HAS_REQUESTS:
            print("[HATA] requests kütüphanesi yok: pip install requests")
            return False
        token   = self.tg.get("token", "")
        chat_id = self.tg.get("chat_id", "")
        if not token or not chat_id:
            print("[HATA] Telegram token/chat_id eksik — alarm_config.yaml'ı kontrol et")
            return False
        try:
            url  = f"https://api.telegram.org/bot{token}/sendMessage"
            resp = _req.post(url, json={
                "chat_id":    str(chat_id),
                "text":       text,
                "parse_mode": "Markdown",
            }, timeout=15)
            if resp.status_code == 200:
                print("  ✅ Telegram bildirimi gönderildi")
                return True
            else:
                print(f"  ✗ Telegram hata: {resp.status_code} {resp.text[:120]}")
                return False
        except Exception as e:
            print(f"  ✗ Telegram bağlantı hatası: {e}")
            return False

    def send_test(self) -> bool:
        text = (
            "🧪 *KuroRecon Fiyat Alarm — Test*\n"
            "Telegram bağlantısı başarılı!\n"
            f"📅 {datetime.now().strftime('%d %b %Y %H:%M')}"
        )
        return self.send_telegram(text)

    # ── Ana akış ─────────────────────────────────────────────────────────────

    def run(self) -> int:
        history     = self.load_history()
        total_alerts = 0

        for watch in self.watches:
            if not watch.get("enabled", True):
                continue
            name = watch.get("name", "?")
            print(f"\n[{name}] Kontrol ediliyor...")
            print(f"  URL : {watch.get('url', '')[:80]}")

            items = self.fetch_prices(watch)
            print(f"  Bulunan: {len(items)} ürün")
            if items:
                print(f"  En ucuz: {items[0]['price']:,.0f} ₺ — {items[0].get('title','')[:50]}")

            alerts = self.check_alerts(watch, items, history)
            for alert in alerts:
                print(f"  🔔 ALARM: {alert.reason} | {alert.new_price:,.0f} ₺")
                self.send_telegram(alert.telegram_text())
                self._push_to_bridge(alert)
                total_alerts += 1

            self._update_history(history, watch, items)

            # İzlemeler arası bekleme
            if self.watches.index(watch) < len(self.watches) - 1:
                delay = float(self.scraper_cfg.get("delay_min", 3))
                time.sleep(delay)

        self.save_history(history)
        print(f"\n✓ Kontrol tamamlandı. {total_alerts} alarm tetiklendi.")
        print(f"  Geçmiş kaydedildi: {self.history_file}")
        return total_alerts
