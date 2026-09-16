// Synthesised sound effects. Everything is generated with WebAudio oscillators
// and noise buffers, so the game ships with no external audio files.

export class Sound {
  constructor() {
    this.ctx = null;
    this.master = null;
    this.muted = false;
    this.last = new Map();
  }

  init() {
    if (this.ctx) {
      if (this.ctx.state === 'suspended') this.ctx.resume();
      return;
    }
    const AC = window.AudioContext || window.webkitAudioContext;
    if (!AC) return;
    this.ctx = new AC();
    this.master = this.ctx.createGain();
    this.master.gain.value = 0.34;
    this.master.connect(this.ctx.destination);
  }

  setMuted(muted) {
    this.muted = muted;
    if (this.master) this.master.gain.value = muted ? 0 : 0.34;
  }

  throttle(key, seconds) {
    const t = this.ctx ? this.ctx.currentTime : 0;
    const last = this.last.get(key) || -1e9;
    if (t - last < seconds) return false;
    this.last.set(key, t);
    return true;
  }

  tone({ freq = 440, freq2 = null, dur = 0.12, type = 'sine', gain = 0.5, delay = 0 }) {
    if (!this.ctx || this.muted) return;
    const t0 = this.ctx.currentTime + delay;
    const osc = this.ctx.createOscillator();
    const env = this.ctx.createGain();
    osc.type = type;
    osc.frequency.setValueAtTime(freq, t0);
    if (freq2 !== null) osc.frequency.exponentialRampToValueAtTime(Math.max(20, freq2), t0 + dur);
    env.gain.setValueAtTime(0.0001, t0);
    env.gain.exponentialRampToValueAtTime(gain, t0 + 0.008);
    env.gain.exponentialRampToValueAtTime(0.0001, t0 + dur);
    osc.connect(env);
    env.connect(this.master);
    osc.start(t0);
    osc.stop(t0 + dur + 0.03);
  }

  noise({ dur = 0.1, gain = 0.4, freq = 900, q = 1, delay = 0, type = 'bandpass' }) {
    if (!this.ctx || this.muted) return;
    const t0 = this.ctx.currentTime + delay;
    const frames = Math.max(1, Math.floor(this.ctx.sampleRate * dur));
    const buf = this.ctx.createBuffer(1, frames, this.ctx.sampleRate);
    const data = buf.getChannelData(0);
    for (let i = 0; i < frames; i++) data[i] = (Math.random() * 2 - 1) * (1 - i / frames);
    const src = this.ctx.createBufferSource();
    src.buffer = buf;
    const filter = this.ctx.createBiquadFilter();
    filter.type = type;
    filter.frequency.value = freq;
    filter.Q.value = q;
    const env = this.ctx.createGain();
    env.gain.value = gain;
    env.gain.setValueAtTime(gain, t0);
    env.gain.exponentialRampToValueAtTime(0.0001, t0 + dur);
    src.connect(filter);
    filter.connect(env);
    env.connect(this.master);
    src.start(t0);
  }

  play(name, detail = {}) {
    if (!this.ctx || this.muted) return;
    switch (name) {
      case 'select':
        if (!this.throttle('select', 0.04)) return;
        this.tone({ freq: 780, freq2: 900, dur: 0.06, type: 'triangle', gain: 0.25 });
        break;
      case 'command':
        if (!this.throttle('command', 0.06)) return;
        this.tone({ freq: 420, freq2: 560, dur: 0.09, type: 'square', gain: 0.16 });
        break;
      case 'place':
        this.noise({ dur: 0.16, gain: 0.32, freq: 420, q: 0.7 });
        this.tone({ freq: 180, freq2: 110, dur: 0.18, type: 'triangle', gain: 0.3 });
        break;
      case 'complete':
        this.tone({ freq: 523, dur: 0.16, type: 'triangle', gain: 0.28 });
        this.tone({ freq: 659, dur: 0.16, type: 'triangle', gain: 0.22, delay: 0.09 });
        this.tone({ freq: 784, dur: 0.22, type: 'triangle', gain: 0.2, delay: 0.18 });
        break;
      case 'train':
        this.tone({ freq: 392, dur: 0.1, type: 'square', gain: 0.18 });
        this.tone({ freq: 587, dur: 0.14, type: 'square', gain: 0.16, delay: 0.1 });
        break;
      case 'gather':
        if (!this.throttle('gather', 0.35)) return;
        this.noise({ dur: 0.05, gain: 0.16, freq: 2400, q: 2 });
        break;
      case 'deposit':
        if (!this.throttle('deposit', 0.12)) return;
        this.tone({ freq: 900, freq2: 1250, dur: 0.07, type: 'sine', gain: 0.16 });
        break;
      case 'hammer':
        if (!this.throttle('hammer', 0.25)) return;
        this.noise({ dur: 0.07, gain: 0.2, freq: 1500, q: 1.4 });
        break;
      case 'hit':
        if (!this.throttle('hit', 0.07)) return;
        this.noise({ dur: 0.06, gain: 0.16, freq: 700, q: 0.9 });
        break;
      case 'arrow':
        if (!this.throttle('arrow', 0.08)) return;
        this.tone({ freq: 1500, freq2: 500, dur: 0.1, type: 'sine', gain: 0.1 });
        break;
      case 'death':
        if (!this.throttle('death', 0.1)) return;
        this.tone({ freq: 320, freq2: 90, dur: 0.3, type: 'sawtooth', gain: 0.16 });
        break;
      case 'collapse':
        this.noise({ dur: 0.55, gain: 0.4, freq: 260, q: 0.6 });
        this.tone({ freq: 120, freq2: 45, dur: 0.5, type: 'sawtooth', gain: 0.24 });
        break;
      case 'error':
        if (!this.throttle('error', 0.25)) return;
        this.tone({ freq: 170, dur: 0.16, type: 'square', gain: 0.16 });
        break;
      case 'warcry':
        this.tone({ freq: 220, freq2: 180, dur: 0.4, type: 'sawtooth', gain: 0.18 });
        this.tone({ freq: 330, freq2: 260, dur: 0.36, type: 'sawtooth', gain: 0.12, delay: 0.05 });
        break;
      case 'victory':
        [523, 659, 784, 1047].forEach((f, i) =>
          this.tone({ freq: f, dur: 0.4, type: 'triangle', gain: 0.28, delay: i * 0.16 }));
        break;
      case 'defeat':
        [392, 349, 294, 233].forEach((f, i) =>
          this.tone({ freq: f, dur: 0.5, type: 'triangle', gain: 0.26, delay: i * 0.2 }));
        break;
      default:
        break;
    }
  }

  // Map simulation events onto sounds.
  handleEvent(ev) {
    switch (ev.type) {
      case 'place': this.play('place'); break;
      case 'complete': if (ev.team === 0) this.play('complete'); break;
      case 'trained': if (ev.team === 0) this.play('train'); break;
      case 'gather': if (ev.team === 0) this.play('gather'); break;
      case 'deposit': if (ev.team === 0) this.play('deposit'); break;
      case 'hammer': this.play('hammer'); break;
      case 'hit': this.play('hit'); break;
      case 'arrow': this.play('arrow'); break;
      case 'death': this.play('death'); break;
      case 'collapse': this.play('collapse'); break;
      case 'warcry': this.play('warcry'); break;
      case 'victory': this.play('victory'); break;
      case 'defeat': this.play('defeat'); break;
      default: break;
    }
  }
}
