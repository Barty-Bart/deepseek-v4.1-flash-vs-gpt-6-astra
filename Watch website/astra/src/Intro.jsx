import { useEffect, useRef, useState } from "react";
import { ArrowDown, ArrowUpRight } from "lucide-react";
import { FrameCache, timeline, storyDistances } from "./sequence";

export default function Intro() {
  const root = useRef(null),
    canvas = useRef(null);
  const [manifest, setManifest] = useState(null);
  const [mobile, setMobile] = useState(
    () =>
      matchMedia(
        "(max-width: 700px), (max-width: 1000px) and (orientation: portrait)",
      ).matches,
  );
  const [reduced, setReduced] = useState(
    () => matchMedia("(prefers-reduced-motion: reduce)").matches,
  );
  const [beat, setBeat] = useState(0),
    [progress, setProgress] = useState(0),
    [resolutionCopy, setResolutionCopy] = useState(false),
    [painted, setPainted] = useState(false);
  const source = manifest?.[mobile ? "portrait" : "landscape"];
  const ready =
    ["accepted", "preview"].includes(manifest?.status) &&
    !!source?.frameCount &&
    !!source?.pattern &&
    !reduced;
  useEffect(() => {
    const controller = new AbortController();
    fetch("/media/manifest.json", { signal: controller.signal })
      .then((r) => (r.ok ? r.json() : null))
      .then(setManifest)
      .catch(() => {});
    const mq = matchMedia(
        "(max-width: 700px), (max-width: 1000px) and (orientation: portrait)",
      ),
      rm = matchMedia("(prefers-reduced-motion: reduce)");
    const change = () => setMobile(mq.matches),
      reduce = () => setReduced(rm.matches);
    mq.addEventListener("change", change);
    rm.addEventListener("change", reduce);
    return () => {
      controller.abort();
      mq.removeEventListener("change", change);
      rm.removeEventListener("change", reduce);
    };
  }, []);
  useEffect(() => {
    setPainted(false);
    setBeat(0);
    setProgress(0);
    root.current?.style.setProperty("--media-expansion", "0");
    if (!ready) return;
    const el = canvas.current;
    el.width = source.width;
    el.height = source.height;
    const ctx = el.getContext("2d", { alpha: false });
    const cache = new FrameCache(source, (bitmap, index) => {
      ctx.drawImage(bitmap, 0, 0, el.width, el.height);
      el.dataset.frame = String(index);
      setPainted(true);
    });
    let tick = 0;
    const update = () => {
      tick = 0;
      const rect = root.current.getBoundingClientRect();
      const p = Math.max(
        0,
        Math.min(1, -rect.top / (root.current.offsetHeight - innerHeight)),
      );
      const t = timeline(p, mobile, source.timeline);
      const smooth = (v) => {
        const x = Math.max(0, Math.min(1, v));
        return x * x * (3 - 2 * x);
      };
      const [expandStart, expandEnd, contractStart, contractEnd] =
        source.mediaExpansion || [0.304, 0.369, 0.579, 0.657];
      const expansion = Math.min(
        smooth((t.frameProgress - expandStart) / (expandEnd - expandStart)),
        1 -
          smooth(
            (t.frameProgress - contractStart) / (contractEnd - contractStart),
          ),
      );
      root.current.style.setProperty("--media-expansion", String(expansion));
      setBeat(t.beat);
      setProgress(p);
      setResolutionCopy(t.frameProgress >= (source.resolutionCopyAt ?? 0));
      cache.seek(t.frameProgress * (source.frameCount - 1));
    };
    const schedule = () => {
      if (!tick) tick = requestAnimationFrame(update);
    };
    addEventListener("scroll", schedule, { passive: true });
    addEventListener("resize", schedule);
    update();
    return () => {
      cache.dispose();
      cancelAnimationFrame(tick);
      removeEventListener("scroll", schedule);
      removeEventListener("resize", schedule);
    };
  }, [source, ready, mobile]);
  return (
    <section
      ref={root}
      id="intro"
      className={`intro ${ready ? "film-ready" : ""}`}
      aria-label="The M01 introduction"
      style={{
        "--story-travel": `${storyDistances(mobile).reduce((a, b) => a + b, 0) * 100}svh`,
      }}
      data-source={mobile ? "portrait" : "landscape"}
      data-sequence={ready ? "active" : "poster"}
      data-beat={beat}
    >
      <div className="intro-stage">
        <div className="hero-coordinate" aria-hidden="true">
          INDEPENDENT WATCHMAKING &nbsp; / &nbsp; EST. 2018
        </div>
        <div
          className={`hero-art ${source?.posterType !== "cutout" ? "full-poster" : ""}`}
        >
          <img
            key={mobile ? "portrait" : "landscape"}
            src={
              source?.poster ||
              `/assets/generated/opening-${mobile ? "portrait" : "landscape"}-v1.webp`
            }
            alt="M01 Midnight concept watch with a blue dial and brushed steel bracelet"
            fetchPriority="high"
            onError={(e) => {
              if (!e.currentTarget.dataset.fallback) {
                e.currentTarget.dataset.fallback = "true";
                e.currentTarget.src = "/assets/midnight-v1.webp";
              }
            }}
          />
        </div>
        <canvas
          ref={canvas}
          className={`film-canvas ${painted ? "visible" : ""}`}
          aria-hidden="true"
        />
        <div className="hero-shade" />
        {(beat === 0 || !ready) && (
          <div className="hero-copy">
            <p className="eyebrow">
              <span className="gold-dash" /> THE M01 COLLECTION
            </p>
            <h1>
              Every part,
              <br />
              <em>a purpose.</em>
            </h1>
            <p className="hero-description">
              Mechanical craft. Made for
              <br className="desktop-break" /> the hours that matter.
            </p>
            <a className="button button-light" href="#collection">
              Explore M01 <ArrowUpRight size={17} />
            </a>
          </div>
        )}
        {ready && beat === 1 && (
          <div className="hero-copy story-copy">
            <p className="eyebrow">02 — THE CONSTRUCTION</p>
            <h2>
              Considered, down to
              <br />
              the smallest detail.
            </h2>
            <p>A complete world of precision, working as one.</p>
          </div>
        )}
        {ready && beat === 3 && resolutionCopy && (
          <div className="hero-copy">
            <p className="eyebrow">04 — THE EVERYDAY</p>
            <h2>
              Made to become
              <br />
              <em>part of your day.</em>
            </h2>
            <a className="button button-light" href="#collection">
              Find your Meridian <ArrowUpRight size={17} />
            </a>
          </div>
        )}
        <div className="hero-bottom">
          <a href="#collection" className="scroll-cue">
            <span className="scroll-line" />
            <span>
              {ready ? "SCROLL TO DISCOVER" : "DISCOVER THE COLLECTION"}
            </span>
            <ArrowDown size={13} />
          </a>
          <div className="hero-product-caption">
            <span>M01 MIDNIGHT</span>
            <span>40 MM &nbsp; · &nbsp; AUTOMATIC &nbsp; · &nbsp; $895</span>
          </div>
          <a href="#collection" className="skip-story">
            {ready ? "Skip story" : "View collection"}{" "}
            <ArrowUpRight size={13} />
          </a>
        </div>
        <span className="art-disclosure">
          {manifest?.status === "accepted"
            ? "Cinematic product film"
            : manifest?.status === "preview"
              ? "Cinematic study · motion preview"
              : "MERIDIAN / THE M01 STUDY"}
        </span>
        {ready && (
          <div
            className="story-progress"
            style={{ transform: `scaleX(${progress})` }}
          />
        )}
      </div>
    </section>
  );
}
