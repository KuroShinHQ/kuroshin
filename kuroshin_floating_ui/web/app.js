// Kuroshin App Logic
// Panel toggle, Drag+Snap, Auto-hide, Sistem butonları, Bridge WebSocket, Status LED

(function () {
  const orb       = document.getElementById('orb-btn');
  const panel     = document.getElementById('chat-panel');
  const closeBtn  = document.getElementById('close-btn');
  const modeBadge = document.getElementById('mode-badge');

  // ── Panel Toggle ──────────────────────────────────────
  let panelOpen = false;
  let _closeListener = null;

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
    if (_closeListener) {
      panel.removeEventListener('transitionend', _closeListener);
      _closeListener = null;
    }
    panelOpen = true;
    resetAutoHide();
    // 1) transform-origin'i anında doğru köşeye ayarla (async IPC'ye bağımlı değil)
    document.getElementById('ui-root').dataset.dir = calcDir();
    // 2) Window'u büyüt
    window.pywebview?.api?.toggle_panel?.(true);
    // 3) Window resize tamamlansın, sonra animasyon başlasın
    setTimeout(() => {
      panel.style.visibility = 'visible';
      void panel.offsetHeight;
      panel.classList.remove('collapsed', 'closing');
    }, 80);
  }

  function closePanel() {
    if (!panelOpen) return;
    panelOpen = false;
    // 1) Animasyonu başlat (window hala büyük — görünür)
    panel.classList.remove('collapsed');
    panel.classList.add('closing');

    _closeListener = function onDone(e) {
      if (e.propertyName !== 'opacity') return;
      panel.removeEventListener('transitionend', _closeListener);
      _closeListener = null;
      panel.classList.remove('closing');
      panel.classList.add('collapsed');
      panel.style.visibility = 'hidden';
      // 2) Animasyon bitti, şimdi window'u küçült
      window.pywebview?.api?.toggle_panel?.(false);
    };
    panel.addEventListener('transitionend', _closeListener);
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

    // Long-press: 600ms → animasyon başlar, 3000ms dolunca ram_purge
    longPressTimer = setTimeout(() => {
      if (!dragging) {
        longPressTriggered = true;
        pressInterval = setInterval(() => {
          // 600ms'den itibaren 2400ms'de 0→1 dolum (toplam = 3sn)
          const progress = Math.min(Math.max((Date.now() - pressStart - 600) / 2400, 0), 1.0);
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
        resetAutoHide();
      }
      if (dragging && Date.now() - lastMove > 16) {
        lastMove = Date.now();
        window.pywebview?.api?.move_window?.(winStartX + dx, winStartY + dy);
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

  // Sayfa başlangıcında panel gizli (collapsed class var, visibility JS yönetir)
  panel.style.visibility = 'hidden';

  // pywebview API hazır olunca bağlan
  function init() {
    connectBridge();
    // settings'ten mod badge'i al
    window.pywebview?.api?.get_settings?.().then(s => {
      if (s?.mode && modeBadge) modeBadge.textContent = s.mode.toUpperCase();
    });
  }

  if (window.pywebview) {
    init();
  } else {
    window.addEventListener('pywebviewready', init);
  }

})();
