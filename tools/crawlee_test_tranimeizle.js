// Crawlee PlaywrightCrawler ile tranimeizle.co test
const { PlaywrightCrawler } = require('./node_modules/crawlee/index.js');

const URL = process.argv[2] || 'https://www.tranimeizle.co/dungeon-meshi-1-bolum-izle';

let pageTitle = '';
let iframes = [];
let videos = [];
let networkEmbeds = [];

const EMBED_KEYWORDS = ['.m3u8', '.mp4', 'filemoon', 'vidmoly', 'sibnet',
  'ok.ru', 'mail.ru', 'doodstream', 'streamtape', 'speedfiles', 'voe.sx', 'mixdrop'];

const crawler = new PlaywrightCrawler({
  headless: true,
  requestHandlerTimeoutSecs: 60,
  maxRequestsPerCrawl: 1,
  navigationTimeoutSecs: 30,
  launchContext: {
    launchOptions: {
      executablePath: '/root/.cache/ms-playwright/chromium-1208/chrome-linux64/chrome',
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
    // Stealth: navigator.webdriver gizle
    await page.addInitScript(() => {
      Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
      Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3] });
      window.chrome = { runtime: {} };
    });

    // Network isteklerini izle
    page.on('request', req => {
      const u = req.url();
      if (EMBED_KEYWORDS.some(k => u.includes(k))) {
        networkEmbeds.push(u);
      }
    });

    await page.waitForLoadState('domcontentloaded', { timeout: 20000 }).catch(() => {});
    pageTitle = await page.title().catch(() => '');
    console.log('Sayfa başlığı:', pageTitle);

    // networkidle bekle
    await page.waitForLoadState('networkidle', { timeout: 8000 }).catch(() => {});

    // 15sn bekle (player yüklensin)
    await new Promise(r => setTimeout(r, 15000));

    // Server sekmesi tıkla (tranimeizle.co)
    const serverSelectors = [
      '.players a:first-child',
      '.eps-server:first-child a',
      '.serverList li:first-child a',
      '.player-options a:first-child',
      '[data-video]:first-child',
    ];
    for (const sel of serverSelectors) {
      try {
        const el = page.locator(sel).first();
        if (await el.isVisible({ timeout: 1000 })) {
          await el.click();
          console.log('Sunucu sekmesi tiklandi:', sel);
          await new Promise(r => setTimeout(r, 3000));
          break;
        }
      } catch {}
    }

    await new Promise(r => setTimeout(r, 5000));

    // JS ile iframe/video topla
    const jsSrcs = await page.evaluate(() => {
      const r = [];
      document.querySelectorAll('iframe, frame').forEach(el => {
        const s = el.src || el.getAttribute('data-src') || el.getAttribute('data-lazy-src');
        if (s && s.startsWith('http')) r.push('iframe::' + s);
      });
      document.querySelectorAll('video, video source').forEach(el => {
        const s = el.src || el.currentSrc || el.getAttribute('data-src');
        if (s && s.startsWith('http')) r.push('video::' + s);
      });
      return [...new Set(r)];
    }).catch(() => []);

    iframes = jsSrcs.filter(s => s.startsWith('iframe::'));
    videos = jsSrcs.filter(s => s.startsWith('video::'));

    const html = await page.content().catch(() => '');
    console.log('HTML uzunluk:', html.length);
  },
  failedRequestHandler({ request }, err) {
    console.error('FAILED:', err?.message || err);
  },
});

console.log('URL:', URL);
crawler.run([URL]).then(() => {
  console.log('\n=== SONUÇ ===');
  console.log('Sayfa başlığı:', pageTitle);
  console.log('iframe sayısı:', iframes.length);
  iframes.forEach(s => console.log(' ', s.slice(0, 120)));
  console.log('video sayısı:', videos.length);
  videos.forEach(s => console.log(' ', s.slice(0, 120)));
  console.log('Network embed:', networkEmbeds.length);
  networkEmbeds.forEach(u => console.log(' ', u.slice(0, 120)));

  const CF = pageTitle.toLowerCase().includes('just a moment') ||
             pageTitle.toLowerCase().includes('bot kontrol') ||
             pageTitle.toLowerCase().includes('checking');
  if (CF) console.log('\n⚠️  BOT SAYFASI TESPİT EDİLDİ');
  else console.log('\n✅ Bot sayfası yok — gerçek sayfa yüklendi');
}).catch(e => console.error('Crawler hatası:', e.message));
