// Kuroshin FAZ-9 — Agent Bridge (Port 3005)
// Ajanların C:\Kuroshin dizinindeki dosyaları okuması ve Lord onayı sonrası yazması için köprü
// Başlatma: node agent_bridge.js (veya Kuroshin_Start.bat içinden)

const http = require('http');
const fs = require('fs');
const path = require('path');

const PORT = 3005;
const PROJECT_ROOT = process.env.KUROSHIN_ROOT || path.resolve(__dirname, '..');

// Güvenlik: Sadece PROJECT_ROOT içindeki dosyalara erişim
function safePath(filePath) {
  const resolved = path.resolve(PROJECT_ROOT, filePath.replace(/^[\/\\]+/, ''));
  if (!resolved.startsWith(PROJECT_ROOT)) {
    throw new Error('Güvenlik ihlali: proje dışına çıkış yasak');
  }
  return resolved;
}

function readBody(req) {
  return new Promise((resolve, reject) => {
    let body = '';
    req.on('data', chunk => body += chunk.toString());
    req.on('end', () => {
      try { resolve(body ? JSON.parse(body) : {}); }
      catch (e) { reject(new Error('JSON parse hatası')); }
    });
    req.on('error', reject);
  });
}

function cors(res) {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET, POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');
}

function json(res, code, data) {
  cors(res);
  res.writeHead(code, { 'Content-Type': 'application/json' });
  res.end(JSON.stringify(data));
}

const server = http.createServer(async (req, res) => {
  cors(res);

  // CORS preflight
  if (req.method === 'OPTIONS') {
    res.writeHead(204);
    res.end();
    return;
  }

  const url = new URL(req.url, `http://localhost:${PORT}`);

  try {
    // GET /list_dir?path=src/components
    if (req.method === 'GET' && url.pathname === '/list_dir') {
      const dirPath = safePath(url.searchParams.get('path') || '');
      const entries = fs.readdirSync(dirPath, { withFileTypes: true });
      json(res, 200, {
        path: dirPath,
        entries: entries.map(e => ({
          name: e.name,
          type: e.isDirectory() ? 'dir' : 'file',
        })),
      });
      return;
    }

    // GET /read_file?path=src/components/PixiGame.tsx
    if (req.method === 'GET' && url.pathname === '/read_file') {
      const filePath = safePath(url.searchParams.get('path') || '');
      if (!fs.existsSync(filePath)) {
        json(res, 404, { error: 'Dosya bulunamadı: ' + filePath });
        return;
      }
      const content = fs.readFileSync(filePath, 'utf8');
      // Büyük dosyaları kırp (LLM context için) — 20000: reminder@15318 gibi derin tanımlar için
      const MAX_CHARS = 20000;
      json(res, 200, {
        path: filePath,
        content: content.length > MAX_CHARS
          ? content.slice(0, MAX_CHARS) + '\n\n... [KISALTILDI - toplam ' + content.length + ' karakter]'
          : content,
        size: content.length,
        truncated: content.length > MAX_CHARS,
      });
      return;
    }

    // POST /write_file — sadece Lord onayından sonra Convex tarafından çağrılır
    if (req.method === 'POST' && url.pathname === '/write_file') {
      const body = await readBody(req);
      const { path: filePath, content, secret } = body;

      // Basit güvenlik: secret token kontrolü
      const WRITE_SECRET = process.env.BRIDGE_SECRET || 'kuroshin-bridge-2026';
      if (secret !== WRITE_SECRET) {
        json(res, 403, { error: 'Yetkisiz yazma girişimi — secret hatalı' });
        return;
      }

      if (!filePath || content === undefined) {
        json(res, 400, { error: 'path ve content zorunlu' });
        return;
      }

      const absPath = safePath(filePath);

      // Yedek al
      if (fs.existsSync(absPath)) {
        const backupDir = path.join(PROJECT_ROOT, 'backups', 'agent_changes');
        fs.mkdirSync(backupDir, { recursive: true });
        const backupName = path.basename(absPath) + '.' + Date.now() + '.bak';
        fs.copyFileSync(absPath, path.join(backupDir, backupName));
      }

      // Klasörü oluştur
      fs.mkdirSync(path.dirname(absPath), { recursive: true });

      // Yaz
      fs.writeFileSync(absPath, content, 'utf8');
      console.log(`[YAZILDI] ${absPath} (${content.length} karakter)`);

      json(res, 200, { ok: true, written: absPath, size: content.length });
      return;
    }

    // POST /open_url — Windows varsayilan tarayicisinda URL ac
    if (req.method === 'POST' && url.pathname === '/open_url') {
      const body = await readBody(req);
      const { url: targetUrl } = body;
      if (!targetUrl || !targetUrl.startsWith('http')) {
        json(res, 400, { error: 'Gecerli bir URL gerekli (http/https)' });
        return;
      }
      const { exec } = require('child_process');
      exec(`start "" "${targetUrl.replace(/"/g, '')}"`, (err) => {
        if (err) console.error('[open_url hata]', err.message);
      });
      json(res, 200, { ok: true, opened: targetUrl });
      return;
    }

    // GET /health
    if (url.pathname === '/health') {
      json(res, 200, { status: 'ok', port: PORT, root: PROJECT_ROOT, ts: Date.now() });
      return;
    }

    json(res, 404, { error: 'Bilinmeyen endpoint: ' + url.pathname });

  } catch (e) {
    console.error('[HATA]', e.message);
    json(res, 500, { error: e.message });
  }
});

server.listen(PORT, '127.0.0.1', () => {
  console.log(`[Kuroshin Agent Bridge] Port ${PORT} üzerinde çalışıyor`);
  console.log(`[Kuroshin Agent Bridge] Proje kökü: ${PROJECT_ROOT}`);
  console.log(`[Kuroshin Agent Bridge] Endpointler: /read_file /write_file /list_dir /health`);
});

server.on('error', (e) => {
  if (e.code === 'EADDRINUSE') {
    console.error(`[HATA] Port ${PORT} zaten kullanımda — bridge zaten çalışıyor olabilir`);
  } else {
    console.error('[HATA]', e);
  }
});
