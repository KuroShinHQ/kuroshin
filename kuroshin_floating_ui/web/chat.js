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
    el.textContent = '';
    el.classList.add('typing-cursor');
    let i = 0;
    const iv = setInterval(() => {
      if (i < text.length) {
        el.textContent += text[i++];
        scrollBottom();
      } else {
        clearInterval(iv);
        el.classList.remove('typing-cursor');
        onDone?.();
      }
    }, 28);
  }

  function addMessage(text, type = 'bot', typing = false, withProgress = false) {
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

    // FAZ-2: Bridge WS üzerinden chancellor'a ilet
    if (window.kuroshinSendWS?.(text)) {
      window.setOrbState?.('PROCESSING');
      return;
    }

    // Fallback: doğrudan pywebview API (bridge henüz bağlı değil)
    if (window.pywebview?.api?.send_message) {
      window.setOrbState?.('PROCESSING');
      const msgDiv = addMessage('...', 'bot', false, true);
      window.pywebview.api.send_message(text).then(resp => {
        msgDiv.remove();
        if (resp) addMessage(resp, 'bot', true);
        window.setOrbState?.('IDLE');
      }).catch(() => {
        msgDiv.remove();
        addMessage('Bağlantı hatası.', 'bot');
        window.setOrbState?.('IDLE');
      });
    } else {
      addMessage('[Bağlantı bekleniyor...]', 'bot');
    }
  }

  input.addEventListener('keydown', e => { if (e.key === 'Enter') sendMessage(); });
  send.addEventListener('click', sendMessage);

  // Welcome
  window.addEventListener('pywebviewready', () => {
    setTimeout(() => addMessage('Kuroshin hazır. ⚡', 'bot', true), 400);
  });
  // pywebview yoksa (geliştirme modu)
  if (!window.pywebview) {
    setTimeout(() => addMessage('Kuroshin hazır. [dev mod]', 'bot', true), 800);
  }

  return { addMessage, clearChat };
})();
