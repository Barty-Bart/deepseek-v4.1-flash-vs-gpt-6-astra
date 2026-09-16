import React, { useEffect, useRef, useState } from "react";
import { createRoot } from "react-dom/client";
import {
  ArrowUpRight,
  ArrowRight,
  ArrowDown,
  Menu,
  X,
  ShoppingBag,
  Plus,
  Minus,
  Check,
  Upload,
  RotateCcw,
  ChevronDown,
} from "lucide-react";
import { brand, products, specifications, money, navigation } from "./content";
import Intro from "./Intro";
import "./styles.css";

export function Compass({ className = "" }) {
  return (
    <svg
      className={className}
      width="27"
      height="35"
      viewBox="0 0 36 44"
      fill="none"
      aria-hidden="true"
    >
      <path
        d="M18 1v42M1 22h34M18 7l5 15-5 15-5-15Z"
        stroke="currentColor"
        strokeWidth="1"
      />
      <circle cx="18" cy="22" r="12" stroke="currentColor" strokeWidth=".7" />
    </svg>
  );
}
export function Wordmark() {
  return (
    <span className="wordmark">
      <Compass />
      MERIDIAN
    </span>
  );
}
export function ProductCard({ product, onSelect, index = 0 }) {
  const [loadedImage, setLoadedImage] = useState(null);
  return (
    <article className="product-card has-generated">
      <button
        className={`product-image ${loadedImage === product.hoverImage ? "supplement-ready" : ""}`}
        onClick={() => onSelect(product.id)}
        aria-label={`Explore ${product.family} ${product.name}`}
      >
        <span className="card-number">0{index + 1} / 05</span>
        <img
          className="product-image-primary"
          src={product.image}
          alt={`${product.family} ${product.name}, ${product.dial.toLowerCase()} dial`}
          loading="lazy"
          width="900"
          height="1100"
        />
        {product.hoverImage && (
          <img
            key={product.hoverImage}
            className="product-image-secondary"
            src={product.hoverImage}
            alt=""
            aria-hidden="true"
            loading="lazy"
            decoding="async"
            width="900"
            height="1205"
            onLoad={() => setLoadedImage(product.hoverImage)}
            onError={() => setLoadedImage(null)}
          />
        )}
        <span className="product-image-bottom">
          <span>{product.note}</span>
          <span className="round-arrow">
            <ArrowUpRight size={19} />
          </span>
        </span>
      </button>
      <div className="product-info">
        <div>
          <button className="product-name" onClick={() => onSelect(product.id)}>
            {product.family} <span>{product.name}</span>
          </button>
          <p>{product.material}</p>
        </div>
        <span className="product-price">{money(product.price)}</span>
      </div>
      <div className="product-swatches">
        <span className="swatch-dot" style={{ background: product.color }} />
        <span>{product.dial}</span>
        <span className="concept-small">40 MM CASE</span>
      </div>
    </article>
  );
}

function readBag() {
  try {
    const data = JSON.parse(localStorage.getItem("meridian-bag-v1") || "[]");
    if (!Array.isArray(data)) return [];
    return products.flatMap((p) => {
      const q = data
        .filter(
          (i) =>
            i?.id === p.id && Number.isInteger(i.quantity) && i.quantity > 0,
        )
        .reduce((n, i) => n + i.quantity, 0);
      return q ? [{ id: p.id, quantity: Math.min(q, 99) }] : [];
    });
  } catch {
    return [];
  }
}
function App() {
  const [bag, setBag] = useState(readBag),
    [overlay, setOverlay] = useState(null),
    [selected, setSelected] = useState("midnight"),
    [quantity, setQuantity] = useState(1),
    [filter, setFilter] = useState("all"),
    [notice, setNotice] = useState(""),
    [scrolled, setScrolled] = useState(false);
  const dialog = useRef(null),
    restoreFocus = useRef(null),
    toastTimer = useRef(null);
  const product = products.find((p) => p.id === selected);
  const count = bag.reduce((sum, p) => sum + p.quantity, 0),
    total = bag.reduce(
      (sum, i) => sum + products.find((p) => p.id === i.id).price * i.quantity,
      0,
    );
  useEffect(() => {
    try {
      localStorage.setItem("meridian-bag-v1", JSON.stringify(bag));
    } catch {
      /* Storage unavailable: the bag remains usable for this visit. */
    }
  }, [bag]);
  useEffect(() => {
    const cb = () => setScrolled(scrollY > 40);
    addEventListener("scroll", cb, { passive: true });
    cb();
    return () => {
      removeEventListener("scroll", cb);
      clearTimeout(toastTimer.current);
    };
  }, []);
  useEffect(() => {
    if (!overlay) return;
    const el = dialog.current;
    restoreFocus.current = document.activeElement;
    el.showModal();
    document.body.style.overflow = "hidden";
    el.querySelector("[data-initial-focus]")?.focus();
    return () => {
      el.close();
      document.body.style.overflow = "";
      if (restoreFocus.current?.isConnected)
        restoreFocus.current.focus({ preventScroll: true });
    };
  }, [!!overlay]);
  useEffect(() => {
    if (location.hash) {
      document.fonts.ready.then(() =>
        requestAnimationFrame(() =>
          document
            .getElementById(decodeURIComponent(location.hash.slice(1)))
            ?.scrollIntoView({ behavior: "instant" }),
        ),
      );
    }
  }, []);
  useEffect(() => {
    if (overlay) {
      const tick = requestAnimationFrame(() =>
        dialog.current?.querySelector("[data-initial-focus]")?.focus(),
      );
      return () => cancelAnimationFrame(tick);
    }
  }, [overlay]);
  const trapFocus = (e) => {
    if (e.key !== "Tab") return;
    const items = [
      ...e.currentTarget.querySelectorAll(
        'button:not([disabled]),a[href],input:not([disabled]),select:not([disabled]),[tabindex="0"]',
      ),
    ].filter((el) => el.getClientRects().length);
    const first = items[0],
      last = items.at(-1);
    if (e.shiftKey && document.activeElement === first) {
      e.preventDefault();
      last?.focus();
    } else if (!e.shiftKey && document.activeElement === last) {
      e.preventDefault();
      first?.focus();
    }
  };
  const openProduct = (id) => {
    setSelected(id);
    setQuantity(1);
    setOverlay("product");
  };
  const announce = (text) => {
    setNotice(text);
    clearTimeout(toastTimer.current);
    toastTimer.current = setTimeout(() => setNotice(""), 4000);
  };
  const add = () => {
    setBag((b) => {
      const current = b.find((i) => i.id === selected);
      return current
        ? b.map((i) =>
            i.id === selected
              ? { ...i, quantity: Math.min(99, i.quantity + quantity) }
              : i,
          )
        : [...b, { id: selected, quantity }];
    });
    announce(`${product.family} ${product.name} added to your demo bag`);
    setOverlay("bag");
  };
  const update = (id, delta) =>
    setBag((b) =>
      b
        .map((i) =>
          i.id === id
            ? { ...i, quantity: Math.min(99, i.quantity + delta) }
            : i,
        )
        .filter((i) => i.quantity > 0),
    );
  const navigate = (id) => {
    setOverlay(null);
    requestAnimationFrame(() => {
      document.getElementById(id)?.scrollIntoView({
        behavior: matchMedia("(prefers-reduced-motion: reduce)").matches
          ? "instant"
          : "smooth",
      });
      history.replaceState(null, "", `#${id}`);
      document.getElementById(id)?.focus({ preventScroll: true });
    });
  };
  return (
    <>
      <a href="#collection" className="skip-link">
        Skip to collection
      </a>
      <header className={`site-header ${scrolled ? "is-scrolled" : ""}`}>
        <a className="brand-link" href="#intro" aria-label="Meridian home">
          <Wordmark />
        </a>
        <nav className="desktop-nav" aria-label="Main navigation">
          {navigation.map(([label, id]) => (
            <a href={`#${id}`} key={id}>
              {label}
            </a>
          ))}
        </nav>
        <div className="header-actions">
          <span className="header-currency">USD</span>
          <button
            className="menu-toggle icon-button"
            onClick={() => setOverlay("menu")}
            aria-label="Open navigation menu"
            aria-expanded={overlay === "menu"}
          >
            <Menu size={22} />
          </button>
          <button
            className="bag-toggle"
            onClick={() => setOverlay("bag")}
            aria-label={`Open bag, ${count} ${count === 1 ? "item" : "items"}`}
          >
            <ShoppingBag size={18} />
            <span className="bag-label">Bag</span>
            <span className="bag-count">{count}</span>
          </button>
        </div>
      </header>
      <main>
        <Intro />
        <section
          id="collection"
          tabIndex="-1"
          className="collection section-pad"
        >
          <div className="section-heading">
            <div>
              <p className="eyebrow">01 / THE COLLECTION</p>
              <h2>
                A measure of
                <br />
                <em>your own.</em>
              </h2>
            </div>
            <div className="section-intro">
              <p>
                Five expressions. One considered approach.
                <br />
                Find the one that feels like you.
              </p>
              <span className="small-note">
                AUTOMATIC MOVEMENTS. EVERYDAY INTENTION.
              </span>
            </div>
          </div>
          <div className="collection-toolbar">
            <div
              className="filter-tabs"
              role="group"
              aria-label="Filter collection"
            >
              {[
                ["all", "All watches"],
                ["M01", "M01 Collection"],
                ["M02", "M02 Atelier"],
              ].map(([value, label]) => (
                <button
                  key={value}
                  onClick={() => setFilter(value)}
                  className={filter === value ? "active" : ""}
                  aria-pressed={filter === value}
                >
                  {label}
                </button>
              ))}
            </div>
            <span className="collection-count">
              {
                products.filter((p) => filter === "all" || p.family === filter)
                  .length
              }{" "}
              TIMEPIECES <span> / USD</span>
            </span>
          </div>
          <div className="product-grid">
            {products
              .filter((p) => filter === "all" || p.family === filter)
              .map((p) => (
                <ProductCard
                  key={p.id}
                  product={p}
                  index={products.indexOf(p)}
                  onSelect={openProduct}
                />
              ))}
            {filter === "all" && (
              <div className="collection-note">
                <Compass />
                <p>
                  Nothing extra.
                  <br />
                  <em>Nothing missing.</em>
                </p>
                <span>
                  A 40 mm case. An automatic heart.
                  <br />A place in your everyday.
                </span>
                <a href="#craft" className="text-link">
                  The thinking behind M01 <ArrowUpRight size={16} />
                </a>
              </div>
            )}
          </div>
        </section>
        <section id="craft" tabIndex="-1" className="craft">
          <div className="craft-visual generated-visual">
            <img
              src="/assets/generated/macro-v1.webp"
              alt="Macro study of intermeshing steel gears, a polished bridge and ruby bearings in the M01 movement"
              loading="lazy"
              width="1400"
              height="1300"
            />
            <div className="image-caption">
              <span>THE M01 / A CLOSER LOOK</span>
              <span>MOVEMENT STUDY</span>
            </div>
          </div>
          <div className="craft-content">
            <p className="eyebrow">02 / THE CRAFT</p>
            <h2>
              Precision,
              <br />
              with a <br />
              <em>human side.</em>
            </h2>
            <p className="body-copy">
              The way light moves across a brushed case. The quiet rhythm of a
              mechanical movement. The feeling of a bracelet that simply fits.
            </p>
            <p className="body-copy muted">
              Good design lives in these details. We bring them together in a
              watch that feels as considered as the time you give it.
            </p>
            <div className="spec-highlights">
              <div>
                <strong>
                  40<span>mm</span>
                </strong>
                <span>Considered proportions</span>
              </div>
              <div>
                <strong>
                  40<span>h</span>
                </strong>
                <span>Power in reserve</span>
              </div>
              <div>
                <strong>
                  100<span>m</span>
                </strong>
                <span>Water resistance</span>
              </div>
            </div>
            <p className="spec-disclosure">
              Fictional product specifications, for this concept.
            </p>
            <button
              className="text-link"
              onClick={() => openProduct("midnight")}
            >
              Explore the details <ArrowUpRight size={17} />
            </button>
          </div>
        </section>
        <section id="about" tabIndex="-1" className="about section-pad">
          <div className="about-top">
            <p className="eyebrow">03 / OUR STORY</p>
            <h2>
              Time well made.
              <br />
              <em>Time well spent.</em>
            </h2>
            <div>
              <p>{brand.story}</p>
              <span className="about-concept">
                An independent watch studio, imagined for this fictional brand
                concept.
              </span>
            </div>
          </div>
          <div className="about-bottom">
            <div className="about-art">
              <img
                className="lifestyle-image"
                src="/assets/generated/lifestyle-v1.webp"
                alt="The M01 Midnight worn on an adult wrist beside warm concrete city architecture"
                loading="lazy"
                width="1440"
                height="960"
              />
              <div className="about-art-copy">
                <Compass />
                <span>
                  MADE FOR
                  <br />
                  THE IN-BETWEEN.
                </span>
              </div>
              <span className="about-art-note">
                MERIDIAN / EVERYDAY, CONSIDERED
              </span>
            </div>
            <div className="about-stats">
              {brand.stats.map((s) => (
                <div key={s.label}>
                  <strong>{s.value}</strong>
                  <span>{s.label}</span>
                </div>
              ))}
              <p>{brand.disclosure}</p>
            </div>
          </div>
        </section>
        <section id="trade-in" tabIndex="-1" className="trade section-pad">
          <div className="trade-copy">
            <p className="eyebrow">04 / A NEW CHAPTER</p>
            <h2>
              We buy
              <br />
              <em>watches, too.</em>
            </h2>
            <p>
              A watch can have more than one story.
              <br />
              Let’s see where yours could go next.
            </p>
            <ol className="trade-steps">
              <li>
                <span>01</span>
                <div>
                  <h3>Tell us about it.</h3>
                  <p>A few details about the watch you have.</p>
                </div>
              </li>
              <li>
                <span>02</span>
                <div>
                  <h3>Receive an assessment.</h3>
                  <p>A considered look at its next possibilities.</p>
                </div>
              </li>
              <li>
                <span>03</span>
                <div>
                  <h3>Choose your next chapter.</h3>
                  <p>Put its value towards something new.</p>
                </div>
              </li>
            </ol>
            <p className="small-note">
              AN ILLUSTRATION OF OUR FICTIONAL TRADE-IN PROCESS.
            </p>
          </div>
          <TradeForm />
        </section>
        <div className="closing-line">
          <Compass />
          <span>Every part, a purpose.</span>
          <a href="#intro" aria-label="Back to top">
            <ArrowUpRight size={26} />
          </a>
        </div>
      </main>
      <footer className="footer">
        <div className="footer-top">
          <a className="brand-link" href="#intro" aria-label="Meridian home">
            <Wordmark />
          </a>
          <nav aria-label="Footer navigation">
            {navigation.map(([label, id]) => (
              <a key={id} href={`#${id}`}>
                {label}
              </a>
            ))}
            <a href="/style-tile.html">
              Design language <ArrowUpRight size={12} />
            </a>
          </nav>
          <span>USD / $</span>
        </div>
        <div className="footer-bottom">
          <p>© 2026 MERIDIAN. A fictional brand demonstration.</p>
          <p>Demo shopping only. No payment, orders or data submission.</p>
        </div>
      </footer>
      <div className={`toast ${notice ? "show" : ""}`} role="status">
        {notice && (
          <>
            <Check size={17} />
            {notice}
          </>
        )}
      </div>
      {overlay && (
        <dialog
          ref={dialog}
          onKeyDown={trapFocus}
          className={`dialog-shell ${overlay === "product" ? "product-dialog" : "drawer"}`}
          onCancel={(e) => {
            e.preventDefault();
            setOverlay(null);
          }}
          onClick={(e) => {
            if (e.target === e.currentTarget) {
              const r = e.currentTarget.getBoundingClientRect();
              if (
                e.clientX < r.left ||
                e.clientX > r.right ||
                e.clientY < r.top ||
                e.clientY > r.bottom
              )
                setOverlay(null);
            }
          }}
          aria-labelledby="dialog-title"
        >
          <button
            data-initial-focus
            className="dialog-close icon-button"
            aria-label="Close panel"
            onClick={() => setOverlay(null)}
          >
            <X size={22} />
          </button>
          {overlay === "menu" && (
            <div className="mobile-menu">
              <p className="eyebrow" id="dialog-title">
                EXPLORE MERIDIAN
              </p>
              <nav aria-label="Mobile navigation">
                {navigation.map(([label, id], i) => (
                  <button key={id} onClick={() => navigate(id)}>
                    <span>0{i + 1}</span>
                    {label}
                    <ArrowUpRight size={23} />
                  </button>
                ))}
              </nav>
              <p>Every part, a purpose.</p>
              <span className="small-note">
                INDEPENDENT WATCHMAKING / EST. 2018
              </span>
            </div>
          )}
          {overlay === "product" && (
            <>
              <div className="detail-image">
                <span className="eyebrow">THE {product.family} COLLECTION</span>
                <img
                  src={product.image}
                  alt={`${product.family} ${product.name} selected watch`}
                  width="900"
                  height="1100"
                />
                <span className="small-note">
                  MERIDIAN / {product.family} COLLECTION
                </span>
              </div>
              <div className="detail-content">
                <p className="eyebrow">EVERYDAY, CONSIDERED</p>
                <h2 id="dialog-title">
                  {product.family} <em>{product.name}</em>
                </h2>
                <div className="detail-price">
                  {money(product.price)} <span>USD</span>
                </div>
                <p>{product.description}</p>
                <fieldset className="variant-picker">
                  <legend>
                    Selected finish: <strong>{product.name}</strong>
                  </legend>
                  <div>
                    {products.map((p) => (
                      <button
                        key={p.id}
                        onClick={() => {
                          setSelected(p.id);
                          setQuantity(1);
                        }}
                        className={`swatch-button ${p.id === selected ? "selected" : ""}`}
                        aria-pressed={p.id === selected}
                        aria-label={`Select ${p.family} ${p.name}`}
                        title={`${p.family} ${p.name}`}
                      >
                        <span style={{ background: p.color }} />
                        {p.id === selected && <Check size={12} />}
                      </button>
                    ))}
                  </div>
                </fieldset>
                <p className="detail-material">{product.material}</p>
                <div className="purchase-row">
                  <Quantity
                    value={quantity}
                    onMinus={() => setQuantity((q) => Math.max(1, q - 1))}
                    onPlus={() => setQuantity((q) => Math.min(99, q + 1))}
                    min={1}
                  />
                  <button className="button button-dark" onClick={add}>
                    Add to demo bag <Plus size={17} />
                  </button>
                </div>
                <dl className="detail-specs">
                  {specifications.slice(0, 5).map(([key, value]) => (
                    <div key={key}>
                      <dt>{key}</dt>
                      <dd>{value}</dd>
                    </div>
                  ))}
                </dl>
                <p className="spec-disclosure">
                  Fictional product specifications. Demo shopping only.
                </p>
              </div>
            </>
          )}
          {(overlay === "bag" || overlay === "summary") && (
            <div className="bag-content">
              <p className="eyebrow">A PLACE FOR THE EVERYDAY</p>
              <h2 id="dialog-title">
                {overlay === "summary" ? "Your demo summary." : "Your bag."}
                <span>{count.toString().padStart(2, "0")}</span>
              </h2>
              {overlay === "summary" && (
                <div className="demo-notice">
                  <Check size={22} />
                  <p>
                    <strong>This is a demonstration.</strong>
                    <br />
                    No payment was taken. No order has been placed.
                  </p>
                </div>
              )}
              {bag.length ? (
                <>
                  <div className="bag-items">
                    {bag.map((item) => {
                      const p = products.find((p) => p.id === item.id);
                      return (
                        <article className="bag-item" key={item.id}>
                          <img
                            src={p.image}
                            alt={`${p.family} ${p.name}`}
                            width="112"
                            height="140"
                          />
                          <div>
                            <h3>
                              {p.family} {p.name}
                            </h3>
                            <p>{p.dial}</p>
                            <strong>{money(p.price * item.quantity)}</strong>
                            {overlay === "bag" ? (
                              <div className="bag-controls">
                                <Quantity
                                  value={item.quantity}
                                  label={`${p.name} quantity`}
                                  min={0}
                                  onMinus={() => update(item.id, -1)}
                                  onPlus={() => update(item.id, 1)}
                                />
                                <button
                                  className="remove-button"
                                  onClick={() =>
                                    setBag((b) =>
                                      b.filter((i) => i.id !== item.id),
                                    )
                                  }
                                  aria-label={`Remove ${p.name}`}
                                >
                                  Remove
                                </button>
                              </div>
                            ) : (
                              <p>
                                Quantity: {item.quantity} · {money(p.price)}{" "}
                                each
                              </p>
                            )}
                          </div>
                        </article>
                      );
                    })}
                  </div>
                  <div className="bag-summary">
                    <div>
                      <span>Demo total</span>
                      <strong data-testid="bag-total">
                        {money(total)} <small>USD</small>
                      </strong>
                    </div>
                    <p>
                      Illustrative prices. No shipping, taxes or payment will be
                      collected.
                    </p>
                    {overlay === "bag" ? (
                      <button
                        className="button button-dark"
                        onClick={() => setOverlay("summary")}
                      >
                        Preview demo checkout <ArrowRight size={17} />
                      </button>
                    ) : (
                      <button
                        className="button button-dark"
                        onClick={() => setOverlay("bag")}
                      >
                        Return to bag <ArrowRight size={17} />
                      </button>
                    )}
                    <button
                      className="reset-bag"
                      onClick={() => {
                        setBag([]);
                        setOverlay("bag");
                        announce("Demo bag reset");
                      }}
                    >
                      <RotateCcw size={14} /> Reset demo bag
                    </button>
                  </div>
                </>
              ) : (
                <div className="empty-bag">
                  <ShoppingBag size={45} strokeWidth={1} />
                  <h3>A little room for possibility.</h3>
                  <p>Your next everyday companion is waiting.</p>
                  <button
                    className="button button-dark"
                    onClick={() => navigate("collection")}
                  >
                    Explore the collection <ArrowUpRight size={17} />
                  </button>
                </div>
              )}
            </div>
          )}
        </dialog>
      )}
    </>
  );
}
function Quantity({ value, onMinus, onPlus, min = 1, label = "Quantity" }) {
  return (
    <div className="quantity-control" aria-label={label}>
      <button
        aria-label={`Decrease ${label.toLowerCase()}`}
        onClick={onMinus}
        disabled={value <= min}
      >
        <Minus size={13} />
      </button>
      <span aria-live="polite">{value}</span>
      <button
        aria-label={`Increase ${label.toLowerCase()}`}
        onClick={onPlus}
        disabled={value >= 99}
      >
        <Plus size={13} />
      </button>
    </div>
  );
}
function TradeForm() {
  const [values, setValues] = useState({ brand: "", model: "", condition: "" }),
    [errors, setErrors] = useState({}),
    [preview, setPreview] = useState(null),
    [prepared, setPrepared] = useState(false),
    [fileName, setFileName] = useState("");
  const fileInput = useRef(null),
    formRef = useRef(null),
    uploadVersion = useRef(0);
  useEffect(
    () => () => {
      if (preview) URL.revokeObjectURL(preview);
    },
    [preview],
  );
  const change = (e) => {
    setValues((v) => ({ ...v, [e.target.name]: e.target.value }));
    setErrors((s) => ({ ...s, [e.target.name]: "" }));
    setPrepared(false);
  };
  const upload = (e) => {
    const file = e.target.files?.[0];
    const version = ++uploadVersion.current;
    setPrepared(false);
    if (!file) return;
    if (
      !["image/jpeg", "image/png", "image/webp", "image/avif"].includes(
        file.type,
      ) ||
      file.size > 8 * 1024 * 1024
    ) {
      setErrors((s) => ({
        ...s,
        image: "Choose a JPG, PNG, WebP or AVIF image under 8 MB.",
      }));
      e.target.value = "";
      return;
    }
    const url = URL.createObjectURL(file),
      img = new Image();
    img.onload = () => {
      if (version !== uploadVersion.current) {
        URL.revokeObjectURL(url);
        return;
      }
      setPreview(url);
      setFileName(file.name);
      setErrors((s) => ({ ...s, image: "" }));
    };
    img.onerror = () => {
      URL.revokeObjectURL(url);
      if (version !== uploadVersion.current) return;
      setErrors((s) => ({
        ...s,
        image: "That image could not be opened. Please choose another.",
      }));
    };
    img.src = url;
  };
  const submit = (e) => {
    e.preventDefault();
    const next = {};
    if (!values.brand.trim()) next.brand = "Enter the watch brand.";
    if (!values.model.trim()) next.model = "Enter the watch model.";
    if (!values.condition) next.condition = "Select the watch condition.";
    if (errors.image) next.image = errors.image;
    setErrors(next);
    if (Object.keys(next).length) {
      formRef.current
        .querySelector(`[name="${Object.keys(next)[0]}"]`)
        ?.focus();
      return;
    }
    setPrepared(true);
  };
  return (
    <form ref={formRef} className="trade-form" noValidate onSubmit={submit}>
      <div className="form-heading">
        <span className="eyebrow">YOUR WATCH, NEXT</span>
        <span>DEMO VALUATION</span>
      </div>
      <h3>
        A new beginning
        <br />
        starts here.
      </h3>
      <div className="form-grid">
        {[
          ["brand", "Watch brand", "e.g. Meridian"],
          ["model", "Model", "e.g. M01 Midnight"],
        ].map(([name, label, placeholder]) => (
          <div className="field" key={name}>
            <label htmlFor={name}>
              {label} <span aria-hidden="true">*</span>
            </label>
            <input
              id={name}
              name={name}
              value={values[name]}
              onChange={change}
              placeholder={placeholder}
              maxLength={100}
              required
              aria-invalid={!!errors[name]}
              aria-describedby={errors[name] ? `${name}-error` : undefined}
            />
            {errors[name] && (
              <span className="field-error" id={`${name}-error`}>
                {errors[name]}
              </span>
            )}
          </div>
        ))}
      </div>
      <div className="field">
        <label htmlFor="condition">
          Condition <span aria-hidden="true">*</span>
        </label>
        <div className="select-wrap">
          <select
            id="condition"
            name="condition"
            required
            value={values.condition}
            onChange={change}
            aria-invalid={!!errors.condition}
            aria-describedby={errors.condition ? "condition-error" : undefined}
          >
            <option value="" disabled>
              Select condition
            </option>
            <option value="unworn">Unworn — never worn</option>
            <option value="excellent">Excellent — minimal signs of wear</option>
            <option value="good">Good — everyday signs of wear</option>
            <option value="fair">Fair — visible wear</option>
            <option value="repair">Needs repair</option>
          </select>
          <ChevronDown size={17} />
        </div>
        {errors.condition && (
          <span className="field-error" id="condition-error">
            {errors.condition}
          </span>
        )}
      </div>
      <div className="field">
        <label htmlFor="image">
          A photo of your watch <span>(optional)</span>
        </label>
        <label
          className={`upload-area ${preview ? "has-image" : ""}`}
          htmlFor="image"
        >
          {preview ? (
            <>
              <img src={preview} alt="Your selected watch upload preview" />
              <span>
                {fileName}
                <small>Click to replace</small>
              </span>
            </>
          ) : (
            <>
              <Upload size={20} />
              <span>
                Add a photo<small>JPG, PNG, WebP or AVIF · up to 8 MB</small>
              </span>
            </>
          )}
          <input
            ref={fileInput}
            id="image"
            name="image"
            type="file"
            accept="image/jpeg,image/png,image/webp,image/avif"
            onChange={upload}
            aria-describedby={errors.image ? "image-error" : undefined}
          />
        </label>
        {preview && (
          <button
            className="remove-button"
            type="button"
            onClick={() => {
              uploadVersion.current++;
              setPreview(null);
              setFileName("");
              setPrepared(false);
              setErrors((s) => ({ ...s, image: "" }));
              fileInput.current.value = "";
            }}
          >
            Remove photo
          </button>
        )}
        {errors.image && (
          <span className="field-error" id="image-error">
            {errors.image}
          </span>
        )}
      </div>
      <button className="button button-dark" type="submit">
        Prepare demo valuation <ArrowUpRight size={17} />
      </button>
      <p className="form-footnote">
        Just a preview. Your details and photo stay in this browser and are
        never submitted.
      </p>
      {prepared && (
        <div className="valuation-success" role="status">
          <Check size={20} />
          <div>
            <strong>
              Demo valuation request prepared — nothing has been sent.
            </strong>
            <p>
              {values.brand.trim()} · {values.model.trim()} ·{" "}
              {values.condition.replaceAll("-", " ")}
              {preview ? " · 1 photo attached" : ""}
            </p>
          </div>
        </div>
      )}
    </form>
  );
}
if (document.getElementById("root"))
  createRoot(document.getElementById("root")).render(<App />);
