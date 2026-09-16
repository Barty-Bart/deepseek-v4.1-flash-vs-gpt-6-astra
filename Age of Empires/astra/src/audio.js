export class Sound {
  constructor() {
    this.muted = localStorage.getItem("hearth-muted") === "true";
    this.ctx = null;
    this.last = {};
  }
  init() {
    if (!this.ctx)
      this.ctx = new (window.AudioContext || window.webkitAudioContext)();
    this.ctx.resume();
  }
  toggle() {
    this.muted = !this.muted;
    localStorage.setItem("hearth-muted", this.muted);
    return this.muted;
  }
  tone(frequency, duration, type = "sine", volume = 0.04, delay = 0) {
    if (this.muted || !this.ctx) return;
    const t = this.ctx.currentTime + delay,
      osc = this.ctx.createOscillator(),
      gain = this.ctx.createGain();
    osc.type = type;
    osc.frequency.setValueAtTime(frequency, t);
    gain.gain.setValueAtTime(0, t);
    gain.gain.linearRampToValueAtTime(volume, t + 0.012);
    gain.gain.exponentialRampToValueAtTime(0.001, t + duration);
    osc.connect(gain);
    gain.connect(this.ctx.destination);
    osc.start(t);
    osc.stop(t + duration);
  }
  play(name) {
    if (this.muted) return;
    const now = performance.now();
    if (now - (this.last[name] || 0) < (name === "hit" ? 180 : 90)) return;
    this.last[name] = now;
    if (name === "select") this.tone(440, 0.08, "sine", 0.022);
    if (name === "arrow") {
      this.tone(760, 0.045, "triangle", 0.012);
      this.tone(360, 0.075, "sine", 0.009, 0.025);
    }
    if (name === "order") {
      this.tone(300, 0.09, "triangle", 0.035);
      this.tone(390, 0.11, "triangle", 0.02, 0.055);
    }
    if (name === "build") {
      this.tone(150, 0.12, "triangle", 0.07);
      this.tone(210, 0.1, "triangle", 0.04, 0.12);
    }
    if (name === "complete")
      [440, 554, 660].forEach((f, i) =>
        this.tone(f, 0.3, "triangle", 0.035, i * 0.09),
      );
    if (name === "hit") {
      this.tone(85, 0.08, "sawtooth", 0.022);
      this.tone(170, 0.055, "triangle", 0.025);
    }
    if (name === "alert")
      [330, 330, 262].forEach((f, i) =>
        this.tone(f, 0.25, "triangle", 0.06, i * 0.22),
      );
    if (name === "error") this.tone(130, 0.16, "triangle", 0.045);
    if (name === "victory")
      [262, 330, 392, 523, 659].forEach((f, i) =>
        this.tone(f, 0.8, "triangle", 0.055, i * 0.18),
      );
    if (name === "defeat")
      [330, 294, 247, 196].forEach((f, i) =>
        this.tone(f, 0.8, "triangle", 0.04, i * 0.26),
      );
  }
}
