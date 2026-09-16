import content from '../content.json';
import { Bag, money } from './bag.js';
import { el, qs, qsa, trapFocus } from './ui.js';
import { StagePlayer } from './stage.js';

/* -------------------------------------------------------------------------- */
/* bootstrap                                                                  */
/* -------------------------------------------------------------------------- */

const S = content.copy;

function boot() {
  if (document.body.dataset.booted) return;
  document.body.dataset.booted = '1';

  hydrateStaticCopy();
  renderCollection();

  const bag = new Bag(content.products, { onChange: onBagChange });
  const ui = new UI(bag);
  window.__meridianUI = ui;
  ui.render();

  startStage();
  wireAnchors();
}

/* -------------------------------------------------------------------------- */
/* static copy — content.json stays the single editable source                */
/* -------------------------------------------------------------------------- */

function hydrateStaticCopy() {
  const set = (sel, text) => {
    const n = qs(sel);
    if (n && text) n.textContent = text;
  };
  set('[data-skip-story]', S.skipStory);
  set('[data-scroll-cue] span', S.scrollCue);
  set('.collection .eyebrow', S.collectionEyebrow);
  set('#collection-title', S.collectionHeadline);
  set('.collection .section-intro', S.collectionIntro);
  set('.collection-note', 'Prices in USD. Concept specifications — illustrative only. Adding to the bag is a demonstration and places no order.');
  set('[data-demo-checkout]', S.demoCheckout);
  set('[data-bag-reset]', S.resetBag);
  set('[data-trade-reset]', S.tradeInReset);
  set('.bag-note', S.bagNote);
  set('[data-trade-form] .form-note', S.formNote);
  set('.form-result-title', S.successMessage);
  set('.demo-summary h3', S.demoSummaryTitle);
  set('.demo-summary > p', S.demoSummaryBody);
  set('[data-demo-close]', S.demoSummaryClose);
}

/* -------------------------------------------------------------------------- */
/* collection                                                                 */
/* -------------------------------------------------------------------------- */

function renderCollection() {
  const grid = qs('[data-product-grid]');
  if (!grid) return;

  for (const p of content.products) {
    // Two layers: the studio still, and a wrist still that replaces it on hover.
    // The wrist layer is inert (empty alt, aria-hidden) so the card keeps one
    // accessible description, and it is only fetched when the card is hovered or
    // focused so five extra images are never paid for up front.
    const media = el('div', { class: 'card-media', role: 'button', tabindex: '0' }, [
      el('span', { class: 'card-badge', text: `${S.selected}: ${p.name}` }),
      el('img', {
        class: 'card-still',
        src: `./${p.image}`,
        alt: p.alt,
        width: 1100,
        height: 1366,
        loading: 'lazy',
        decoding: 'async',
      }),
      el('img', {
        class: 'card-wrist',
        src: `./${p.wristImage}`,
        alt: '',
        'aria-hidden': 'true',
        width: 1100,
        height: 1366,
        loading: 'lazy',
        decoding: 'async',
      }),
    ]);
    media.dataset.openProduct = p.id;
    media.setAttribute('aria-label', `${p.name}, ${money(p.price)}. ${S.viewDetails}.`);

    const card = el('li', { class: 'product-card', dataset: { productId: p.id } }, [
      media,
      el('div', { class: 'card-body' }, [
        el('div', { class: 'card-row' }, [
          el('h3', { class: 'card-name', text: p.name }),
          el('p', { class: 'card-price', text: money(p.price) }),
        ]),
        el('p', { class: 'card-blurb', text: p.blurb }),
        el('p', { class: 'card-specs' }, [
          el('span', { class: 'card-swatch', style: `background:${p.swatch}`, 'aria-hidden': 'true' }),
          el('span', { text: `${p.caseFinish} · ${p.strap}` }),
        ]),
        el('div', { class: 'card-actions' }, [
          el('button', {
            class: 'btn btn-primary',
            type: 'button',
            dataset: { quickAdd: p.id },
            text: S.addToBag,
          }),
          el('button', {
            class: 'btn btn-quiet',
            type: 'button',
            dataset: { openProduct: p.id },
            text: S.viewDetails,
          }),
        ]),
      ]),
    ]);
    grid.append(card);
  }

  // keyboard + pointer delegation for the media surface
  grid.addEventListener('click', (ev) => {
    const trigger = ev.target.closest('[data-open-product]');
    if (!trigger) return;
    window.dispatchEvent(new CustomEvent('meridian:open-product', { detail: trigger.dataset.openProduct }));
  });
  grid.addEventListener('keydown', (ev) => {
    if (ev.key !== 'Enter' && ev.key !== ' ') return;
    const trigger = ev.target.closest('[data-open-product]');
    if (!trigger || ev.target.closest('button')) return;
    ev.preventDefault();
    window.dispatchEvent(new CustomEvent('meridian:open-product', { detail: trigger.dataset.openProduct }));
  });
}

/* -------------------------------------------------------------------------- */
/* UI controller: header, menu, product panel, bag drawer                     */
/* -------------------------------------------------------------------------- */

class UI {
  constructor(bag) {
    this.bag = bag;
    this.header = qs('[data-header]');
    this.menu = qs('[data-mobile-menu]');
    this.menuToggle = qs('[data-menu-toggle]');
    this.productModal = qs('[data-product-modal]');
    this.bagModal = qs('[data-bag-modal]');
    this.lastFocus = null;
    this.qty = 1;
    this.selectedId = content.products[0].id;
    this.panelId = content.products[0].id;
  }

  render() {
    this.wireHeader();
    this.wireMenu();
    this.wireProductPanel();
    this.wireBag();
    this.wireTrade();
    this.renderBag();
    this.renderVariants();
  }

  /* ---------------- header ---------------- */

  wireHeader() {
    const sync = () => {
      const solid = window.scrollY > window.innerHeight * 0.7;
      this.header.classList.toggle('is-solid', solid);
    };
    sync();
    window.addEventListener('scroll', sync, { passive: true });
  }

  /* ---------------- mobile menu ---------------- */

  wireMenu() {
    this.menuRelease = null;

    const open = () => {
      this.lastFocus = document.activeElement;
      this.menu.hidden = false;
      document.body.classList.add('menu-open', 'is-locked');
      this.menuToggle.setAttribute('aria-expanded', 'true');
      this.menuToggle.setAttribute('aria-label', 'Close menu');
      this.menuRelease = trapFocus(this.menu);
    };

    const close = ({ focusToggle = true } = {}) => {
      if (this.menu.hidden) return;
      this.menu.hidden = true;
      document.body.classList.remove('menu-open', 'is-locked');
      this.menuToggle.setAttribute('aria-expanded', 'false');
      this.menuToggle.setAttribute('aria-label', 'Open menu');
      if (this.menuRelease) this.menuRelease();
      this.menuRelease = null;
      if (focusToggle) (this.lastFocus || this.menuToggle).focus();
    };

    this.closeMenu = close;

    this.menuToggle.addEventListener('click', () => {
      if (this.menu.hidden) open();
      else close();
    });

    this.menu.addEventListener('click', (ev) => {
      const link = ev.target.closest('a[href^="#"]');
      if (!link) return;
      close({ focusToggle: false });
    });

    document.addEventListener('keydown', (ev) => {
      if (ev.key !== 'Escape') return;
      if (!this.menu.hidden) close();
      else if (!this.productModal.hidden) this.closeProduct();
      else if (!this.bagModal.hidden) this.closeBag();
    });
  }

  /* ---------------- product panel ---------------- */

  wireProductPanel() {
    this.productModal.addEventListener('click', (ev) => {
      if (ev.target.closest('[data-modal-close]')) this.closeProduct();
    });

    window.addEventListener('meridian:open-product', (ev) => {
      this.openProduct(ev.detail);
    });

    qs('[data-qty-up]').addEventListener('click', () => this.setQty(this.qty + 1));
    qs('[data-qty-down]').addEventListener('click', () => this.setQty(this.qty - 1));
    qs('[data-pm-add]').addEventListener('click', () => {
      this.bag.add(this.panelId, this.qty);
      this.setQty(1);
      this.closeProduct();
      this.openBag();
      toast(`${this.productById(this.panelId).name} added to the bag`);
    });
  }

  productById(id) {
    return content.products.find((p) => p.id === id) || content.products[0];
  }

  setQty(n) {
    this.qty = Math.max(1, Math.min(9, n));
    qs('[data-qty-value]').textContent = String(this.qty);
    qs('[data-qty-down]').disabled = this.qty <= 1;
    qs('[data-qty-up]').disabled = this.qty >= 9;
  }

  renderVariants() {
    const list = qs('[data-pm-variants]');
    list.replaceChildren();
    for (const p of content.products) {
      const chip = el('span', { class: 'variant-chip', style: `background:${p.swatch}`, 'aria-hidden': 'true' });
      const btn = el('button', {
        class: 'variant-option',
        type: 'button',
        'aria-pressed': String(p.id === this.panelId),
        dataset: { variant: p.id },
      }, [chip, el('span', { text: p.name })]);
      btn.addEventListener('click', () => this.selectVariant(p.id));
      list.append(el('li', {}, [btn]));
    }
  }

  selectVariant(id) {
    const p = this.productById(id);
    this.panelId = id;
    this.selectedId = id;
    qs('[data-pm-title]').textContent = p.name;
    qs('[data-pm-price]').textContent = money(p.price);
    qs('[data-pm-blurb]').textContent = p.blurb;
    const img = qs('[data-pm-image]');
    img.src = `./${p.image}`;
    img.alt = p.alt;

    const specs = qs('[data-pm-specs]');
    specs.replaceChildren();
    const rows = [
      ...content.sharedSpecs,
      { label: 'Dial', value: p.swatchName },
      { label: 'Case finish', value: p.caseFinish },
      { label: 'Strap', value: p.strap },
    ];
    for (const row of rows) {
      specs.append(el('div', {}, [el('dt', { text: row.label }), el('dd', { text: row.value })]));
    }

    qsa('[data-variant]').forEach((b) => {
      b.setAttribute('aria-pressed', String(b.dataset.variant === id));
    });
    qsa('.product-card').forEach((c) => {
      c.classList.toggle('is-selected', c.dataset.productId === id);
    });
    this.setQty(1);
  }

  openProduct(id) {
    this.lastFocus = document.activeElement;
    this.selectVariant(id);
    this.productModal.hidden = false;
    document.body.classList.add('is-locked');
    this.productRelease = trapFocus(this.productModal, { initial: qs('.modal-close', this.productModal) });
  }

  closeProduct() {
    if (this.productModal.hidden) return;
    this.productModal.hidden = true;
    document.body.classList.remove('is-locked');
    if (this.productRelease) this.productRelease();
    this.productRelease = null;
    if (this.lastFocus) this.lastFocus.focus();
  }

  /* ---------------- bag drawer ---------------- */

  wireBag() {
    qs('[data-bag-open]').addEventListener('click', () => this.openBag());
    this.bagModal.addEventListener('click', (ev) => {
      if (ev.target.closest('[data-bag-dismiss]')) this.closeBag();
    });

    qs('[data-bag-reset]').addEventListener('click', () => {
      this.bag.reset();
      toast('Bag reset');
    });

    qs('[data-demo-checkout]').addEventListener('click', () => this.showDemoSummary());
    qs('[data-demo-close]').addEventListener('click', () => {
      const s = qs('[data-demo-summary]');
      s.hidden = true;
      qs('[data-demo-checkout]').focus();
    });

    // quick add from the grid
    qs('[data-product-grid]').addEventListener('click', (ev) => {
      const btn = ev.target.closest('[data-quick-add]');
      if (!btn) return;
      const p = this.productById(btn.dataset.quickAdd);
      this.bag.add(p.id, 1);
      this.selectedId = p.id;
      qsa('.product-card').forEach((c) => c.classList.toggle('is-selected', c.dataset.productId === p.id));
      toast(`${p.name} added to the bag`);
    });

    this.bagBody = qs('[data-bag-body]');
    this.bagList = qs('[data-bag-list]');
    this.bagEmpty = qs('[data-bag-empty]');
    this.bagFoot = qs('[data-bag-foot]');

    // One delegated listener keeps the row controls working across re-renders.
    this.bagList.addEventListener('click', (ev) => {
      const inc = ev.target.closest('[data-inc]');
      const dec = ev.target.closest('[data-dec]');
      const remove = ev.target.closest('[data-remove]');
      if (inc) {
        const current = this.lineQty(inc.dataset.inc);
        this.bag.setQty(inc.dataset.inc, current + 1);
      } else if (dec) {
        const current = this.lineQty(dec.dataset.dec);
        if (current <= 1) this.bag.remove(dec.dataset.dec);
        else this.bag.setQty(dec.dataset.dec, current - 1);
      } else if (remove) {
        this.bag.remove(remove.dataset.remove);
      }
    });
  }

  lineQty(id) {
    const line = this.bag.lines().find((l) => l.product.id === id);
    return line ? line.qty : 0;
  }

  openBag() {
    if (this.menu && !this.menu.hidden) this.closeMenu({ focusToggle: false });
    this.lastFocus = document.activeElement;
    this.bagModal.hidden = false;
    document.body.classList.add('is-locked');
    this.bagRelease = trapFocus(this.bagModal, { initial: qs('.modal-close', this.bagModal) });
  }

  closeBag() {
    if (this.bagModal.hidden) return;
    this.bagModal.hidden = true;
    document.body.classList.remove('is-locked');
    if (this.bagRelease) this.bagRelease();
    this.bagRelease = null;
    if (this.lastFocus) this.lastFocus.focus();
  }

  renderBag() {
    const lines = this.bag.lines();
    const count = this.bag.count();

    qsa('[data-bag-count]').forEach((n) => {
      n.textContent = String(count);
    });
    qsa('[data-bag-count-sr]').forEach((n) => {
      n.textContent = `Bag, ${count} ${count === 1 ? 'item' : 'items'}`;
    });

    this.bagEmpty.hidden = lines.length > 0;
    this.bagList.replaceChildren();

    for (const line of lines) {
      const p = line.product;
      const item = el('li', { class: 'bag-item' }, [
        el('img', { src: `./${p.image}`, alt: '', width: 84, height: 105, loading: 'lazy' }),
        el('div', { class: 'bag-item-body' }, [
          el('p', { class: 'bag-item-name', text: p.name }),
          el('p', { class: 'bag-item-price', text: `${money(p.price)} each` }),
          el('div', { class: 'bag-item-controls' }, [
            el('button', { type: 'button', dataset: { dec: p.id }, 'aria-label': `Decrease quantity of ${p.name}`, text: '−' }),
            el('span', { class: 'bag-item-qty', text: String(line.qty) }),
            el('button', { type: 'button', dataset: { inc: p.id }, 'aria-label': `Increase quantity of ${p.name}`, text: '+' }),
            el('button', { type: 'button', dataset: { remove: p.id }, 'aria-label': `Remove ${p.name} from bag`, text: S.remove }),
          ]),
        ]),
      ]);
      item.append(el('span', { class: 'bag-item-line', text: money(line.line) }));
      this.bagList.append(item);
    }

    const subtotal = this.bag.subtotal();
    qs('[data-total-subtotal]').textContent = money(subtotal);
    qs('[data-total-grand]').textContent = money(subtotal);
    this.bagFoot.style.display = lines.length ? '' : 'none';
    if (!lines.length) qs('[data-demo-summary]').hidden = true;
  }

  showDemoSummary() {
    const lines = this.bag.lines();
    if (!lines.length) return;
    const list = qs('[data-demo-lines]');
    list.replaceChildren();
    for (const l of lines) {
      list.append(el('li', {}, [
        el('span', { text: `${l.product.name} × ${l.qty}` }),
        el('span', { text: money(l.line) }),
      ]));
    }
    qs('[data-demo-total]').textContent = `Demo total ${money(this.bag.subtotal())} · nothing charged`;
    const panel = qs('[data-demo-summary]');
    panel.hidden = false;
    panel.focus();
  }

  /* ---------------- trade-in form ---------------- */

  wireTrade() {
    const form = qs('[data-trade-form]');
    if (!form) return;
    const result = qs('[data-trade-result]');

    const setError = (name, message) => {
      const box = qs(`[data-error-for="${name}"]`);
      if (box) {
        box.textContent = message || '';
        box.hidden = !message;
        box.closest('.field').classList.toggle('has-error', Boolean(message));
      }
      const field = qs(`[name="${name}"]`, form);
      if (field) {
        if (message) field.setAttribute('aria-invalid', 'true');
        else field.removeAttribute('aria-invalid');
      }
    };

    const validate = () => {
      let firstBad = null;
      const brand = form.brand.value.trim();
      const model = form.model.value.trim();
      const condition = form.condition.value;

      if (brand.length < 2) {
        setError('brand', 'Enter the brand name.');
        firstBad = firstBad || form.brand;
      } else setError('brand', '');

      if (model.length < 2) {
        setError('model', 'Enter the model name.');
        firstBad = firstBad || form.model;
      } else setError('model', '');

      if (!condition) {
        setError('condition', 'Choose the current condition.');
        firstBad = firstBad || form.condition;
      } else setError('condition', '');

      return firstBad;
    };

    form.addEventListener('submit', (ev) => {
      ev.preventDefault();
      const bad = validate();
      if (bad) {
        bad.focus();
        return;
      }
      const summary = qs('[data-trade-summary]');
      summary.replaceChildren();
      const rows = [
        ['Brand', form.brand.value.trim()],
        ['Model', form.model.value.trim()],
        ['Condition', form.condition.value],
        ['Photo', form.photo.files && form.photo.files[0] ? `${form.photo.files[0].name} (previewed locally)` : 'None attached'],
      ];
      for (const [k, v] of rows) {
        summary.append(el('div', {}, [el('dt', { text: k }), el('dd', { text: v })]));
      }
      result.hidden = false;
      result.focus();
    });

    form.addEventListener('input', (ev) => {
      const name = ev.target.name;
      if (name && ['brand', 'model', 'condition'].includes(name)) setError(name, '');
    });

    form.addEventListener('reset', () => {
      ['brand', 'model', 'condition', 'photo'].forEach((n) => setError(n, ''));
      result.hidden = true;
      clearPhoto();
    });

    qs('[data-trade-reset]').addEventListener('click', () => {
      form.reset();
      form.brand.focus();
    });

    /* photo preview — read locally with FileReader, never uploaded */
    const preview = qs('[data-photo-preview]');
    const previewImg = qs('[data-photo-image]');
    const previewCaption = qs('[data-photo-caption]');

    function clearPhoto() {
      if (previewImg.src && previewImg.src.startsWith('blob:')) URL.revokeObjectURL(previewImg.src);
      previewImg.removeAttribute('src');
      preview.hidden = true;
      previewCaption.textContent = '';
    }

    form.photo.addEventListener('change', () => {
      const file = form.photo.files && form.photo.files[0];
      setError('photo', '');
      if (!file) {
        clearPhoto();
        return;
      }
      if (!file.type.startsWith('image/')) {
        clearPhoto();
        setError('photo', 'Choose an image file (JPG, PNG or WebP).');
        return;
      }
      if (file.size > 12 * 1024 * 1024) {
        clearPhoto();
        setError('photo', 'That image is larger than 12 MB. Choose a smaller file.');
        return;
      }
      clearPhoto();
      const objectUrl = URL.createObjectURL(file);
      previewImg.onload = () => {
        preview.hidden = false;
      };
      previewImg.src = objectUrl;
      previewImg.alt = `Preview of ${file.name}`;
      previewCaption.textContent = `${file.name} — previewed in this browser only, never uploaded.`;
    });

    this.clearPhoto = clearPhoto;
  }
}

function onBagChange(bag, { force } = {}) {
  const ui = window.__meridianUI;
  if (!ui) return;
  ui.renderBag();
  if (force) qsa('.product-card').forEach((c) => c.classList.remove('is-selected'));
}

let toastTimer = null;
function toast(message) {
  const node = qs('[data-bag-toast]');
  if (!node) return;
  node.textContent = message;
  node.hidden = false;
  requestAnimationFrame(() => node.classList.add('is-shown'));
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => {
    node.classList.remove('is-shown');
    setTimeout(() => {
      node.hidden = true;
    }, 320);
  }, 2600);
}

/* -------------------------------------------------------------------------- */
/* cinematic stage                                                            */
/* -------------------------------------------------------------------------- */

function startStage() {
  const track = qs('[data-stage-track]');
  const canvas = qs('[data-stage-canvas]');
  const poster = qs('[data-stage-poster]');
  if (!track || !canvas || !poster) return;

  const beats = qsa('.beat');
  const progressLabel = qs('[data-stage-progress]');
  const scrollCue = qs('[data-scroll-cue]');

  const player = new StagePlayer({
    track,
    canvas,
    poster,
    onProgress: ({ frame, total, beat, progress }) => {
      if (progressLabel && beat) {
        progressLabel.textContent = `${beat.label} · ${String(frame + 1).padStart(3, '0')}/${total}`;
      }
      if (scrollCue) scrollCue.classList.toggle('is-hidden', progress > 0.04);
    },
    onBeatChange: (beat) => {
      if (!beat) return;
      for (const node of beats) {
        node.classList.toggle('is-active', node.dataset.beat === beat.id);
      }
      document.documentElement.dataset.beat = beat.id;
    },
  });

  // exposed for the local inspection harness only
  window.__stage = player;

  // reduced motion: composed still, no canvas, all beats visible in normal flow
  if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
    beats.forEach((b) => b.classList.add('is-active'));
    if (scrollCue) scrollCue.classList.add('is-hidden');
    if (progressLabel) progressLabel.textContent = '';
  } else {
    player.init();
  }

  const skip = qs('[data-skip-story]');
  if (skip) {
    skip.addEventListener('click', () => {
      const target = qs('#collection');
      if (!target) return;
      target.scrollIntoView({ behavior: 'smooth', block: 'start' });
    });
  }
}

/* -------------------------------------------------------------------------- */
/* anchor scrolling that respects the fixed header                            */
/* -------------------------------------------------------------------------- */

function wireAnchors() {
  document.addEventListener('click', (ev) => {
    const link = ev.target.closest('a[href^="#"]');
    if (!link) return;
    const id = link.getAttribute('href');
    if (!id || id === '#') return;
    const target = document.querySelector(id);
    if (!target) return;
    ev.preventDefault();
    // measure the real header rather than trusting a token: the offset must hold
    // at every breakpoint, including the shorter mobile bar
    const header = qs('[data-header]');
    const pad = (header ? header.getBoundingClientRect().height : 84) + 16;
    const y = Math.max(0, target.getBoundingClientRect().top + window.scrollY - pad);
    const reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    window.scrollTo({ top: y, behavior: reduced ? 'auto' : 'smooth' });
    if (history.replaceState) history.replaceState(null, '', id);
  });
}

/* -------------------------------------------------------------------------- */

function start() {
  boot();
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', start, { once: true });
} else {
  start();
}
