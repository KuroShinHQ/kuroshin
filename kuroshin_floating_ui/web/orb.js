// Kuroshin WebGL Orb Shader
// Kaynak: stitch shader/code.html + project_circle GLSL
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

  // setOrbState WebGL'den bağımsız — CSS class + shader state
  const STATE = { IDLE: 0, PROCESSING: 1, DONE: 2, ALARM: 3, GHOST: 4 };
  let currentState = 0;

  window.setOrbState = function (name) {
    currentState = STATE[name] ?? 0;
    const btn = document.getElementById('orb-btn');
    if (!btn) return;
    if (name === 'ALARM') btn.classList.add('alarm-state');
    else btn.classList.remove('alarm-state');
  };

  const gl = canvas.getContext('webgl') || canvas.getContext('experimental-webgl');
  if (!gl) {
    // WebGL yok — fallback dot göster, canvas gizle; setOrbState CSS-only çalışır
    canvas.style.display = 'none';
    return;
  }

  // WebGL çalışıyor → fallback gizle
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

  // ── Fragment Shader ──
  const fs = `
precision highp float;
uniform float u_time;
uniform vec2  u_res;
uniform float u_state; // 0=IDLE 1=PROC 2=DONE 3=ALARM 4=GHOST
uniform float u_press; // 0.0-1.0: long-press RAM dolum animasyonu
varying vec2  v_uv;

const vec3 NAVY   = vec3(0.004, 0.016, 0.063);
const vec3 PURPLE = vec3(0.447, 0.063, 0.565);
const vec3 CYAN   = vec3(0.000, 0.902, 0.851);
const vec3 ALARM  = vec3(1.000, 0.290, 0.180);
const vec3 GREEN  = vec3(0.435, 0.980, 0.745);
const vec3 GREY   = vec3(0.200, 0.200, 0.220);

float hash(vec2 p) {
  return fract(sin(dot(p, vec2(127.1,311.7))) * 43758.5453);
}

float noise(vec2 p) {
  vec2 i = floor(p), f = fract(p);
  f = f*f*(3.0-2.0*f);
  return mix(
    mix(hash(i), hash(i+vec2(1,0)), f.x),
    mix(hash(i+vec2(0,1)), hash(i+vec2(1,1)), f.x),
    f.y
  );
}

float fbm(vec2 p) {
  float v=0.0, a=0.5;
  mat2 rot = mat2(1.6,1.2,-1.2,1.6);
  for (int i=0;i<5;i++) { v+=a*noise(p); p=rot*p*2.0; a*=0.5; }
  return v;
}

void main() {
  vec2  uv   = (v_uv - 0.5) * 2.0;
  float dist = length(uv);

  // Hız (state + press artışı)
  float spd = 1.0;
  if (u_state==1.0) spd=3.5;
  if (u_state==3.0) spd=5.0;
  if (u_state==4.0) spd=0.3; // GHOST: yavaş
  spd += u_press * 4.0;       // basılı → hızlanır
  float t = u_time * spd;

  // Nefes
  float breath = sin(t*0.5)*0.04 + 0.96;

  // FBM gürültüsü
  vec2 q = vec2(fbm(uv+t*0.2), fbm(uv+1.0));
  vec2 r = vec2(fbm(uv+4.0*q+t*0.1), fbm(uv+4.0*q+1.0));
  float f = fbm(uv + 4.0*r);

  // Renk paleti (state'e göre)
  vec3 c1 = NAVY, c2 = PURPLE, rimC = CYAN;
  if (u_state==3.0) { c1=vec3(0.04,0.0,0.0); c2=vec3(0.92,0.06,0.06); rimC=vec3(1.0,0.22,0.05); }
  else if (u_state==2.0) { c1=vec3(0,0.15,0.08); c2=GREEN; rimC=GREEN; }
  else if (u_state==4.0) { c1=vec3(0.04,0.04,0.05); c2=GREY; rimC=GREY; }

  // Press: rengi kırmızıya kaydır (smooth, sadece FBM paletine)
  if (u_press > 0.0) {
    c1   = mix(c1,   vec3(0.05, 0.00, 0.00), u_press * 0.7);
    c2   = mix(c2,   vec3(0.85, 0.08, 0.01), u_press * 0.7);
    rimC = mix(rimC, vec3(1.00, 0.20, 0.04), u_press);
  }

  vec3 color = mix(c1, c2, f);

  // Press: dışarıdan içe dolum — u_press=0 tamamen görünmez
  // threshold=1.0(dışarıda) → 0.08(neredeyse tümü), fill sadece dist>threshold bölgesine
  if (u_press > 0.0) {
    float threshold = 1.0 - u_press * 0.92;
    float fill = smoothstep(threshold - 0.12, threshold + 0.04, dist);
    vec3 fireColor = vec3(0.95, 0.15, 0.02) * (0.75 + 0.25 * sin(t * 10.0));
    color = mix(color, fireColor, fill * sqrt(u_press));
  }

  // Rim glow (Stitch-inspired: 0.70 tighter)
  float rim = smoothstep(0.70, 1.0, dist * breath);
  color = mix(color, rimC, rim*(0.5+0.5*sin(t+f*10.0)));

  // PROCESSING: dönen tarama halkası (belirgin)
  if (u_state==1.0) {
    // ring: radyal sinüs dalgası (içten dışa döner)
    float ring  = sin(dist*20.0 - t*15.0)*0.5 + 0.5;
    ring = ring * ring; // keskinleştir
    // rMask: orb merkezinden kenara bant (edge0 < edge1 zorunlu)
    float rMask = smoothstep(0.10, 0.45, dist) * (1.0 - smoothstep(0.55, 0.92, dist));
    // temel rengi de aydınlat
    color = mix(color, vec3(0.05, 0.35, 0.90), 0.35);
    color += vec3(0.15, 0.75, 1.0) * ring * rMask * 0.90;
  }

  // ALARM: nabız (sinüs darbe)
  if (u_state==3.0) {
    float pulse = sin(t*6.0)*0.22 + 0.78;
    color *= pulse;
  }

  // Daire kırpma (Stitch-inspired: 0.97 daha keskin kenar)
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

  const aPos  = gl.getAttribLocation(prog, 'a_pos');
  gl.enableVertexAttribArray(aPos);
  gl.vertexAttribPointer(aPos, 2, gl.FLOAT, false, 0, 0);

  const uTime  = gl.getUniformLocation(prog, 'u_time');
  const uRes   = gl.getUniformLocation(prog, 'u_res');
  const uState = gl.getUniformLocation(prog, 'u_state');
  const uPress = gl.getUniformLocation(prog, 'u_press');

  gl.enable(gl.BLEND);
  gl.blendFunc(gl.SRC_ALPHA, gl.ONE_MINUS_SRC_ALPHA);

  // press değeri — lerp ile smooth geçiş (ani flash engeli)
  let pressValue  = 0;
  let pressTarget = 0;
  window.setOrbPress = function (v) { pressTarget = Math.max(0, Math.min(1, v)); };

  // setOrbState shader tarafını da günceller (WebGL uniform)
  const _baseSetOrbState = window.setOrbState;
  window.setOrbState = function (name) {
    _baseSetOrbState(name);
    currentState = STATE[name] ?? 0;
  };

  function render(t) {
    if (typeof ResizeObserver === 'undefined') syncSize();
    // smooth lerp: her frame'de hedefe %25 yaklaş (~400ms tam geçiş @ 60fps)
    pressValue += (pressTarget - pressValue) * 0.25;
    if (pressValue < 0.001) pressValue = 0;
    gl.viewport(0, 0, canvas.width, canvas.height);
    gl.clearColor(0, 0, 0, 0);
    gl.clear(gl.COLOR_BUFFER_BIT);
    gl.uniform1f(uTime, t * 0.001);
    gl.uniform2f(uRes, canvas.width, canvas.height);
    gl.uniform1f(uState, currentState);
    gl.uniform1f(uPress, pressValue);
    gl.drawArrays(gl.TRIANGLE_STRIP, 0, 4);
    requestAnimationFrame(render);
  }

  render(0);
})();
