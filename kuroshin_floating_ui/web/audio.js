// Kuroshin Audio Reactive — Web Audio API FFT Analyzer
// Bass/Mid/Treble → window.audioData → orb.js shader uniforms
//
// Smooth teknik (YouTube kalitesi):
//   1. smoothingTimeConstant=0.88 → FFT kendisi zaten yumuşak
//   2. EMA attack/release: ses yükselince hızlı (0.3), düşünce yavaş (0.07)
//   3. Soft-clip: 1.0 üzerini kesmek yerine tanh ile yumuşak sınır

(function () {
  let analyser  = null;
  let dataArr   = null;
  let active    = false;

  // EMA önceki değerler
  let _prev = { bass: 0, mid: 0, treble: 0, amp: 0 };

  window.audioData = { bass: 0, mid: 0, treble: 0, amp: 0 };

  // Exponential moving average — attack hızlı, release yavaş
  function ema(prev, next) {
    const alpha = next > prev ? 0.30 : 0.07;
    return prev + alpha * (next - prev);
  }

  // tanh soft-clip: lineer 0-1 arası, üzerinde yumuşak sıkıştırma
  function softClip(x, gain) {
    return Math.tanh(x * gain) / Math.tanh(gain);
  }

  async function startAudio() {
    if (active) return;
    try {
      const stream   = await navigator.mediaDevices.getUserMedia({ audio: true, video: false });
      const audioCtx = new (window.AudioContext || window.webkitAudioContext)();
      analyser = audioCtx.createAnalyser();
      analyser.fftSize               = 1024;
      analyser.smoothingTimeConstant = 0.88;  // yüksek → akıcı FFT
      analyser.minDecibels           = -90;
      analyser.maxDecibels           = -10;
      audioCtx.createMediaStreamSource(stream).connect(analyser);
      dataArr = new Uint8Array(analyser.frequencyBinCount); // 512 bin
      active  = true;
      tick();
    } catch (_) {
      // Mikrofon izni yok — audioData sıfır kalır, orb normal davranır
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

    // Ham değerler (kazanç faktörü: mikrofon hassasiyeti telafisi)
    const rawBass   = avg(0,   5)   * 2.2;
    const rawMid    = avg(6,   50)  * 2.8;
    const rawTreble = avg(51,  200) * 3.2;
    const rawAmp    = avg(0,   200) * 2.5;

    // Soft-clip + EMA smooth
    _prev.bass   = ema(_prev.bass,   softClip(rawBass,   2.0));
    _prev.mid    = ema(_prev.mid,    softClip(rawMid,    2.0));
    _prev.treble = ema(_prev.treble, softClip(rawTreble, 2.0));
    _prev.amp    = ema(_prev.amp,    softClip(rawAmp,    2.0));

    window.audioData = {
      bass:   _prev.bass,
      mid:    _prev.mid,
      treble: _prev.treble,
      amp:    _prev.amp,
    };

    requestAnimationFrame(tick);
  }

  // İlk pointer event'te başlat (getUserMedia user-gesture gerektirir)
  document.addEventListener('pointerdown', function onFirst() {
    startAudio();
  }, { once: true });

  window.startAudioReactive = startAudio;
})();
