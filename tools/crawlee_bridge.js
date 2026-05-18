// Kuroshin Crawlee Bridge v1.0 — Port 3006
// Walker Agent Python tarafından HTTP üzerinden çağrılır
// mod: simple (native http) | playwright (JS-render) | stealth (anti-bot)

const http = require('http');
const https = require('https');

const PORT = 3006;
const CRAWLEE_CHAR_LIMIT = 12000;
const REQUEST_TIMEOUT_MS = 35000;

// ── Crawlee loader ────────────────────────────────────────────────────────
// Crawlee v3: exports["require"] = ./index.js — require() ile yüklenir
let _crawlee = null;

function getCrawlee() {
  if (_crawlee) return _crawlee;
  try {
    _crawlee = require('./node_modules/crawlee/index.js');
    console.log('[CRAWLEE] Modül yüklendi');
    return _crawlee;
  } catch (e) {
    console.error('[CRAWLEE] Modül yüklenemedi:', e.message);
    return null;
  }
}

// ── Yardımcı ──────────────────────────────────────────────────────────────
function readBody(req) {
  return new Promise((resolve, reject) => {
    let body = '';
    req.on('data', chunk => (body += chunk.toString()));
    req.on('end', () => {
      try {
        resolve(body ? JSON.parse(body) : {});
      } catch (e) {
        reject(new Error('JSON parse hatası'));
      }
    });
    req.on('error', reject);
  });
}

function jsonResp(res, code, data) {
  res.writeHead(code, { 'Content-Type': 'application/json' });
  res.end(JSON.stringify(data));
}

// HTML → düz metin (script/style/tag temizle)
function htmlToText(html) {
  return html
    .replace(/<script[\s\S]*?<\/script>/gi, '')
    .replace(/<style[\s\S]*?<\/style>/gi, '')
    .replace(/<!--[\s\S]*?-->/g, '')
    .replace(/<[^>]+>/g, ' ')
    .replace(/&nbsp;/g, ' ')
    .replace(/&amp;/g, '&')
    .replace(/&lt;/g, '<')
    .replace(/&gt;/g, '>')
    .replace(/&quot;/g, '"')
    .replace(/\s+/g, ' ')
    .trim()
    .slice(0, CRAWLEE_CHAR_LIMIT);
}

// ── Mod 1: Basit HTTP fetch (JS gerektirmeyen siteler) ────────────────────
function simpleFetch(url) {
  return new Promise((resolve, reject) => {
    const lib = url.startsWith('https') ? https : http;
    const timer = setTimeout(() => reject(new Error('Timeout (simple fetch)')), REQUEST_TIMEOUT_MS);
    const req = lib.get(
      url,
      {
        headers: {
          'User-Agent':
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 ' +
            '(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
          Accept: 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        },
        timeout: REQUEST_TIMEOUT_MS,
      },
      res => {
        clearTimeout(timer);
        // Yönlendirme (3xx) takibi
        if (res.statusCode >= 300 && res.statusCode < 400 && res.headers.location) {
          simpleFetch(res.headers.location).then(resolve).catch(reject);
          return;
        }
        let data = '';
        res.on('data', chunk => (data += chunk));
        res.on('end', () => resolve(data));
      }
    );
    req.on('error', e => { clearTimeout(timer); reject(e); });
    req.on('timeout', () => { clearTimeout(timer); req.destroy(); reject(new Error('Socket timeout')); });
  });
}

// ── Mod 2 & 3: Crawlee PlaywrightCrawler ─────────────────────────────────
async function crawleePlaywright(url, stealth = false) {
  const crawlee = getCrawlee();
  if (!crawlee) throw new Error('Crawlee modülü yüklenemedi');

  const { PlaywrightCrawler } = crawlee;
  let pageContent = '';
  let crawlError = null;

  const crawler = new PlaywrightCrawler({
    headless: true,
    requestHandlerTimeoutSecs: 40,
    maxRequestsPerCrawl: 1,
    navigationTimeoutSecs: 30,
    // WSL2 / sandbox-less ortam için zorunlu
    launchContext: {
      launchOptions: {
        args: [
          '--no-sandbox',
          '--disable-setuid-sandbox',
          '--disable-dev-shm-usage',
          '--disable-gpu',
          '--disable-blink-features=AutomationControlled',
        ],
      },
    },
    async requestHandler({ page }) {
      try {
        // stealth: navigator.webdriver gizle, gerçekçi UA
        if (stealth) {
          await page.addInitScript(() => {
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
          });
        }
        await page.waitForLoadState('domcontentloaded', { timeout: 15000 }).catch(() => {});
        pageContent = await page.content();
      } catch (e) {
        crawlError = e;
      }
    },
    failedRequestHandler({ request }, err) {
      crawlError = err || new Error('Request failed: ' + request.url);
    },
  });

  await crawler.run([url]);

  if (crawlError && !pageContent) {
    throw crawlError;
  }
  return pageContent;
}

// ── Ana crawl fonksiyonu — mod dispatch + fallback zinciri ────────────────
async function crawl(url, mode) {
  const t0 = Date.now();
  let html = '';
  let usedMode = mode;

  if (mode === 'simple') {
    html = await simpleFetch(url);
  } else {
    try {
      html = await crawleePlaywright(url, mode === 'stealth');
    } catch (e) {
      console.warn(`[CRAWLEE] ${mode} başarısız (${e.message}), simple fallback deneniyor...`);
      usedMode = 'simple-fallback';
      html = await simpleFetch(url);
    }
  }

  const content = htmlToText(html);
  const elapsed = ((Date.now() - t0) / 1000).toFixed(1);
  console.log(`[CRAWLEE] Tamamlandı: ${content.length} karakter, ${elapsed}s (mod: ${usedMode})`);
  return { content, usedMode, elapsed: parseFloat(elapsed) };
}

// ── HTTP Sunucu ───────────────────────────────────────────────────────────
const server = http.createServer(async (req, res) => {
  const urlObj = new URL(req.url, `http://localhost:${PORT}`);

  // GET /health
  if (req.method === 'GET' && urlObj.pathname === '/health') {
    jsonResp(res, 200, { status: 'ok', port: PORT, service: 'kuroshin-crawlee-bridge', version: '1.0' });
    return;
  }

  // POST /crawl
  if (req.method === 'POST' && urlObj.pathname === '/crawl') {
    let body = {};
    try {
      body = await readBody(req);
    } catch (e) {
      jsonResp(res, 400, { error: e.message });
      return;
    }

    const targetUrl = body.url;
    const mode = (body.mode || 'playwright').toLowerCase();

    if (!targetUrl || !/^https?:\/\//i.test(targetUrl)) {
      jsonResp(res, 400, { error: 'Geçerli http/https URL gerekli' });
      return;
    }

    if (!['simple', 'playwright', 'stealth'].includes(mode)) {
      jsonResp(res, 400, { error: 'Geçersiz mod: simple | playwright | stealth' });
      return;
    }

    console.log(`[CRAWLEE] İstek: ${targetUrl} (mod: ${mode})`);

    try {
      const result = await crawl(targetUrl, mode);
      jsonResp(res, 200, {
        ok: true,
        url: targetUrl,
        mode: result.usedMode,
        content: result.content,
        length: result.content.length,
        elapsed: result.elapsed,
      });
    } catch (e) {
      console.error('[CRAWLEE] Hata:', e.message);
      jsonResp(res, 500, { ok: false, error: e.message, url: targetUrl });
    }
    return;
  }

  jsonResp(res, 404, { error: 'Bilinmeyen endpoint: ' + urlObj.pathname });
});

server.listen(PORT, '127.0.0.1', () => {
  console.log(`[Kuroshin Crawlee Bridge] http://127.0.0.1:${PORT} — hazır`);
  console.log(`[Kuroshin Crawlee Bridge] Mod: simple | playwright | stealth`);
});

server.on('error', e => {
  if (e.code === 'EADDRINUSE') {
    console.error(`[HATA] Port ${PORT} zaten kullanımda`);
  } else {
    console.error('[HATA]', e);
  }
});
