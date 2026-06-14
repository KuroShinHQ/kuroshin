// Kuroshin App Logic
// Panel toggle, Drag+Snap, Auto-hide, Sistem butonları, Bridge WebSocket, Status LED

(function () {
  const orb       = document.getElementById('orb-btn');
  const panel     = document.getElementById('chat-panel');
  const closeBtn  = document.getElementById('close-btn');
  const modeBadge = document.getElementById('mode-badge');

  // ── Panel Toggle ──────────────────────────────────────
  let panelOpen  = false;
  let _closeTimer = null;
  let _openTimer  = null;

  function calcDir() {
    const sw = window.screen.width;
    const sh = window.screen.height;
    const cx = window.screenX + 46;
    const cy = window.screenY + 46;
    if (cx > sw / 2 && cy > sh / 2) return 'bottom-right';
    if (cx <= sw / 2 && cy > sh / 2) return 'bottom-left';
    if (cx > sw / 2)                 return 'top-right';
    return 'top-left';
  }

  function openPanel() {
    // Yarım kalan kapanma animasyonunu iptal et
    if (_closeTimer) { clearTimeout(_closeTimer); _closeTimer = null; }
    panelOpen = true;
    resetAutoHide();
    document.getElementById('ui-root').dataset.dir = calcDir();
    // display:none olan paneli layout'a geri al — ÖNCE yap, SONRA window büyüsün
    panel.style.display = '';
    window.pywebview?.api?.toggle_panel?.(true);
    // Window resize bitmesini bekle, sonra animasyonu başlat
    _openTimer = setTimeout(() => {
      _openTimer = null;
      panel.style.visibility = 'visible';
      void panel.offsetHeight;           // reflow zorla → transition tetiklensin
      panel.classList.remove('collapsed', 'closing');
    }, 80);
  }

  function closePanel() {
    if (!panelOpen) return;
    panelOpen = false;
    // Yarım kalan açılma timer'ını iptal et
    if (_openTimer) { clearTimeout(_openTimer); _openTimer = null; }

    // 1) Kapanış animasyonunu başlat
    panel.classList.remove('collapsed');
    panel.classList.add('closing');

    // 2) Animasyon bitince (transform 0.44s, opacity 0.30s — 460ms yeterli) pencereyi küçült
    // transitionend yerine setTimeout: QWebEngine'de transitionend çoğunlukla tetiklenmiyor
    _closeTimer = setTimeout(() => {
      _closeTimer = null;
      panel.classList.remove('closing');
      panel.classList.add('collapsed');
      panel.style.visibility = 'hidden';
      panel.style.display    = 'none';   // layout'tan çıkar → WebGL rAF 92×92 penceresinde donmaz
      window.pywebview?.api?.toggle_panel?.(false);
    }, 460);
  }

  closeBtn.addEventListener('click', e => { e.stopPropagation(); closePanel(); });

  // Click-outside → kapat
  document.addEventListener('click', e => {
    if (panelOpen && !panel.contains(e.target) && !orb.contains(e.target)) {
      closePanel();
    }
  });

  // ── Drag + 4 Köşe Snap ──────────────────────────────
  let dragging   = false;
  let lastMove   = 0;
  let dragStartX = 0, dragStartY  = 0;
  let winStartX  = 0, winStartY   = 0;
  const DRAG_THRESHOLD = 5;

  // Sürükleme hız/yön — shader trail için
  window.orbVelocity = { vx: 0, vy: 0, speed: 0 };
  let _prevDragX = 0, _prevDragY = 0;

  // ── Long-press RAM Purge (3sn basılı → otomatik) ───
  let longPressTimer     = null;
  let pressInterval      = null;
  let pressStart         = 0;
  let longPressTriggered = false;

  orb.addEventListener('mousedown', e => {
    if (e.button !== 0) return;
    dragging           = false;
    longPressTriggered = false;
    pressStart         = Date.now();
    dragStartX         = e.screenX;
    dragStartY = e.screenY;
    winStartX  = window.screenX;
    winStartY  = window.screenY;
    e.preventDefault();

    // Long-press: 600ms → animasyon başlar, 2000ms dolunca ram_purge
    longPressTimer = setTimeout(() => {
      if (!dragging) {
        longPressTriggered = true;
        pressInterval = setInterval(() => {
          // 600ms'den itibaren 1400ms'de 0→1 dolum (toplam = 2sn)
          const progress = Math.min(Math.max((Date.now() - pressStart - 600) / 1400, 0), 1.0);
          window.setOrbPress?.(progress);
          if (progress >= 1.0) {
            clearInterval(pressInterval);
            pressInterval = null;
            window.setOrbPress?.(0);
            window.pywebview?.api?.ram_purge?.();
            ChatManager?.addMessage('🧹 RAM cache temizleniyor...', 'bot', true);
          }
        }, 30);
      }
    }, 600);

    const onMove = ev => {
      const dx = ev.screenX - dragStartX;
      const dy = ev.screenY - dragStartY;
      if (!dragging && (Math.abs(dx) > DRAG_THRESHOLD || Math.abs(dy) > DRAG_THRESHOLD)) {
        dragging = true;
        clearTimeout(longPressTimer);
        clearInterval(pressInterval);
        pressInterval = null;
        window.setOrbPress?.(0);
        orb.classList.add('dragging');
        _prevDragX = ev.screenX;
        _prevDragY = ev.screenY;
        resetAutoHide();
      }
      if (dragging && Date.now() - lastMove > 16) {
        lastMove = Date.now();
        window.pywebview?.api?.move_window?.(winStartX + dx, winStartY + dy);
        // Hız vektörü hesapla → shader trail için
        const vx = ev.screenX - _prevDragX;
        const vy = ev.screenY - _prevDragY;
        const spd = Math.min(Math.hypot(vx, vy) / 18, 1.0);
        const len = Math.hypot(vx, vy) || 1;
        window.orbVelocity = { vx: vx / len, vy: -vy / len, speed: spd };
        _prevDragX = ev.screenX;
        _prevDragY = ev.screenY;
      }
    };

    const onUp = ev => {
      clearTimeout(longPressTimer);
      clearInterval(pressInterval);
      pressInterval = null;
      window.setOrbPress?.(0);
      document.removeEventListener('mousemove', onMove);
      document.removeEventListener('mouseup', onUp);
      orb.classList.remove('dragging');
      orb.classList.remove('auto-hidden');  // BUG-2: görünmez kalma fix

      if (dragging) {
        const dx = ev.screenX - dragStartX;
        const dy = ev.screenY - dragStartY;
        snapToCornerIfNear(winStartX + dx, winStartY + dy);
        window.orbVelocity = { vx: 0, vy: 0, speed: 0 };  // trail sönsün
      } else {
        // gerçek click: <250ms VE longPress hiç tetiklenmemiş (QWebChannel IPC gecikmesi 50ms+ olabilir)
        const elapsed = Date.now() - pressStart;
        if (elapsed < 250 && !longPressTriggered) {
          if (panelOpen) closePanel(); else openPanel();
        }
      }
      dragging = false;
    };

    document.addEventListener('mousemove', onMove);
    document.addEventListener('mouseup', onUp);
  });

  function snapToCornerIfNear(wx, wy) {
    const sw = window.screen.width;
    const sh = window.screen.height;
    const WW  = 92;  // orb pencere boyutu (sabit)
    const PAD = 16;
    const SNAP_DIST = 80;  // px — bu mesafeden yakınsa köşeye snap yap

    const corners = [
      { name: 'top-left',     x: PAD,            y: PAD },
      { name: 'top-right',    x: sw - WW - PAD,  y: PAD },
      { name: 'bottom-left',  x: PAD,            y: sh - WW - PAD },
      { name: 'bottom-right', x: sw - WW - PAD,  y: sh - WW - PAD },
    ];

    const cx = wx + WW / 2;
    const cy = wy + WW / 2;
    let best = null, bestD = Infinity;
    for (const c of corners) {
      const d = Math.hypot(cx - (c.x + WW / 2), cy - (c.y + WW / 2));
      if (d < bestD) { bestD = d; best = c; }
    }

    if (best && bestD <= SNAP_DIST) {
      // Köşeye yakın → snap
      window.pywebview?.api?.move_window?.(best.x, best.y);
      window.pywebview?.api?.save_position?.(best.x, best.y, best.name);
    } else {
      // Serbestçe bırak
      window.pywebview?.api?.save_position?.(wx, wy, 'free');
    }
  }

  // ── Auto-hide (2 dakika) ─────────────────────────────
  const AUTO_HIDE_MS = 10 * 60 * 1000;  // 10 dakika
  let autoHideTimer  = null;

  function resetAutoHide() {
    clearTimeout(autoHideTimer);
    orb.classList.remove('auto-hidden');
    autoHideTimer = setTimeout(() => {
      if (!panelOpen) orb.classList.add('auto-hidden');
    }, AUTO_HIDE_MS);
  }

  document.addEventListener('mousemove', resetAutoHide, { passive: true });
  document.addEventListener('keydown',   resetAutoHide, { passive: true });
  orb.addEventListener('mouseenter', () => { orb.classList.remove('auto-hidden'); resetAutoHide(); });
  resetAutoHide();

  // ── Günün Saatine Göre Renk ──────────────────────────
  // 0.0 = gece (22:00-06:00), 1.0 = tam gündüz (08:00-18:00)
  function calcTimeOfDay() {
    const h = new Date().getHours() + new Date().getMinutes() / 60;
    if (h < 6 || h >= 21) return 0;          // gece
    if (h < 8)  return (h - 6) / 2;          // şafak: 0→1
    if (h < 18) return 1;                     // gündüz
    return 1 - (h - 18) / 3;                 // alacakaranlık: 1→0
  }
  window.orbTimeOfDay = calcTimeOfDay();
  setInterval(() => { window.orbTimeOfDay = calcTimeOfDay(); }, 60000); // her dakika

  // ── Scroll ile Opacity ───────────────────────────────
  window.orbOpacityTarget = 1.0;
  orb.addEventListener('wheel', e => {
    e.preventDefault();
    const delta = e.deltaY > 0 ? -0.08 : 0.08; // aşağı=soluk, yukarı=parlak
    window.orbOpacityTarget = Math.min(1.0, Math.max(0.15, (window.orbOpacityTarget) + delta));
  }, { passive: false });

  // ── Sağ tık Zoom Toggle ──────────────────────────────
  let orbZoomed = false;
  // Bu WebView'da context menü gerekmez — her yerde engelle
  document.addEventListener('contextmenu', e => e.preventDefault());

  orb.addEventListener('contextmenu', e => {
    e.preventDefault();
    e.stopPropagation();
    if (panelOpen) return;  // panel açıkken zoom yok
    orbZoomed = !orbZoomed;
    orb.classList.toggle('orb-zoomed', orbZoomed);
    resetAutoHide();
  });

  // ── Sistem Butonları ─────────────────────────────────
  document.getElementById('btn-ram')?.addEventListener('click', e => {
    e.stopPropagation();
    ChatManager?.addMessage('🧹 RAM temizleniyor...', 'bot', true);
    window.pywebview?.api?.ram_purge?.();
  });

  document.getElementById('btn-llm')?.addEventListener('click', e => {
    e.stopPropagation();
    ChatManager?.addMessage('🔄 Mod-2 toggle...', 'bot', true);
    window.pywebview?.api?.llm_toggle?.();
  });

  document.getElementById('btn-restart')?.addEventListener('click', () => {
    window.pywebview?.api?.chancellor_restart?.();
    ChatManager?.addMessage('Chancellor restart tetiklendi...', 'bot', true);
  });

  document.getElementById('btn-alarm')?.addEventListener('click', () => {
    ChatManager?.addMessage('🔔 Alarm durumu yükleniyor...', 'bot');
    window.pywebview?.api?.show_alarms?.();
  });

  // ── Başlangıç Auto-Open Toggle ───────────────────────
  let _autoOpenEnabled = false;

  function setAutoOpenUI(enabled) {
    _autoOpenEnabled = enabled;
    const icon  = document.getElementById('autoopen-icon');
    const label = document.getElementById('autoopen-label');
    const btn   = document.getElementById('btn-autoopen');
    if (!icon || !label || !btn) return;
    if (enabled) {
      icon.style.color       = '#6ffbbe';
      icon.style.textShadow  = '0 0 8px #6ffbbe88';
      label.style.color      = 'rgba(111,251,190,0.8)';
      btn.style.borderColor  = 'rgba(111,251,190,0.25)';
    } else {
      icon.style.color       = '#444';
      icon.style.textShadow  = 'none';
      label.style.color      = '';
      btn.style.borderColor  = '';
    }
  }

  document.getElementById('btn-autoopen')?.addEventListener('click', e => {
    e.stopPropagation();
    const next = !_autoOpenEnabled;
    setAutoOpenUI(next);
    window.pywebview?.api?.set_auto_open?.(next);
    ChatManager?.addMessage(
      next ? '⏻ Başlangıçta panel otomatik açılacak' : '⏻ Başlangıç auto-open kapatıldı',
      'bot', true
    );
  });

  // openPanel'i global yap — Python startup auto-open için
  window.openPanel = openPanel;

  // ── Panel Drag (status-bar'dan) ─────────────────────
  const statusBar = document.querySelector('.status-bar');
  let panelDragging = false;
  let pdStartX = 0, pdStartY = 0;
  let pdWinX   = 0, pdWinY   = 0;
  let pdLastMove = 0;

  statusBar.addEventListener('mousedown', e => {
    if (e.button !== 0) return;
    panelDragging = true;
    pdStartX = e.screenX;
    pdStartY = e.screenY;
    pdWinX   = window.screenX;
    pdWinY   = window.screenY;
    e.preventDefault();
    e.stopPropagation();

    const onMove = ev => {
      if (!panelDragging) return;
      const now = Date.now();
      if (now - pdLastMove < 16) return;
      pdLastMove = now;
      window.pywebview?.api?.move_window?.(
        pdWinX + (ev.screenX - pdStartX),
        pdWinY + (ev.screenY - pdStartY)
      );
    };

    const onUp = ev => {
      panelDragging = false;
      document.removeEventListener('mousemove', onMove);
      document.removeEventListener('mouseup', onUp);
      window.pywebview?.api?.save_position?.(window.screenX, window.screenY, 'free');
    };

    document.addEventListener('mousemove', onMove);
    document.addEventListener('mouseup', onUp);
  });

  // ── Status LED Güncelleme ────────────────────────────
  function setLED(id, online) {
    const el = document.getElementById(id);
    if (!el) return;
    el.className = 'led-dot ' + (online ? 'led-online' : 'led-offline');
  }

  function updateLEDs(s) {
    if (s.ch  !== undefined) setLED('led-ch',  s.ch);
    if (s.lm  !== undefined) setLED('led-lm',  s.lm);   // bridge compat
    if (s.lm1 !== undefined) setLED('led-lm',  s.lm1);  // L1 = Huihui :8080
    if (s.lm2 !== undefined) setLED('led-lm2', s.lm2);  // L2 = Mod-2 :8082
    if (s.wk  !== undefined) setLED('led-wk',  s.wk);
  }

  // Python background thread runJS ile LED'leri push eder (JS polling yok)
  window.updateLEDs = updateLEDs;

  // ── Hardware Monitor Güncelleme ──────────────────────
  // CPU/RAM yükü → shader renk kaydırma
  window.orbLoad = 0.0;

  function updateHW(s) {
    const cpuEl = document.getElementById('hw-cpu-val');
    if (cpuEl && s.cpu_pct >= 0) {
      const t = s.cpu_temp > 0 ? ` ${s.cpu_temp}°` : '';
      cpuEl.textContent = `${Math.round(s.cpu_pct)}%${t}`;
      cpuEl.style.color = s.cpu_pct > 80 ? '#ffb4ab' : s.cpu_pct > 55 ? '#ffd966' : '#6ffbbe';
    }
    const ramEl = document.getElementById('hw-ram-val');
    if (ramEl) {
      ramEl.textContent = `${s.ram_used_gb}/${s.ram_total_gb}G ${Math.round(s.ram_pct)}%`;
      ramEl.style.color = s.ram_pct > 85 ? '#ffb4ab' : s.ram_pct > 65 ? '#ffd966' : '#6ffbbe';
    }
    const gpuEl = document.getElementById('hw-gpu-val');
    if (gpuEl) {
      if (s.gpu_pct >= 0) {
        const gt = s.gpu_temp >= 0 ? ` ${s.gpu_temp}°` : '';
        gpuEl.textContent = `${s.gpu_pct}%${gt}`;
        gpuEl.style.color = s.gpu_temp > 80 ? '#ffb4ab' : s.gpu_temp > 65 ? '#ffd966' : '#6ffbbe';
      } else {
        gpuEl.textContent = '--';
      }
    }
    // CPU/RAM yükü → shader için orbLoad güncelle (0.0-1.0)
    // Ağırlık: CPU %70, RAM %30 — CPU ani spike'ları daha görünür olsun
    const load = Math.max(0, Math.min(1, (s.cpu_pct * 0.7 + s.ram_pct * 0.3) / 100));
    window.orbLoad = load;
  }

  window.updateHW = updateHW;

  // ── Bridge WebSocket (:9003) ─────────────────────────
  let ws = null, wsRetries = 0;

  function connectBridge() {
    try {
      ws = new WebSocket('ws://localhost:9003');

      ws.onopen = () => {
        wsRetries = 0;
        // LED durumunu Python _led_poll belirler — WS bağlantısı ≠ CH sağlığı
      };

      ws.onmessage = e => {
        let msg;
        try { msg = JSON.parse(e.data); } catch { return; }

        if (msg.type === 'chat') {
          ChatManager?.addMessage(msg.text, 'bot', true);
          window.setOrbState?.('IDLE');
        } else if (msg.type === 'processing') {
          window.setOrbState?.('PROCESSING');
        } else if (msg.type === 'done') {
          window.setOrbState?.('DONE');
          setTimeout(() => window.setOrbState?.('IDLE'), 2000);
        } else if (msg.type === 'alarm') {
          window.setOrbState?.('ALARM');
          ChatManager?.addMessage('⚡ ALARM: ' + msg.text, 'bot');
          if (!panelOpen) openPanel();
          setTimeout(() => window.setOrbState?.('IDLE'), 6000);
        } else if (msg.type === 'status') {
          updateLEDs(msg);
          if (msg.mode && modeBadge) modeBadge.textContent = msg.mode.toUpperCase();
        }
      };

      ws.onclose = () => {
        setLED('led-ch', false);
        const delay = Math.min(1000 * Math.pow(2, wsRetries++), 30000);
        setTimeout(connectBridge, delay);
      };

      ws.onerror = () => ws.close();

    } catch (_) {
      setTimeout(connectBridge, 5000);
    }
  }

  // FAZ-2: chat.js'den WS üzerinden mesaj gönderme
  window.kuroshinSendWS = function (text) {
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({ type: 'user_message', text }));
      return true;
    }
    return false;
  };

  // ── Magnetic Mouse — orb iç fluid fare yönüne çekiliyor ───
  window.mouseInfluence = { nx: 0, ny: 0, pull: 0 };
  document.addEventListener('mousemove', e => {
    const rect = orb.getBoundingClientRect();
    const cx   = rect.left + rect.width  / 2;
    const cy   = rect.top  + rect.height / 2;
    // Normalize: orb yarıçapının kaç katı uzakta?
    const r    = (rect.width / 2) || 46;
    const dx   = (e.clientX - cx) / r;
    const dy   = (e.clientY - cy) / r;
    const dist = Math.hypot(dx, dy);
    // pull: 0(çok uzak) → 1(orb üzerinde), max etki 2.5x yarıçap içinde
    const pull = Math.max(0, 1.0 - dist / 2.5);
    window.mouseInfluence = { nx: dx / Math.max(dist, 0.01), ny: -dy / Math.max(dist, 0.01), pull };
  }, { passive: true });

  // Sayfa başlangıcında panel gizli — display:none ile layouttan da çıkar
  panel.style.visibility = 'hidden';
  panel.style.display    = 'none';

  // pywebview API hazır olunca bağlan
  function init() {
    connectBridge();
    window.pywebview?.api?.get_settings?.().then(s => {
      if (s?.mode && modeBadge) modeBadge.textContent = s.mode.toUpperCase();
      setAutoOpenUI(!!s?.auto_open);
    });
  }

  if (window.pywebview) {
    init();
  } else {
    window.addEventListener('pywebviewready', init);
  }

})();
