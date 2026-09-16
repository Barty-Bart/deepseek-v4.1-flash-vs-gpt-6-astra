/** Small shared DOM helpers. */

export const qs = (sel, root = document) => root.querySelector(sel);
export const qsa = (sel, root = document) => Array.from(root.querySelectorAll(sel));

export function el(tag, props = {}, children = []) {
  const node = document.createElement(tag);
  for (const [k, v] of Object.entries(props)) {
    if (v === null || v === undefined || v === false) continue;
    if (k === 'class') node.className = v;
    else if (k === 'html') node.innerHTML = v;
    else if (k === 'text') node.textContent = v;
    else if (k === 'dataset') Object.assign(node.dataset, v);
    else if (k.startsWith('on') && typeof v === 'function') node.addEventListener(k.slice(2), v);
    else node.setAttribute(k, v === true ? '' : String(v));
  }
  for (const c of [].concat(children)) {
    if (c === null || c === undefined || c === false) continue;
    node.append(c instanceof Node ? c : document.createTextNode(String(c)));
  }
  return node;
}

/** Focus trap used by both dialogs. */
export function trapFocus(container, { initial } = {}) {
  const selectors =
    'a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])';
  const list = () => Array.from(container.querySelectorAll(selectors)).filter((n) => n.offsetParent !== null);
  const first = initial || list()[0];
  if (first) first.focus();
  const onKey = (ev) => {
    if (ev.key !== 'Tab') return;
    const items = list();
    if (!items.length) return;
    const firstItem = items[0];
    const lastItem = items[items.length - 1];
    if (ev.shiftKey && document.activeElement === firstItem) {
      ev.preventDefault();
      lastItem.focus();
    } else if (!ev.shiftKey && document.activeElement === lastItem) {
      ev.preventDefault();
      firstItem.focus();
    }
  };
  container.addEventListener('keydown', onKey);
  return () => container.removeEventListener('keydown', onKey);
}
