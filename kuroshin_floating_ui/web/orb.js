// Kuroshin WebGL Orb Shader — FAZ-4 Physics Pro
// Durumlar: 0=IDLE, 1=PROCESSING, 2=DONE, 3=ALARM, 4=GHOST

(function () {
  const canvas = document.getElementById('webgl-orb');

  function syncSize() {
    const w = canvas.clientWidth  || 64;
    const h = canvas.clientHeight || 64;
    if (canvas.width !== w || canvas.height !== h) {
      canvas.width  = w;
      canvas.height = h;
    }
  }
  if (typeof ResizeObserver !== 'undefined') {
    new ResizeObserver(syncSize).observe(canvas);
  }
  syncSize();

  const STATE = { IDLE: 0, PROCESSING: 1, DONE: 2, ALARM: 3, GHOST: 4 };
  let currentState = 0;
  let doneBurst    = 0.0;
  // Su dalgalanma (ripple) — tıklanan noktadan yayılan dalga
  let ripPos = [0.0, 0.0]; // UV [-1,1] koordinatı
  let ripT   = 0.0;        // 1.0 → 0.0 azalır (~1.2s)

  window.setOrbState = function (name) {
    const prev = currentState;
    currentState = STATE[name] ?? 0;
    const btn = document.getElementById('orb-btn');
    if (!btn) return;
    if (name === 'ALARM') btn.classList.add('alarm-state');
    else btn.classList.remove('alarm-state');
    if (name === 'DONE' && prev !== STATE.DONE) doneBurst = 1.0;
  };

  const gl = canvas.getContext('webgl') || canvas.getContext('experimental-webgl');
  if (!gl) {
    canvas.style.display = 'none';
    return;
  }

  // setOrbPress burada tanımla — shader derleme hatasından bağımsız çalışsın
  let pressValue  = 0;
  let pressTarget = 0;
  window.setOrbPress = function (v) { pressTarget = Math.max(0, Math.min(1, v)); };

  const fallback = document.getElementById('orb-fallback');
  if (fallback) fallback.style.display = 'none';

  // ── Vertex Shader ──
  const vs = `
attribute vec2 a_pos;
varying   vec2 v_uv;
void main() {
  v_uv        = a_pos * 0.5 + 0.5;
  gl_Position = vec4(a_pos, 0.0, 1.0);
}`;

  // ── Fragment Shader — FAZ-4 Physics Pro ──
  const fs = `
precision highp float;
uniform float u_time;
uniform vec2  u_res;
uniform float u_state;
uniform float u_press;
uniform float u_burst;   // DONE flash (1.0→0.0)
uniform vec2  u_rip_pos; // tıklanan UV [-1,1]
uniform float u_rip_t;   // 1.0→0.0 dalga ömrü
uniform float u_bass;    // 0-1 mikrofon bass (0-215 Hz)
uniform float u_mid;     // 0-1 mikrofon mid  (215-2150 Hz)
uniform float u_treble;  // 0-1 mikrofon treble (2150+ Hz)
uniform float u_amp;     // 0-1 genel amplitude
uniform vec2  u_mag;     // fare yön vektörü normalize [-1,1]
uniform float u_pull;    // 0-1 fare yakınlık kuvveti
varying vec2  v_uv;

// Kuroshin renk paleti
const vec3 NAVY   = vec3(0.004, 0.016, 0.063);
const vec3 PURPLE = vec3(0.447, 0.063, 0.565);
const vec3 CYAN   = vec3(0.000, 0.902, 0.851);
const vec3 GREEN  = vec3(0.435, 0.980, 0.745);
const vec3 GREY   = vec3(0.200, 0.200, 0.220);

float hash(vec2 p) {
  p = fract(p * vec2(127.1, 311.7));
  p += dot(p, p + 45.32);
  return fract(p.x * p.y);
}

float noise(vec2 p) {
  vec2 i = floor(p), f = fract(p);
  f = f * f * (3.0 - 2.0 * f);
  return mix(
    mix(hash(i), hash(i + vec2(1,0)), f.x),
    mix(hash(i + vec2(0,1)), hash(i + vec2(1,1)), f.x),
    f.y
  );
}

float fbm(vec2 p) {
  float v = 0.0, a = 0.5;
  mat2 rot = mat2(1.6, 1.2, -1.2, 1.6);
  for (int i = 0; i < 5; i++) { v += a * noise(p); p = rot * p * 2.0; a *= 0.5; }
  return v;
}

// Vortex: açısal döndürme (sıvı dönme efekti)
vec2 vortex(vec2 p, float str) {
  float r = length(p);
  float angle = str * (1.0 - r);
  float s = sin(angle), c = cos(angle);
  return vec2(c * p.x - s * p.y, s * p.x + c * p.y);
}

// Yüzen partiküller (#5) — geometrik düz yükselme, ses=parlaklık nabızı
float floatParticles(vec2 uv, float ftime, float bass) {
  float v = 0.0;
  for (int i = 0; i < 8; i++) {
    float fi    = float(i);
    // Geometrik: geniş X aralığı + hash varyasyon → daha dağınık görünüm
    float px    = (fi / 7.0) * 1.60 - 0.80;
    px += (hash(vec2(fi * 3.71, 2.13)) - 0.5) * 0.14; // sabit hash (titreşmiyor)
    float phase = fract(fi * 0.137 + ftime * 0.018); // ~55sn/döngü, çok yavaş
    float py    = mix(0.82, -0.95, phase);
    vec2  pos   = vec2(px, py);
    float inOrb = step(length(pos), 0.88);
    float d     = length(uv - pos);
    // Ses → sabit parlaklık artışı (sin titreşimi yok — "hızlı" yanılsaması kalkıyor)
    float pulse = 1.0 + bass * 0.25;
    float bri   = smoothstep(0.0, 0.18, phase) * (1.0 - phase) * (1.0 - phase) * pulse;
    float dot_  = smoothstep(0.026, 0.0, d);
    float glow  = smoothstep(0.080, 0.0, d) * 0.20;
    v += inOrb * bri * (dot_ + glow);
  }
  return clamp(v, 0.0, 1.0);
}

// Sparkle: orb içinde parlayan noktalar
float sparkle(vec2 uv, float t) {
  float v = 0.0;
  for (int i = 0; i < 6; i++) {
    float fi = float(i);
    vec2 seed = vec2(fi * 1.37, fi * 2.71);
    vec2 pos  = vec2(noise(seed + t * 0.3) - 0.5, noise(seed + t * 0.3 + 5.0) - 0.5) * 0.8;
    float d   = length(uv - pos);
    float bri = noise(seed + t * 1.5 + 3.0);
    v += bri * smoothstep(0.08, 0.0, d);
  }
  return clamp(v, 0.0, 1.0);
}

void main() {
  vec2  uv_raw = (v_uv - 0.5) * 2.0;

  // Lens bulge (#3) — fare yakınken merkez şişiyor (dome/fish-eye)
  // k > 0: barrel → merkez büyüyor, kenarlar sıkışıyor
  float lensK = u_pull * 0.42;
  float rawR  = length(uv_raw);
  float lensR = rawR * (1.0 - lensK * (1.0 - rawR * rawR));
  vec2  uv    = (rawR > 0.001) ? normalize(uv_raw) * lensR : uv_raw;
  float dist  = length(uv);

  // Hız — mid frekanslar akışı hızlandırıyor
  float spd = 1.0 + u_mid * 0.6;
  if (u_state == 1.0) spd = 3.5 + u_mid * 3.0;
  if (u_state == 3.0) spd = 5.0 + u_bass * 2.0;
  if (u_state == 4.0) spd = 0.3;
  spd += u_press * 4.0;
  float t = u_time * spd;

  // Nefes — bass ile şişiyor (konuşunca / müzik çalarken orb büyür)
  float breathAmp = (u_state == 4.0) ? 0.08 : 0.04 + u_bass * 0.06;
  float breath    = sin(t * 0.5) * breathAmp + (1.0 - breathAmp);

  // Vortex kuvveti — mid frekanslar döndürüyor
  float vStr = 1.2 + u_press * 2.0 + u_mid * 0.6;
  if (u_state == 1.0) vStr = 3.0 + sin(t) * 1.5 + u_mid * 3.0;
  if (u_state == 3.0) vStr = -4.0 - u_bass * 2.0; // ters + bas güçlendirme
  if (u_state == 4.0) vStr = 0.4;
  vec2 uv_v = vortex(uv, vStr * 0.4);

  // Magnetic mouse — fluid fare yönüne doğru çekiliyor
  // u_mag: fare yön birimi, u_pull: 0(uzak)→1(üstünde)
  vec2 magBias = u_mag * u_pull * 0.22;  // max 0.22 UV offset

  // Ripple → FBM fizik displacement (dalga partikül/fluidi iter)
  vec2 ripPhys = vec2(0.0);
  if (u_rip_t > 0.0) {
    float rfade   = u_rip_t * u_rip_t;
    float relaps  = 1.0 - u_rip_t;
    vec2  rdir    = uv - u_rip_pos;
    float rd      = length(rdir);
    float wFront  = relaps * 1.6;
    // Dalga cephesindeki itme kuvveti: Gaussian × sinüs
    float push    = exp(-abs(rd - wFront) * 9.0) * sin((rd - wFront) * 18.0) * rfade;
    // Radyal yönde it (merkeze doğru ve dışa — su gerçeği)
    ripPhys = normalize(rdir + 0.0001) * push * 0.28;
  }

  // 3 katman domain warping + ripple + magnetic pull
  vec2 uv_p = uv_v + ripPhys + magBias;
  vec2 q  = vec2(fbm(uv_p + t * 0.20), fbm(uv_p + 1.0));
  vec2 r  = vec2(fbm(uv_p + 4.0 * q + t * 0.10), fbm(uv_p + 4.0 * q + 1.0));
  vec2 s2 = vec2(fbm(uv_p + 3.0 * r + t * 0.05), fbm(uv_p + 3.0 * r + 2.7));
  float f = fbm(uv_p + 4.0 * s2);

  // Renk paleti (state)
  vec3 c1 = NAVY, c2 = PURPLE, rimC = CYAN;
  if (u_state == 3.0) { c1 = vec3(0.04,0.0,0.0); c2 = vec3(0.92,0.06,0.06); rimC = vec3(1.0,0.22,0.05); }
  else if (u_state == 2.0) { c1 = vec3(0.0,0.15,0.08); c2 = GREEN; rimC = GREEN; }
  else if (u_state == 4.0) { c1 = vec3(0.04,0.04,0.05); c2 = GREY; rimC = GREY; }

  // Press: kırmızıya kaydır
  if (u_press > 0.0) {
    c1   = mix(c1,   vec3(0.05, 0.00, 0.00), u_press * 0.7);
    c2   = mix(c2,   vec3(0.85, 0.08, 0.01), u_press * 0.7);
    rimC = mix(rimC, vec3(1.00, 0.20, 0.04), u_press);
  }

  // ── FAZ-5 #4 Chromatic Aberration — prizma kenar efekti ──
  // FBM-CA procedural shaderda etkisiz → doğrudan renk kanalı manipülasyonu
  float caDist  = smoothstep(0.58, 0.99, dist);    // yalnızca dış %40 kenar bandı
  float caPull  = u_pull * 0.75;
  float caAudio = pow(u_amp, 3.0) * 0.05;          // ses: küp → neredeyse etkisiz
  float ca      = (0.40 + caPull) * caDist + caAudio;
  if (u_state == 1.0) ca *= 1.5;
  if (u_state == 3.0) ca *= 2.8;
  if (u_state == 4.0) ca *= 0.2;

  vec3 color = mix(c1, c2, f);

  // ── FAZ-5 #6 Subsurface Scattering — cam/jade derinliği, içten ışık saçılımı ──
  // sssThick: gerçek küre kalınlık haritası → merkez=1.0 (kalın), kenar=0.0 (ince)
  float sssThick = sqrt(max(0.0, 1.0 - dist * dist));
  // tek yumuşak merkez glow (Gaussian ring yok — dağınık iç ışık hissi)
  float sssGlow  = pow(sssThick, 1.4) * 0.62;
  // nefes + bass senkron
  float sssMod   = (1.0 + sin(t * 0.5) * 0.08) * (1.0 + u_bass * 0.25);
  if (u_state == 4.0) sssMod *= 0.30;
  vec3 sssColor  = rimC * 0.50 + vec3(0.02, 0.01, 0.08);
  color += sssColor * sssGlow * sssMod;

  // Dış rim: kırmızı saçak (prizma kırmızıyı en çok kırar)
  color.r += ca * 0.85;
  color.g -= ca * 0.30;
  color.b -= ca * 0.42;

  // İç kenar bandı: mavi/cyan geri dönüşü → net R/B split hissi
  float caInner = (1.0 - smoothstep(0.56, 0.80, dist)) * (1.0 - smoothstep(0.30, 0.56, dist)) * ca * 0.65;
  color.b += caInner * 0.58;
  color.r -= caInner * 0.22;

  // Sparkle — fare çekimine + treble'a tepki veriyor
  if (u_state == 0.0 || u_state == 2.0) {
    float sp = sparkle((uv + magBias * 0.65) * 0.9, t * 0.4);
    color += rimC * sp * (0.6 + u_treble * 1.4);
  }

  // Yüzen partiküller (#5) — IDLE: orb içinden yukarı yükselen parıltı
  // uv_raw kullan: lens distorsiyonu partikülleri titretiyordu (hız yanılsaması)
  if (u_state == 0.0) {
    float fp = floatParticles(uv_raw, u_time, u_bass);
    color += rimC * fp * 0.88;
  }

  // Press dolum (dıştan içe)
  if (u_press > 0.0) {
    float threshold = 1.0 - u_press * 0.92;
    float fill = smoothstep(threshold - 0.12, threshold + 0.04, dist);
    vec3 fireColor = vec3(0.95, 0.15, 0.02) * (0.75 + 0.25 * sin(t * 10.0));
    color = mix(color, fireColor, fill * sqrt(u_press));
  }

  // Iridescent rim — treble parlatıyor + fare tarafında ekstra parlaklık
  float rimR = smoothstep(0.68, 1.0, dist * breath);
  float rimG = smoothstep(0.72, 1.0, dist * breath);
  float rimB = smoothstep(0.70, 1.0, dist * breath);
  // Fare yönündeki rim kısmı daha parlak (dot product: fare yönüne bakan yüzey)
  float magGlow = max(0.0, dot(normalize(uv + 0.001), u_mag)) * u_pull * 0.6;
  float rimMod  = 0.5 + 0.5 * sin(t + f * 10.0) + u_treble * 0.9 + magGlow;
  color.r = mix(color.r, rimC.r, rimR * rimMod);
  color.g = mix(color.g, rimC.g, rimG * rimMod);
  color.b = mix(color.b, rimC.b, rimB * rimMod * 1.2);
  // Genel ses pulse — tüm orb amplitude ile nefes alır
  color *= (1.0 + u_amp * 0.28);

  // PROCESSING: çift tarama halkası
  if (u_state == 1.0) {
    float ring1 = sin(dist * 20.0 - t * 15.0) * 0.5 + 0.5;
    float ring2 = sin(dist * 12.0 + t * 10.0) * 0.5 + 0.5;
    ring1 *= ring1;
    ring2 *= ring2 * 0.6;
    float rMask = smoothstep(0.10, 0.45, dist) * (1.0 - smoothstep(0.55, 0.92, dist));
    color = mix(color, vec3(0.05, 0.35, 0.90), 0.35);
    color += vec3(0.15, 0.75, 1.0) * (ring1 + ring2) * rMask * 0.85;
  }

  // ALARM: nabız + titreme
  if (u_state == 3.0) {
    float pulse  = sin(t * 6.0) * 0.22 + 0.78;
    float jitter = noise(uv * 8.0 + t * 12.0) * 0.08;
    color *= (pulse + jitter);
  }

  // DONE: flash burst (u_burst 1→0)
  if (u_burst > 0.0) {
    float ring = smoothstep(u_burst, u_burst - 0.15, dist);
    color = mix(color, vec3(1.0), ring * u_burst * 2.5);
    color += GREEN * (1.0 - dist) * u_burst * 1.2;
  }

  // Su dalgalanma ripple — tıklanan noktadan yayılan halkalar
  if (u_rip_t > 0.0) {
    float fade    = u_rip_t * u_rip_t;            // ease-out fade
    float elapsed = 1.0 - u_rip_t;                // 0→1 zaman ilerledikçe
    vec2  ripDir  = uv - u_rip_pos;
    float rd      = length(ripDir);
    // UV distortion: optik kırılma — ripple fizik displacement ile senkron
    float wFront  = elapsed * 1.6;
    float distort = exp(-abs(rd - wFront) * 14.0) * sin((rd - wFront) * 28.0) * 0.055 * fade;
    vec2  uvD     = uv_p + normalize(ripDir + 0.0001) * distort;
    float fD      = fbm(uvD + 4.0 * s2);
    color         = mix(color, mix(c1, c2, fD), abs(distort) * 20.0 * fade);
    // 3 yayılan halka (dış kenarlarda sönümleme)
    float ripple  = 0.0;
    for (int i = 0; i < 3; i++) {
      float fi  = float(i);
      float wc  = elapsed * 1.6 - fi * 0.18;
      float ring = sin((rd - wc) * 32.0) * exp(-abs(rd - wc) * 10.0);
      ripple   += ring * (1.0 - fi * 0.28);
    }
    ripple *= fade;
    color  += rimC * max(0.0, ripple) * 0.55;
    color  -= vec3(1.0) * max(0.0, -ripple) * 0.18;
  }

  // Daire kırpma
  float alpha = smoothstep(1.0, 0.97, dist);

  gl_FragColor = vec4(color, alpha);
}`;

  function makeShader(type, src) {
    const s = gl.createShader(type);
    gl.shaderSource(s, src);
    gl.compileShader(s);
    if (!gl.getShaderParameter(s, gl.COMPILE_STATUS)) {
      console.error('Shader hata:', gl.getShaderInfoLog(s));
      return null;
    }
    return s;
  }

  const prog = gl.createProgram();
  gl.attachShader(prog, makeShader(gl.VERTEX_SHADER, vs));
  gl.attachShader(prog, makeShader(gl.FRAGMENT_SHADER, fs));
  gl.linkProgram(prog);
  if (!gl.getProgramParameter(prog, gl.LINK_STATUS)) {
    console.error('Program hata:', gl.getProgramInfoLog(prog));
    return;
  }
  gl.useProgram(prog);

  const buf = gl.createBuffer();
  gl.bindBuffer(gl.ARRAY_BUFFER, buf);
  gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([-1,-1, 1,-1, -1,1, 1,1]), gl.STATIC_DRAW);

  const aPos   = gl.getAttribLocation(prog, 'a_pos');
  gl.enableVertexAttribArray(aPos);
  gl.vertexAttribPointer(aPos, 2, gl.FLOAT, false, 0, 0);

  const uTime   = gl.getUniformLocation(prog, 'u_time');
  const uRes    = gl.getUniformLocation(prog, 'u_res');
  const uState  = gl.getUniformLocation(prog, 'u_state');
  const uPress  = gl.getUniformLocation(prog, 'u_press');
  const uBurst  = gl.getUniformLocation(prog, 'u_burst');
  const uRipPos  = gl.getUniformLocation(prog, 'u_rip_pos');
  const uRipT    = gl.getUniformLocation(prog, 'u_rip_t');
  const uBass    = gl.getUniformLocation(prog, 'u_bass');
  const uMid     = gl.getUniformLocation(prog, 'u_mid');
  const uTreble  = gl.getUniformLocation(prog, 'u_treble');
  const uAmp     = gl.getUniformLocation(prog, 'u_amp');
  const uMag     = gl.getUniformLocation(prog, 'u_mag');
  const uPull    = gl.getUniformLocation(prog, 'u_pull');

  gl.enable(gl.BLEND);
  gl.blendFunc(gl.SRC_ALPHA, gl.ONE_MINUS_SRC_ALPHA);

  // Tıklama ripple — canvas'ta pointerdown anında UV koordinatı hesapla
  canvas.addEventListener('pointerdown', function (e) {
    const rect = canvas.getBoundingClientRect();
    const nx   = (e.clientX - rect.left)  / rect.width;
    const ny   = (e.clientY - rect.top)   / rect.height;
    // UV [-1,1] aralığına çevir (Y ekseni WebGL'de tersine)
    ripPos = [(nx - 0.5) * 2.0, -(ny - 0.5) * 2.0];
    ripT   = 1.0;
  });

  const _baseSetOrbState = window.setOrbState;
  window.setOrbState = function (name) {
    _baseSetOrbState(name);
    currentState = STATE[name] ?? 0;
  };

  function render(t) {
    if (typeof ResizeObserver === 'undefined') syncSize();
    // smooth lerp press
    pressValue += (pressTarget - pressValue) * 0.25;
    if (pressValue < 0.001) pressValue = 0;
    // DONE burst decay (~0.8s @ 60fps)
    if (doneBurst > 0) doneBurst = Math.max(0, doneBurst - 0.020);
    // Ripple decay (~1.2s @ 60fps)
    if (ripT > 0) ripT = Math.max(0, ripT - 0.014);

    gl.viewport(0, 0, canvas.width, canvas.height);
    gl.clearColor(0, 0, 0, 0);
    gl.clear(gl.COLOR_BUFFER_BIT);
    gl.uniform1f(uTime,   t * 0.001);
    gl.uniform2f(uRes,    canvas.width, canvas.height);
    gl.uniform1f(uState,  currentState);
    gl.uniform1f(uPress,  pressValue);
    gl.uniform1f(uBurst,  doneBurst);
    gl.uniform2f(uRipPos, ripPos[0], ripPos[1]);
    gl.uniform1f(uRipT,   ripT);
    // Ses reaktif uniform'lar — audioData yoksa sıfır (sessiz)
    const ad = window.audioData     || { bass: 0, mid: 0, treble: 0, amp: 0 };
    const mi = window.mouseInfluence || { nx: 0, ny: 0, pull: 0 };
    gl.uniform1f(uBass,   ad.bass);
    gl.uniform1f(uMid,    ad.mid);
    gl.uniform1f(uTreble, ad.treble);
    gl.uniform1f(uAmp,    ad.amp);
    gl.uniform2f(uMag,    mi.nx, mi.ny);
    gl.uniform1f(uPull,   mi.pull);
    gl.drawArrays(gl.TRIANGLE_STRIP, 0, 4);
    requestAnimationFrame(render);
  }

  render(0);
})();
