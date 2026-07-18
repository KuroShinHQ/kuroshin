// Crawlee Bridge'e tranimeizle.co stealth testi
const http = require('http');

const body = JSON.stringify({
  url: 'https://www.tranimeizle.co/dungeon-meshi-1-bolum-izle',
  mode: 'stealth'
});

const req = http.request({
  hostname: '127.0.0.1',
  port: 3006,
  path: '/crawl',
  method: 'POST',
  headers: { 'Content-Type': 'application/json', 'Content-Length': Buffer.byteLength(body) }
}, res => {
  let data = '';
  res.on('data', c => data += c);
  res.on('end', () => {
    try {
      const j = JSON.parse(data);
      console.log('ok:', j.ok);
      console.log('mod:', j.mode);
      console.log('süre:', j.elapsed + 's');
      console.log('uzunluk:', j.length);
      console.log('içerik baş (500):', (j.content || '').slice(0, 500));
    } catch(e) {
      console.log('RAW:', data.slice(0, 500));
    }
  });
});

req.on('error', e => console.error('HATA:', e.message));
req.write(body);
req.end();
