// Kuroshin Audio Reactive — Web Audio API FFT Analyzer
// Bass/Mid/Treble → window.audioData → orb.js shader uniforms
// sampleRate=44100, fftSize=1024, binWidth≈43 Hz
//   bass:   bin 0-5    → 0-215 Hz   (davul, bas)
//   mid:    bin 6-50   → 215-2150 Hz (vokal, melodi)
//   treble: bin 51-200 → 2150-8620 Hz (tiz, nefes, sibilans)

(function () {
  let analyser = null;
  let dataArr  = null;
  let active   = false;

  window.audioData = { bass: 0, mid: 0, treble: 0, amp: 0 };

  async function startAudio() {
    if (active) return;
    try {
      const stream   = await navigator.mediaDevices.getUserMedia({ audio: true, video: false });
      const audioCtx = new (window.AudioContext || window.webkitAudioContext)();
      analyser = audioCtx.createAnalyser();
      analyser.fftSize                = 1024;
      analyser.smoothingTimeConstant  = 0.75;  // çok keskin değil, akıcı
      analyser.minDecibels            = -90;
      analyser.maxDecibels            = -10;
      audioCtx.createMediaStreamSource(stream).connect(analyser);
      dataArr = new Uint8Array(analyser.frequencyBinCount); // 512 bin
      active  = true;
      tick();
    } catch (_) {
      // Mikrofon izni yok veya hata — audioData sıfır kalır, orb normal davranır
    }
  }

  function avg(s, e) {
    let sum = 0;
    for (let i = s; i <= e; i++) sum += dataArr[i];
    return sum / ((e - s + 1) * 255);
  }

  function tick() {
    if (!active) return;
    analyser.getByteFrequencyData(dataArr);
    const b = avg(0,   5);    // bass
    const m = avg(6,   50);   // mid
    const t = avg(51,  200);  // treble
    const a = avg(0,   200);  // genel amplitude
    // Soft-clip: güçlü sesler çok abartısız davransın
    window.audioData = {
      bass:   Math.min(b * 1.8, 1.0),
      mid:    Math.min(m * 2.2, 1.0),
      treble: Math.min(t * 2.5, 1.0),
      amp:    Math.min(a * 2.0, 1.0),
    };
    requestAnimationFrame(tick);
  }

  // İlk pointer event'te başlat (getUserMedia user-gesture gerektirir)
  document.addEventListener('pointerdown', function onFirst() {
    startAudio();
  }, { once: true });

  window.startAudioReactive = startAudio;
})();
