// Kuroshin App Logic
// Panel toggle, Drag+Snap, Auto-hide, Sistem butonları, Bridge WebSocket, Status LED

(function () {
  const orb       = document.getElementById('orb-btn');
  const panel     = document.getElementById('chat-panel');
  const closeBtn  = document.getElementById('close-btn');
  const modeBadge = document.getElementById('mode-badge');

  // ── Panel Toggle ──────────────────────────────────────
  let panelOpen = false;

  function openPanel() {
    panel.classList.remove('collapsed');
    panelOpen = true;
    resetAutoHide();
    window.pywebview?.api?.toggle_panel?.(true);
  }

  function closePanel() {
    panel.classList.add('collapsed');
    panelOpen = false;
    window.pywebview?.api?.toggle_panel?.(false);
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
  let dragStartX = 0, dragStartY  = 0;
  let winStartX  = 0, winStartY   = 0;
  const DRAG_THRESHOLD = 5;

  orb.addEventListener('mousedown', e => {
    if (e.button !== 0) return;
    dragging   = false;
    dragStartX = e.screenX;
    dragStartY = e.screenY;
    // window.screenX/Y = pywebview penceresinin ekrandaki pozisyonu
    winStartX  = window.screenX;
    winStartY  = window.screenY;
    e.preventDefault();

    const onMove = ev => {
      const dx = ev.screenX - dragStartX;
      const dy = ev.screenY - dragStartY;
      if (!dragging && (Math.abs(dx) > DRAG_THRESHOLD || Math.abs(dy) > DRAG_THRESHOLD)) {
        dragging = true;
        orb.classList.add('dragging');
        resetAutoHide();
      }
      if (dragging) {
        window.pywebview?.api?.move_window?.(winStartX + dx, winStartY + dy);
      }
    };

    const onUp = ev => {
      document.removeEventListener('mousemove', onMove);
      document.removeEventListener('mouseup', onUp);
      orb.classList.remove('dragging');

      if (dragging) {
        const dx = ev.screenX - dragStartX;
        const dy = ev.screenY - dragStartY;
        snapToCorner(winStartX + dx, winStartY + dy);
      } else {
        // Tıklama: panel aç/kapat
        if (panelOpen) closePanel(); else openPanel();
      }
      dragging = false;
    };

    document.addEventListener('mousemove', onMove);
    document.addEventListener('mouseup', onUp);
  });

  function snapToCorner(wx, wy) {
    const sw = window.screen.width;
    const sh = window.screen.height;
    const ww = window.outerWidth;
    const wh = window.outerHeight;
    const PAD = 16;

    const corners = [
      { name: 'top-left',     x: PAD,           y: PAD },
      { name: 'top-right',    x: sw - ww - PAD, y: PAD },
      { name: 'bottom-left',  x: PAD,           y: sh - wh - PAD },
      { name: 'bottom-right', x: sw - ww - PAD, y: sh - wh - PAD },
    ];

    const cx = wx + ww / 2;
    const cy = wy + wh / 2;
    let best = corners[3], bestD = Infinity;
    for (const c of corners) {
      const d = Math.hypot(cx - (c.x + ww / 2), cy - (c.y + wh / 2));
      if (d < bestD) { bestD = d; best = c; }
    }

    window.pywebview?.api?.move_window?.(best.x, best.y);
    // best.x/y = pencerenin sol-üst köşesi → doğrudan kaydet
    window.pywebview?.api?.save_position?.(best.x, best.y, best.name);
  }

  // ── Auto-hide (2 dakika) ─────────────────────────────
  const AUTO_HIDE_MS = 2 * 60 * 1000;
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
  document.getElementById('btn-ram')?.addEventListener('click', () => {
    window.pywebview?.api?.ram_purge?.();
    ChatManager?.addMessage('RAM cache temizleniyor...', 'bot', true);
  });

  document.getElementById('btn-llm')?.addEventListener('click', () => {
    window.pywebview?.api?.llm_toggle?.();
    ChatManager?.addMessage('[FAZ-3] LLM toggle yapılandırılmadı.', 'bot');
  });

  document.getElementById('btn-restart')?.addEventListener('click', () => {
    window.pywebview?.api?.chancellor_restart?.();
    ChatManager?.addMessage('Chancellor restart tetiklendi...', 'bot', true);
  });

  document.getElementById('btn-alarm')?.addEventListener('click', () => {
    window.pywebview?.api?.show_alarms?.();
    ChatManager?.addMessage('[FAZ-3] Alarm listesi yapılandırılmadı.', 'bot');
  });

  // ── Status LED Güncelleme ────────────────────────────
  function setLED(id, online) {
    const el = document.getElementById(id);
    if (!el) return;
    el.className = 'led-dot ' + (online ? 'led-online' : 'led-offline');
  }

  function updateLEDs(s) {
    if (s.ch !== undefined) setLED('led-ch', s.ch);
    if (s.lm !== undefined) setLED('led-lm', s.lm);
    if (s.wk !== undefined) setLED('led-wk', s.wk);
  }

  // 10 sn polling (pywebview HTTP health check)
  setInterval(() => {
    window.pywebview?.api?.get_status?.().then(s => { if (s) updateLEDs(s); });
  }, 10000);

  // ── Bridge WebSocket (:9003) ─────────────────────────
  let ws = null, wsRetries = 0;

  function connectBridge() {
    try {
      ws = new WebSocket('ws://localhost:9003');

      ws.onopen = () => {
        wsRetries = 0;
        setLED('led-ch', true);
      };

      ws.onmessage = e => {
        let msg;
        try { msg = JSON.parse(e.data); } catch { return; }

        if (msg.type === 'chat') {
          ChatManager?.addMessage(msg.text, 'bot', false);
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
