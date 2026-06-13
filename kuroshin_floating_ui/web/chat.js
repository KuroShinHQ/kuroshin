// Kuroshin Chat Manager
// Mesaj render, typewriter, progress bar, input handler

const ChatManager = (function () {
  const area  = document.getElementById('chat-area');
  const input = document.getElementById('cmd-input');
  const send  = document.getElementById('send-btn');

  function scrollBottom() {
    requestAnimationFrame(() => { area.scrollTop = area.scrollHeight; });
  }

  function typeText(el, text, onDone) {
    // HTML taglarını soyup typing'de plain text göster, bitince HTML render
    const plain = text.replace(/<br\s*\/?>/gi, '\n').replace(/<[^>]+>/g, '');
    el.textContent = '';
    el.classList.add('typing-cursor');
    let i = 0;
    const iv = setInterval(() => {
      if (i < plain.length) {
        el.textContent += plain[i++];
        scrollBottom();
      } else {
        clearInterval(iv);
        el.classList.remove('typing-cursor');
        el.innerHTML = text;
        onDone?.();
      }
    }, 28);
  }

  function addMessage(text, type = 'bot', typing = false, withProgress = false) {
    if (window.__chatAborted && type === 'bot') {
      window.__chatAborted = false;
      return null;
    }
    const div = document.createElement('div');
    div.className = type === 'user' ? 'msg-user' : 'msg-bot';

    const span = document.createElement('span');
    div.appendChild(span);

    if (withProgress) {
      const bar = document.createElement('div');
      bar.className = 'progress-bar';
      bar.innerHTML = '<div class="progress-bar-fill"></div>';
      div.appendChild(bar);
    }

    area.appendChild(div);
    scrollBottom();

    if (typing && type === 'bot') {
      typeText(span, text, () => {
        if (withProgress) div.querySelector('.progress-bar')?.remove();
        scrollBottom();
      });
    } else if (type === 'bot') {
      span.innerHTML = text;
      scrollBottom();
    } else {
      span.textContent = text;
      scrollBottom();
    }

    return div;
  }

  function clearChat() { area.innerHTML = ''; }

  // ── Gönder ──
  function sendMessage() {
    const text = input.value.trim();
    if (!text) return;
    addMessage(text, 'user');
    input.value = '';

    const st = window.currentLEDStatus || {};

    // LLM yok
    if (!st.lm1 && !st.lm2) {
      addMessage('⚠️ LLM yok — panelden LLM butonuna bas', 'bot');
      return;
    }

    window.setOrbState?.('PROCESSING');

    if (st.lm2 && !st.lm1) {
      // Normal Mode: Qwen3-1.7B → api.py routing (yanıt runJS ile gelir)
      window.pywebview?.api?.send_message?.(text);
      return;
    }

    // Turbo Mode (lm1 aktif): WS → Bridge → Chancellor
    if (window.kuroshinSendWS?.(text)) return;

    // WS yoksa API fallback (Turbo)
    window.pywebview?.api?.send_message?.(text);
  }

  input.addEventListener('keydown', e => { if (e.key === 'Enter') sendMessage(); });
  send.onclick = sendMessage;

  // Welcome
  window.addEventListener('pywebviewready', () => {
    setTimeout(() => addMessage('Kuroshin hazır. ⚡', 'bot', true), 400);
  });
  // pywebview yoksa (geliştirme modu)
  if (!window.pywebview) {
    setTimeout(() => addMessage('Kuroshin hazır. [dev mod]', 'bot', true), 800);
  }

  // ── Input kilidi (yanıt beklenirken) ──
  window.__chatAborted = false;
  function _disableInput() {
    input.disabled = true;
    send.textContent = '⬛';
    send.title = 'İptal';
    send.onclick = function () {
      window.__chatAborted = true;
      window.__removePending?.();
    };
  }
  function _restoreInput() {
    input.disabled = false;
    input.focus();
    send.textContent = '▶';
    send.title = '';
    send.onclick = sendMessage;
  }

  // ── Thinking bar (pending) ──
  let __pendingDiv = null;
  window.__addPending = function () {
    if (__pendingDiv) return;
    _disableInput();
    const div  = document.createElement('div');
    div.className = 'msg-bot msg-pending';
    div.innerHTML  = '<span class="thinking-dots"><span></span><span></span><span></span></span>';
    area.appendChild(div);
    scrollBottom();
    __pendingDiv = div;
  };
  window.__removePending = function () {
    if (__pendingDiv) { __pendingDiv.remove(); __pendingDiv = null; }
    _restoreInput();
  };

  return { addMessage, clearChat };
})();
