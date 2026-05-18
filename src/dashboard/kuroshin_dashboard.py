#!/usr/bin/env python3
"""
Kuroshin Dashboard v1.0
Saf stdlib HTTP server — localhost:7070
Python 3.8+ uyumlu, sifir bagimlilik.
"""
import subprocess, json, time
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed

PORT = 8888
LOG_DIR    = Path(r"C:\Kuroshin\logs")
MOOD_PATH  = Path(r"C:\Kuroshin\soul\mood_state.json")
IC_SES_LOG = Path(r"C:\Kuroshin\logs\ic_ses.log")

SERVICES = [
    {"name": "Qwen3-8B Abliterated (llama-server)", "port": 8080, "path": "/health"},
    {"name": "LiteLLM Proxy",         "port": 6000, "path": "/v1/models"},
    {"name": "LitServe",              "port": 6001, "path": "/health"},
    {"name": "ChromaDB",              "port": 8100, "path": "/api/v2/heartbeat"},
    {"name": "Walker Agent",          "port": 9002, "path": "/status"},
    {"name": "Agent Bridge",          "port": 3005, "path": "/health"},
    {"name": "Nuclear Search",        "port": 8091, "path": "/search?q=test"},
    {"name": "OpenClaw",              "port": 18789, "path": "/"},
]


def check_port(port, path):
    try:
        req = urllib.request.Request(f"http://127.0.0.1:{port}{path}")
        with urllib.request.urlopen(req, timeout=3) as r:
            return {"status": "UP", "code": str(r.status)}
    except Exception as e:
        code = str(getattr(e, "code", "ERR"))
        ok = code in ("200","201","204","401","405")
        return {"status": "UP" if ok else "DOWN", "code": code}


def get_gpu():
    try:
        r = subprocess.run(
            ["nvidia-smi","--query-gpu=memory.used,memory.total,utilization.gpu",
             "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=5)
        p = [x.strip() for x in r.stdout.strip().split(",")]
        if len(p) == 3:
            return {"used_mb": int(p[0]), "total_mb": int(p[1]), "util_pct": int(p[2])}
    except Exception:
        pass
    return {"used_mb": 0, "total_mb": 8188, "util_pct": 0}


def get_soul_json():
    result = {"mood": {}, "ic_ses": [], "ilgi_skoru": 0.5, "son_guncelleme": ""}
    try:
        mood = json.loads(MOOD_PATH.read_text(encoding="utf-8"))
        result["mood"] = mood.get("duygular", {})
        result["ilgi_skoru"] = mood.get("odul_mekanizmasi", {}).get("ilgi_skoru", 0.5)
        result["son_guncelleme"] = mood.get("_son_guncelleme", "")
    except Exception:
        pass
    try:
        lines = IC_SES_LOG.read_text(encoding="utf-8").strip().split("\n")
        # Son 6 satırı al, boşları temizle
        result["ic_ses"] = [l for l in lines[-6:] if l.strip()]
    except Exception:
        pass
    return result


def get_status_json():
    def check_one(s):
        c = check_port(s["port"], s["path"])
        return {"name": s["name"], "port": s["port"],
                "status": c["status"], "code": c["code"]}

    with ThreadPoolExecutor(max_workers=8) as ex:
        svcs = list(ex.map(check_one, SERVICES))

    gpu = get_gpu()
    up = sum(1 for s in svcs if s["status"] == "UP")
    return {"services": svcs, "gpu": gpu,
            "summary": {"up": up, "total": len(svcs),
                        "pct": round(up * 100 / len(svcs))}}


HTML = r"""<!DOCTYPE html>
<html lang="tr"><head>
<meta charset="UTF-8"><title>Kuroshin Dashboard</title>
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{background:#0a0a0f;color:#e0e0e0;font-family:'Courier New',monospace;padding:20px}
h1{color:#00ff88;font-size:1.4em;margin-bottom:4px}
.sub{color:#555;font-size:.78em;margin-bottom:20px}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:12px}
.card{background:#111;border:1px solid #1e1e1e;border-radius:6px;padding:14px}
.card.soul{border-color:#2a1a3a;grid-column:1/-1}
.card h2{font-size:.8em;color:#666;margin-bottom:12px;text-transform:uppercase;letter-spacing:2px}
.row{display:flex;justify-content:space-between;align-items:center;padding:5px 0;border-bottom:1px solid #151515}
.row:last-child{border-bottom:none}
.nm{font-size:.82em}
.badge{font-size:.72em;padding:2px 8px;border-radius:10px;font-weight:bold}
.UP{background:#0d2e1a;color:#00ff88;border:1px solid #00ff8855}
.DOWN{background:#2e0d0d;color:#ff4444;border:1px solid #ff444455}
.bar-bg{background:#1a1a1a;border-radius:3px;height:8px;margin-top:6px}
.bar{height:8px;border-radius:3px;background:linear-gradient(90deg,#00ff88,#ffaa00);transition:width .6s}
.lbl{font-size:.72em;color:#555;margin-top:3px}
.big{font-size:1.05em;color:#00ff88}
/* Duygu grid */
.duygu-grid{display:grid;grid-template-columns:repeat(5,1fr);gap:8px;margin-top:4px}
.duygu{text-align:center}
.duygu-name{font-size:.65em;color:#555;margin-bottom:3px;text-transform:uppercase}
.duygu-bar-bg{background:#1a1a1a;border-radius:2px;height:60px;display:flex;align-items:flex-end}
.duygu-bar{width:100%;border-radius:2px;transition:height .6s;min-height:2px}
.duygu-val{font-size:.7em;color:#888;margin-top:3px}
/* İç ses */
.ic-ses-box{background:#0d0d15;border:1px solid #1a1a2a;border-radius:4px;padding:10px;margin-top:10px;max-height:160px;overflow-y:auto}
.ic-ses-line{font-size:.75em;color:#7a7a9a;padding:3px 0;border-bottom:1px solid #111}
.ic-ses-line.think{color:#9a8aaa}
.ic-ses-line:last-child{border-bottom:none;color:#c0b0d0}
/* İlgi skoru */
.ilgi-wrap{margin-top:10px}
.ilgi-label{font-size:.72em;color:#666;margin-bottom:4px}
.ilgi-bar-bg{background:#1a1a1a;border-radius:3px;height:6px}
.ilgi-bar{height:6px;border-radius:3px;background:linear-gradient(90deg,#6644aa,#cc44ff);transition:width .6s}
</style></head><body>
<h1>&#128081; KUROSHIN COMMAND CENTER</h1>
<div class="sub">Her 5 saniyede guncellenir &mdash; <span id="ts"></span></div>
<div class="grid" id="grid"><div class="card"><h2>Yukleniyor...</h2></div></div>
<script>
const DUYGU_RENK={merak:'#44aaff',sogukkan:'#aaaaff',gurur:'#ffaa44',yorgunluk:'#666688',huzun:'#4466aa',ofke:'#ff4444',heyecan:'#ffff44',tatminsizlik:'#ff8844',derin_dusunce:'#aa44ff',bagli_hissetme:'#44ffaa'};

function duyguBar(k,v){
  const h=Math.round(v*58)+2;
  const r=DUYGU_RENK[k]||'#888';
  return '<div class="duygu"><div class="duygu-name">'+k.replace('_',' ')+'</div>'+
    '<div class="duygu-bar-bg"><div class="duygu-bar" style="height:'+h+'px;background:'+r+'"></div></div>'+
    '<div class="duygu-val">'+v.toFixed(2)+'</div></div>';
}

async function load(){
  try{
    const [ds,ss]=await Promise.all([
      fetch('/api/status').then(r=>r.json()),
      fetch('/api/soul').then(r=>r.json())
    ]);
    document.getElementById('ts').textContent=new Date().toLocaleTimeString('tr-TR');
    const g=ds.gpu,pct=Math.round(g.used_mb*100/g.total_mb),s=ds.summary;

    const ozet='<div class="card"><h2>Sistem Ozeti</h2>'+
      '<div class="row"><span class="nm">Aktif Servis</span><span class="big">'+s.up+'/'+s.total+'</span></div>'+
      '<div class="row"><span class="nm">GPU VRAM</span><span class="badge '+(pct>85?'DOWN':'UP')+'">'+g.used_mb+' / '+g.total_mb+' MB</span></div>'+
      '<div class="bar-bg"><div class="bar" style="width:'+pct+'%"></div></div>'+
      '<div class="lbl">%'+pct+' dolu | Islem: %'+g.util_pct+'</div></div>';

    const svcler='<div class="card"><h2>Servisler</h2>'+
      ds.services.map(sv=>'<div class="row"><span class="nm">'+sv.name+'</span><span class="badge '+sv.status+'">'+sv.status+'</span></div>').join('')+
      '</div>';

    const ilgiPct=Math.round((ss.ilgi_skoru||0)*100);
    const duyguHTML=Object.entries(ss.mood||{}).map(([k,v])=>duyguBar(k,v)).join('');
    const icSesHTML=(ss.ic_ses||[]).map(l=>{
      const isThink=l.includes('[İÇ SES]');
      return '<div class="ic-ses-line'+(isThink?' think':'')+'">'+l.replace(/</g,'&lt;')+'</div>';
    }).join('');

    const ruh='<div class="card soul"><h2>&#129504; Kuroshin Ruh Hali &nbsp;<span style="color:#444;font-size:.8em">'+
      (ss.son_guncelleme||'')+'</span></h2>'+
      '<div class="ilgi-wrap"><div class="ilgi-label">İlgi Skoru (kuroshin_user aktivitesi): %'+ilgiPct+'</div>'+
      '<div class="ilgi-bar-bg"><div class="ilgi-bar" style="width:'+ilgiPct+'%"></div></div></div>'+
      '<div class="duygu-grid" style="margin-top:14px">'+duyguHTML+'</div>'+
      '<div style="margin-top:14px;font-size:.75em;color:#555;margin-bottom:6px">İÇ SES KAYITLARI</div>'+
      '<div class="ic-ses-box">'+
      (icSesHTML||'<div class="ic-ses-line" style="color:#333">Henuz kayit yok...</div>')+
      '</div></div>';

    document.getElementById('grid').innerHTML=ozet+svcler+ruh;
  }catch(e){
    document.getElementById('grid').innerHTML='<div class="card"><h2>Baglanti hatasi</h2><p style="color:#555;font-size:.8em;margin-top:8px">'+e+'</p></div>';
  }
}
load();setInterval(load,5000);
</script></body></html>"""


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a): pass  # sessiz mod

    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/api/status":
            data = json.dumps(get_status_json()).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
        elif path == "/api/soul":
            data = json.dumps(get_soul_json(), ensure_ascii=False).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
        else:
            body = HTML.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)


if __name__ == "__main__":
    server = HTTPServer(("0.0.0.0", PORT), Handler)
    print(f"Kuroshin Dashboard baslatiliyor -> http://localhost:{PORT}")
    server.serve_forever()
